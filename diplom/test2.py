import osmnx as ox
import networkx as nx
import rtree.index
from math import sqrt
import folium

cur_typ = ''

def CreateBoxIndex(G):
    idx = rtree.index.Index()
    for i, (node_id, data) in enumerate(G.nodes(data=True)):
        x, y = data['x'], data['y']
        idx.insert(node_id, (x, y, x, y))
    return idx


def GetEdgesQuiet(G, quiet_nodes):
    G_quiet = G.copy()
    quiet_set = set(quiet_nodes)
    
    for u, v, key, data in G_quiet.edges(keys=True, data=True):
        length = data['length']
    
        u_quiet = u in quiet_set
        v_quiet = v in quiet_set
        
        if u_quiet and v_quiet:
            data[cur_typ] = length * 0.1
        elif u_quiet or v_quiet:
            data[cur_typ] = length * 0.5
        else:
            data[cur_typ] = length
    
    return G_quiet


def CalcOrientBox(center, dx, dy, radius, l, r):
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


def Find_BoxNodes(G, box_index, center, dx, dy, radius, l, r):
    quiet_nodes = []
    box = CalcOrientBox(center, dx, dy, radius, l, r)
    box_node = list(box_index.intersection(box))
    for node_id in box_node:
        if G.nodes[node_id].get(cur_typ):
            quiet_nodes.append(node_id)
    return quiet_nodes


def GetNeedRoute(G, box_index, route, distance, side):
    quiet_nodes = []
    radius = distance / 2
    if(radius > 2000): radius = 2000
    elif(radius < 400): radius = 400
    for i in range(len(route)-1):
        cur_node = G.nodes[route[i]]
        next_node = G.nodes[route[i+1]]
        dx = next_node['x'] - cur_node['x']
        dy = next_node['y'] - cur_node['y']
        length = sqrt(dx*dx + dy*dy)
        if length > 0:
            dx /= length
            dy /= length
        if side == "right":
            search_nodes = Find_BoxNodes(G, box_index, cur_node, dx, dy, radius, 0, 1)
        else:
            search_nodes = Find_BoxNodes(G, box_index, cur_node, dx, dy, radius, -1, 0)
        quiet_nodes.extend(search_nodes)
    return list(set(quiet_nodes))


def SelectSide(G, box_index, route, distance):
    right_side = GetNeedRoute(G, box_index, route, distance, "right")
    left_side = GetNeedRoute(G, box_index, route, distance, "left")
    if len(right_side) > len(left_side):
        return right_side
    else:
        return left_side


def FindNeedLenght(G, route):
    dlina = 0
    for node in range(len(route)-1):
        u, v = route[node], route[node+1]
        edge_data = G.get_edge_data(u, v)
        dlina += float(edge_data[min(edge_data.keys())].get('length', 0.0))
    return dlina
        

def SelectRoute(G, box_index, route, distance):
    for u, v, key, data in G.edges(keys=True, data=True):
        if cur_typ in data:
            data[cur_typ] = float(data[cur_typ])
    cur_side_nodes = SelectSide(G, box_index, route, distance)
    G_cur = GetEdgesQuiet(G, cur_side_nodes)
    cur_route = ox.shortest_path(G_cur, node1, node2, weight=cur_typ)
    cur_distance = int(FindNeedLenght(G_cur, cur_route))
    print(f"Длина {cur_typ} маршрута: {cur_distance} м")
    return cur_route, cur_distance


def GetRouteCoordinate(G, route):
    coords = []
    for node in route:
        node_data = G.nodes[node]
        coords.append([node_data['y'], node_data['x']])
    return coords


def UserInput():
    print("Введите координаты точки начала маршрута (в формате: широта, долгота): ")
    point1 = input().split(',')
    lat1 = float(point1[0].strip())
    lon1 = float(point1[1].strip())
    print("Введите координаты точки конца маршрута (в формате: широта, долгота): ")
    point2 = input().split(',')
    lat2 = float(point2[0].strip())
    lon2 = float(point2[1].strip())
    return (lat1, lon1), (lat2, lon2)


file_path = 'D:\\project\\diplom\\graphs\\novosibirsk_graph.graphml'
G = ox.load_graphml(file_path)
box_index = CreateBoxIndex(G)

#start_point, end_point = UserInput()
start_point = (55.047929, 82.872188)
end_point = (55.047929, 82.872188)
#end_point = (55.062517, 82.829405)
node1 = ox.distance.nearest_nodes(G, start_point[1], start_point[0])
node2 = ox.distance.nearest_nodes(G, end_point[1], end_point[0])
route = ox.shortest_path(G, node1, node2, weight='length')
distance = int(nx.shortest_path_length(G, node1, node2, weight='length'))
print(f"Длина стандартного маршрута: {distance} м")

cur_typ = 'quiet'
quiet_route, quiet_distance = SelectRoute(G, box_index, route, distance)
cur_typ = 'beautiful'
beautiful_route, beautiful_distance = SelectRoute(G, box_index, route, distance)

center_lat = (start_point[0] + end_point[0]) / 2
center_lon = (start_point[1] + end_point[1]) / 2

m = folium.Map(location=[center_lat, center_lon], zoom_start=14)

standard_coords = GetRouteCoordinate(G, route)
quiet_coords = GetRouteCoordinate(G, quiet_route)
beautiful_coords = GetRouteCoordinate(G, beautiful_route)

standard_group = folium.FeatureGroup(name='Кратчайший маршрут', show=True)
quiet_group = folium.FeatureGroup(name='Тихий маршрут', show=True)
beautiful_group = folium.FeatureGroup(name='Красивый маршрут', show=True)

folium.PolyLine(standard_coords, color='blue', weight=5, 
         popup=f'{distance}м').add_to(standard_group)
folium.PolyLine(quiet_coords, color='green', weight=5,
         popup=f'{quiet_distance}м').add_to(quiet_group)
folium.PolyLine(beautiful_coords, color='red', weight=5,
         popup=f'{beautiful_distance}м').add_to(beautiful_group)

folium.Marker([start_point[0], start_point[1]], popup='Начало', 
              icon=folium.Icon(color='green')).add_to(m)
folium.Marker([end_point[0], end_point[1]], popup='Конец', 
              icon=folium.Icon(color='red')).add_to(m)

standard_group.add_to(m)
quiet_group.add_to(m)
beautiful_group.add_to(m)
folium.LayerControl(collapsed=False).add_to(m)

legend = '''
<div id="route-legend" style="position: fixed; 
     bottom: 20px; right: 20px; width: 220px; z-index: 9999;
     font-family: Arial, sans-serif; background-color: white;
     border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
     padding: 12px 15px; opacity: 0.95;">
     
     <div style="margin-bottom: 10px; font-size: 14px; color: #333;">
         <b>Маршруты:</b>
     </div>
     
     <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <span style="color: blue; font-size: 20px; line-height: 1; margin-left: 5px; margin-right: 12px;">━━━</span>
        <span style="font-size: 13px;"><b>Кратчайший</b></span>
     </div>
     
     <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <span style="color: green; font-size: 20px; line-height: 1; margin-left: 5px; margin-right: 12px;">━━━</span>
        <span style="font-size: 13px;"><b>Тихий</b></span>
     </div>
     
     <div style="display: flex; align-items: center;">
        <span style="color: red; font-size: 20px; line-height: 1; margin-left: 5px; margin-right: 12px;">━━━</span>
        <span style="font-size: 13px;"><b>Красивый</b></span>
     </div>
</div>
'''
m.get_root().html.add_child(folium.Element(legend))
m.save('D:\\project\\diplom\\graphs\\folium_map.html')