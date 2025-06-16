"""
Visual Simulation Runner

This script provides a simple interface to run the different simulation scenarios
with visual representation.
"""

import os
import sys
import time
import argparse
import importlib
from enum import Enum

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from SimpleGantrySimulation import GantryRobot, ObjectType
from visualization.visual_sim import create_visualization, run_visualization_with_scenario

class ScenarioType(Enum):
    DOOR_ASSEMBLY = "door_assembly"
    ENGINE_ASSEMBLY = "engine_assembly"
    PCB_ASSEMBLY = "pcb_assembly"
    DEMO = "demo"

def run_demo(robot, vis=None):
    """
    Run a simple demo of the gantry robot movements.
    
    Args:
        robot: The GantryRobot instance to use.
        vis: Optional VisualSimulation instance.
    """
    print("Running demo scenario")
    
    # Pick and place operations
    robot.pick_and_place(
        ObjectType.METAL_PART,
        pick_pos=(100, 100, 10),
        place_pos=(200, 100, 10)
    )
    
    robot.pick_and_place(
        ObjectType.CYLINDER,
        pick_pos=(100, -100, 10),
        place_pos=(200, -100, 10)
    )
    
    robot.pick_and_place(
        ObjectType.BOX,
        pick_pos=(-100, 100, 10),
        place_pos=(-200, 100, 10)
    )
    
    robot.pick_and_place(
        ObjectType.SHEET,
        pick_pos=(-100, -100, 10),
        place_pos=(-200, -100, 10)
    )
    
    # Arc movement
    print("Testing arc movement")
    robot.arc_move(
        start_point=(0, 0, 20),
        end_point=(100, 100, 20),
        center_point=(0, 100),
        speed=500
    )
    
    # Spiral movement
    print("Testing spiral movement")
    robot.spiral_move(
        center_xy=(0, 0),
        start_radius=50,
        end_radius=100,
        total_angle_rad=6.28,  # 2*pi
        z_start=10,
        z_increment_per_rad=1,
        speed=500
    )
    
    # Laser welding
    print("Testing laser welding")
    robot.laser_weld(
        start_point=(0, 0, 10),
        end_point=(100, 0, 10),
        speed=10,
        power=1000,
        focus_setting=0.5
    )
    
    # Laser marking
    print("Testing laser marking")
    robot.laser_mark(
        target_point=(0, 0, 10),
        text="SERIAL123",
        speed=10,
        power=500,
        font_size=12
    )
    
    print("Demo completed")

def run_door_assembly():
    """Run the door assembly scenario with visualization."""
    from scenarios.door_assembly import DoorAssemblyStation
    
    door_station = DoorAssemblyStation()
    robot, vis = create_visualization(door_station.gantry)
    
    # Start visualization
    vis.start()
    
    # Run the scenario
    vis.run_scenario(door_station.run_assembly_process)
    
    return robot, vis

def run_engine_assembly():
    """Run the engine assembly scenario with visualization."""
    from scenarios.engine_assembly import engine_assembly_sequence
    
    return run_visualization_with_scenario(engine_assembly_sequence)

def run_pcb_assembly():
    """Run the PCB assembly scenario with visualization."""
    from scenarios.pcb_assembly import PCBAssemblyLine
    
    assembly_line = PCBAssemblyLine()
    
    # Just visualize the main gantry robot
    # You'll need to adapt this based on how PCBAssemblyLine is structured
    # and which robot you want to visualize
    if hasattr(assembly_line, 'gantry'):
        robot, vis = create_visualization(assembly_line.gantry)
    else:
        robot, vis = create_visualization()
    
    # Start visualization
    vis.start()
    
    # Run the scenario
    vis.run_scenario(assembly_line.run_assembly, pcb_count=3)
    
    return robot, vis

def run_demo_scenario():
    """Run the demo scenario with visualization."""
    robot, vis = create_visualization()
    
    # Start visualization
    vis.start()
    
    # Run the demo
    vis.run_scenario(run_demo, robot, vis)
    
    return robot, vis

def main():
    """Main entry point for the visual simulation runner."""
    parser = argparse.ArgumentParser(description="Run gantry robot simulation with visualization")
    parser.add_argument(
        "scenario",
        type=str,
        choices=[s.value for s in ScenarioType],
        help="Scenario to run"
    )
    args = parser.parse_args()
    
    scenario_type = ScenarioType(args.scenario)
    
    try:
        if scenario_type == ScenarioType.DOOR_ASSEMBLY:
            robot, vis = run_door_assembly()
        elif scenario_type == ScenarioType.ENGINE_ASSEMBLY:
            robot, vis = run_engine_assembly()
        elif scenario_type == ScenarioType.PCB_ASSEMBLY:
            robot, vis = run_pcb_assembly()
        elif scenario_type == ScenarioType.DEMO:
            robot, vis = run_demo_scenario()
        
        print(f"Press ESC to exit the {scenario_type.value} visualization")
        
        # Keep the main thread alive until the visualization is closed
        try:
            while vis.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Interrupted by user")
        finally:
            vis.stop()
    
    except Exception as e:
        print(f"Error running scenario {scenario_type.value}: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
