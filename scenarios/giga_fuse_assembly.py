import sys
import os
import logging
import random
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from SimpleGantrySimulation import GantryRobot, ObjectType
import sim_database_manager as dbm
import file_logger
from sim_opc_server import sim_opc_instance
from laser_marker_adapter import LaserMarkerAdapter
import ui_interaction_service as ui_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler("logs/giga_fuse_assembly.log"),
        logging.StreamHandler()
    ]
)

class GigaFuse:
    def __init__(self, serial_number: str):
        self.serial_number = serial_number
        self.resistance = 0.0 # Ohms
        self.calibrated_resistance = 0.0
        self.blow_current = 0.0 # Amps
        self.is_assembled = False
        self.is_calibrated = False
        self.is_characterized = False
        self.is_enclosed = False
        self.is_tested = False
        self.is_marked = False
        self.status = "In_Progress"

class MESInterface:
    """
    Mock Interface to an Ignition MES system.
    Publishes status updates via OPC tags and logs "MES" events.
    """
    def __init__(self, logger):
        self.logger = logger

    def publish_status(self, station: str, serial_number: str, status: str, data: dict = None):
        """
        Publish status to MES (simulated).
        """
        # Update OPC tags for live monitoring (Ignition would read these)
        sim_opc_instance.write_tag(f"MES.{station}.Status", status)
        sim_opc_instance.write_tag(f"MES.{station}.LastPart", serial_number)
        
        if data:
            for key, value in data.items():
                sim_opc_instance.write_tag(f"MES.{station}.Data.{key}", value)
        
        # Log the event as if sending a message to the MES server
        msg = {
            "target": "Ignition_MES_Server",
            "station": station,
            "serial": serial_number,
            "status": status,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.logger.info(f"[MES_LINK] >> {json.dumps(msg)}")

class HMIInterface:
    """
    Interface for HMI interactions.
    Exposes status to the UI service and handles simulated inputs.
    """
    def __init__(self, logger):
        self.logger = logger
        self.e_stop_active = False
        
        # Initialize HMI tags
        sim_opc_instance.write_tag("HMI.SystemState", "Idle")
        sim_opc_instance.write_tag("HMI.EStop", False)
        sim_opc_instance.write_tag("HMI.AlertMessage", "")

    def update_display(self, message: str):
        self.logger.info(f"[HMI_DISPLAY] {message}")
        sim_opc_instance.write_tag("HMI.AlertMessage", message)

    def check_e_stop(self) -> bool:
        # In a real system, this would read a hardware input or UI button
        # Here we simulate it via an OPC tag that could be toggled externally
        tag = sim_opc_instance.read_tag("HMI.EStop")
        if tag and tag['value']:
            if not self.e_stop_active:
                self.logger.critical("[HMI] E-STOP ACTIVATED!")
                self.e_stop_active = True
                sim_opc_instance.write_tag("HMI.SystemState", "EMERGENCY_STOP")
            return True
        return False

    def clear_e_stop(self):
        self.logger.info("[HMI] E-Stop Cleared")
        self.e_stop_active = False
        sim_opc_instance.write_tag("HMI.EStop", False)
        sim_opc_instance.write_tag("HMI.SystemState", "Idle")

class GigaFuseAssemblyLine:
    def __init__(self):
        self.logger = logging.getLogger("GigaFuseLine")
        self.mes = MESInterface(self.logger)
        self.hmi = HMIInterface(self.logger)
        
        # Robots
        self.robots = {
            "assembler": GantryRobot(),
            "calibrator": GantryRobot(), # Laser Trimmer
            "tester": GantryRobot(),
            "marker": GantryRobot()
        }
        
        # Laser Integration for Calibration (Trimming) and Marking
        self.trim_laser = LaserMarkerAdapter(self.robots["calibrator"], vendor="coherent", model="PowerLine E")
        self.mark_laser = LaserMarkerAdapter(self.robots["marker"], vendor="keyence", model="MD-X")
        
        self.current_recipe_id = None

    def check_safety(self):
        if self.hmi.check_e_stop():
            raise RuntimeError("E-STOP Active")

    def step_assembly(self, fuse: GigaFuse):
        self.check_safety()
        self.logger.info(f"Starting Assembly for {fuse.serial_number}")
        self.hmi.update_display(f"Assembling {fuse.serial_number}")
        self.mes.publish_status("Assembly", fuse.serial_number, "Started")
        
        robot = self.robots["assembler"]
        
        # Simulate pick and place of fuse element
        robot.pick_and_place(ObjectType.METAL_PART, (10, 10, 0), (100, 100, 0))
        
        fuse.is_assembled = True
        fuse.resistance = random.uniform(0.0015, 0.0020) # Initial resistance variation
        
        self.mes.publish_status("Assembly", fuse.serial_number, "Completed", {"RawResistance": fuse.resistance})

    def step_calibration(self, fuse: GigaFuse):
        self.check_safety()
        self.logger.info(f"Starting Calibration (Laser Trim) for {fuse.serial_number}")
        self.hmi.update_display(f"Calibrating {fuse.serial_number}")
        
        robot = self.robots["calibrator"]
        target_resistance = 0.0020 # Ohms
        
        # Simulate laser trimming path
        # A precise cut to increase resistance to target
        start_trim = (100, 100, 10)
        end_trim = (105, 100, 10)
        
        # Use the laser adapter (Coherent)
        # In a real scenario, we'd measure resistance live while trimming
        robot.laser_weld(start_trim, end_trim, speed=5, power=500, focus_setting=0.0) # Reusing weld for cut simulation
        
        # Simulate result
        fuse.calibrated_resistance = target_resistance + random.uniform(-0.00001, 0.00001)
        fuse.is_calibrated = True
        
        self.mes.publish_status("Calibration", fuse.serial_number, "Completed", {"CalibratedResistance": fuse.calibrated_resistance})

    def step_characterization(self, fuse: GigaFuse):
        self.check_safety()
        self.logger.info(f"Starting Characterization for {fuse.serial_number}")
        self.hmi.update_display(f"Testing {fuse.serial_number}")
        
        # Simulate high current pulse test
        current_pulse = 500 # Amps
        voltage_drop = current_pulse * fuse.calibrated_resistance
        
        fuse.is_characterized = True
        
        self.mes.publish_status("Characterization", fuse.serial_number, "Completed", {"VoltageDrop": voltage_drop})

    def step_enclosure(self, fuse: GigaFuse):
        self.check_safety()
        self.logger.info(f"Enclosing {fuse.serial_number}")
        
        robot = self.robots["assembler"] # Reuse assembler for cover
        robot.pick_and_place(ObjectType.BOX, (20, 20, 0), (100, 100, 10))
        
        fuse.is_enclosed = True
        self.mes.publish_status("Enclosure", fuse.serial_number, "Completed")

    def step_testing(self, fuse: GigaFuse):
        self.check_safety()
        self.logger.info(f"Final Testing {fuse.serial_number}")
        
        # Simulate visual check and continuity
        passed = random.random() > 0.05 # 95% yield
        
        fuse.is_tested = True
        if passed:
            fuse.status = "Passed"
        else:
            fuse.status = "Failed"
            self.logger.error(f"Fuse {fuse.serial_number} FAILED final test")
            dbm.create_error("Tester", "F-TEST-01", "Final Continuity Fail", "high")
        
        self.mes.publish_status("Testing", fuse.serial_number, fuse.status)

    def step_marking(self, fuse: GigaFuse):
        if fuse.status != "Passed":
            self.logger.info(f"Skipping marking for failed part {fuse.serial_number}")
            return

        self.check_safety()
        self.logger.info(f"Laser Marking {fuse.serial_number}")
        self.hmi.update_display(f"Marking {fuse.serial_number}")
        
        robot = self.robots["marker"]
        
        # Mark Data
        mark_text = f"GIGA-FUSE | {fuse.serial_number} | 500A"
        robot.laser_mark((100, 100, 20), mark_text, speed=100, power=80, font_size=8)
        
        fuse.is_marked = True
        self.mes.publish_status("Marking", fuse.serial_number, "Completed")

    def run_production_run(self, count: int = 1):
        self.logger.info(f"Starting Production Run: {count} units")
        self.hmi.update_display("Starting Production Run")
        sim_opc_instance.write_tag("HMI.SystemState", "Running")
        
        self.current_recipe_id = dbm.create_recipe(
            "GigaFuse_500A_Gen3",
            ["FuseElement_Cu", "Housing_Ceramic", "Cover_Plastic"],
            ["Assembly", "LaserTrim", "PulseTest", "Enclose", "FinalTest", "LaserMark"]
        )
        
        for i in range(count):
            serial = f"GF500-{datetime.now().strftime('%Y%m%d')}-{i+1:04d}"
            fuse = GigaFuse(serial)
            
            try:
                self.step_assembly(fuse)
                self.step_calibration(fuse)
                self.step_characterization(fuse)
                self.step_enclosure(fuse)
                self.step_testing(fuse)
                self.step_marking(fuse)
                
                # Log Final Result
                dbm.create_result(
                    self.current_recipe_id, 
                    1, 
                    "Success" if fuse.status == "Passed" else "Failed",
                    "AutoLine", 
                    "Day"
                )
                
            except RuntimeError as e:
                self.logger.critical(f"Production halted: {e}")
                self.hmi.update_display(f"HALTED: {e}")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error on {serial}: {e}")
                dbm.create_error("System", "ERR-999", str(e), "critical")
        
        self.hmi.update_display("Production Run Finished")
        sim_opc_instance.write_tag("HMI.SystemState", "Idle")

if __name__ == "__main__":
    line = GigaFuseAssemblyLine()
    
    # Simulate an E-Stop trigger during the run for demonstration
    # In a real app, this would be async, but here we can just run normally
    # or inject a thread to toggle the tag.
    
    line.run_production_run(count=2)
