import sys
import os
import logging
from datetime import datetime
import math

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from SimpleGantrySimulation import GantryRobot, ObjectType, ForceSensor
from laser_marker import create_laser_marker
from laser_marker_adapter import LaserMarkerAdapter

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

            # New arc move:
            logger.info(f"Moving to approach hinge {i+1} area with an arc path")
            # Get current gantry position (X, Y, Z) from motors
            # Assuming motor indices 0, 1, 2 are X, Y, Z respectively
            arc_start_point = (self.gantry.motors[0].position, 
                               self.gantry.motors[1].position, 
                               self.gantry.motors[2].position)
            arc_end_point_xyz = (pos[0]-50, pos[1], pos[2]+30) # Target endpoint for the arc
            
            # Define a center for the arc, e.g. offset from start or midpoint
            # For simplicity, let's try to make a gentle curve.
            # If start_x is far from end_x, use that difference. Otherwise, create an offset perpendicular to the general direction.
            # Let's use a simpler center calculation for now:
            arc_center_x = (arc_start_point[0] + arc_end_point_xyz[0]) / 2
            arc_center_y = arc_start_point[1] + 50 # Create a curve by offsetting Y
            arc_center_xy = (arc_center_x, arc_center_y)
            
            # Ensure the start_point for arc_move is indeed where the gantry is.
            # The arc_move itself does not move to start_point, it calculates path from it.
            # Current gantry.move_to updates motor positions, so arc_start_point should be accurate.

            self.gantry.arc_move(start_point=arc_start_point, 
                                 end_point=arc_end_point_xyz, 
                                 center_point=arc_center_xy, 
                                 speed=800)
            # After arc_move, gantry is at arc_end_point_xyz. Now set desired orientation.
            self.gantry.move_to(arc_end_point_xyz, (45,0)) # Ensure final orientation is set

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
            (340, 150, 25), (260, 150, 25) # Back to start to complete loop
        ]

        # New spiral move for sealant application at a corner before stripping:
        # This simulates applying a circular bead of sealant before placing the main strip.
        sealant_application_center = (strip_path[0][0] - 5, strip_path[0][1] - 5) # Near the start of the strip path
        sealant_z_level = strip_path[0][2] # Same Z as weather strip
        
        logger.info(f"Applying sealant in a spiral pattern at {sealant_application_center} before weather stripping.")
        # First, move to a safe start Z above the sealant application point
        self.gantry.move_to((sealant_application_center[0], sealant_application_center[1], sealant_z_level + 20), (0,0))
        
        self.gantry.spiral_move(
            center_xy=sealant_application_center,
            start_radius=2,  # Start with a small radius
            end_radius=10,   # Spiral outwards to a 10mm radius
            total_angle_rad=math.pi * 4,  # Two full rotations (2 * 2pi)
            z_start=sealant_z_level,      # Start at the application Z
            z_increment_per_rad=0.05,     # Slightly go down as it spirals (0.05mm per radian)
                                          # Total Z change: 0.05 * 4 * pi approx 0.628 mm
            speed=300                     # Speed for spiral segments
        )
        logger.info("Sealant application spiral complete.")
        
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