"""
Test script for LaserMarker and LaserMarkerAdapter

This script demonstrates how to use the LaserMarker classes and LaserMarkerAdapter
to integrate laser marker functionality with the GantryRobot simulation.
"""

import sys
import os
import logging
import time
from typing import Tuple

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from SimpleGantrySimulation import GantryRobot, ObjectType
from laser_marker import create_laser_marker, LaserMarkerType, LaserOperationMode, LaserMarkerStatus
from laser_marker_adapter import LaserMarkerAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler("laser_marker_test.log"),
        logging.StreamHandler()
    ]
)

def test_laser_marker():
    """Test basic laser marker functionality."""
    logger = logging.getLogger("test_laser_marker")
    logger.info("Testing LaserMarker classes...")
    
    # Create Keyence laser marker
    keyence = create_laser_marker("keyence", "MD-F3000")
    logger.info(f"Created {keyence}")
    
    # Test marking operation
    keyence.mark(
        target_point=(100, 100, 10),
        text="SERIAL-123456",
        power=30,
        speed=100,
        font_size=8.0
    )
    
    # Test welding operation
    keyence.weld(
        start_point=(150, 50, 20),
        end_point=(200, 50, 20),
        power=50,
        speed=10,
        focus_setting=0.2
    )
    
    # Create TRUMPF laser marker
    trumpf = create_laser_marker("trumpf", "TruMark 5010")
    logger.info(f"Created {trumpf}")
    
    # Test marking operation
    trumpf.mark(
        target_point=(120, 120, 15),
        text="BATCH-XYZ-789",
        power=40,
        speed=120,
        font_size=10.0
    )
    
    # Test model-specific operations
    keyence.save_job("job1", {"text": "TEST-123", "position": (100, 100, 10)})
    keyence.load_job("job1")
    keyence.run_job()
    
    trumpf.save_program("program1", {"text": "TRUMPF-TEST", "position": (120, 120, 15)})
    trumpf.load_program("program1")
    trumpf.execute_program()
    
    logger.info("LaserMarker tests completed successfully")

def test_adapter_with_gantry():
    """Test LaserMarkerAdapter with GantryRobot."""
    logger = logging.getLogger("test_adapter_with_gantry")
    logger.info("Testing LaserMarkerAdapter with GantryRobot...")
    
    # Create a GantryRobot instance
    gantry = GantryRobot()
    
    # Create an adapter with a Keyence laser marker
    adapter = LaserMarkerAdapter(gantry, vendor="keyence", model="MD-F3000")
    logger.info(f"Created adapter with {adapter.get_laser_marker().name}")
    
    # Test laser_weld via the adapter
    gantry.laser_weld(
        start_point=(50, 50, 20),
        end_point=(150, 50, 20),
        speed=15,
        power=45,
        focus_setting=0.0
    )
    
    # Test laser_mark via the adapter
    gantry.laser_mark(
        target_point=(200, 200, 10),
        text="GANTRY-TEST-123",
        speed=100,
        power=30,
        font_size=5.0
    )
    
    # Switch to a different laser marker
    adapter.replace_laser_marker("trumpf", "TruMark 6130")
    logger.info(f"Switched to {adapter.get_laser_marker().name}")
    
    # Test with the new laser marker
    gantry.laser_weld(
        start_point=(100, 100, 25),
        end_point=(200, 100, 25),
        speed=20,
        power=80,
        focus_setting=-0.2
    )
    
    logger.info("LaserMarkerAdapter tests completed successfully")

def test_coherent_laser_marker():
    """Test the Coherent laser marker functionality."""
    logger = logging.getLogger("test_coherent_laser_marker")
    logger.info("Testing Coherent LaserMarker...")
    
    # Create Coherent laser marker
    coherent = create_laser_marker("coherent", "StarFiber 150")
    logger.info(f"Created {coherent}")
    
    # Test marking operation
    coherent.mark(
        target_point=(150, 150, 12),
        text="COHERENT-TEST-456",
        power=40,
        speed=140,
        font_size=7.5
    )
    
    # Test welding operation
    coherent.weld(
        start_point=(180, 70, 25),
        end_point=(230, 70, 25),
        power=120,
        speed=12,
        focus_setting=-0.3
    )
    
    # Test job saving and loading
    coherent.save_job("coherent_job1", {
        "text": "COHERENT-JOB-TEST",
        "position": (150, 150, 12),
        "power": 35,
        "speed": 130
    })
    
    coherent.load_job("coherent_job1")
    coherent.run_job()
    
    logger.info("Coherent LaserMarker tests completed successfully")

