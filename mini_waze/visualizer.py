import tkinter as tk
from PIL import Image, ImageTk
import os

class MapVisualizer:
    def __init__(self, canvas, engine):
        self.canvas = canvas
        self.engine = engine
        self.assets = {}
        self.load_assets()
        
        # Colors - Waze Dark Aesthetic
        self.COLOR_BG = "#18191C"
        self.COLOR_ROAD = "#3C3E43"
        self.COLOR_PATH = "#33E5FF"
        self.COLOR_NODE = "#5C5E62"
        self.COLOR_TEXT = "#E0E0E0"
        self.COLOR_CRASH = "#FF4B4B"

        self.path_line_ids = []
        self.car_id = None
        self.destination_id = None
        self.crash_icons = {} # (u, v): canvas_id

        self.canvas.config(bg=self.COLOR_BG)
        self.draw_base_map()

    def load_assets(self):
        asset_dir = os.path.join(os.path.dirname(__file__), "assets")
        try:
            self.assets['car'] = ImageTk.PhotoImage(Image.open(os.path.join(asset_dir, "car_icon.png")).resize((40, 40)))
            self.assets['crash'] = ImageTk.PhotoImage(Image.open(os.path.join(asset_dir, "crash_icon.png")).resize((30, 30)))
            self.assets['pin'] = ImageTk.PhotoImage(Image.open(os.path.join(asset_dir, "pin_icon.png")).resize((40, 40)))
            # New Hazard Icons
            self.assets['traffic'] = ImageTk.PhotoImage(Image.open(os.path.join(asset_dir, "Emerencia.png")).resize((30, 30)))
            self.assets['construction'] = ImageTk.PhotoImage(Image.open(os.path.join(asset_dir, "Cono.png")).resize((30, 30)))
            self.assets['police'] = ImageTk.PhotoImage(Image.open(os.path.join(asset_dir, "policia.png")).resize((30, 30)))
        except Exception as e:
            print(f"Error loading assets: {e}")
            # Fallback will just drawing shapes

    def draw_base_map(self):
        self.canvas.delete("all")
        
        # Draw roads (edges)
        for u, v, data in self.engine.graph.edges(data=True):
            pos_u = (self.engine.nodes[u]["x"], self.engine.nodes[u]["y"])
            pos_v = (self.engine.nodes[v]["x"], self.engine.nodes[v]["y"])
            
            # Hit area (invisible thick line for easier clicking)
            hit_id = self.canvas.create_line(
                pos_u[0], pos_u[1], pos_v[0], pos_v[1], 
                width=20, fill="", tags=("road_hit", f"edge_{u}_{v}")
            )
            
            # Visual road
            line_id = self.canvas.create_line(
                pos_u[0], pos_u[1], pos_v[0], pos_v[1], 
                width=6, fill=self.COLOR_ROAD, capstyle=tk.ROUND, tags=("road", f"edge_{u}_{v}")
            )
            
            # Bind to hit area
            self.canvas.tag_bind(hit_id, "<Button-1>", lambda e, u=u, v=v: self.on_road_click(u, v))
            # Also bind to visual road just in case
            self.canvas.tag_bind(line_id, "<Button-1>", lambda e, u=u, v=v: self.on_road_click(u, v))

        # Draw nodes
        for id, data in self.engine.nodes.items():
            # Chip-style node background
            padding = 10
            text_id = self.canvas.create_text(
                0, 0, text=data["name"], 
                fill=self.COLOR_TEXT, font=("Segoe UI", 9, "bold"),
                anchor=tk.CENTER
            )
            bbox = self.canvas.bbox(text_id)
            width = (bbox[2] - bbox[0]) + padding * 2
            height = (bbox[3] - bbox[1]) + 6
            
            # Create a rounded-rect effect with a rectangle
            self.canvas.create_rectangle(
                data["x"] - width/2, data["y"] - height/2,
                data["x"] + width/2, data["y"] + height/2,
                fill="#1E232F", outline="#33E5FF", width=1, tags="node_bg"
            )
            
            # Reposition text above bg
            self.canvas.coords(text_id, data["x"], data["y"])
            self.canvas.tag_raise(text_id)
            
            # Small glow point
            self.canvas.create_oval(
                data["x"]-3, data["y"]-15, data["x"]+3, data["y"]-9, 
                fill="#33E5FF", outline=""
            )

    def on_road_click(self, u, v, active_tool='crash'):
        # Toggle incident logic - engine returns actual incident type and if it was applied
        incident_type, is_active = self.engine.toggle_incident(u, v, active_tool)
        if incident_type:
            self.update_incident_visual(u, v, incident_type, is_active)
        # Main app will hook this for recalculation

    def update_incident_visual(self, u, v, incident_type, is_active):
        tag = f"incident_{u}_{v}"
        # Remove old visual first just in case
        self.remove_incident_tag(tag, u, v)
        
        if is_active:
            mid_x = (self.engine.nodes[u]["x"] + self.engine.nodes[v]["x"]) / 2
            mid_y = (self.engine.nodes[u]["y"] + self.engine.nodes[v]["y"]) / 2
            
            # Map type to asset
            if incident_type in self.assets:
                cid = self.canvas.create_image(mid_x, mid_y, image=self.assets[incident_type], tags=(tag, "incident_icon"))
            else:
                colors = {'crash': 'red', 'traffic': 'orange', 'construction': 'yellow', 'police': 'blue'}
                fill_color = colors.get(incident_type, 'gray')
                cid = self.canvas.create_oval(mid_x-10, mid_y-10, mid_x+10, mid_y+10, fill=fill_color, tags=(tag, "incident_icon"))
            
            # Bind DOUBLE CLICK to remove
            self.canvas.tag_bind(cid, "<Double-Button-1>", lambda e, u=u, v=v: self.on_incident_double_click(u, v))
            self.crash_icons[(u, v)] = cid

    def on_incident_double_click(self, u, v):
        # Force remove
        self.engine.remove_incident(u, v)
        tag = f"incident_{u}_{v}"
        self.remove_incident_tag(tag, u, v)
        # Notify main app for recalculation
        if hasattr(self, "on_crash_removed"):
            self.on_crash_removed()

    def remove_incident_tag(self, tag, u, v):
        if (u, v) in self.crash_icons:
            self.canvas.delete(self.crash_icons[(u, v)])
            del self.crash_icons[(u, v)]
        elif (v, u) in self.crash_icons:
             self.canvas.delete(self.crash_icons[(v, u)])
             del self.crash_icons[(v, u)]


    def draw_path(self, path):
        # Clear old path
        for pid in self.path_line_ids:
            self.canvas.delete(pid)
        self.path_line_ids = []

        if not path or len(path) < 2:
            return

        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            pos_u = (self.engine.nodes[u]["x"], self.engine.nodes[u]["y"])
            pos_v = (self.engine.nodes[v]["x"], self.engine.nodes[v]["y"])
            
            pid = self.canvas.create_line(
                pos_u[0], pos_u[1], pos_v[0], pos_v[1], 
                width=10, fill=self.COLOR_PATH, capstyle=tk.ROUND, tags="path"
            )
            self.path_line_ids.append(pid)
            self.canvas.tag_lower(pid, "road") # Keep below roads but above bg? Actually above roads.
        
        # Bring path above roads
        self.canvas.tag_raise("path")
        self.canvas.tag_raise("car")
        self.canvas.tag_raise("pin")

    def update_car_position(self, x, y):
        if self.car_id:
            self.canvas.delete(self.car_id)
        
        if 'car' in self.assets:
            self.car_id = self.canvas.create_image(x, y, image=self.assets['car'], tags="car")
        else:
            self.car_id = self.canvas.create_oval(x-10, y-10, x+10, y+10, fill="blue", tags="car")
        self.canvas.tag_raise("car")

    def update_destination_pin(self, node_id):
        if self.destination_id:
            self.canvas.delete(self.destination_id)
        
        if node_id is None:
            return

        x, y = self.engine.nodes[node_id]["x"], self.engine.nodes[node_id]["y"]
        if 'pin' in self.assets:
            self.destination_id = self.canvas.create_image(x, y-20, image=self.assets['pin'], tags="pin")
        else:
            self.destination_id = self.canvas.create_oval(x-5, y-5, x+5, y+5, fill="red", tags="pin")
        self.canvas.tag_raise("pin")

    def clear_navigation(self):
        for pid in self.path_line_ids:
            self.canvas.delete(pid)
        self.path_line_ids = []
        if self.car_id:
            self.canvas.delete(self.car_id)
            self.car_id = None
        if self.destination_id:
            self.canvas.delete(self.destination_id)
            self.destination_id = None
