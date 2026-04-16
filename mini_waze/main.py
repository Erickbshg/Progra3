import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from engine import WazeEngine
from visualizer import MapVisualizer
import time

class MiniWazeApp(tb.Window):
    def __init__(self):
        super().__init__(themename="darkly", title="Mini Waze - Dijkstra Simulator")
        self.geometry("1100x850")
        
        self.engine = WazeEngine()
        
        # Create map canvas first so visualizer can use it
        self.main_container = tb.Frame(self)
        self.main_container.pack(fill=BOTH, expand=YES)
        
        self.map_frame = tb.Frame(self.main_container, padding=2, bootstyle="info")
        self.map_frame.pack(side=RIGHT, fill=BOTH, expand=YES)
        
        self.map_canvas = tk.Canvas(self.map_frame, width=800, height=800, highlightthickness=0)
        self.map_canvas.pack(fill=BOTH, expand=YES)

        # Now create visualizer
        self.visualizer = MapVisualizer(self.map_canvas, self.engine)

        # Setup the rest of the UI (sidebar)
        self.setup_ui()
        
        # Simulation State
        self.current_path = []
        self.current_node_index = 0
        self.simulating = False
        self.car_x = 0
        self.car_y = 0
        self.target_destination = None
        
        # Override visualizer's click callback to include recalculation
        self.visualizer.on_road_click = self.handle_incident_report
        self.visualizer.on_crash_removed = self.recalculate_route
        
        # Tool state
        self.active_tool = 'crash' 

    def setup_ui(self):
        # Sidebar with refined style
        self.sidebar = tb.Frame(self.main_container, width=320, padding=20, bootstyle="secondary")
        self.sidebar.pack(side=LEFT, fill=Y)
        self.sidebar.pack_propagate(False) # Fixed width
        
        # App Branding
        header_frame = tb.Frame(self.sidebar, bootstyle="secondary")
        header_frame.pack(fill=X, pady=(0, 25))
        
        # Logo using Pin Asset
        if 'pin' in self.visualizer.assets:
            logo_img = self.visualizer.assets['pin']
            tb.Label(header_frame, image=logo_img, bootstyle="secondary").pack(side=LEFT, padx=(0, 10))
        else:
            tb.Label(header_frame, text="📍", font=("Segoe UI Symbol", 24)).pack(side=LEFT, padx=(0, 10))
            
        tb.Label(header_frame, text="Mini Waze", font=("Segoe UI", 22, "bold")).pack(side=LEFT)
        
        # Search Entry Block
        search_container = tb.Frame(self.sidebar, bootstyle="secondary")
        search_container.pack(fill=X, pady=10)
        
        self.search_var = tk.StringVar()
        self.search_entry = tb.Entry(
            search_container, 
            textvariable=self.search_var, 
            font=("Segoe UI", 11),
            bootstyle="dark"
        )
        self.search_entry.pack(fill=X, pady=5)
        self.search_entry.bind("<Return>", lambda e: self.search_destination())
        
        tb.Button(self.sidebar, text="Calcular Ruta", command=self.search_destination, bootstyle="info-outline").pack(fill=X, pady=5)
        
        tb.Separator(self.sidebar, bootstyle="info").pack(fill=X, pady=20)
        
        # Location List
        tb.Label(self.sidebar, text="LUGARES CERCANOS", font=("Segoe UI", 8, "bold"), bootstyle="info").pack(anchor=W)
        
        # Scrollable container for locations
        self.loc_container = tb.Frame(self.sidebar, bootstyle="secondary")
        self.loc_container.pack(fill=BOTH, expand=YES, pady=10)
        
        # Grid of buttons
        locations = self.engine.get_all_locations()
        for i, (id, name) in enumerate(locations):
            btn = tb.Button(
                self.loc_container, 
                text=f"📍 {name}", 
                command=lambda node_id=id: self.select_destination(node_id), 
                bootstyle="link",
                padding=5
            )
            btn.pack(anchor=W, fill=X)

        # REPORTS SECTION (NEW)
        tb.Separator(self.sidebar, bootstyle="info").pack(fill=X, pady=20)
        tb.Label(self.sidebar, text="HERRAMIENTA DE REPORTE", font=("Segoe UI", 8, "bold"), bootstyle="info").pack(anchor=W)
        
        reports_frame = tb.Frame(self.sidebar, bootstyle="secondary")
        reports_frame.pack(fill=X, pady=10)
        
        # Dictionary to store tool buttons to visually indicate selection
        self.tool_buttons = {}

        def set_tool(tool_name):
            self.active_tool = tool_name
            # Reset all button styles to dark, then set active to info/primary
            for name, btn in self.tool_buttons.items():
                if name == tool_name:
                    btn.configure(bootstyle="info")
                else:
                    btn.configure(bootstyle="dark")
                    
        # Tool: Crash
        if 'crash' in self.visualizer.assets:
            btn = tb.Button(reports_frame, image=self.visualizer.assets['crash'], bootstyle="info", command=lambda: set_tool('crash'))
            btn.pack(side=LEFT, padx=5)
            self.tool_buttons['crash'] = btn
            
        # Tool: Traffic
        if 'traffic' in self.visualizer.assets:
            btn = tb.Button(reports_frame, image=self.visualizer.assets['traffic'], bootstyle="dark", command=lambda: set_tool('traffic'))
            btn.pack(side=LEFT, padx=5)
            self.tool_buttons['traffic'] = btn
            
        # Tool: Construction
        if 'construction' in self.visualizer.assets:
            btn = tb.Button(reports_frame, image=self.visualizer.assets['construction'], bootstyle="dark", command=lambda: set_tool('construction'))
            btn.pack(side=LEFT, padx=5)
            self.tool_buttons['construction'] = btn
            
        # Tool: Police
        if 'police' in self.visualizer.assets:
            btn = tb.Button(reports_frame, image=self.visualizer.assets['police'], bootstyle="dark", command=lambda: set_tool('police'))
            btn.pack(side=LEFT, padx=5)
            self.tool_buttons['police'] = btn

        tb.Label(self.sidebar, text="Selecciona un icono y haz clic en el mapa.", font=("Segoe UI", 8), bootstyle="secondary").pack(anchor=W)

        # Navigation Info Card (Hidden by default or minimalist)
        self.nav_card = tb.Frame(self.sidebar, padding=15, bootstyle="dark")
        self.nav_card.pack(fill=X, side=BOTTOM, pady=10)
        
        self.status_label = tb.Label(self.nav_card, text="Explorando el mapa...", font=("Segoe UI", 9))
        self.status_label.pack()
        
        self.eta_label = tb.Label(self.nav_card, text="", font=("Segoe UI", 12, "bold"), bootstyle="info")
        self.eta_label.pack(pady=5)
        

    def search_destination(self):
        name = self.search_var.get()
        node_id = self.engine.find_node_by_name(name)
        if node_id is not None:
            self.select_destination(node_id)
        else:
            messagebox.showwarning("No encontrado", f"No se encontró el lugar: {name}")

    def select_destination(self, node_id):
        self.target_destination = node_id
        self.visualizer.update_destination_pin(node_id)
        
        # For simplicity, start navigation from node 4 (Casa) by default
        start_node = 4 
        path = self.engine.get_shortest_path(start_node, node_id)
        
        if path:
            self.current_path = path
            self.visualizer.draw_path(path)
            self.start_simulation()
        else:
            messagebox.showerror("Error", "No existe ruta hacia el destino")

    def start_simulation(self):
        if self.simulating:
            self.simulating = False # Reset if one is running
        
        self.simulating = True
        self.current_node_index = 0
        start_node = self.current_path[0]
        self.car_x = self.engine.nodes[start_node]["x"]
        self.car_y = self.engine.nodes[start_node]["y"]
        self.animate_step()

    def handle_incident_report(self, u, v):
        """Called when a user clicks a road to report an incident."""
        incident_type, is_active = self.engine.toggle_incident(u, v, self.active_tool)
        
        if incident_type:
             self.visualizer.update_incident_visual(u, v, incident_type, is_active)
        
        # If we are navigating, check if we need to recalculate
        if self.simulating and self.target_destination is not None:
            self.status_label.config(text="⚠️ ¡Recalculando ruta!")
            self.recalculate_route()

    def recalculate_route(self):
        # We find the node we are currently "heading to" or closest to
        # For simplicity, we use the current_node_index as the last reached node
        current_reached_node = self.current_path[self.current_node_index]
        
        new_path = self.engine.get_shortest_path(current_reached_node, self.target_destination)
        if new_path:
            self.current_path = new_path
            self.current_node_index = 0 # Restart from current node in the new path list
            self.visualizer.draw_path(new_path)
            self.status_label.config(text="Ruta optimizada")
        else:
            self.status_label.config(text="🚫 Sin salida")
            self.simulating = False
            messagebox.showerror("Error", "No hay rutas alternativas disponibles.")

    def animate_step(self):
        if not self.simulating or self.current_node_index >= len(self.current_path) - 1:
            if self.simulating:
                self.status_label.config(text="🚩 Destino alcanzado")
                self.eta_label.config(text="Llegaste")
            self.simulating = False
            return

        target_node = self.current_path[self.current_node_index + 1]
        target_x = self.engine.nodes[target_node]["x"]
        target_y = self.engine.nodes[target_node]["y"]

        # Simple Linear Interpolation
        dx = target_x - self.car_x
        dy = target_y - self.car_y
        dist_to_node = (dx**2 + dy**2)**0.5
        
        speed = 8 # Slightly faster for better feel
        
        if dist_to_node < speed:
            # We reached the node
            self.car_x = target_x
            self.car_y = target_y
            self.current_node_index += 1
            
            # Update ETA based on remaining path
            remaining_dist = 0
            for i in range(self.current_node_index, len(self.current_path)-1):
                u, v = self.current_path[i], self.current_path[i+1]
                remaining_dist += self.engine.graph[u][v]['weight']
            
            eta_min = int(remaining_dist / 100) # Arbitrary factor for "minutes"
            self.eta_label.config(text=f"ETA: {eta_min} min")
            self.status_label.config(text=f"Hacia: {self.engine.nodes[self.current_path[-1]]['name']}")
        else:
            # Move towards target
            self.car_x += (dx / dist_to_node) * speed
            self.car_y += (dy / dist_to_node) * speed

        self.visualizer.update_car_position(self.car_x, self.car_y)
        self.after(25, self.animate_step) # 40 FPS

if __name__ == "__main__":
    app = MiniWazeApp()
    app.mainloop()
