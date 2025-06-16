"""
Visual Simulation Module for Gantry Robot Simulation

This module provides a graphical representation of the gantry robot simulation
using Pygame. It visualizes the robot's position, gripper state, and movements
in a 2D top-down view.
"""

import os
import sys
import math
import pygame
import threading
import time
from typing import Dict, List, Tuple, Optional, Union, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from SimpleGantrySimulation import GantryRobot, GripperType, ObjectType

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
BACKGROUND_COLOR = (240, 240, 240)
GRID_COLOR = (200, 200, 200)
GRID_SIZE = 50
ROBOT_COLOR = (50, 50, 200)
GRIPPER_COLORS = {
    GripperType.SUCTION: (100, 100, 255),
    GripperType.PARALLEL: (100, 255, 100),
    GripperType.MAGNETIC: (255, 100, 100),
    GripperType.SOFT: (255, 255, 100)
}
OBJECT_COLORS = {
    ObjectType.BOX: (150, 75, 0),
    ObjectType.CYLINDER: (100, 100, 100),
    ObjectType.SHEET: (200, 200, 200),
    ObjectType.METAL_PART: (120, 120, 140),
    ObjectType.FRAGILE: (255, 200, 200)
}
ROBOT_SIZE = 30
GRIPPER_SIZE = 15
OBJECT_SIZES = {
    ObjectType.BOX: 25,
    ObjectType.CYLINDER: 20,
    ObjectType.SHEET: 30,
    ObjectType.METAL_PART: 15,
    ObjectType.FRAGILE: 20
}

# Scaling factor to convert simulation coordinates to screen coordinates
SCALE_FACTOR = 2.0  # 1 unit in simulation = 2 pixels on screen
X_OFFSET = SCREEN_WIDTH // 2
Y_OFFSET = SCREEN_HEIGHT // 2

