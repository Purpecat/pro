import osmnx as ox
import geopandas as gpd
import networkx as nx
from shapely.geometry import Point
import rtree.index

ox.settings.overpass_url = 'https://overpass.kumi.systems/api/interpreter'
place = "Новосибирск, Россия"
file_path = 'D:\\project\\diplom\\graphs\\novosibirsk_graph.graphml'


def CreateBoxIndex(G):
    idx = rtree.index.Index()
    for i, (node_id, data) in enumerate(G.nodes(data=True)):
        x, y = data['x'], data['y']
        idx.insert(node_id, (x, y, x, y))
    return idx


def GetNeedNodes(G, gdf, box_index):
    nodes_quiet = set()
    for ind, object in gdf.iterrows():
        geom = object.geometry
        geo_type = geom.geom_type
        if geo_type in ['Polygon', 'MultiPolygon', 'LineString', 'MultiLineString']:
            bbox = geom.bounds
        elif geo_type == 'Point':
            bbox = (geom.x, geom.y, geom.x, geom.y)
        else:
            continue
        box_node = list(box_index.intersection(bbox))
        for node_id in box_node:
            node_data = G.nodes[node_id]
            node_point = Point(node_data['x'], node_data['y'])
            if geo_type == 'Point':
                nodes_quiet.add(node_id)
            elif geo_type in ['Polygon', 'MultiPolygon']:
                if geom.contains(node_point):
                    nodes_quiet.add(node_id)
            elif geo_type in ['LineString', 'MultiLineString']:
                buffer_line = geom.buffer(50 / 111000)
                if buffer_line.contains(node_point):
                    nodes_quiet.add(node_id)
    return list(nodes_quiet)


def MakeGraph(G, tags, type):
    gdf = ox.features.features_from_place(place, tags)

    if len(gdf) > 0:
        box_index = CreateBoxIndex(G)
        quiet_nodes = GetNeedNodes(G, gdf, box_index)
        print(f"{type} узлов: {len(quiet_nodes)}")

        quiet_added = 0
        for node_id in quiet_nodes:
            if type not in G.nodes[node_id]:
                G.nodes[node_id][type] = True
                quiet_added += 1
        print(f"добавлено {type} узлов: {quiet_added}")


try:
    G = ox.graph_from_place(place, network_type='walk')
except Exception as e:
    print(f"ошибка {e}")
    raise

beautiful_tags = {
    'tourism': ['museum', 'gallery', 'attraction', 'viewpoint', 'artwork', 'monument'],
    'historic': True,
    'man_made': ['quay', 'pier', 'bridge'],
    'amenity': ['fountain'],
    'leisure': ['park'],
    'natural' : ['water', 'beach']
}

quiet_tags = {
    'leisure': ['park', 'garden', 'playground'],
    'highway': ['path', 'pedestrian'],
    'natural' : ['tree', 'tree_row', 'wood', 'grassland', 'scrub']
}


MakeGraph(G, quiet_tags, 'quiet')
MakeGraph(G, beautiful_tags, 'beautiful')
ox.save_graphml(G, file_path, gephi=False, encoding='utf-8')
print("граф сохранён")