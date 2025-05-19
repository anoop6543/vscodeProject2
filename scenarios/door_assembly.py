import sys
import os
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from SimpleGantrySimulation import GantryRobot, ObjectType, ForceSensor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("door_assembly.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DoorAssemblyStation:
    def __init__(self):
        self.gantry = GantryRobot()
        # Add additional force sensors for quality checks
        self.corner_force_sensors = [ForceSensor() for _ in range(4)]
        
    def run_assembly_process(self):
        logger.info("Starting door panel assembly process")
        
        # Phase 1: Pick up door panel frame (metal sheet)
        logger.info("Phase 1: Door frame placement")
        self.gantry.pick_and_place(
            ObjectType.SHEET,
            pick_pos=(50, 50, 10),
            place_pos=(300, 200, 20)
        )
        
        # Phase 2: Install door hinges (precision required)
        logger.info("Phase 2: Hinge installation")
        hinge_positions = [(290, 150, 20), (290, 250, 20)]
        
        for i, pos in enumerate(hinge_positions):
            logger.info(f"Installing hinge {i+1}/2")
            # Approach with precision
            self.gantry.move_to((pos[0]-50, pos[1], pos[2]+30), (45, 0))
            # Precision movement
            self.gantry.select_gripper(ObjectType.METAL_PART)
            
            # Pick up hinge
            hinge_pickup = (100, 100 + i*20, 10)
            self.gantry.move_to(hinge_pickup, (0, 0))
            self.gantry.extend_retract(True)
            self.gantry.operate_gripper(False)
            logger.info(f"Force detected: {self.gantry.force_sensor.get_force():.2f}N")
            self.gantry.current_gripper.pick(ObjectType.METAL_PART)
            self.gantry.extend_retract(False)
            
            # Position hinge with precise alignment
            self.gantry.move_to((pos[0], pos[1], pos[2]+20), (45, 0))
            self.gantry.drives[5].command_move(45, speed=50)  # Fine rotation
            
            # Slowly place with force feedback
            self.gantry.extend_retract(True)
            for j in range(20, 0, -2):  # Slow approach
                self.gantry.drives[2].command_move(pos[2]+j, speed=50)
                force = self.gantry.force_sensor.get_force()
                logger.info(f"Approach force: {force:.2f}N")
                if force > 30:  # Force threshold
                    logger.warning(f"Excessive force detected: {force:.2f}N")
                    break
            
            self.gantry.operate_gripper(True)
            self.gantry.current_gripper.place(pos)
            self.gantry.extend_retract(False)
            
            # Install screws for the hinge
            screw_offsets = [(5, 5, 0), (5, -5, 0), (-5, 5, 0), (-5, -5, 0)]
            for j, offset in enumerate(screw_offsets):
                screw_pos = (pos[0] + offset[0], pos[1] + offset[1], pos[2] + offset[2])
                logger.info(f"Installing screw {j+1}/4 for hinge {i+1}")
                self.gantry.pick_and_place(
                    ObjectType.CYLINDER,
                    pick_pos=(150, 100 + j*10, 10),
                    place_pos=screw_pos
                )
                # Simulate tightening
                self.gantry.drives[5].command_move(360, speed=180)
        
        # Phase 3: Install window (fragile)
        logger.info("Phase 3: Window installation")
        self.gantry.pick_and_place(
            ObjectType.FRAGILE,
            pick_pos=(150, 200, 10),
            place_pos=(300, 200, 25)
        )
        
        # Phase 4: Apply weather stripping (flexible material)
        logger.info("Phase 4: Weather stripping application")
        # Define weather strip path around the door
        strip_path = [
            (260, 150, 25), (260, 250, 25), (340, 250, 25), 
            (340, 150, 25), (260, 150, 25)
        ]
        
        self.gantry.select_gripper(ObjectType.SOFT)
        # Get weather strip roll
        self.gantry.move_to((200, 100, 20), (0, 0))
        self.gantry.extend_retract(True)
        self.gantry.operate_gripper(False)
        self.gantry.current_gripper.pick(ObjectType.FRAGILE)
        self.gantry.extend_retract(False)
        
        # Apply along the path
        for i, point in enumerate(strip_path):
            logger.info(f"Weather strip application point {i+1}/{len(strip_path)}")
            self.gantry.move_to(point, (0, -45))  # Tilt to apply pressure
            # Simulate pressing with force feedback
            force = self.gantry.force_sensor.get_force()
            logger.info(f"Application force: {force:.2f}N")
        
        self.gantry.operate_gripper(True)
        
        # Phase 5: Quality check
        logger.info("Phase 5: Door quality check")
        check_points = [
            (270, 160, 20), (270, 240, 20), (330, 240, 20), (330, 160, 20)
        ]
        
        for i, point in enumerate(check_points):
            logger.info(f"Quality check point {i+1}/4")
            self.gantry.move_to(point, (0, 0))
            self.gantry.extend_retract(True)
            # Read from corner force sensors
            force = self.corner_force_sensors[i].get_force()
            logger.info(f"Corner {i+1} test force: {force:.2f}N")
            if force < 5 or force > 50:
                logger.warning(f"Quality issue at corner {i+1}: force = {force:.2f}N")
            self.gantry.extend_retract(False)
        
        logger.info("Door panel assembly completed")

if __name__ == "__main__":
    start_time = datetime.now()
    logger.info(f"Assembly start time: {start_time}")
    
    door_station = DoorAssemblyStation()
    door_station.run_assembly_process()
    
    end_time = datetime.now()
    logger.info(f"Assembly end time: {end_time}")
    logger.info(f"Total assembly time: {end_time - start_time}")