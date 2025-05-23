import unittest
import sys
import os
from unittest.mock import patch, call

# Adjust sys.path to include the parent directory (project root)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import classes from SimpleGantrySimulation
# Note: SimpleGantrySimulation is a file without a .py extension.
# Python's import mechanism can sometimes handle this, but if not,
# a workaround might be needed (e.g., renaming the file or using importlib).
# For now, let's assume direct import works if it's in sys.path.
# If "ModuleNotFoundError: No module named 'SimpleGantrySimulation'" occurs,
# it means Python is not finding it directly.
# The provided environment seems to handle direct import of SimpleGantrySimulation.
from SimpleGantrySimulation import GantryRobot, ObjectType, GripperType, Motor

class TestGantryRobot(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        self.robot = GantryRobot()
        # self.LOG_PREFIX = "[GantryRobot] " # Removed as per new strategy
        # self.robot.LOG_PREFIX = self.LOG_PREFIX # Removed

    def test_initialization(self):
        """Test the GantryRobot's initial state."""
        self.assertEqual(len(self.robot.motors), 8, "Should have 8 motors")
        self.assertEqual(len(self.robot.drives), 8, "Should have 8 drives")
        self.assertIsNotNone(self.robot.force_sensor, "Force sensor should be initialized")
        self.assertEqual(self.robot.current_gripper.gripper_type, GripperType.SUCTION, "Default gripper should be Suction")
        self.assertEqual(self.robot.laser_status, "OFF", "Laser should be OFF initially")

    @patch('builtins.print') # Mock print to avoid console output during tests
    def test_select_gripper(self, mock_print):
        """Test gripper selection based on object type."""
        test_cases = {
            ObjectType.BOX: GripperType.SUCTION,
            ObjectType.SHEET: GripperType.SUCTION,
            ObjectType.CYLINDER: GripperType.PARALLEL,
            ObjectType.METAL_PART: GripperType.MAGNETIC,
            ObjectType.FRAGILE: GripperType.SOFT,
        }
        for obj_type, expected_gripper_type in test_cases.items():
            with self.subTest(obj_type=obj_type):
                self.robot.select_gripper(obj_type)
                self.assertEqual(self.robot.current_gripper.gripper_type, expected_gripper_type)
                mock_print.assert_called_with(f"Selected gripper: {expected_gripper_type.value}")

    @patch('builtins.print') # Mock print
    def test_move_to(self, mock_print):
        """Test the move_to method updates motor positions."""
        target_position = (100.0, 150.0, 50.0)
        target_orientation = (45.0, 30.0)
        
        self.robot.move_to(target_position, target_orientation)
        
        self.assertEqual(self.robot.motors[0].position, target_position[0], "X-axis position incorrect") # X
        self.assertEqual(self.robot.motors[1].position, target_position[1], "Y-axis position incorrect") # Y
        self.assertEqual(self.robot.motors[2].position, target_position[2], "Z-axis position incorrect") # Z
        self.assertEqual(self.robot.motors[5].position, target_orientation[0], "Rotate motor position incorrect") # Rotate
        self.assertEqual(self.robot.motors[6].position, target_orientation[1], "Tilt motor position incorrect")   # Tilt

    @patch('builtins.print') # Mock print
    def test_extend_retract(self, mock_print):
        """Test extend and retract functionality."""
        # Motor 3 is Extend, Motor 4 is Retract
        # Based on implementation: extend_retract(True) moves motor 3 to 100
        # extend_retract(False) moves motor 4 to 0 (or 100 if it's a target, then 0)
        # The current implementation has extend_retract(True) use motors[3] (Extend)
        # and extend_retract(False) use motors[4] (Retract).
        # They are separate motors for extend and retract actions.
        
        self.robot.extend_retract(True) # Extend
        self.assertEqual(self.robot.motors[3].position, 100, "Extend motor (motors[3]) position incorrect after extend")
        
        self.robot.extend_retract(False) # Retract
        self.assertEqual(self.robot.motors[4].position, 0, "Retract motor (motors[4]) position incorrect after retract")

    @patch('builtins.print') # Mock print
    def test_operate_gripper(self, mock_print):
        """Test gripper open and close operations."""
        # Motor 7 is Gripper
        self.robot.operate_gripper(True) # Open
        self.assertEqual(self.robot.motors[7].position, 1, "Gripper motor position incorrect after open")
        
        self.robot.operate_gripper(False) # Close
        self.assertEqual(self.robot.motors[7].position, 0, "Gripper motor position incorrect after close")

    @patch('SimpleGantrySimulation.GantryRobot.select_gripper')
    @patch('SimpleGantrySimulation.GantryRobot.move_to')
    @patch('SimpleGantrySimulation.GantryRobot.extend_retract')
    @patch('SimpleGantrySimulation.GantryRobot.operate_gripper')
    @patch('SimpleGantrySimulation.Gripper.pick')
    @patch('SimpleGantrySimulation.Gripper.place')
    @patch('SimpleGantrySimulation.ForceSensor.get_force', return_value=10.0) # Mock force sensor to return a value
    @patch('builtins.print') # Mock print for logging
    def test_pick_and_place_flow(self, mock_print, mock_get_force, mock_gripper_place, 
                               mock_gripper_pick, mock_operate_gripper, 
                               mock_extend_retract, mock_move_to_gantry, mock_select_gripper): # Renamed mock_move_to to mock_move_to_gantry
        """Test the sequence of operations in pick_and_place."""
        obj_type = ObjectType.METAL_PART
        pick_pos = (10, 20, 30)
        place_pos = (100, 120, 130)

        self.robot.pick_and_place(obj_type, pick_pos, place_pos)

        # Check if select_gripper was called
        mock_select_gripper.assert_called_once_with(obj_type)
        
        # Check calls to move_to
        # Expected calls: 1. to pick_pos, 2. to place_pos
        move_to_calls = [
            call(pick_pos, (0,0)), # Initial move to pick_pos
            call(place_pos, (0,0)) # Move to place_pos
        ]
        mock_move_to_gantry.assert_has_calls(move_to_calls) # Use renamed mock
        self.assertEqual(mock_move_to_gantry.call_count, 2) # Use renamed mock

        # Check calls to extend_retract
        # Expected: Extend(T), Retract(F), Extend(T), Retract(F)
        extend_retract_calls = [
            call(True),  # Extend to pick
            call(False), # Retract after pick
            call(True),  # Extend to place
            call(False)  # Retract after place
        ]
        mock_extend_retract.assert_has_calls(extend_retract_calls)
        self.assertEqual(mock_extend_retract.call_count, 4)

        # Check calls to operate_gripper
        # Expected: Close(F) to pick, Open(T) to place
        operate_gripper_calls = [
            call(False), # Close to pick
            call(True)   # Open to place
        ]
        mock_operate_gripper.assert_has_calls(operate_gripper_calls)
        self.assertEqual(mock_operate_gripper.call_count, 2)

        # Check that the current gripper's pick and place methods were called
        # Since select_gripper is mocked, self.robot.current_gripper is the initial one.
        # To properly test this, we might need a more complex setup or to not mock select_gripper,
        # but for this scope, let's assume the correct gripper was selected and its methods would be called.
        # If select_gripper was not mocked, we would check:
        # self.robot.current_gripper.pick.assert_called_once_with(obj_type)
        # self.robot.current_gripper.place.assert_called_once_with(place_pos)
        # For now, let's check the mocked pick/place on the Gripper class prototype
        mock_gripper_pick.assert_called_once_with(self.robot.current_gripper, obj_type) # Pass self instance
        mock_gripper_place.assert_called_once_with(self.robot.current_gripper, place_pos) # Pass self instance


        # Check final motor positions (X, Y, Z should be at place_pos)
        # This assumes that the mocked move_to still updates the motor positions,
        # which it won't by default. For a true state check without mocking move_to,
        # we would run it and check self.robot.motors.
        # Since move_to is mocked, we cannot directly verify motor positions here
        # unless we make the mock function also update the motor positions.
        # Let's remove this part of the test as it conflicts with mocking move_to.
        # self.assertEqual(self.robot.motors[0].position, place_pos[0])
        # self.assertEqual(self.robot.motors[1].position, place_pos[1])
        # self.assertEqual(self.robot.motors[2].position, place_pos[2])

    @patch('builtins.print')
    def test_laser_weld(self, mock_print):
        start_point = (10.0, 20.0, 30.0)
        end_point = (110.0, 20.0, 30.0) # 100mm weld in X
        speed = 20.0
        power = 1500.0
        focus = 0.1

        self.assertEqual(self.robot.laser_status, "OFF")
        self.robot.laser_weld(start_point, end_point, speed, power, focus)
        self.assertEqual(self.robot.laser_status, "OFF")

        self.assertEqual(self.robot.motors[0].position, end_point[0])
        self.assertEqual(self.robot.motors[1].position, end_point[1])
        self.assertEqual(self.robot.motors[2].position, end_point[2])
        
        # Robust log checking
        logs = [call_arg[0][0] for call_arg in mock_print.call_args_list] # Extract all printed strings
        
        self.assertTrue(any(f"Starting laser weld from {start_point} to {end_point}" in log for log in logs), "Missing: Starting weld log")
        self.assertTrue(any("Laser status: WELDING" in log for log in logs), "Missing: Laser status WELDING log")
        self.assertTrue(any(f"LaserWeld: Moving to weld start point: {start_point}" in log for log in logs), "Missing: Moving to weld start log")
        self.assertTrue(any(f"LaserWeld: Weld path distance: {100.00:.2f}mm" in log for log in logs), "Missing: Weld path distance log")
        self.assertTrue(any(f"LaserWeld: Welding at ({end_point[0]:.2f}, {end_point[1]:.2f}, {end_point[2]:.2f})" in log for log in logs), "Missing: Welding at end_point log")
        self.assertTrue(any(f"LaserWeld: Ensuring final weld position at ({end_point[0]:.2f}, {end_point[1]:.2f}, {end_point[2]:.2f})" in log for log in logs), "Missing: Ensuring final weld position log")
        self.assertTrue(any("Laser weld completed. Laser status: OFF" in log for log in logs), "Missing: Weld completed log")

        # Test spot weld (zero distance)
        mock_print.reset_mock()
        spot_point = (5.0, 5.0, 5.0)
        self.robot.laser_weld(spot_point, spot_point, speed, power, focus)
        self.assertEqual(self.robot.laser_status, "OFF")
        self.assertEqual(self.robot.motors[0].position, spot_point[0])
        
        logs = [call_arg[0][0] for call_arg in mock_print.call_args_list]
        self.assertTrue(any("LaserWeld: Start and end points are the same." in log for log in logs), "Missing: Spot weld start/end same log")
        self.assertTrue(any(f"LaserWeld: Welding at ({spot_point[0]:.2f}, {spot_point[1]:.2f}, {spot_point[2]:.2f}) (spot weld)" in log for log in logs), "Missing: Spot weld action log")

    @patch('builtins.print')
    def test_laser_mark(self, mock_print):
        target_point = (50.0, 60.0, 70.0)
        text_to_mark = "TestSN123"
        speed = 50.0
        power = 100.0
        font_size = 12.0

        self.assertEqual(self.robot.laser_status, "OFF")
        self.robot.laser_mark(target_point, text_to_mark, speed, power, font_size)
        self.assertEqual(self.robot.laser_status, "OFF")

        self.assertEqual(self.robot.motors[0].position, target_point[0])
        self.assertEqual(self.robot.motors[1].position, target_point[1])
        self.assertEqual(self.robot.motors[2].position, target_point[2])

        # Robust log checking
        logs = [call_arg[0][0] for call_arg in mock_print.call_args_list]

        self.assertTrue(any(f"Starting laser mark at {target_point} with text '{text_to_mark}'" in log for log in logs), "Missing: Starting mark log")
        self.assertTrue(any("Laser status: MARKING" in log for log in logs), "Missing: Laser status MARKING log")
        self.assertTrue(any(f"LaserMark: Moving to mark target point: {target_point}" in log for log in logs), "Missing: Moving to mark target log")
        self.assertTrue(any(f"LaserMark: Marking text: '{text_to_mark}'" in log for log in logs), "Missing: Marking text log")
        # Duration is calculated, check for its presence rather than exact value if it's complex
        self.assertTrue(any("LaserMark: Simulated marking duration:" in log for log in logs), "Missing: Simulated duration log")
        self.assertTrue(any("Laser mark completed. Laser status: OFF" in log for log in logs), "Missing: Mark completed log")

if __name__ == '__main__':
    unittest.main()
