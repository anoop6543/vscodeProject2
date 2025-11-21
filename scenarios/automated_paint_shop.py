import sys
import os
import logging
import random
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from SimpleGantrySimulation import GantryRobot, ObjectType
import sim_database_manager as dbm
import file_logger
from sim_opc_server import sim_opc_instance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler("logs/paint_shop.log"),
        logging.StreamHandler()
    ]
)

class PaintRobot(GantryRobot):
    """
    Specialized GantryRobot for painting applications.
    """
    def __init__(self, robot_id: str):
        super().__init__()
        self.robot_id = robot_id
        # Add specific paint gun tags
        sim_opc_instance.write_tag(f"{self.robot_id}.SprayGun.FlowRate", 0.0)
        sim_opc_instance.write_tag(f"{self.robot_id}.SprayGun.AtomizationAir", 0.0)
        sim_opc_instance.write_tag(f"{self.robot_id}.SprayGun.FanWidth", 0.0)

    def spray_paint(self, start_pos: Tuple[float, float, float], end_pos: Tuple[float, float, float], 
                   color: str, layer: str):
        """
        Simulate spraying paint along a path.
        """
        logging.info(f"[{self.robot_id}] Spraying {layer} ({color}) from {start_pos} to {end_pos}")
        
        # Set Gun Parameters based on layer
        if layer == "Primer":
            flow = 250.0
            fan = 300.0
        elif layer == "Base":
            flow = 200.0
            fan = 250.0
        else: # Clear
            flow = 180.0
            fan = 280.0
            
        sim_opc_instance.write_tag(f"{self.robot_id}.SprayGun.FlowRate", flow)
        sim_opc_instance.write_tag(f"{self.robot_id}.SprayGun.FanWidth", fan)
        sim_opc_instance.write_tag(f"{self.robot_id}.Status", f"Spraying_{layer}")
        
        # Move along the path (simulated as a single move for now, could be arc/spiral)
        self.move_to(start_pos, (0, 0))
        # Simulate spray on
        time.sleep(0.5) 
        self.move_to(end_pos, (0, 0))
        
        sim_opc_instance.write_tag(f"{self.robot_id}.SprayGun.FlowRate", 0.0)
        sim_opc_instance.write_tag(f"{self.robot_id}.Status", "Idle")

class PaintBooth:
    """
    Manages the paint booth environment.
    """
    def __init__(self, booth_id: str):
        self.booth_id = booth_id
        self.temperature = 22.0 # Celsius
        self.humidity = 55.0 # % RH
        self.airflow = 0.5 # m/s
        
        # Initialize OPC tags
        sim_opc_instance.write_tag(f"{self.booth_id}.Temp", self.temperature)
        sim_opc_instance.write_tag(f"{self.booth_id}.Humidity", self.humidity)
        sim_opc_instance.write_tag(f"{self.booth_id}.Airflow", self.airflow)

    def update_environment(self):
        """Simulate environmental fluctuations"""
        self.temperature += random.uniform(-0.1, 0.1)
        self.humidity += random.uniform(-0.5, 0.5)
        
        # Check limits
        if not (20.0 <= self.temperature <= 25.0):
            logging.warning(f"[{self.booth_id}] Temperature out of range: {self.temperature:.2f}")
            dbm.create_error(self.booth_id, "ENV-001", "Temperature Deviation", "medium")
            
        if not (45.0 <= self.humidity <= 65.0):
            logging.warning(f"[{self.booth_id}] Humidity out of range: {self.humidity:.2f}")
             # dbm.create_error(self.booth_id, "ENV-002", "Humidity Deviation", "low") # Optional

        sim_opc_instance.write_tag(f"{self.booth_id}.Temp", self.temperature)
        sim_opc_instance.write_tag(f"{self.booth_id}.Humidity", self.humidity)

class AutomatedPaintShop:
    def __init__(self):
        self.logger = logging.getLogger("PaintShop")
        self.robot = PaintRobot("PaintRobot1")
        self.booth = PaintBooth("Booth1")
        self.recipe_id = None

    def run_paint_job(self, part_id: str, color_code: str):
        self.logger.info(f"Starting paint job for Part {part_id} - Color: {color_code}")
        
        # Create Recipe if not exists (simplified)
        if not self.recipe_id:
            self.recipe_id = dbm.create_recipe(
                "Standard_3Layer_Paint",
                ["Primer_Grey", f"Base_{color_code}", "Clear_Coat_Gloss"],
                ["Clean", "Primer", "FlashOff", "BaseCoat", "FlashOff", "ClearCoat", "Bake"]
            )

        start_time = datetime.now()
        
        # 1. Environmental Check
        self.booth.update_environment()
        
        # 2. Preparation (Cleaning)
        self.logger.info("Step: Cleaning")
        self.robot.move_to((0, 0, 100), (0, 0)) # Home
        time.sleep(0.5)
        
        # 3. Primer Application
        self.logger.info("Step: Primer Coat")
        self.robot.spray_paint((10, 10, 50), (10, 90, 50), "Grey", "Primer")
        self.robot.spray_paint((20, 10, 50), (20, 90, 50), "Grey", "Primer")
        # ... more passes
        
        # 4. Base Coat Application
        self.logger.info(f"Step: Base Coat ({color_code})")
        self.booth.update_environment() # Check env again
        self.robot.spray_paint((10, 10, 50), (10, 90, 50), color_code, "Base")
        self.robot.spray_paint((20, 10, 50), (20, 90, 50), color_code, "Base")
        
        # 5. Clear Coat Application
        self.logger.info("Step: Clear Coat")
        self.robot.spray_paint((10, 10, 50), (10, 90, 50), "Clear", "Clear")
        
        # 6. Curing (Simulated)
        self.logger.info("Step: Curing/Bake")
        time.sleep(1.0)
        
        # Log Results
        cycle_time = (datetime.now() - start_time).total_seconds()
        dbm.create_result(self.recipe_id, 1, "Success", "AutoPaint", "Shift_A")
        
        file_logger.log_production_result(
            self.recipe_id, "Standard_3Layer_Paint", 1, "Success", "AutoPaint", "Shift_A", cycle_time
        )
        
        self.logger.info(f"Paint job completed for {part_id} in {cycle_time:.2f}s")

if __name__ == "__main__":
    shop = AutomatedPaintShop()
    shop.run_paint_job("Door_Panel_L_001", "MidnightBlue")
    shop.run_paint_job("Hood_002", "RacingRed")
