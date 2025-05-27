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
import sim_database_manager as dbm # Use an alias for convenience
import file_logger # For structured file logging
from sim_opc_server import sim_opc_instance # OPC server instance

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
        self.inspection_results_summary = [] # For tracking pass/fail of components on current PCB
        self.pcb_recipe_id = None # To store the ID of the created recipe
    
    def move_conveyor(self, distance: float):
        """Simulate conveyor movement"""
        self.main_logger.info(f"Moving conveyor by {distance}mm")
        sim_opc_instance.write_tag("Conveyor.IsRunning", True)
        self.conveyor_position += distance
        time.sleep(abs(distance) / 100)  # Simulate time to move conveyor
        sim_opc_instance.write_tag("Conveyor.IsRunning", False)
        self.main_logger.info(f"Conveyor movement finished. OPC tag Conveyor.IsRunning updated.")
        
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
            # Log error to file_logger
            file_logger.log_error(
                machine_id=f"Robot.{robot_name}",
                error_code="PICK_EXCEPTION_002",
                description=f"Exception during pick of {component_name}: {str(e)}",
                severity="high",
                scenario_context=f"Component: {component_name}" # pcb_index not available here
            )
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
            # Log error to file_logger
            file_logger.log_error(
                machine_id=f"Robot.{robot_name}",
                error_code="PLACE_EXCEPTION_003",
                description=f"Exception during place of {component_name}: {str(e)}",
                severity="high",
                scenario_context=f"Component: {component_name}" # pcb_index not available here
            )
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

        # --- Example: Create a sample recipe for the PCB being assembled ---
        # (This is a simplified example; in a real system, recipes would be pre-loaded or selected)
        self.pcb_recipe_id = dbm.create_recipe(
            name=f"Standard PCB Assembly - {datetime.now().strftime('%Y%m%d_%H%M')}", # Ensure unique name for demo
            ingredients=[comp.name for comp in self.components[:5]], # Sample ingredients: first 5 components
            steps=[f"Place {spec[0]} at ({spec[1]},{spec[2]})" for spec in self.pcb_spec] # Sample steps from spec
        )
        self.main_logger.info(f"Created/loaded Recipe ID {self.pcb_recipe_id} for current PCB type.")
        retrieved_recipe = dbm.get_recipe(self.pcb_recipe_id)
        if retrieved_recipe: # Check if recipe was found
            self.main_logger.info(f"Recipe details: {retrieved_recipe['name']}, {len(retrieved_recipe['ingredients'])} ingredients, {len(retrieved_recipe['steps'])} steps.")
        else:
            self.main_logger.error(f"Could not retrieve recipe ID {self.pcb_recipe_id} after creation.")

        for pcb_index in range(pcb_count):
            pcb_start_time = datetime.now()
            self.main_logger.info(f"Assembly of PCB {pcb_index+1}/{pcb_count} started")
            self.inspection_results_summary = [] # Reset for current PCB
            
            # Load new PCB
            self.move_conveyor(300)
            
            # Process each component from the PCB spec
            for comp_index, (comp_name, x, y, rotation) in enumerate(self.pcb_spec):
                self.main_logger.info(f"Processing component {comp_index+1}/{len(self.pcb_spec)}: {comp_name}")
                
                component_start_time = datetime.now()
                
                
                # 1. Pick component with feeder robot
                # OPC: Simulate reading a sensor for item presence before picking
                item_present_tag_id = f"SimPLC.Feeder.{comp_name}.ItemPresent"
                if not sim_opc_instance.read_tag(item_present_tag_id):
                    sim_opc_instance.add_tag(item_present_tag_id, True) # Assume item is present for demo
                    self.main_logger.info(f"OPC: Added and set dummy tag {item_present_tag_id} to True for demo.")

                item_present_opc_data = sim_opc_instance.read_tag(item_present_tag_id)
                item_is_present = item_present_opc_data['value'] if item_present_opc_data else False
                
                self.main_logger.info(f"OPC Check: {item_present_tag_id} = {item_is_present}")

                pick_success = False # Initialize before conditional pick
                if item_is_present:
                    pick_success = self.pick_component("feeder", comp_name)
                else:
                    self.main_logger.warning(f"OPC: Item {comp_name} not present in feeder. Skipping pick.")
                
                if not pick_success:
                    self.main_logger.error(f"Failed to pick {comp_name} (Item present: {item_is_present}), skipping")
                    # --- Log error using file_logger ---
                    file_logger.log_error(
                        machine_id="Robot.feeder", # Specific robot causing the error
                        error_code="PICK_FAIL_PCB_001",
                        description=f"Failed to pick component: {comp_name}",
                        severity="medium",
                        scenario_context=f"PCB_Index_{pcb_index}_Component_{comp_name}"
                    )
                    # self.main_logger.info(f"Error logged for pick failure of {comp_name}.") # Keep if desired
                    self.inspection_results_summary.append(False) # Log failure for this component
                    continue
                
                # 2. Transfer to placer robot (simulated)
                self.main_logger.info(f"Transferring {comp_name} from feeder to placer robot")
                time.sleep(0.5)  # Simulate transfer time
                
                # 3. Place component with placer robot
                pcb_position = (x, y, 5)  # Z=5mm is PCB surface
                place_success = self.place_component("placer", comp_name, pcb_position, rotation)
                if not place_success:
                    self.main_logger.error(f"Failed to place {comp_name}, skipping inspection")
                    # --- Log error using file_logger ---
                    file_logger.log_error(
                        machine_id="Robot.placer", # Specific robot causing the error
                        error_code="PLACE_FAIL_PCB_001",
                        description=f"Failed to place component: {comp_name}",
                        severity="medium",
                        scenario_context=f"PCB_Index_{pcb_index}_Component_{comp_name}"
                    )
                    self.inspection_results_summary.append(False) # Log failure for this component
                    continue
                
                # 4. Inspect component with inspector robot
                inspection_success = self.inspect_component("inspector", comp_name, pcb_position)
                
                # Record cycle time for this component
                component_end_time = datetime.now()
                cycle_time = (component_end_time - component_start_time).total_seconds()
                self.cycle_times.append(cycle_time)
                self.main_logger.info(f"Component cycle time: {cycle_time:.2f} seconds")
                
                # Record cycle time for this component
                component_end_time = datetime.now()
                cycle_time = (component_end_time - component_start_time).total_seconds()
                self.cycle_times.append(cycle_time)
                self.main_logger.info(f"Component cycle time: {cycle_time:.2f} seconds")
                
                self.inspection_results_summary.append(inspection_success) # Track result for this component

                # Rework if needed
                if not inspection_success:
                    self.main_logger.warning(f"Rework needed for {comp_name}")
                    # Simulate rework process
                    # For rework, let's log another potential error if rework pick fails
                    rework_pick_success = self.pick_component("placer", comp_name) 
                    if not rework_pick_success:
                        dbm.create_error(
                            machine_id="Robot.placer",
                            error_code="REWORK_PICK_FAIL_002",
                            description=f"Failed to pick {comp_name} for rework.",
                            severity="high"
                        )
                        self.main_logger.error(f"Error logged for rework pick failure of {comp_name}.")
                        # If rework pick fails, the component remains failed for this PCB
                    else:
                        time.sleep(1.0)  # Simulate rework time
                        self.place_component("placer", comp_name, pcb_position, rotation)
                        reinspection = self.inspect_component("inspector", comp_name, pcb_position)
                        self.main_logger.info(f"Rework result: {'SUCCESS' if reinspection else 'FAILURE'}")
                        # Update the summary for this component based on reinspection if needed,
                        # for simplicity, we'll assume the initial failure still marks the PCB as potentially flawed.
                        # Or, if rework makes it good, find the last False and update it.
                        # For now, the initial failure is recorded. A more complex system would handle this.


            # After component loop, before moving PCB out:
            self.main_logger.info(f"All components processed for PCB {pcb_index+1}. Proceeding to final checks, laser marking, and result logging.")

            # --- Simulate a final PCB-level critical fault detection ---
            # This is a conceptual example. In a real scenario, this might be based on multiple failed inspections.
            # For demonstration, let's assume 1 out of 5 PCBs has a critical fault found by the inspection station.
            
            # Ensure pcb_index is available from the main loop: for pcb_index in range(pcb_count):
            # The prompt uses (pcb_index + 1) % 5 == 0. Let's use pcb_index % 4 == 0 for variety (0, 4, 8...)
            # to ensure it triggers on the first PCB if pcb_count is 1 and also for the 5th if pcb_count is 5.
            # Let's stick to the prompt's (pcb_index + 1) % 5 == 0 for consistency.
            if (pcb_index + 1) % 5 == 0: 
                critical_fault_description = f"Critical fault detected on PCB {pcb_index + 1} (e.g., board crack)."
                faulting_station_id = "InspectionStation_01" # Example station ID
                error_code_critical = "INSP_CRITICAL_001"

                self.main_logger.warning(f"OPC_DB_LINK: {critical_fault_description} at {faulting_station_id}")

                # 1. Update OPC Tag to reflect the fault status
                opc_station_status_tag = f"PCBLine.{faulting_station_id}.Status"
                sim_opc_instance.write_tag(opc_station_status_tag, "CriticalFault")
                self.main_logger.info(f"OPC_DB_LINK: Updated OPC tag {opc_station_status_tag} to CriticalFault.")

                # 2. Log this critical fault to file_logger
                file_logger.log_error(
                    machine_id=faulting_station_id,
                    error_code=error_code_critical,
                    description=critical_fault_description,
                    severity="critical",
                    scenario_context=f"PCB_Index_{pcb_index}"
                )
                self.main_logger.info(f"OPC_DB_LINK: Critical fault logged to error.log.")

                # 3. Log this critical fault to the database manager
                dbm.create_error(
                    machine_id=faulting_station_id,
                    error_code=error_code_critical,
                    description=critical_fault_description,
                    severity="critical"
                )
                self.main_logger.info(f"OPC_DB_LINK: Critical fault logged to sim_database_manager.")
                
                # Note: As per prompt, this fault does not currently override overall_pcb_status for the result log.
                # In a real system, overall_pcb_status would likely be set to "critical_failure" here.
            
            # --- Example: Log production result ---
            # Determine status based on inspection or other factors
            overall_pcb_status = "success" if all(self.inspection_results_summary) else "failed_inspection"
            
            # Calculate cycle time for the PCB
            current_pcb_cycle_time = (datetime.now() - pcb_start_time).total_seconds()

            recipe_name_for_log = "Unknown Recipe"
            if self.pcb_recipe_id is not None:
                recipe_details = dbm.get_recipe(self.pcb_recipe_id)
                if recipe_details:
                    recipe_name_for_log = recipe_details['name']
                
                # Log to sim_database_manager
                dbm.create_result(
                    recipe_id=self.pcb_recipe_id,
                    output_quantity=1, 
                    status=overall_pcb_status,
                    operator="OperatorPCB1", 
                    shift="DayShift"
                )
                self.main_logger.info(f"Production result logged to DB Manager for PCB {pcb_index+1} with status: {overall_pcb_status}.")

                # Log to file_logger
                file_logger.log_production_result(
                    recipe_id=self.pcb_recipe_id,
                    recipe_name=recipe_name_for_log,
                    output_quantity=1,
                    status=overall_pcb_status,
                    operator="OperatorPCB_Line1",
                    shift="CurrentShift", # Example, could be dynamic
                    cycle_time_seconds=current_pcb_cycle_time
                )
                self.main_logger.info(f"Production result logged to file_logger for PCB {pcb_index+1}.")
            else:
                self.main_logger.error("No valid pcb_recipe_id to log result against for DB Manager.")
                # Log a generic production result if recipe ID is missing for file logger
                file_logger.log_production_result(
                    recipe_id=0, # Placeholder
                    recipe_name="Unknown Recipe",
                    output_quantity=1,
                    status=overall_pcb_status,
                    operator="OperatorPCB_Line1",
                    shift="CurrentShift",
                    cycle_time_seconds=current_pcb_cycle_time
                )
                self.main_logger.info(f"Generic production result logged to file_logger for PCB {pcb_index+1}.")


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
            # pcb_end_time = datetime.now() # This is already captured by current_pcb_cycle_time calculation
            # pcb_time = (pcb_end_time - pcb_start_time).total_seconds() # Already calculated
            self.main_logger.info(f"PCB {pcb_index+1} completed in {current_pcb_cycle_time:.2f} seconds")

            # --- Example: Update System.Heartbeat OPC tag ---
            hb_tag = sim_opc_instance.read_tag("System.Heartbeat")
            if hb_tag:
                new_hb_value = hb_tag['value'] + 1
                sim_opc_instance.write_tag("System.Heartbeat", new_hb_value)
                self.main_logger.info(f"OPC: System.Heartbeat incremented to {new_hb_value}.")
            else: # Should not happen as it's initialized
                sim_opc_instance.add_tag("System.Heartbeat", 1)
                self.main_logger.info(f"OPC: System.Heartbeat initialized to 1.")


            # --- Example: Log KPIs for the placer robot for this PCB ---
            # These are dummy KPI values for demonstration.
            simulated_oee = random.uniform(0.7, 0.9)
            simulated_availability = random.uniform(0.8, 0.95)
            simulated_performance = random.uniform(0.85, 0.98)
            # Quality based on inspection summary for this PCB
            successful_components = sum(1 for success_status in self.inspection_results_summary if success_status)
            total_components_processed = len(self.inspection_results_summary)
            simulated_quality = successful_components / total_components_processed if total_components_processed > 0 else 0.0
            
            avg_component_cycle_time_for_pcb = sum(self.cycle_times[-total_components_processed:]) / total_components_processed if total_components_processed > 0 else 15.0 # Placeholder
            simulated_defect_rate = 1.0 - simulated_quality

            file_logger.log_kpi(
                machine_id="Robot.placer", 
                oee=round(simulated_oee, 3),
                availability=round(simulated_availability, 3),
                performance=round(simulated_performance, 3),
                quality=round(simulated_quality, 3),
                cycle_time=round(avg_component_cycle_time_for_pcb, 2),
                defect_rate=round(simulated_defect_rate, 3),
                throughput=float(total_components_processed) # Example throughput: components per PCB processing time
            )
            self.robot_loggers["placer"].info(f"KPIs logged via file_logger for placer robot after PCB {pcb_index+1}.")

        # Print final statistics
        self.report_statistics()

        self.main_logger.info("\n--- Retrieving sample data from DB Manager ---")
        all_recipes_final = dbm.get_all_recipes()
        self.main_logger.info(f"Total recipes in DB: {len(all_recipes_final)}")
        if all_recipes_final:
            self.main_logger.info(f"Last recipe added: {all_recipes_final[-1]['name']}")

        all_results_final = dbm.get_all_results()
        self.main_logger.info(f"Total results in DB: {len(all_results_final)}")
        if all_results_final:
            self.main_logger.info(f"Last result status: {all_results_final[-1]['status']}")

        all_errors_final = dbm.get_all_errors()
        self.main_logger.info(f"Total errors in DB: {len(all_errors_final)}")
        if all_errors_final:
            self.main_logger.info(f"Last error description: {all_errors_final[-1]['description']}")
    
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
    assembly_line.run_assembly(pcb_count=5)  # Assemble 5 PCBs to test the critical fault simulation