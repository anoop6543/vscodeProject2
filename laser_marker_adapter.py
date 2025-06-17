"""
Laser Marker Adapter for Gantry Robot Simulation

This module provides an adapter that integrates the LaserMarker classes with
the GantryRobot class, allowing for seamless integration of laser marker functionality
into existing gantry robot simulations.
"""

import logging
from typing import Tuple, Optional, Dict, Any, List, Union

from SimpleGantrySimulation import GantryRobot
from laser_marker import LaserMarker, create_laser_marker, LaserMarkerType, LaserOperationMode
from sim_opc_server import sim_opc_instance

class LaserMarkerAdapter:
    """
    Adapter class that integrates LaserMarker with GantryRobot.
    
    This class works as a bridge between the GantryRobot class and the LaserMarker classes,
    allowing the GantryRobot to use different laser marker implementations without
    modifying its core code.
    """
    
    def __init__(self, 
                 robot: GantryRobot, 
                 laser_marker: Optional[LaserMarker] = None,
                 vendor: str = "keyence",
                 model: Optional[str] = None):
        """
        Initialize the adapter with a GantryRobot and optionally a LaserMarker.
        
        Args:
            robot: The GantryRobot instance to integrate with
            laser_marker: An existing LaserMarker instance (optional)
            vendor: Vendor name for creating a new laser marker if one isn't provided
            model: Model name for creating a new laser marker if one isn't provided
        """
        self.robot = robot
        self.logger = logging.getLogger("LaserMarkerAdapter")
        
        # Create a laser marker if one isn't provided
        if laser_marker is None:
            self.laser_marker = create_laser_marker(vendor, model)
        else:
            self.laser_marker = laser_marker
            
        # Store original methods before patching
        self._original_laser_weld = None
        if hasattr(robot, 'laser_weld'):
            self._original_laser_weld = robot.laser_weld
            
        self._original_laser_mark = None
        if hasattr(robot, 'laser_mark'):
            self._original_laser_mark = robot.laser_mark
            
        # Patch the robot with the new laser methods
        self._patch_robot()
        
        self.logger.info(f"LaserMarkerAdapter initialized with {self.laser_marker.name}")
        
    def _patch_robot(self):
        """Patch the robot's laser methods to use the laser marker."""
        # Replace laser_weld method
        def new_laser_weld(start_point: Tuple[float, float, float],
                          end_point: Tuple[float, float, float],
                          speed: float, power: float, focus_setting: float):
            """Patched laser_weld method that uses the laser marker."""
            # Update status in GantryRobot to maintain compatibility
            self.robot.laser_status = "WELDING"
            sim_opc_instance.write_tag("GantryRobot.Status", self.robot.laser_status)
            
            # Set laser marker position to match robot position
            self.laser_marker.set_position(
                position=(self.robot.motors[0].position, 
                          self.robot.motors[1].position, 
                          self.robot.motors[2].position),
                orientation=(self.robot.motors[5].position,
                             self.robot.motors[6].position)
            )
            
            # Move the robot to the start point using the original move_to method
            original_orientation = (self.robot.motors[5].position, self.robot.motors[6].position)
            self.robot.move_to(start_point, original_orientation)
            
            # Perform welding with the laser marker
            result = self.laser_marker.weld(
                start_point=start_point,
                end_point=end_point,
                power=power,
                speed=speed,
                focus_setting=focus_setting
            )
            
            # Update robot status and position to match end point
            self.robot.motors[0].position = end_point[0]
            self.robot.motors[1].position = end_point[1]
            self.robot.motors[2].position = end_point[2]
            
            # Reset status
            self.robot.laser_status = "OFF"
            sim_opc_instance.write_tag("GantryRobot.Status", "Idle")
            
            return result
            
        # Replace laser_mark method
        def new_laser_mark(target_point: Tuple[float, float, float],
                          text: str, speed: float, power: float, font_size: float = 10.0):
            """Patched laser_mark method that uses the laser marker."""
            # Update status in GantryRobot to maintain compatibility
            self.robot.laser_status = "MARKING"
            sim_opc_instance.write_tag("GantryRobot.Status", self.robot.laser_status)
            
            # Set laser marker position to match robot position
            self.laser_marker.set_position(
                position=(self.robot.motors[0].position, 
                          self.robot.motors[1].position, 
                          self.robot.motors[2].position),
                orientation=(self.robot.motors[5].position,
                             self.robot.motors[6].position)
            )
            
            # Move the robot to the target point using the original move_to method
            original_orientation = (self.robot.motors[5].position, self.robot.motors[6].position)
            self.robot.move_to(target_point, original_orientation)
            
            # Perform marking with the laser marker
            result = self.laser_marker.mark(
                target_point=target_point,
                text=text,
                power=power,
                speed=speed,
                font_size=font_size
            )
            
            # Reset status
            self.robot.laser_status = "OFF"
            sim_opc_instance.write_tag("GantryRobot.Status", "Idle")
            
            return result
            
        # Attach methods to robot
        self.robot.laser_weld = new_laser_weld
        self.robot.laser_mark = new_laser_mark
        
    def restore_original_methods(self):
        """Restore the robot's original laser methods."""
        if self._original_laser_weld is not None:
            self.robot.laser_weld = self._original_laser_weld
            
        if self._original_laser_mark is not None:
            self.robot.laser_mark = self._original_laser_mark
            
        self.logger.info("Restored original laser methods to robot")
        
    def get_laser_marker(self) -> LaserMarker:
        """
        Get the laser marker instance.
        
        Returns:
            The laser marker instance
        """
        return self.laser_marker
        
    def replace_laser_marker(self, 
                            vendor: str, 
                            model: Optional[str] = None) -> LaserMarker:
        """
        Replace the current laser marker with a new one.
        
        Args:
            vendor: Vendor name for the new laser marker
            model: Model name for the new laser marker (optional)
            
        Returns:
            The new laser marker instance
        """
        old_marker = self.laser_marker
        self.laser_marker = create_laser_marker(vendor, model)
        self._patch_robot()  # Re-patch with the new laser marker
        self.logger.info(f"Replaced {old_marker.name} with {self.laser_marker.name}")
        return self.laser_marker
        
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the adapter and laser marker.
        
        Returns:
            Dictionary with current status values
        """
        return {
            "robot_status": self.robot.laser_status if hasattr(self.robot, 'laser_status') else "UNKNOWN",
            "laser_marker": self.laser_marker.get_status()
        }
