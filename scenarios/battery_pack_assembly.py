import sys
import os
import logging
import random
import time
import math
from typing import List, Dict, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from SimpleGantrySimulation import GantryRobot, ObjectType, Motor, Sensor
import sim_database_manager as dbm
import file_logger
from sim_opc_server import sim_opc_instance
from laser_marker_adapter import LaserMarkerAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler("logs/battery_pack_assembly.log"),
        logging.StreamHandler()
    ]
)

class BatteryCell:
    def __init__(self, cell_id: str, voltage: float, capacity: float):
        self.cell_id = cell_id
        self.voltage = voltage # Volts, e.g., 3.7
        self.capacity = capacity # Ah, e.g., 2.5
        self.weight = 45.0 # grams
        self.diameter = 18.0 # mm (18650)
        self.height = 65.0 # mm

class Busbar:
    def __init__(self, material: str = "Copper"):
        self.material = material
        self.thickness = 1.0 # mm

class BatteryModuleCase:
    def __init__(self, module_id: str):
        self.module_id = module_id
        self.cells: List[BatteryCell] = []
        self.is_sealed = False

class BatteryPackAssemblyLine:
    def __init__(self):
        self.robots = {
            "dispenser": GantryRobot(), # For thermal paste
            "cell_loader": GantryRobot(), # For picking and placing cells
            "welder": GantryRobot() # For busbar welding and marking
        }
        self.main_logger = logging.getLogger("BatteryPackAssembly")
        self.robot_loggers = {
            name: logging.getLogger(f"Robot.{name}") 
            for name in self.robots.keys()
        }
        
        # Initialize Laser Adapter for the welder robot
        # We'll use a high-power fiber laser for welding
        self.laser_adapter = LaserMarkerAdapter(
            self.robots["welder"], 
            vendor="trumpf", 
            model="TruMark 6130"
        )
        
        self.conveyor_position = 0.0
        self.recipe_id = None

    def move_conveyor(self, distance: float):
        """Simulate conveyor movement"""
        self.main_logger.info(f"Moving conveyor by {distance}mm")
        sim_opc_instance.write_tag("Conveyor.IsRunning", True)
        self.conveyor_position += distance
        time.sleep(abs(distance) / 200) # Faster conveyor for this line
        sim_opc_instance.write_tag("Conveyor.IsRunning", False)
        self.main_logger.info("Conveyor movement finished.")

    def apply_thermal_paste(self, case_position: Tuple[float, float, float]):
        """
        Apply thermal paste in a continuous path pattern on the case bottom.
        """
        robot = self.robots["dispenser"]
        logger = self.robot_loggers["dispenser"]
        
        logger.info(f"Starting thermal paste application at {case_position}")
        
        # Move to start position
        start_x = case_position[0] + 10
        start_y = case_position[1] + 10
        z_height = case_position[2] + 5 # Just above the case floor
        
        robot.move_to((start_x, start_y, z_height + 20), (0, 0)) # Approach
        robot.move_to((start_x, start_y, z_height), (0, 0)) # Down to dispense height
        
        # Simulate dispensing on
        sim_opc_instance.write_tag("Dispenser.ValveOpen", True)
        logger.info("Dispenser valve OPEN")
        
        # Create a snake path for paste
        # Cover a 100x100 area
        width = 100
        length = 100
        step = 20
        
        current_x = start_x
        current_y = start_y
        
        # Use a series of moves to simulate the path
        # In a real scenario, this might be a single complex path command, 
        # but here we chain move_to calls or use arc_move for turns if we want to be fancy.
        # Let's use simple linear moves for the snake pattern.
        
        for i in range(0, width, step):
            # Move Y direction
            target_y = start_y + length if (i // step) % 2 == 0 else start_y
            robot.move_to((current_x, target_y, z_height), (0, 0))
            current_y = target_y
            
            # Move X step
            if i + step < width:
                current_x += step
                robot.move_to((current_x, current_y, z_height), (0, 0))
        
        sim_opc_instance.write_tag("Dispenser.ValveOpen", False)
        logger.info("Dispenser valve CLOSED")
        robot.move_to((current_x, current_y, z_height + 50), (0, 0)) # Retract

    def load_cells(self, case_position: Tuple[float, float, float]):
        """
        Pick and place 16 cells into the case in a 4x4 matrix.
        """
        robot = self.robots["cell_loader"]
        logger = self.robot_loggers["cell_loader"]
        
        logger.info("Starting cell loading process (4x4 Matrix)")
        
        # Feeder location for cells
        feeder_base = (50, 300, 10)
        
        # Matrix offsets in the case
        rows = 4
        cols = 4
        cell_spacing = 20 # mm
        
        for r in range(rows):
            for c in range(cols):
                cell_id = f"CELL_{r}_{c}"
                
                # 1. Pick Cell
                # Simulate fetching from a gravity feeder (always same pick point or slight variation)
                pick_pos = (feeder_base[0], feeder_base[1], feeder_base[2])
                
                robot.select_gripper(ObjectType.CYLINDER)
                robot.move_to((pick_pos[0], pick_pos[1], pick_pos[2] + 20), (0, 0))
                robot.move_to(pick_pos, (0, 0))
                robot.current_gripper.pick(ObjectType.CYLINDER)
                robot.move_to((pick_pos[0], pick_pos[1], pick_pos[2] + 50), (0, 0)) # Lift
                
                # 2. Place Cell
                place_x = case_position[0] + 10 + (c * cell_spacing)
                place_y = case_position[1] + 10 + (r * cell_spacing)
                place_z = case_position[2] + 5 # Inside case
                
                robot.move_to((place_x, place_y, place_z + 50), (0, 0)) # Approach
                robot.move_to((place_x, place_y, place_z), (0, 0)) # Place depth
                
                # Check force to ensure we are pressing into paste but not crushing
                force = robot.force_sensor.get_force()
                if force > 50:
                    logger.warning(f"High insertion force detected at {r},{c}: {force:.2f}N")
                
                robot.current_gripper.place((place_x, place_y, place_z))
                robot.move_to((place_x, place_y, place_z + 50), (0, 0)) # Retract
                
                logger.info(f"Placed cell {cell_id} at ({r}, {c})")

    def weld_busbars(self, case_position: Tuple[float, float, float]):
        """
        Weld busbars to the cell terminals using the laser welder.
        """
        robot = self.robots["welder"]
        logger = self.robot_loggers["welder"]
        
        logger.info("Starting busbar welding process")
        
        # Assume busbar is already placed (simplified)
        
        # Weld points corresponding to the 4x4 matrix
        rows = 4
        cols = 4
        cell_spacing = 20
        
        for r in range(rows):
            for c in range(cols):
                # Calculate terminal position
                weld_x = case_position[0] + 10 + (c * cell_spacing)
                weld_y = case_position[1] + 10 + (r * cell_spacing)
                weld_z = case_position[2] + 65 # Top of cell height
                
                # Perform a small circular weld or spot weld pattern
                # We'll use laser_weld for a small linear stitch
                
                start_weld = (weld_x - 2, weld_y, weld_z)
                end_weld = (weld_x + 2, weld_y, weld_z)
                
                logger.info(f"Welding cell terminal at ({r}, {c})")
                
                # Use the adapter to weld
                # Note: The adapter patches the robot, so we can call laser_weld directly on 'robot'
                # if we assigned it back, or use self.laser_adapter.robot (which is the same object).
                # However, since we instantiated LaserMarkerAdapter(robot, ...), it modifies the robot instance in-place
                # if the adapter implementation does so.
                # Let's check laser_marker_adapter.py... yes, it patches the instance methods.
                
                robot.laser_weld(
                    start_point=start_weld,
                    end_point=end_weld,
                    speed=10, # Slow precision weld
                    power=2000, # High power
                    focus_setting=0.0
                )
                
                # Simulate checking weld quality via OPC
                sim_opc_instance.write_tag("Welder.LastWeldQuality", "OK")

    def mark_module(self, case_position: Tuple[float, float, float], module_id: str):
        """
        Laser mark the module ID on the case.
        """
        robot = self.robots["welder"]
        logger = self.robot_loggers["welder"]
        
        logger.info(f"Marking module ID: {module_id}")
        
        # Marking position on the side of the case
        mark_x = case_position[0] + 50
        mark_y = case_position[1] - 10 # Side
        mark_z = case_position[2] + 30
        
        robot.laser_mark(
            target_point=(mark_x, mark_y, mark_z),
            text=module_id,
            speed=200,
            power=50,
            font_size=5.0
        )

    def run_scenario(self, num_modules: int = 1):
        self.main_logger.info(f"Starting Battery Pack Assembly Scenario for {num_modules} modules")
        
        # Create Recipe in DB
        self.recipe_id = dbm.create_recipe(
            name="EV_Battery_Module_4x4",
            ingredients=["Case_Type_A", "Cell_18650_LiIon", "Busbar_Cu_0.5mm", "Thermal_Paste_X"],
            steps=["Dispense Paste", "Load 16 Cells", "Place Busbar", "Laser Weld 32 Points", "Mark ID"]
        )
        
        for i in range(num_modules):
            module_id = f"MOD_{datetime.now().strftime('%Y%m%d')}_{i+1:03d}"
            self.main_logger.info(f"Processing Module: {module_id}")
            
            start_time = datetime.now()
            
            # 1. Move Case into position
            self.move_conveyor(500)
            case_pos = (200, 200, 0) # Workstation position
            
            # 2. Apply Thermal Paste
            self.apply_thermal_paste(case_pos)
            
            # 3. Load Cells
            self.load_cells(case_pos)
            
            # 4. Weld Busbars
            self.weld_busbars(case_pos)
            
            # 5. Mark Module
            self.mark_module(case_pos, module_id)
            
            # 6. Log Results
            cycle_time = (datetime.now() - start_time).total_seconds()
            
            dbm.create_result(
                recipe_id=self.recipe_id,
                output_quantity=1,
                status="Success",
                operator="AutoLine_1",
                shift="Day"
            )
            
            file_logger.log_production_result(
                recipe_id=self.recipe_id,
                recipe_name="EV_Battery_Module_4x4",
                output_quantity=1,
                status="Success",
                operator="AutoLine_1",
                shift="Day",
                cycle_time_seconds=cycle_time
            )
            
            # Log KPI
            file_logger.log_kpi(
                machine_id="BatteryLine_Main",
                oee=0.92,
                availability=0.98,
                performance=0.95,
                quality=0.99,
                cycle_time=cycle_time,
                defect_rate=0.01
            )
            
            self.main_logger.info(f"Module {module_id} completed in {cycle_time:.2f}s")
            
            # Move out
            self.move_conveyor(500)

if __name__ == "__main__":
    line = BatteryPackAssemblyLine()
    line.run_scenario(num_modules=1)
