import sys
import os
import logging
import random
import time
from typing import List, Dict, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from SimpleGantrySimulation import GantryRobot, ObjectType, Motor, Sensor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler("pcb_assembly.log"),
        logging.StreamHandler()
    ]
)

class Component:
    def __init__(self, name: str, size: float, weight: float, placement_force: float):
        self.name = name
        self.size = size  # mm
        self.weight = weight  # grams
        self.placement_force = placement_force  # Newtons
        self.logger = logging.getLogger(f"Component.{name}")
        
    def __str__(self):
        return f"{self.name} (size={self.size}mm, weight={self.weight}g)"

class PCBAssemblyLine:
    def __init__(self):
        self.robots = {
            "feeder": GantryRobot(),
            "placer": GantryRobot(),
            "inspector": GantryRobot()
        }
        self.conveyor_position = 0.0
        self.main_logger = logging.getLogger("PCBAssemblyLine")
        self.robot_loggers = {
            name: logging.getLogger(f"Robot.{name}") 
            for name in self.robots.keys()
        }
        
        # Component library
        self.components = [
            Component("Resistor_SMD", 2.0, 0.1, 1.0),
            Component("Capacitor_10uF", 3.0, 0.2, 1.5),
            Component("IC_MCU", 10.0, 1.0, 2.0),
            Component("IC_Memory", 8.0, 0.8, 2.0),
            Component("Connector_USB", 15.0, 3.0, 5.0),
            Component("Crystal_16MHz", 5.0, 0.3, 1.0),
            Component("LED_RGB", 3.0, 0.2, 1.0),
            Component("Inductor_10uH", 4.0, 0.5, 2.0),
            Component("Switch_Tactile", 6.0, 0.6, 3.0),
            Component("Diode_Schottky", 2.0, 0.1, 1.0)
        ]
        
        # Define component positions in feeder
        self.feeder_positions = {}
        for i, component in enumerate(self.components):
            self.feeder_positions[component.name] = (50 + (i % 5) * 30, 50 + (i // 5) * 30, 10)
            
        # Define PCB specifications - list of components and their positions
        self.pcb_spec = [
            # component_name, x, y, rotation
            ("IC_MCU", 200, 150, 0),
            ("IC_Memory", 200, 180, 0),
            ("Connector_USB", 160, 150, 90),
            ("Crystal_16MHz", 230, 160, 0),
            ("Capacitor_10uF", 240, 150, 0),
            ("Capacitor_10uF", 240, 160, 0),
            ("Resistor_SMD", 220, 140, 0),
            ("Resistor_SMD", 230, 140, 0),
            ("Resistor_SMD", 240, 140, 0),
            ("LED_RGB", 180, 170, 0),
            ("Switch_Tactile", 180, 190, 0),
            ("Inductor_10uH", 210, 190, 0),
            ("Diode_Schottky", 220, 190, 0),
        ]
        
        # Quality metrics
        self.placement_accuracy = []
        self.cycle_times = []
    
    def move_conveyor(self, distance: float):
        """Simulate conveyor movement"""
        self.main_logger.info(f"Moving conveyor by {distance}mm")
        self.conveyor_position += distance
        time.sleep(abs(distance) / 100)  # Simulate time to move conveyor
        
    def get_component_by_name(self, name: str) -> Component:
        """Find a component by name"""
        for component in self.components:
            if component.name == name:
                return component
        raise ValueError(f"Component {name} not found in library")
    
    def pick_component(self, robot_name: str, component_name: str) -> bool:
        """Pick a component from the feeder"""
        robot = self.robots[robot_name]
        logger = self.robot_loggers[robot_name]
        
        try:
            component = self.get_component_by_name(component_name)
            feeder_pos = self.feeder_positions[component_name]
            
            logger.info(f"Picking {component}")
            
            # Select appropriate gripper based on component size
            if component.size <= 3.0:
                obj_type = ObjectType.FRAGILE
            elif component.weight > 2.0:
                obj_type = ObjectType.METAL_PART
            else:
                obj_type = ObjectType.CYLINDER
                
            robot.select_gripper(obj_type)
            robot.move_to(feeder_pos, (0, 0))
            robot.extend_retract(True)
            
            # Adjust picking speed based on component size/fragility
            if component.size <= 3.0:
                robot.drives[7].command_move(0, speed=50)  # Close gripper slowly
            else:
                robot.operate_gripper(False)
                
            force = robot.force_sensor.get_force()
            logger.info(f"Pickup force: {force:.2f}N")
            
            # Check if force is appropriate
            if force > component.placement_force * 2:
                logger.warning(f"Excessive pickup force: {force:.2f}N")
                
            robot.current_gripper.pick(obj_type)
            robot.extend_retract(False)
            return True
            
        except Exception as e:
            logger.error(f"Error picking component: {e}")
            return False
    
    def place_component(self, robot_name: str, component_name: str, 
                        position: Tuple[float, float, float], rotation: float) -> bool:
        """Place a component on the PCB"""
        robot = self.robots[robot_name]
        logger = self.robot_loggers[robot_name]
        
        try:
            component = self.get_component_by_name(component_name)
            logger.info(f"Placing {component} at {position} with rotation {rotation}°")
            
            # Move to position with proper rotation
            robot.move_to((position[0], position[1], position[2] + 20), (rotation, 0))
            
            # Slow approach for precision
            for height in range(20, 0, -2):
                robot.drives[2].command_move(position[2] + height, speed=50)
                time.sleep(0.05)  # Small delay for precision
            
            # Apply correct placement force
            force = robot.force_sensor.get_force()
            logger.info(f"Placement force before adjustment: {force:.2f}N")
            
            # Adjust force if needed
            target_force = component.placement_force
            if force < target_force * 0.8:
                logger.info(f"Increasing placement force to reach target {target_force:.2f}N")
                # Simulate pressing slightly more
                robot.drives[2].command_move(position[2] - 0.5, speed=20)
                force = robot.force_sensor.get_force()
                logger.info(f"Adjusted placement force: {force:.2f}N")
            
            # Release component
            if component.size <= 3.0:
                robot.drives[7].command_move(1, speed=50)  # Open gripper slowly
            else:
                robot.operate_gripper(True)
                
            # Record placement accuracy (simulated)
            placement_error = random.uniform(0, 0.5)  # mm error
            self.placement_accuracy.append(placement_error)
            logger.info(f"Placement accuracy: ±{placement_error:.3f}mm")
            
            # Log if placement error is too high
            if placement_error > 0.3:
                logger.warning(f"Placement accuracy exceeds threshold: {placement_error:.3f}mm")
            
            robot.extend_retract(False)
            return True
            
        except Exception as e:
            logger.error(f"Error placing component: {e}")
            return False
    
    def inspect_component(self, robot_name: str, component_name: str, 
                          position: Tuple[float, float, float]) -> bool:
        """Inspect a placed component"""
        robot = self.robots[robot_name]
        logger = self.robot_loggers[robot_name]
        
        logger.info(f"Inspecting {component_name} at {position}")
        
        # Move to inspection position
        robot.move_to((position[0], position[1], position[2] + 10), (0, 45))  # Tilt for camera angle
        
        # Simulate inspection process
        inspection_results = {
            "presence": random.uniform(0, 1) > 0.05,  # 95% chance component is present
            "alignment": random.uniform(0, 1) > 0.1,  # 90% chance alignment is good
            "polarity": random.uniform(0, 1) > 0.05,  # 95% chance polarity is correct
            "solder": random.uniform(0, 1) > 0.2,     # 80% chance solder is good
        }
        
        # Log inspection results
        for check, result in inspection_results.items():
            status = "PASS" if result else "FAIL"
            if result:
                logger.info(f"Inspection - {check}: {status}")
            else:
                logger.warning(f"Inspection - {check}: {status}")
        
        # Overall pass/fail
        overall_result = all(inspection_results.values())
        if overall_result:
            logger.info("Component inspection PASSED")
        else:
            logger.warning("Component inspection FAILED")
            
        return overall_result
    
    def run_assembly(self, pcb_count: int = 1):
        """Run the assembly process for multiple PCBs"""
        self.main_logger.info(f"Starting assembly of {pcb_count} PCBs")
        
        for pcb_index in range(pcb_count):
            pcb_start_time = datetime.now()
            self.main_logger.info(f"Assembly of PCB {pcb_index+1}/{pcb_count} started")
            
            # Load new PCB
            self.move_conveyor(300)
            
            # Process each component from the PCB spec
            for comp_index, (comp_name, x, y, rotation) in enumerate(self.pcb_spec):
                self.main_logger.info(f"Processing component {comp_index+1}/{len(self.pcb_spec)}: {comp_name}")
                
                component_start_time = datetime.now()
                
                # 1. Pick component with feeder robot
                pick_success = self.pick_component("feeder", comp_name)
                if not pick_success:
                    self.main_logger.error(f"Failed to pick {comp_name}, skipping")
                    continue
                
                # 2. Transfer to placer robot (simulated)
                self.main_logger.info(f"Transferring {comp_name} from feeder to placer robot")
                time.sleep(0.5)  # Simulate transfer time
                
                # 3. Place component with placer robot
                pcb_position = (x, y, 5)  # Z=5mm is PCB surface
                place_success = self.place_component("placer", comp_name, pcb_position, rotation)
                if not place_success:
                    self.main_logger.error(f"Failed to place {comp_name}, skipping inspection")
                    continue
                
                # 4. Inspect component with inspector robot
                inspection_success = self.inspect_component("inspector", comp_name, pcb_position)
                
                # Record cycle time for this component
                component_end_time = datetime.now()
                cycle_time = (component_end_time - component_start_time).total_seconds()
                self.cycle_times.append(cycle_time)
                self.main_logger.info(f"Component cycle time: {cycle_time:.2f} seconds")
                
                # Rework if needed
                if not inspection_success:
                    self.main_logger.warning(f"Rework needed for {comp_name}")
                    # Simulate rework process
                    self.pick_component("placer", comp_name)
                    time.sleep(1.0)  # Simulate rework time
                    self.place_component("placer", comp_name, pcb_position, rotation)
                    reinspection = self.inspect_component("inspector", comp_name, pcb_position)
                    self.main_logger.info(f"Rework result: {'SUCCESS' if reinspection else 'FAILURE'}")

            # After loop, before moving PCB out:
            self.main_logger.info(f"All components processed for PCB {pcb_index+1}. Proceeding to laser marking.")
            
            # Assume marking is done by the 'inspector' robot
            inspector_robot = self.robots["inspector"]
            
            # Define marking parameters
            # Position can be relative to PCB or a fixed station point
            # Let's assume the PCB is at conveyor_position + some offset for the center.
            # Current conveyor_position would be 300 after loading this PCB.
            # Let's mark near the center of a typical PCB of size, say, 100x100, placed at x=200, y=150.
            # If the conveyor moves the PCB origin to (0,0) at the station, then mark_target_point would be relative to PCB.
            # For simplicity, let's use a fixed point relative to the gantry's workspace that represents the marking station for the PCB.
            # Assuming the PCB is now at a position where (e.g. 200,150) on PCB is (200,150) in gantry coordinates.
            mark_target_point = (200 + 50, 150 + 50, 5 + 1) # Mark on top of PCB, slightly offset from center, Z just above surface.
            serial_number = f"PCB_SN_{datetime.now().strftime('%Y%m%d%H%M%S')}_{pcb_index+1}"
            
            self.robot_loggers["inspector"].info(f"Performing laser marking for PCB {pcb_index+1}. Serial: {serial_number}")
            inspector_robot.laser_mark(
                target_point=mark_target_point,
                text=serial_number,
                speed=150, # mm/s
                power=30,  # Watts for marking
                font_size=2 # Small font for PCB
            )
            self.robot_loggers["inspector"].info(f"Laser marking completed for PCB {pcb_index+1}")
            
            # Move completed PCB out
            self.move_conveyor(300)
            
            # Calculate PCB assembly time
            pcb_end_time = datetime.now()
            pcb_time = (pcb_end_time - pcb_start_time).total_seconds()
            self.main_logger.info(f"PCB {pcb_index+1} completed in {pcb_time:.2f} seconds")
        
        # Print final statistics
        self.report_statistics()
    
    def report_statistics(self):
        """Report assembly statistics"""
        self.main_logger.info("====== ASSEMBLY STATISTICS ======")
        
        if self.cycle_times:
            avg_cycle = sum(self.cycle_times) / len(self.cycle_times)
            self.main_logger.info(f"Average component cycle time: {avg_cycle:.2f} seconds")
            self.main_logger.info(f"Fastest component: {min(self.cycle_times):.2f} seconds")
            self.main_logger.info(f"Slowest component: {max(self.cycle_times):.2f} seconds")
        
        if self.placement_accuracy:
            avg_accuracy = sum(self.placement_accuracy) / len(self.placement_accuracy)
            self.main_logger.info(f"Average placement accuracy: ±{avg_accuracy:.3f}mm")
            self.main_logger.info(f"Best placement: ±{min(self.placement_accuracy):.3f}mm")
            self.main_logger.info(f"Worst placement: ±{max(self.placement_accuracy):.3f}mm")

if __name__ == "__main__":
    assembly_line = PCBAssemblyLine()
    assembly_line.run_assembly(pcb_count=3)  # Assemble 3 PCBs