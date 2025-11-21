import sys
import os
import logging
import random
import time
import math
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sim_database_manager as dbm
from sim_opc_server import sim_opc_instance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler("logs/agv_delivery.log"),
        logging.StreamHandler()
    ]
)

class AGV:
    def __init__(self, agv_id: str):
        self.agv_id = agv_id
        self.position = (0, 0) # x, y
        self.battery_level = 100.0 # %
        self.status = "Idle" # Idle, Moving, Loading, Unloading, Charging
        self.current_load = None
        self.destination = None
        
        # Initialize OPC tags
        sim_opc_instance.write_tag(f"{self.agv_id}.Status", self.status)
        sim_opc_instance.write_tag(f"{self.agv_id}.Battery", self.battery_level)
        sim_opc_instance.write_tag(f"{self.agv_id}.Position.X", self.position[0])
        sim_opc_instance.write_tag(f"{self.agv_id}.Position.Y", self.position[1])

    def move_to(self, target_pos: Tuple[float, float]):
        """Simulate movement to a target position."""
        self.status = "Moving"
        sim_opc_instance.write_tag(f"{self.agv_id}.Status", self.status)
        logging.info(f"[{self.agv_id}] Moving from {self.position} to {target_pos}")
        
        # Calculate distance and time
        dx = target_pos[0] - self.position[0]
        dy = target_pos[1] - self.position[1]
        distance = math.sqrt(dx**2 + dy**2)
        speed = 100.0 # units/sec
        duration = distance / speed
        
        # Simulate movement (simplified, just wait)
        time.sleep(duration / 10) # Speed up simulation
        
        self.position = target_pos
        self.battery_level -= (distance * 0.05) # Consume battery
        
        sim_opc_instance.write_tag(f"{self.agv_id}.Position.X", self.position[0])
        sim_opc_instance.write_tag(f"{self.agv_id}.Position.Y", self.position[1])
        sim_opc_instance.write_tag(f"{self.agv_id}.Battery", self.battery_level)
        
        self.status = "Idle"
        sim_opc_instance.write_tag(f"{self.agv_id}.Status", self.status)

    def load_material(self, material: str):
        self.status = "Loading"
        sim_opc_instance.write_tag(f"{self.agv_id}.Status", self.status)
        logging.info(f"[{self.agv_id}] Loading {material}")
        time.sleep(1.0)
        self.current_load = material
        self.status = "Idle"
        sim_opc_instance.write_tag(f"{self.agv_id}.Status", self.status)

    def unload_material(self):
        self.status = "Unloading"
        sim_opc_instance.write_tag(f"{self.agv_id}.Status", self.status)
        logging.info(f"[{self.agv_id}] Unloading {self.current_load}")
        time.sleep(1.0)
        self.current_load = None
        self.status = "Idle"
        sim_opc_instance.write_tag(f"{self.agv_id}.Status", self.status)

    def charge(self):
        self.status = "Charging"
        sim_opc_instance.write_tag(f"{self.agv_id}.Status", self.status)
        logging.info(f"[{self.agv_id}] Charging...")
        time.sleep(2.0)
        self.battery_level = 100.0
        sim_opc_instance.write_tag(f"{self.agv_id}.Battery", self.battery_level)
        self.status = "Idle"
        sim_opc_instance.write_tag(f"{self.agv_id}.Status", self.status)

class FleetManager:
    def __init__(self):
        self.agvs = [AGV("AGV_01"), AGV("AGV_02"), AGV("AGV_03")]
        self.warehouse_pos = (0, 0)
        self.charging_pos = (10, 0)
        self.stations = {
            "BatteryLine": (100, 200),
            "FuseLine": (300, 200),
            "PaintShop": (500, 100)
        }
        self.logger = logging.getLogger("FleetManager")

    def dispatch_agv(self, station_name: str, material: str):
        """Find nearest available AGV and dispatch it."""
        self.logger.info(f"Request received: Deliver {material} to {station_name}")
        
        # Find best AGV (Idle and enough battery)
        best_agv = None
        min_dist = float('inf')
        
        for agv in self.agvs:
            if agv.status == "Idle" and agv.battery_level > 20.0:
                dist = math.sqrt((agv.position[0] - self.warehouse_pos[0])**2 + 
                                 (agv.position[1] - self.warehouse_pos[1])**2)
                if dist < min_dist:
                    min_dist = dist
                    best_agv = agv
        
        if best_agv:
            self.logger.info(f"Dispatching {best_agv.agv_id}")
            
            # 1. Go to Warehouse
            best_agv.move_to(self.warehouse_pos)
            
            # 2. Load
            best_agv.load_material(material)
            
            # 3. Go to Station
            target_pos = self.stations.get(station_name, (0,0))
            best_agv.move_to(target_pos)
            
            # 4. Unload
            best_agv.unload_material()
            
            # 5. Check Battery / Return
            if best_agv.battery_level < 40.0:
                self.logger.info(f"{best_agv.agv_id} battery low, sending to charger.")
                best_agv.move_to(self.charging_pos)
                best_agv.charge()
            else:
                # Return to warehouse staging or stay put? Let's return to warehouse area
                best_agv.move_to((self.warehouse_pos[0] + 20, self.warehouse_pos[1]))
                
        else:
            self.logger.warning("No available AGVs!")

    def run_simulation_cycle(self):
        """Simulate a shift of requests."""
        requests = [
            ("BatteryLine", "Cells_18650_Pallet"),
            ("FuseLine", "Ceramic_Housings"),
            ("PaintShop", "Paint_Drums_Blue"),
            ("BatteryLine", "Busbar_Coils")
        ]
        
        for station, material in requests:
            self.dispatch_agv(station, material)
            time.sleep(1.0) # Interval between requests

if __name__ == "__main__":
    manager = FleetManager()
    manager.run_simulation_cycle()
