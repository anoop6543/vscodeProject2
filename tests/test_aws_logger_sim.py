import unittest
import sys
import os
import json
import shutil
from datetime import datetime as dt_class, timezone # Alias for datetime.datetime
from unittest.mock import patch, mock_open, call

# Adjust sys.path to include the parent directory (project root)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import aws_logger_sim as awsl

class TestAwsLoggerSim(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        self.test_logs_dir = "test_aws_logs_temp" # Unique name for this test suite
        self.original_logs_dir = awsl.LOGS_DIR
        awsl.LOGS_DIR = self.test_logs_dir

        if os.path.exists(self.test_logs_dir):
            shutil.rmtree(self.test_logs_dir)
        os.makedirs(self.test_logs_dir, exist_ok=True)

    def tearDown(self):
        """Clean up after each test."""
        awsl.LOGS_DIR = self.original_logs_dir
        if os.path.exists(self.test_logs_dir):
            shutil.rmtree(self.test_logs_dir)

    @patch('aws_logger_sim.datetime.datetime')
    @patch('builtins.open', new_callable=mock_open)
    def test_log_structure_and_content(self, mock_file_open, mock_datetime_aws):
        mock_now = dt_class(2023, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
        # For isoformat() + "Z", the datetime object should ideally be naive UTC or timezone-aware UTC.
        # Python's isoformat() on naive datetime doesn't add 'Z'.
        # Let's adjust the mock to return a naive datetime, as the original code uses utcnow() without tz.
        mock_naive_now = dt_class(2023, 1, 1, 10, 30, 0)
        mock_datetime_aws.utcnow.return_value = mock_naive_now
        expected_timestamp = mock_naive_now.isoformat() + "Z"
        
        details_dict = {"key": "value", "num": 123}
        awsl.log_to_aws_sim("INFO", "TestCategory", "Test message", details=details_dict)
        
        expected_path = os.path.join(self.test_logs_dir, awsl.AWS_SIM_LOG_FILE)
        mock_file_open.assert_called_once_with(expected_path, "a")
        
        handle = mock_file_open()
        # First call to write is json.dump, second is newline
        written_json_str = handle.write.call_args_list[0][0][0] 
        written_data = json.loads(written_json_str)
        
        self.assertEqual(written_data['timestamp'], expected_timestamp)
        self.assertEqual(written_data['log_level'], "INFO")
        self.assertEqual(written_data['category'], "TestCategory")
        self.assertEqual(written_data['message'], "Test message")
        self.assertEqual(written_data['details'], details_dict)
        
        self.assertEqual(handle.write.call_args_list[1][0][0], "\n")

    @patch('aws_logger_sim.datetime.datetime')
    @patch('builtins.open', new_callable=mock_open)
    def test_log_with_no_details(self, mock_file_open, mock_datetime_aws):
        mock_naive_now = dt_class(2023, 1, 1, 10, 30, 0)
        mock_datetime_aws.utcnow.return_value = mock_naive_now
        
        awsl.log_to_aws_sim("ERROR", "NoDetails", "Message without details")
        
        handle = mock_file_open()
        written_json_str = handle.write.call_args_list[0][0][0]
        written_data = json.loads(written_json_str)
        
        self.assertNotIn("details", written_data, "Details field should be absent if not provided")

    @patch('aws_logger_sim.datetime.datetime')
    @patch('builtins.open', new_callable=mock_open)
    def test_log_with_non_dict_details(self, mock_file_open, mock_datetime_aws):
        mock_naive_now = dt_class(2023, 1, 1, 10, 30, 0)
        mock_datetime_aws.utcnow.return_value = mock_naive_now
        
        detail_string = "this is a string"
        awsl.log_to_aws_sim("WARNING", "NonDictDetails", "Message with string detail", details=detail_string)
        
        handle = mock_file_open()
        written_json_str = handle.write.call_args_list[0][0][0]
        written_data = json.loads(written_json_str)
        
        self.assertIn("details", written_data)
        self.assertEqual(written_data['details'], {"raw": detail_string})

    @patch('aws_logger_sim.datetime.datetime')
    @patch('builtins.open', new_callable=mock_open)
    def test_log_level_uppercased(self, mock_file_open, mock_datetime_aws):
        mock_naive_now = dt_class(2023, 1, 1, 10, 30, 0)
        mock_datetime_aws.utcnow.return_value = mock_naive_now

        awsl.log_to_aws_sim("info", "CaseTest", "Lowercase level")
        
        handle = mock_file_open()
        written_json_str = handle.write.call_args_list[0][0][0]
        written_data = json.loads(written_json_str)
        
        self.assertEqual(written_data['log_level'], "INFO")

    @patch('aws_logger_sim.os.makedirs')
    @patch('aws_logger_sim.os.path.exists', return_value=False)
    def test_directory_creation(self, mock_path_exists, mock_makedirs):
        # Call a function that internally calls _ensure_logs_dir_exists
        with patch('builtins.open', new_callable=mock_open): # Mock open to prevent actual file write
            awsl.log_to_aws_sim("INFO", "DirTest", "Testing dir creation")
        
        mock_path_exists.assert_called_with(self.test_logs_dir)
        mock_makedirs.assert_called_once_with(self.test_logs_dir)
        
    @patch('aws_logger_sim.os.path.exists', return_value=True) # Assume dir exists
    @patch('builtins.open', side_effect=IOError("Disk full"))
    @patch('builtins.print')
    def test_io_error_fallback_to_print(self, mock_print, mock_open_error, mock_path_exists):
        awsl.log_to_aws_sim("CRITICAL", "IOErrorTest", "Cannot write to file")
        
        # Check that print was called with messages indicating the critical error and fallback
        self.assertTrue(any("CRITICAL: Error writing to AWS sim log file" in call_args[0][0] for call_args in mock_print.call_args_list))
        self.assertTrue(any("FALLBACK_AWS_SIM_LOG:" in call_args[0][0] for call_args in mock_print.call_args_list))

    @patch('aws_logger_sim.os.path.exists', return_value=True) # Assume dir exists
    @patch('builtins.open', new_callable=mock_open) # Allow open to be mocked successfully
    @patch('json.dump', side_effect=TypeError("Cannot serialize complex object"))
    @patch('builtins.print')
    def test_type_error_fallback_to_print(self, mock_print_type_error, mock_json_dump_error, mock_open_type_error, mock_path_exists_type_error):
        awsl.log_to_aws_sim("CRITICAL", "TypeErrorTest", "Serialization issue", details={"unserializable": object()})
        
        self.assertTrue(any("CRITICAL: Error serializing AWS sim log entry to JSON" in call_args[0][0] for call_args in mock_print_type_error.call_args_list))
        self.assertTrue(any("FALLBACK_AWS_SIM_LOG:" in call_args[0][0] for call_args in mock_print_type_error.call_args_list))
        # Check if the fallback log contains a message about serialization error
        self.assertTrue(any("Serialization Error - see console for original message" in call_args[0][0] for call_args in mock_print_type_error.call_args_list if "FALLBACK_AWS_SIM_LOG:" in call_args[0][0]))


if __name__ == '__main__':
    unittest.main()
