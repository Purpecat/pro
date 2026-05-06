import osmnx as ox
import networkx as nx
import rtree.index
from math import sqrt

class RouteBuilder:
    def __init__(self, graph_file):
        print("Загрузка графа...")
        self.G = ox.load_graphml(graph_file)
        self.box_index = self._create_index()
        print(f"Граф загружен. Узлов: {len(self.G.nodes)}")
    
    
    def _create_index(self):
        idx = rtree.index.Index()
        for node_id, data in self.G.nodes(data=True):
            x, y = data['x'], data['y']
            idx.insert(node_id, (x, y, x, y))
        return idx
    
    
    def _calc_orient_box(self, center, dx, dy, radius, l, r):
        center_x, center_y = center['x'], center['y']
        width_x = -dy 
        width_y = dx
        corn = []
        for vverx in [0, 1]:
            for side in [l, r]:
                vec_x = (vverx * radius * dx + side * radius * width_x) / 111000
                vec_y = (vverx * radius * dy + side * radius * width_y) / 111000
                corn.append((center_x + vec_x, center_y + vec_y))
        x = [x[0] for x in corn]
        y = [x[1] for x in corn]
        return (min(x), min(y), max(x), max(y))
    
    
    def _find_box_nodes(self, center, dx, dy, radius, l, r, route_type):
        quiet_nodes = []
        box = self._calc_orient_box(center, dx, dy, radius, l, r)
        box_node = list(self.box_index.intersection(box))
        for node_id in box_node:
            if self.G.nodes[node_id].get(route_type):
                quiet_nodes.append(node_id)
        return quiet_nodes
    
    
    def _get_need_route(self, route, distance, side, route_type):
        quiet_nodes = []
        radius = distance / 2
        if radius > 2000: 
            radius = 2000
        elif radius < 400: 
            radius = 400
            
        for i in range(len(route)-1):
            cur_node = self.G.nodes[route[i]]
            next_node = self.G.nodes[route[i+1]]
            dx = next_node['x'] - cur_node['x']
            dy = next_node['y'] - cur_node['y']
            length = sqrt(dx*dx + dy*dy)
            if length > 0:
                dx /= length
                dy /= length
            if side == "right":
                search_nodes = self._find_box_nodes(cur_node, dx, dy, radius, 0, 1, route_type)
            else:
                search_nodes = self._find_box_nodes(cur_node, dx, dy, radius, -1, 0, route_type)
            quiet_nodes.extend(search_nodes)
        return list(set(quiet_nodes))
    
    
    def _select_side(self, route, distance, route_type):
        right_side = self._get_need_route(route, distance, "right", route_type)
        left_side = self._get_need_route(route, distance, "left", route_type)
        return right_side if len(right_side) > len(left_side) else left_side
    
    
    def _get_edges_quiet(self, quiet_nodes, route_type):
        G_quiet = self.G.copy()
        quiet_set = set(quiet_nodes)
        
        for u, v, key, data in G_quiet.edges(keys=True, data=True):
            length = data['length']
            u_quiet = u in quiet_set
            v_quiet = v in quiet_set
            
            if u_quiet and v_quiet:
                data[route_type] = length * 0.1
            elif u_quiet or v_quiet:
                data[route_type] = length * 0.5
            else:
                data[route_type] = length
        
        return G_quiet
    
    
    def _find_need_length(self, G, route):
        dlina = 0
        for node in range(len(route)-1):
            u, v = route[node], route[node+1]
            edge_data = G.get_edge_data(u, v)
            dlina += float(edge_data[min(edge_data.keys())].get('length', 0.0))
        return dlina
    
    
    def _select_route(self, node1, node2, standard_route, distance, route_type):
        side_nodes = self._select_side(standard_route, distance, route_type)
        G_special = self._get_edges_quiet(side_nodes, route_type)
        special_route = ox.shortest_path(G_special, node1, node2, weight=route_type)
        special_distance = self._find_need_length(G_special, special_route)
        
        return special_route, special_distance
    
    
    def get_route_coordinates(self, route):
        coords = []
        for node in route:
            node_data = self.G.nodes[node]
            coords.append([node_data['y'], node_data['x']])
        return coords


    def _calculate_duration(self, distance_meters, route_type):
        speeds = {
            'standard': 5,
            'quiet': 4,
            'beautiful': 4
        }
        speed_kmh = speeds.get(route_type)
        distance_km = distance_meters / 1000.0
        min = int((distance_km / speed_kmh) * 60)
        return min
    
    
    def build_routes(self, start_point, end_point):
        node1 = ox.distance.nearest_nodes(self.G, start_point[1], start_point[0])
        node2 = ox.distance.nearest_nodes(self.G, end_point[1], end_point[0])
        
        standard_route = ox.shortest_path(self.G, node1, node2, weight='length')
        standard_distance = int(nx.shortest_path_length(self.G, node1, node2, weight='length'))
        print(f"Кратчайший маршрут: {standard_distance} м")
        
        quiet_route, quiet_distance = self._select_route(
            node1, node2, standard_route, standard_distance, 'quiet'
        )
        print(f"Тихий маршрут: {quiet_distance} м")
        
        beautiful_route, beautiful_distance = self._select_route(
            node1, node2, standard_route, standard_distance, 'beautiful'
        )
        print(f"Красивый маршрут: {beautiful_distance} м")
        
        standard_duration = self._calculate_duration(standard_distance, 'standard')
        quiet_duration = self._calculate_duration(quiet_distance, 'quiet')
        beautiful_duration = self._calculate_duration(beautiful_distance, 'beautiful')
        
        result = {
            'standard': {
                'name': 'Оптимальный',
                'coords': self.get_route_coordinates(standard_route),
                'distance': standard_distance,
                'duration': standard_duration,
                'color': 'blue'
            },
            'quiet': {
                'name': 'Тихий',
                'coords': self.get_route_coordinates(quiet_route),
                'distance': int(quiet_distance),
                'duration': quiet_duration,
                'color': 'green'
            },
            'beautiful': {
                'name': 'Красивый',
                'coords': self.get_route_coordinates(beautiful_route),
                'distance': int(beautiful_distance),
                'duration': beautiful_duration,
                'color': 'red'
            }
        }
        
        return result