def modify_engine_assembly_scenario():
    """
    Demonstrate how to modify the engine_assembly.py scenario
    to use the LaserMarkerAdapter with a specific laser marker.
    """
    logger = logging.getLogger("modify_engine_assembly")
    logger.info("Demonstrating engine assembly scenario modification...")
    
    # Print the code that would be added to engine_assembly.py
    code = """
# At the top of the file, add these imports:
from laser_marker import create_laser_marker
from laser_marker_adapter import LaserMarkerAdapter

# Inside the engine_assembly_sequence function, before the welding step:
def engine_assembly_sequence():
    # ... existing code ...
    
    # Phase 6.5: Welding critical seam on cylinder head
    logger.info("Phase 6.5: Welding critical seam on cylinder head")
    
    # Create a laser marker adapter with a high-power fiber laser for welding
    laser_adapter = LaserMarkerAdapter(gantry, vendor="trumpf", model="TruMark 6130")
    logger.info(f"Using {laser_adapter.get_laser_marker().name} for cylinder head welding")
    
    # Define weld path
    weld_start_point = (190, 190, 26)
    weld_end_point = (230, 190, 26)
    
    # The laser_weld method now uses the TruMark laser through the adapter
    gantry.laser_weld(
        start_point=weld_start_point,
        end_point=weld_end_point,
        speed=15,
        power=1800,
        focus_setting=-0.2
    )
    logger.info("Critical seam welding completed.")
    
    # ... continue with the rest of the sequence ...
"""
    print(code)
    logger.info("See printed code for how to modify engine_assembly.py")

def modify_pcb_assembly_scenario():
    """
    Demonstrate how to modify the pcb_assembly.py scenario
    to use the LaserMarkerAdapter with a specific laser marker.
    """
    logger = logging.getLogger("modify_pcb_assembly")
    logger.info("Demonstrating PCB assembly scenario modification...")
    
    # Print the code that would be added to pcb_assembly.py
    code = """
# At the top of the file, add these imports:
from laser_marker import create_laser_marker
from laser_marker_adapter import LaserMarkerAdapter

# Inside the PCBAssemblyLine class's __init__ method, add:
def __init__(self):
    # ... existing code ...
    
    # Create laser marker adapters for the robots
    self.laser_adapters = {}
    # Use Keyence for the inspector robot (good for marking)
    self.laser_adapters["inspector"] = LaserMarkerAdapter(
        self.robots["inspector"], 
        vendor="keyence", 
        model="MD-X1500"
    )
    self.main_logger.info(f"Using {self.laser_adapters['inspector'].get_laser_marker().name} for PCB marking")

# Then in the run_assembly method, the laser marking code remains the same:
inspector_robot.laser_mark(
    target_point=mark_target_point,
    text=serial_number,
    speed=150,
    power=30,
    font_size=2
)
# The adapter takes care of using the Keyence laser marker
"""
    print(code)
    logger.info("See printed code for how to modify pcb_assembly.py")

def modify_door_assembly_scenario():
    """
    Demonstrate how to modify the door_assembly.py scenario
    to use the LaserMarkerAdapter with a Coherent laser marker.
    """
    logger = logging.getLogger("modify_door_assembly")
    logger.info("Demonstrating door assembly scenario modification...")
    
    # Print the code that would be added to door_assembly.py
    code = """
# At the top of the file, add these imports:
from laser_marker import create_laser_marker
from laser_marker_adapter import LaserMarkerAdapter

# Inside the door_assembly_sequence function, add:
def door_assembly_sequence():
    # ... existing code ...
    
    # Phase 4.5: Adding laser-cut seal channels before applying sealant
    logger.info("Phase 4.5: Adding laser-cut seal channels before applying sealant")
    
    # Create a laser marker adapter with a CO2 laser for cutting
    laser_adapter = LaserMarkerAdapter(gantry, vendor="coherent", model="Diamond CO2")
    
    # Define cut points for the sealant channel
    cut_start_point = (door_width - 20, 20, 5)
    cut_end_point = (door_width - 150, 20, 5)
    
    # The laser_weld method can be used for cutting when using a CO2 laser
    # with the right power and speed settings
    gantry.laser_weld(
        start_point=cut_start_point,
        end_point=cut_end_point,
        speed=25,
        power=180,
        focus_setting=0.5
    )
    
    logger.info(f"Using {laser_adapter.get_laser_marker().name} for seal channel cutting")
    logger.info("Seal channel cutting completed.")
    
    # ... continue with the existing sealant application using spiral_move ...
"""
    print(code)
    logger.info("See printed code for how to modify door_assembly.py")

if __name__ == "__main__":
    print("\n=== Testing Laser Marker Classes ===\n")
    test_laser_marker()
    
    print("\n=== Testing Laser Marker Adapter with GantryRobot ===\n")
    test_adapter_with_gantry()
    
    print("\n=== Testing Coherent Laser Marker ===\n")
    test_coherent_laser_marker()
    
    print("\n=== Example: Modifying Engine Assembly Scenario ===\n")
    modify_engine_assembly_scenario()
    
    print("\n=== Example: Modifying PCB Assembly Scenario ===\n")
    modify_pcb_assembly_scenario()
    
    print("\n=== Example: Modifying Door Assembly Scenario ===\n")
    modify_door_assembly_scenario()
    
    print("\n=== Example: Modifying Door Assembly Scenario ===\n")
    modify_door_assembly_scenario()
