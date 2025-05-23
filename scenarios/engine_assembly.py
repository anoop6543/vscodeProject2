import sys
import os
import time
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from SimpleGantrySimulation import GantryRobot, ObjectType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("engine_assembly.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def engine_assembly_sequence():
    logger.info("Starting engine assembly sequence")
    gantry = GantryRobot()
    
    # Engine block placement
    logger.info("Phase 1: Engine block positioning")
    gantry.pick_and_place(
        ObjectType.METAL_PART,
        pick_pos=(50, 50, 20),
        place_pos=(200, 200, 0)
    )
    
    # Crankshaft installation
    logger.info("Phase 2: Crankshaft installation")
    gantry.pick_and_place(
        ObjectType.CYLINDER,
        pick_pos=(80, 50, 20),
        place_pos=(200, 200, 10)
    )
    
    # Pistons installation - for each of 4 cylinders
    logger.info("Phase 3: Pistons installation")
    piston_pickup_locations = [
        (100, 60, 20), (100, 70, 20), (100, 80, 20), (100, 90, 20)
    ]
    piston_placement_locations = [
        (180, 190, 15), (200, 190, 15), (220, 190, 15), (240, 190, 15)
    ]
    
    for i, (pickup, placement) in enumerate(zip(piston_pickup_locations, piston_placement_locations)):
        logger.info(f"Installing piston {i+1}/4")
        # For pistons, we need more precision and careful handling
        gantry.move_to(pickup, (0, 0))
        gantry.extend_retract(True)
        # Slow down for precision
        gantry.drives[7].command_move(0, speed=50)  # Close gripper slowly
        logger.info(f"Force detected: {gantry.force_sensor.get_force():.2f}N")
        gantry.current_gripper.pick(ObjectType.METAL_PART)
        gantry.extend_retract(False)
        
        # Move to placement position with careful rotation
        gantry.move_to((placement[0], placement[1], placement[2] + 30), (90, 0))
        gantry.extend_retract(True)
        # Insert with slow vertical movement
        gantry.drives[2].command_move(placement[2], speed=100)  # Z-axis slow insertion
        gantry.drives[7].command_move(1, speed=50)  # Open gripper slowly
        gantry.current_gripper.place(placement)
        gantry.extend_retract(False)
        logger.info(f"Piston {i+1} installed successfully")
    
    # Cylinder head installation
    logger.info("Phase 4: Cylinder head placement")
    gantry.pick_and_place(
        ObjectType.METAL_PART,
        pick_pos=(150, 50, 20),
        place_pos=(210, 200, 25)
    )
    
    # Apply gasket (fragile handling)
    logger.info("Phase 5: Gasket application")
    gantry.pick_and_place(
        ObjectType.FRAGILE,
        pick_pos=(160, 50, 20),
        place_pos=(210, 200, 24)
    )
    
    # Bolts installation - precise pattern
    logger.info("Phase 6: Fastening bolts")
    bolt_locations = [
        (170, 180, 30), (170, 220, 30), (250, 180, 30), (250, 220, 30),
        (190, 200, 30), (230, 200, 30), (210, 180, 30), (210, 220, 30)
    ]
    
    for i, bolt_loc in enumerate(bolt_locations):
        logger.info(f"Installing bolt {i+1}/8")
        gantry.pick_and_place(
            ObjectType.CYLINDER,
            pick_pos=(180 + i*5, 50, 20),
            place_pos=bolt_loc
        )
        # Simulate tightening with rotation
        gantry.move_to(bolt_loc, (0, 0))
        for _ in range(5):  # Multiple rotations to simulate tightening
            gantry.drives[5].command_move(360, speed=120)  # Rotate
            time.sleep(0.5)  # Simulate time to tighten

    # Phase 6.5: Welding critical seam on cylinder head
    logger.info("Phase 6.5: Welding critical seam on cylinder head")
    # Define weld path (e.g., a short line on the cylinder head)
    # These points are illustrative and should align with the engine model.
    # Assuming the cylinder head is around (210, 200, 25)
    weld_start_point = (190, 190, 26) # Start point of the weld seam
    weld_end_point = (230, 190, 26)   # End point of the weld seam
    
    # Ensure gantry is at a safe height before starting weld sequence, if needed
    # gantry.move_to((weld_start_point[0], weld_start_point[1], weld_start_point[2] + 10), (0,0))

    gantry.laser_weld(
        start_point=weld_start_point,
        end_point=weld_end_point,
        speed=15,      # mm/s, adjusted for precision
        power=1800,    # Watts, typical for steel
        focus_setting=-0.2 # Focus slightly into the material
    )
    logger.info("Critical seam welding completed.")
    
    logger.info("Engine assembly sequence completed")

if __name__ == "__main__":
    start_time = datetime.now()
    logger.info(f"Starting time: {start_time}")
    engine_assembly_sequence()
    end_time = datetime.now()
    logger.info(f"Ending time: {end_time}")
    logger.info(f"Total duration: {end_time - start_time}")