class VisualSimulation:
    """
    Provides a visual representation of the gantry robot simulation.
    """
    def __init__(self, robot: GantryRobot):
        """
        Initialize the visual simulation.
        
        Args:
            robot: The GantryRobot instance to visualize.
        """
        self.robot = robot
        self.running = False
        self.screen = None
        self.font = None
        self.objects = {}  # Track objects in the simulation
        self.update_thread = None
        self.simulation_thread = None
        self.lock = threading.Lock()
        
        # Initialize path tracing
        self.path_history = []
        self.max_path_history = 100
        
        # Initialize Pygame
        pygame.init()
        pygame.display.set_caption("Gantry Robot Simulation")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.font = pygame.font.SysFont('Arial', 16)
        self.clock = pygame.time.Clock()
        
    def convert_coordinates(self, x: float, y: float) -> Tuple[int, int]:
        """
        Convert simulation coordinates to screen coordinates.
        
        Args:
            x: X coordinate in simulation space.
            y: Y coordinate in simulation space.
            
        Returns:
            Tuple of (screen_x, screen_y) coordinates.
        """
        screen_x = int(X_OFFSET + x * SCALE_FACTOR)
        screen_y = int(Y_OFFSET - y * SCALE_FACTOR)  # Y is inverted in pygame
        return screen_x, screen_y
        
    def draw_grid(self):
        """Draw a grid on the background for reference."""
        # Draw horizontal grid lines
        for y in range(0, SCREEN_HEIGHT, GRID_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (SCREEN_WIDTH, y), 1)
        
        # Draw vertical grid lines
        for x in range(0, SCREEN_WIDTH, GRID_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, SCREEN_HEIGHT), 1)
        
        # Draw axes
        pygame.draw.line(self.screen, (0, 0, 0), (0, Y_OFFSET), (SCREEN_WIDTH, Y_OFFSET), 2)
        pygame.draw.line(self.screen, (0, 0, 0), (X_OFFSET, 0), (X_OFFSET, SCREEN_HEIGHT), 2)
        
        # Label axes
        x_label = self.font.render("X", True, (0, 0, 0))
        y_label = self.font.render("Y", True, (0, 0, 0))
        self.screen.blit(x_label, (SCREEN_WIDTH - 20, Y_OFFSET + 10))
        self.screen.blit(y_label, (X_OFFSET + 10, 20))
        
        # Draw coordinate markers
        for i in range(-10, 11, 5):
            x_pos = X_OFFSET + i * GRID_SIZE
            y_pos = Y_OFFSET - i * GRID_SIZE
            
            if 0 <= x_pos < SCREEN_WIDTH:
                pygame.draw.line(self.screen, (0, 0, 0), (x_pos, Y_OFFSET - 5), (x_pos, Y_OFFSET + 5), 2)
                if i != 0:
                    marker = self.font.render(str(i * GRID_SIZE // SCALE_FACTOR), True, (0, 0, 0))
                    self.screen.blit(marker, (x_pos - 10, Y_OFFSET + 10))
            
            if 0 <= y_pos < SCREEN_HEIGHT:
                pygame.draw.line(self.screen, (0, 0, 0), (X_OFFSET - 5, y_pos), (X_OFFSET + 5, y_pos), 2)
                if i != 0:
                    marker = self.font.render(str(i * GRID_SIZE // SCALE_FACTOR), True, (0, 0, 0))
                    self.screen.blit(marker, (X_OFFSET + 10, y_pos - 10))
    
    def draw_robot(self):
        """Draw the gantry robot."""
        with self.lock:
            # Get robot position
            x_pos = self.robot.motors[0].position
            y_pos = self.robot.motors[1].position
            z_pos = self.robot.motors[2].position
            rotation = self.robot.motors[5].position
            tilt = self.robot.motors[6].position
            
            # Add position to path history
            self.path_history.append((x_pos, y_pos))
            if len(self.path_history) > self.max_path_history:
                self.path_history.pop(0)
            
            # Draw path history
            if len(self.path_history) > 1:
                for i in range(1, len(self.path_history)):
                    start = self.convert_coordinates(self.path_history[i-1][0], self.path_history[i-1][1])
                    end = self.convert_coordinates(self.path_history[i][0], self.path_history[i][1])
                    alpha = 100 + 155 * (i / len(self.path_history))  # Path gets more solid towards the end
                    path_color = (100, 100, 255, int(alpha))
                    pygame.draw.line(self.screen, path_color, start, end, 2)
            
            # Convert to screen coordinates
            screen_x, screen_y = self.convert_coordinates(x_pos, y_pos)
            
            # Draw robot body (adjust size based on Z height for perspective)
            size_factor = max(0.5, 1.0 - z_pos / 200)  # Smaller when higher
            robot_radius = int(ROBOT_SIZE * size_factor)
            pygame.draw.circle(self.screen, ROBOT_COLOR, (screen_x, screen_y), robot_radius)
            
            # Draw robot orientation indicator
            end_x = screen_x + int(robot_radius * math.cos(math.radians(rotation)))
            end_y = screen_y - int(robot_radius * math.sin(math.radians(rotation)))
            pygame.draw.line(self.screen, (0, 0, 0), (screen_x, screen_y), (end_x, end_y), 3)
            
            # Draw gripper
            gripper_color = GRIPPER_COLORS.get(self.robot.current_gripper.gripper_type, (255, 255, 255))
            gripper_x = screen_x + int(1.5 * robot_radius * math.cos(math.radians(rotation)))
            gripper_y = screen_y - int(1.5 * robot_radius * math.sin(math.radians(rotation)))
            gripper_radius = int(GRIPPER_SIZE * size_factor)
            pygame.draw.circle(self.screen, gripper_color, (gripper_x, gripper_y), gripper_radius)
            
            # Draw robot status
            status_text = f"X: {x_pos:.1f}, Y: {y_pos:.1f}, Z: {z_pos:.1f}"
            gripper_text = f"Gripper: {self.robot.current_gripper.gripper_type.value}"
            status_surface = self.font.render(status_text, True, (0, 0, 0))
            gripper_surface = self.font.render(gripper_text, True, (0, 0, 0))
            self.screen.blit(status_surface, (10, 10))
            self.screen.blit(gripper_surface, (10, 30))
            
            # Draw laser status if applicable
            if hasattr(self.robot, 'laser_status') and self.robot.laser_status != "OFF":
                laser_text = f"Laser: {self.robot.laser_status}"
                laser_surface = self.font.render(laser_text, True, (255, 0, 0))
                self.screen.blit(laser_surface, (10, 50))
                
                # Draw laser beam
                if self.robot.laser_status == "WELDING" or self.robot.laser_status == "MARKING":
                    beam_length = int(z_pos * SCALE_FACTOR)
                    start_point = (gripper_x, gripper_y)
                    end_point = (gripper_x, gripper_y + beam_length)
                    
                    # Draw pulsing laser beam
                    time_factor = (pygame.time.get_ticks() % 500) / 500.0
                    beam_width = 1 + int(2 * time_factor)
                    beam_alpha = 100 + int(155 * time_factor)
                    beam_color = (255, 0, 0, beam_alpha)
                    
                    pygame.draw.line(self.screen, beam_color, start_point, end_point, beam_width)
    
    def add_object(self, obj_id: str, obj_type: ObjectType, position: Tuple[float, float, float]):
        """
        Add an object to the simulation.
        
        Args:
            obj_id: Unique identifier for the object.
            obj_type: Type of object (Box, Cylinder, etc.)
            position: (x, y, z) coordinates of the object.
        """
        with self.lock:
            self.objects[obj_id] = {
                'type': obj_type,
                'position': position
            }
    
    def move_object(self, obj_id: str, position: Tuple[float, float, float]):
        """
        Move an object in the simulation.
        
        Args:
            obj_id: Identifier for the object to move.
            position: New (x, y, z) coordinates.
        """
        with self.lock:
            if obj_id in self.objects:
                self.objects[obj_id]['position'] = position
    
    def remove_object(self, obj_id: str):
        """
        Remove an object from the simulation.
        
        Args:
            obj_id: Identifier for the object to remove.
        """
        with self.lock:
            if obj_id in self.objects:
                del self.objects[obj_id]
    
    def draw_objects(self):
        """Draw all objects in the simulation."""
        with self.lock:
            for obj_id, obj_data in self.objects.items():
                obj_type = obj_data['type']
                x, y, z = obj_data['position']
                
                # Convert to screen coordinates
                screen_x, screen_y = self.convert_coordinates(x, y)
                
                # Adjust size based on z height for perspective
                size_factor = max(0.5, 1.0 - z / 200)
                obj_size = int(OBJECT_SIZES.get(obj_type, 20) * size_factor)
                
                # Get object color
                obj_color = OBJECT_COLORS.get(obj_type, (150, 150, 150))
                
                # Draw the object
                if obj_type == ObjectType.BOX:
                    rect = pygame.Rect(
                        screen_x - obj_size // 2,
                        screen_y - obj_size // 2,
                        obj_size,
                        obj_size
                    )
                    pygame.draw.rect(self.screen, obj_color, rect)
                elif obj_type == ObjectType.CYLINDER:
                    pygame.draw.circle(self.screen, obj_color, (screen_x, screen_y), obj_size // 2)
                    # Add ellipse on top to give 3D effect
                    ellipse_rect = pygame.Rect(
                        screen_x - obj_size // 2,
                        screen_y - obj_size // 4,
                        obj_size,
                        obj_size // 2
                    )
                    pygame.draw.ellipse(self.screen, obj_color, ellipse_rect)
                elif obj_type == ObjectType.SHEET:
                    # Draw a thin rectangle
                    rect = pygame.Rect(
                        screen_x - obj_size // 2,
                        screen_y - obj_size // 6,
                        obj_size,
                        obj_size // 3
                    )
                    pygame.draw.rect(self.screen, obj_color, rect)
                elif obj_type == ObjectType.METAL_PART:
                    # Draw a polygon for metal part
                    points = [
                        (screen_x - obj_size // 2, screen_y - obj_size // 2),
                        (screen_x + obj_size // 2, screen_y - obj_size // 2),
                        (screen_x + obj_size // 2, screen_y + obj_size // 2),
                        (screen_x, screen_y + obj_size // 2),
                        (screen_x - obj_size // 2, screen_y)
                    ]
                    pygame.draw.polygon(self.screen, obj_color, points)
                elif obj_type == ObjectType.FRAGILE:
                    # Draw a circle with a cross inside
                    pygame.draw.circle(self.screen, obj_color, (screen_x, screen_y), obj_size // 2)
                    pygame.draw.line(self.screen, (0, 0, 0), 
                                    (screen_x - obj_size // 3, screen_y - obj_size // 3),
                                    (screen_x + obj_size // 3, screen_y + obj_size // 3), 2)
                    pygame.draw.line(self.screen, (0, 0, 0), 
                                    (screen_x + obj_size // 3, screen_y - obj_size // 3),
                                    (screen_x - obj_size // 3, screen_y + obj_size // 3), 2)
                else:
                    # Default: draw a circle
                    pygame.draw.circle(self.screen, obj_color, (screen_x, screen_y), obj_size // 2)
    
    def update_display(self):
        """Update the display with the current simulation state."""
        self.screen.fill(BACKGROUND_COLOR)
        self.draw_grid()
        self.draw_objects()
        self.draw_robot()
        pygame.display.flip()
        self.clock.tick(60)  # 60 FPS
    
    def handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
    
    def update_loop(self):
        """Main update loop for the visualization."""
        while self.running:
            self.handle_events()
            self.update_display()
            time.sleep(0.016)  # ~60 FPS
    
    def start(self):
        """Start the visualization."""
        self.running = True
        self.update_thread = threading.Thread(target=self.update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def stop(self):
        """Stop the visualization."""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
        pygame.quit()
    
    def run_scenario(self, scenario_func, *args, **kwargs):
        """
        Run a scenario function in a separate thread.
        
        Args:
            scenario_func: The scenario function to run.
            *args, **kwargs: Arguments to pass to the scenario function.
        """
        def run_scenario_thread():
            try:
                scenario_func(*args, **kwargs)
            except Exception as e:
                print(f"Error in scenario: {e}")
        
        self.simulation_thread = threading.Thread(target=run_scenario_thread)
        self.simulation_thread.daemon = True
        self.simulation_thread.start()

# Monkey patch GantryRobot to update visualization
def patch_gantry_robot(robot, vis):
    """
    Patch GantryRobot methods to update visualization.
    
    Args:
        robot: The GantryRobot instance to patch.
        vis: The VisualSimulation instance.
    """
    original_pick_and_place = robot.pick_and_place
    original_move_to = robot.move_to
    
    def patched_pick_and_place(obj_type, pick_pos, place_pos):
        # Create a unique ID for the object
        obj_id = f"obj_{id(obj_type)}_{int(time.time() * 1000)}"
        
        # Add object at pick position
        vis.add_object(obj_id, obj_type, pick_pos)
        
        # Call original method
        result = original_pick_and_place(obj_type, pick_pos, place_pos)
        
        # Update object position
        vis.move_object(obj_id, place_pos)
        
        return result
    
    def patched_move_to(position, orientation):
        # Call original method
        result = original_move_to(position, orientation)
        
        # No need to update visualization here as it reads directly from robot state
        return result
    
    # Apply patches
    robot.pick_and_place = lambda obj_type, pick_pos, place_pos: patched_pick_and_place(obj_type, pick_pos, place_pos)
    robot.move_to = lambda position, orientation: patched_move_to(position, orientation)
    
    return robot

def create_visualization(robot=None):
    """
    Create and return a visualization instance.
    
    Args:
        robot: Optional GantryRobot instance. If None, a new one will be created.
    
    Returns:
        A tuple of (robot, visualization) instances.
    """
    if robot is None:
        robot = GantryRobot()
    
    vis = VisualSimulation(robot)
    patched_robot = patch_gantry_robot(robot, vis)
    
    return patched_robot, vis

def run_visualization_with_scenario(scenario_func, *args, **kwargs):
    """
    Run a visualization with a specific scenario.
    
    Args:
        scenario_func: Function that runs the scenario.
        *args, **kwargs: Arguments to pass to the scenario function.
    
    Returns:
        A tuple of (robot, visualization) instances.
    """
    robot = GantryRobot()
    vis = VisualSimulation(robot)
    patched_robot = patch_gantry_robot(robot, vis)
    
    # Start visualization
    vis.start()
    
    # Run scenario
    vis.run_scenario(scenario_func, *args, **kwargs)
    
    return patched_robot, vis
