import unittest
import sys
import os
from datetime import datetime as dt_class # Alias to avoid confusion with 'datetime' module
from unittest.mock import patch

# Adjust sys.path to include the parent directory (project root)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sim_opc_server import SimOpcServer

class TestSimOpcServer(unittest.TestCase):

    def setUp(self):
        """Set up a fresh SimOpcServer instance for each test."""
        self.server = SimOpcServer()

    def test_initial_tags_exist(self):
        """Test that key sample tags are initialized correctly."""
        # Check a few sample tags
        temp_tag_id = "SimPLC.S1.Temp"
        status_tag_id = "GantryRobot.Status"
        heartbeat_tag_id = "System.Heartbeat"

        self.assertIn(temp_tag_id, self.server.tags)
        self.assertIn(status_tag_id, self.server.tags)
        self.assertIn(heartbeat_tag_id, self.server.tags)

        temp_tag_data = self.server.read_tag(temp_tag_id)
        self.assertEqual(temp_tag_data["value"], 25.0)
        self.assertEqual(temp_tag_data["quality"], "Good")
        self.assertIsInstance(temp_tag_data["timestamp"], dt_class)

        status_tag_data = self.server.read_tag(status_tag_id)
        self.assertEqual(status_tag_data["value"], "Idle")

        heartbeat_tag_data = self.server.read_tag(heartbeat_tag_id)
        self.assertEqual(heartbeat_tag_data["value"], 0)

    def test_add_new_tag(self):
        """Test adding a completely new tag."""
        tag_id = "MyNewDevice.Sensor1.Value"
        initial_value = 123.45
        initial_quality = "Good"
        
        # Mock datetime to check timestamp
        mock_now = dt_class(2023, 1, 1, 10, 0, 0)
        with patch('sim_opc_server.datetime.datetime') as mock_datetime_module:
            mock_datetime_module.utcnow.return_value = mock_now
            self.assertTrue(self.server.add_tag(tag_id, initial_value, initial_quality))
        
        self.assertIn(tag_id, self.server.tags)
        tag_data = self.server.read_tag(tag_id)
        self.assertEqual(tag_data["value"], initial_value)
        self.assertEqual(tag_data["quality"], initial_quality)
        self.assertEqual(tag_data["timestamp"], mock_now)

    def test_add_tag_updates_existing(self):
        """Test that add_tag updates an existing tag's value and timestamp."""
        tag_id = "SimPLC.S1.Temp"
        original_data = self.server.read_tag(tag_id)
        self.assertIsNotNone(original_data)
        
        new_value = 99.9
        mock_now_update = dt_class(2023, 1, 1, 11, 0, 0)
        
        with patch('sim_opc_server.datetime.datetime') as mock_datetime_module:
            mock_datetime_module.utcnow.return_value = mock_now_update
            self.assertTrue(self.server.add_tag(tag_id, new_value, "Uncertain"))

        updated_data = self.server.read_tag(tag_id)
        self.assertEqual(updated_data["value"], new_value)
        self.assertEqual(updated_data["quality"], "Uncertain")
        self.assertEqual(updated_data["timestamp"], mock_now_update)
        self.assertNotEqual(updated_data["timestamp"], original_data["timestamp"])

    def test_add_tag_invalid_id(self):
        """Test add_tag with invalid tag IDs."""
        self.assertFalse(self.server.add_tag(None, 100))
        self.assertFalse(self.server.add_tag("", 200))

    def test_read_existing_tag(self):
        """Test reading a known existing tag."""
        tag_id = "SimPLC.S1.Pressure"
        tag_data = self.server.read_tag(tag_id)
        self.assertIsNotNone(tag_data)
        self.assertEqual(tag_data["value"], 101.2) # From _initialize_sample_tags
        self.assertEqual(tag_data["quality"], "Good")
        self.assertIsInstance(tag_data["timestamp"], dt_class)

    def test_read_non_existent_tag(self):
        """Test reading a tag that does not exist."""
        self.assertIsNone(self.server.read_tag("NonExistent.Tag.Id"))

    @patch('sim_opc_server.datetime.datetime')
    def test_write_existing_tag(self, mock_datetime_module_write):
        """Test writing to an existing tag."""
        tag_id = "SimPLC.S1.Temp"
        original_data = self.server.read_tag(tag_id)
        original_timestamp = original_data["timestamp"]

        new_value = 35.7
        mock_now_write = dt_class(2023, 1, 1, 12, 30, 0)
        mock_datetime_module_write.utcnow.return_value = mock_now_write

        self.assertTrue(self.server.write_tag(tag_id, new_value))
        
        updated_data = self.server.read_tag(tag_id)
        self.assertEqual(updated_data["value"], new_value)
        self.assertEqual(updated_data["timestamp"], mock_now_write)
        self.assertNotEqual(updated_data["timestamp"], original_timestamp) # Timestamp should have changed

    def test_write_non_existent_tag(self):
        """Test writing to a non-existent tag."""
        self.assertFalse(self.server.write_tag("NonExistent.Tag.ToWrite", 500))

    def test_get_all_tags_returns_copy(self):
        """Test that get_all_tags returns a copy, not a reference."""
        all_tags_initial = self.server.get_all_tags()
        num_initial_tags = len(all_tags_initial)

        all_tags_initial["NewKeyAddedToCopy"] = "NewValue"
        
        # The internal tags dictionary should not be affected
        self.assertEqual(len(self.server.tags), num_initial_tags)
        self.assertNotIn("NewKeyAddedToCopy", self.server.tags)

    def test_get_all_tags_content(self):
        """Test the content and count of get_all_tags."""
        # Count based on _initialize_sample_tags
        # SimPLC.S1.Temp, SimPLC.S1.Pressure, SimPLC.S1.ItemPresent (3)
        # GantryRobot.AxisX.ActualPosition, GantryRobot.AxisY.ActualPosition, GantryRobot.AxisZ.ActualPosition, GantryRobot.Status (4)
        # Conveyor.IsRunning (1)
        # System.Heartbeat (1)
        # Total = 3 + 4 + 1 + 1 = 9
        expected_initial_tag_count = 9 
        all_tags = self.server.get_all_tags()
        self.assertEqual(len(all_tags), expected_initial_tag_count)
        self.assertIn("SimPLC.S1.Temp", all_tags)
        self.assertIn("GantryRobot.Status", all_tags)

    @patch('sim_opc_server.datetime.datetime')
    def test_timestamps_update_on_write_and_add(self, mock_datetime_module):
        """Test that timestamps are correctly updated by write_tag and add_tag."""
        mock_now_initial = dt_class(2023, 1, 1, 12, 0, 0)
        mock_datetime_module.utcnow.return_value = mock_now_initial

        # Test with write_tag
        write_tag_id = "SimPLC.S1.Temp" # Existing tag
        self.server.write_tag(write_tag_id, 30.0)
        tag_data_write = self.server.read_tag(write_tag_id)
        self.assertEqual(tag_data_write['timestamp'], mock_now_initial)

        # Test with add_tag (for a new tag)
        mock_now_add = dt_class(2023, 1, 1, 12, 5, 0) # Different time
        mock_datetime_module.utcnow.return_value = mock_now_add
        
        add_tag_id = "New.Test.Tag.For.Timestamp"
        self.server.add_tag(add_tag_id, 123)
        new_tag_data = self.server.read_tag(add_tag_id)
        self.assertEqual(new_tag_data['timestamp'], mock_now_add)

        # Test add_tag updating an existing tag (should also update timestamp)
        mock_now_update_add = dt_class(2023, 1, 1, 12, 10, 0)
        mock_datetime_module.utcnow.return_value = mock_now_update_add
        self.server.add_tag(write_tag_id, 35.0) # Update the tag previously written
        updated_existing_tag_data = self.server.read_tag(write_tag_id)
        self.assertEqual(updated_existing_tag_data['timestamp'], mock_now_update_add)


if __name__ == '__main__':
    unittest.main()
