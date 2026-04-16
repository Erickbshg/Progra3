import networkx as nx
import math
import unicodedata

def normalize_text(text):
    """Removes accents and converts to lowercase for robust matching."""
    text = unicodedata.normalize('NFD', text)
    text = "".join([c for c in text if unicodedata.category(c) != 'Mn'])
    return text.lower().strip()

class WazeEngine:
    def __init__(self):
        self.graph = nx.Graph()
        self.nodes = {}  # id: (x, y, name)
        
        # Edge id tuple (min_u, max_v) mapped to incident type constant
        self.active_incidents = {} 
        self.setup_map()

    def setup_map(self):
        """Creates a fictional city graph."""
        # Define nodes: (id, x, y, name)
        # X, Y range from 0 to 800 for the canvas
        raw_nodes = [
            (0, 100, 100, "Residencial A"),
            (1, 300, 100, "Parque Central"),
            (2, 500, 100, "Centro Cívico"),
            (3, 700, 100, "Shell Station"),
            (4, 100, 300, "Casa"),
            (5, 300, 310, "Intersección Sur"),
            (6, 450, 300, "Plaza Mayor"),
            (7, 700, 300, "Mercado"),
            (8, 100, 500, "Biblioteca"),
            (9, 300, 550, "Gimnasio"),
            (10, 500, 500, "Hospital"),
            (11, 750, 500, "Estadio"),
            (12, 100, 700, "Zona Residencial B"),
            (13, 300, 750, "Restaurante"),
            (14, 550, 700, "Oficinas Trabajo"),
            (15, 750, 750, "Salida Autopista"),
            (16, 400, 150, "Intersección Norte"),
            (17, 600, 400, "Avenida Principal"),
            (18, 200, 400, "Cruce Secundario"),
            (19, 400, 600, "Mirador")
        ]

        for id, x, y, name in raw_nodes:
            self.nodes[id] = {"x": x, "y": y, "name": name}
            self.graph.add_node(id, pos=(x, y), name=name)

        # Define edges (road segments)
        # Weights are Euclidean distances by default
        edges = [
            (0, 1), (1, 2), (2, 3), (0, 4), (1, 16), (2, 16), (3, 7),
            (4, 5), (5, 6), (6, 7), (4, 8), (5, 18), (6, 17), (7, 11),
            (8, 9), (9, 10), (10, 11), (8, 12), (9, 19), (10, 19), (11, 15),
            (12, 13), (13, 14), (14, 15), (14, 10), (5, 9), (1, 5), (16, 6),
            (18, 9), (17, 10), (18, 8), (17, 7)
        ]

        for u, v in edges:
            dist = self.calculate_distance(u, v)
            self.graph.add_edge(u, v, weight=dist, original_weight=dist)

    def calculate_distance(self, u, v):
        pos_u = (self.nodes[u]["x"], self.nodes[u]["y"])
        pos_v = (self.nodes[v]["x"], self.nodes[v]["y"])
        return math.sqrt((pos_u[0] - pos_v[0])**2 + (pos_u[1] - pos_v[1])**2)

    def get_shortest_path(self, start_id, end_id):
        try:
            path = nx.dijkstra_path(self.graph, start_id, end_id, weight='weight')
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def toggle_incident(self, u, v, incident_type):
        """Applies or removes an incident on an edge, modifying its weight based on type."""
        if not self.graph.has_edge(u, v):
            return None, False
            
        edge_id = tuple(sorted((u, v)))
        
        # Weight multipliers based on incident type
        multipliers = {
            'crash': 1000000,   # Blocked completely
            'traffic': 5,       # Heavy slowdown (Emerencia)
            'construction': 3,  # Moderate slowdown (Cono)
            'police': 1.5       # Minor slowdown (policia)
        }
        
        # If the exact same incident is already there, remove it
        if edge_id in self.active_incidents and self.active_incidents[edge_id] == incident_type:
            orig = self.graph[u][v]['original_weight']
            self.graph[u][v]['weight'] = orig
            del self.active_incidents[edge_id]
            return incident_type, False # False means removed
            
        # Otherwise, apply or change to the new incident type
        orig = self.graph[u][v]['original_weight']
        multiplier = multipliers.get(incident_type, 1)
        self.graph[u][v]['weight'] = orig * multiplier
        self.active_incidents[edge_id] = incident_type
        
        return incident_type, True # True means applied
        
    def remove_incident(self, u, v):
        """Force removal of any incident on the edge."""
        if not self.graph.has_edge(u, v):
            return
        edge_id = tuple(sorted((u, v)))
        if edge_id in self.active_incidents:
            orig = self.graph[u][v]['original_weight']
            self.graph[u][v]['weight'] = orig
            del self.active_incidents[edge_id]

    def get_all_locations(self):
        return [(id, data["name"]) for id, data in self.nodes.items()]

    def find_node_by_name(self, name):
        search_name = normalize_text(name)
        for id, data in self.nodes.items():
            if search_name in normalize_text(data["name"]):
                return id
        return None
