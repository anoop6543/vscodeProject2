import unittest
import sys
import os
import json
import shutil
from datetime import datetime as dt # Alias for datetime.datetime
from unittest.mock import patch, mock_open, call

# Adjust sys.path to include the parent directory (project root)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import file_logger as fl

class TestFileLogger(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        self.test_logs_dir = "test_logs_temp_file_logger" # Unique name for this test suite
        # Override the LOGS_DIR in the file_logger module for the duration of the tests
        self.original_logs_dir = fl.LOGS_DIR
        fl.LOGS_DIR = self.test_logs_dir

        # Clean up the test logs directory before each test
        if os.path.exists(self.test_logs_dir):
            shutil.rmtree(self.test_logs_dir)
        # Create it fresh for each test (ensure_logs_dir_exists will also do this, but good to be explicit)
        os.makedirs(self.test_logs_dir, exist_ok=True)

    def tearDown(self):
        """Clean up after each test."""
        # Restore the original LOGS_DIR
        fl.LOGS_DIR = self.original_logs_dir
        if os.path.exists(self.test_logs_dir):
            shutil.rmtree(self.test_logs_dir)

    @patch('file_logger.datetime.datetime')
    @patch('file_logger.log_to_file')
    def test_log_error(self, mock_log_to_file, mock_datetime):
        mock_now = dt(2023, 10, 26, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now
        expected_timestamp = mock_now.isoformat() + "Z"

        fl.log_error("Machine1", "E101", "Test Error", "high", "TestScenario")
        
        expected_entry = {
            "timestamp": expected_timestamp,
            "machine_id": "Machine1",
            "error_code": "E101",
            "description": "Test Error",
            "severity": "high",
            "scenario_context": "TestScenario"
        }
        mock_log_to_file.assert_called_once_with("error.log", expected_entry)

    @patch('file_logger.datetime.datetime')
    @patch('file_logger.log_to_file')
    def test_log_production_result(self, mock_log_to_file, mock_datetime):
        mock_now = dt(2023, 10, 26, 13, 0, 0)
        mock_datetime.utcnow.return_value = mock_now
        expected_timestamp = mock_now.isoformat() + "Z"

        fl.log_production_result(123, 100, "success", "OperatorA", "Shift1", "RecipeX", 25.5)
        
        expected_entry = {
            "timestamp": expected_timestamp,
            "recipe_id": 123,
            "output_quantity": 100,
            "status": "success",
            "operator": "OperatorA",
            "shift": "Shift1",
            "recipe_name": "RecipeX",
            "cycle_time_seconds": 25.5
        }
        mock_log_to_file.assert_called_once_with("production.log", expected_entry)

    @patch('file_logger.datetime.datetime')
    @patch('file_logger.log_to_file')
    def test_log_kpi(self, mock_log_to_file, mock_datetime):
        mock_now = dt(2023, 10, 26, 14, 0, 0)
        mock_datetime.utcnow.return_value = mock_now
        expected_timestamp = mock_now.isoformat() + "Z"

        fl.log_kpi("MachineX", 0.85, 0.90, 0.95, 0.99, 10.2, 0.01, 120.0, 5.0, 50.0)
        
        expected_entry = {
            "timestamp": expected_timestamp,
            "machine_id": "MachineX",
            "OEE": 0.85,
            "availability": 0.90,
            "performance": 0.95,
            "quality": 0.99,
            "cycle_time": 10.2,
            "defect_rate": 0.01,
            "MTBF": 120.0,
            "MTTR": 5.0,
            "throughput": 50.0
        }
        mock_log_to_file.assert_called_once_with("kpi.log", expected_entry)

    @patch('file_logger.os.makedirs')
    @patch('file_logger.os.path.exists', return_value=False)
    def test_ensure_logs_dir_exists_creates_dir(self, mock_exists, mock_makedirs):
        # Temporarily set LOGS_DIR to something that _ensure_logs_dir_exists will check
        # This tests the internal helper, usually called by log_to_file
        fl._ensure_logs_dir_exists()
        mock_makedirs.assert_called_once_with(self.test_logs_dir)

    @patch('file_logger._perform_log_rotation') # Mock rotation to isolate file writing
    @patch('builtins.open', new_callable=mock_open)
    @patch('file_logger.datetime.datetime')
    def test_log_to_file_writes_correctly(self, mock_datetime, mock_file_open, mock_rotation):
        mock_now = dt(2023, 10, 26, 15, 0, 0)
        mock_datetime.utcnow.return_value = mock_now
        expected_timestamp = mock_now.isoformat() + "Z"
        
        log_data = {"message": "hello test"}
        expected_log_data_with_ts = {"message": "hello test", "timestamp": expected_timestamp}

        fl.log_to_file("test.log", log_data)

        mock_rotation.assert_called_once_with(os.path.join(self.test_logs_dir, "test.log"))
        mock_file_open.assert_called_once_with(os.path.join(self.test_logs_dir, "test.log"), "a")
        
        # Get the file handle from the mock
        handle = mock_file_open()
        
        # Check that json.dump was called with the correct data and file handle
        # json.dump(log_entry_dict, f)
        # f.write("\n")
        # We can check the arguments of write. json.dump writes to the handle.
        # The mock_open().write captures all writes.
        
        # Verify the content written by json.dump and the subsequent newline
        # json.dump doesn't return the string, it writes directly to the file handle.
        # We can check the calls to handle.write.
        # The first call to write will be from json.dump, the second is the newline.
        self.assertEqual(handle.write.call_count, 2)
        written_json_string = handle.write.call_args_list[0][0][0]
        self.assertEqual(json.loads(written_json_string), expected_log_data_with_ts)
        handle.write.assert_any_call("\n")


    @patch('file_logger.os.path.exists')
    @patch('file_logger.os.path.getsize')
    @patch('file_logger.os.rename')
    @patch('file_logger.os.remove')
    def test_log_rotation_no_rotation_needed(self, mock_remove, mock_rename, mock_getsize, mock_exists):
        log_file = os.path.join(self.test_logs_dir, "app.log")
        mock_exists.return_value = True # Assume log file exists
        mock_getsize.return_value = fl.MAX_LOG_SIZE_BYTES - 1 # Size is less than max

        fl._perform_log_rotation(log_file)

        mock_rename.assert_not_called()
        mock_remove.assert_not_called()

    @patch('file_logger.os.path.exists')
    @patch('file_logger.os.path.getsize')
    @patch('file_logger.os.rename')
    @patch('file_logger.os.remove')
    def test_log_rotation_happens_no_backups_exist(self, mock_remove, mock_rename, mock_getsize, mock_exists):
        log_file = os.path.join(self.test_logs_dir, "app.log")
        
        # Only the main log file exists
        mock_exists.side_effect = lambda path: path == log_file
        mock_getsize.return_value = fl.MAX_LOG_SIZE_BYTES + 1 # Size exceeds max

        fl._perform_log_rotation(log_file)

        mock_rename.assert_called_once_with(log_file, f"{log_file}.1")
        mock_remove.assert_not_called() # No old backups to remove

    @patch('file_logger.os.path.exists')
    @patch('file_logger.os.path.getsize')
    @patch('file_logger.os.rename')
    @patch('file_logger.os.remove')
    def test_log_rotation_all_backups_exist(self, mock_remove, mock_rename, mock_getsize, mock_exists):
        log_file_base = os.path.join(self.test_logs_dir, "app.log")
        
        # Simulate all files exist: app.log, app.log.1, ..., app.log.5
        def side_effect_exists(path):
            if path == log_file_base: return True
            for i in range(1, fl.MAX_LOG_BACKUPS + 1):
                if path == f"{log_file_base}.{i}":
                    return True
            return False
        mock_exists.side_effect = side_effect_exists
        mock_getsize.return_value = fl.MAX_LOG_SIZE_BYTES + 1 # Size exceeds max

        fl._perform_log_rotation(log_file_base)

        # Verify removal of the oldest backup
        mock_remove.assert_called_once_with(f"{log_file_base}.{fl.MAX_LOG_BACKUPS}")

        # Verify renaming sequence
        expected_rename_calls = []
        for i in range(fl.MAX_LOG_BACKUPS - 1, 0, -1):
            expected_rename_calls.append(call(f"{log_file_base}.{i}", f"{log_file_base}.{i+1}"))
        expected_rename_calls.append(call(log_file_base, f"{log_file_base}.1"))
        
        mock_rename.assert_has_calls(expected_rename_calls, any_order=False)
        self.assertEqual(mock_rename.call_count, fl.MAX_LOG_BACKUPS)


    @patch('file_logger.os.path.exists')
    @patch('file_logger.os.path.getsize')
    @patch('file_logger.os.rename')
    @patch('file_logger.os.remove')
    def test_log_rotation_some_backups_exist(self, mock_remove, mock_rename, mock_getsize, mock_exists):
        log_file_base = os.path.join(self.test_logs_dir, "app.log")
        
        # Simulate app.log, app.log.1, app.log.2 exist
        def side_effect_exists(path):
            if path == log_file_base: return True
            if path == f"{log_file_base}.1": return True
            if path == f"{log_file_base}.2": return True
            return False
        mock_exists.side_effect = side_effect_exists
        mock_getsize.return_value = fl.MAX_LOG_SIZE_BYTES + 1 # Size exceeds max

        fl._perform_log_rotation(log_file_base)
        
        mock_remove.assert_not_called() # No backup should reach MAX_LOG_BACKUPS number yet

        expected_rename_calls = [
            call(f"{log_file_base}.2", f"{log_file_base}.3"),
            call(f"{log_file_base}.1", f"{log_file_base}.2"),
            call(log_file_base, f"{log_file_base}.1")
        ]
        mock_rename.assert_has_calls(expected_rename_calls, any_order=False)
        self.assertEqual(mock_rename.call_count, 3)


if __name__ == '__main__':
    unittest.main()
