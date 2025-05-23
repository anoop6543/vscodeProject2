import unittest
import sys
import os

# Adjust sys.path to include the parent directory (project root)
# This allows importing AnalyzeSerialData which is in the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from AnalyzeSerialData import process_serial_data

class TestProcessSerialData(unittest.TestCase):

    def test_valid_data(self):
        data = "$l1.0,2.1,3.2,4.3,5.4,6.5,7.6,8.7,9.8,10.9,11.0,12.1,13.2,14.3,15.4,16.5$r"
        success, result = process_serial_data(data)
        self.assertTrue(success)
        self.assertEqual(len(result), 16)
        self.assertIsInstance(result[0], float)
        self.assertEqual(result, [1.0, 2.1, 3.2, 4.3, 5.4, 6.5, 7.6, 8.7, 9.8, 10.9, 11.0, 12.1, 13.2, 14.3, 15.4, 16.5])

    def test_missing_start_marker(self):
        data = "1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0,16.0$r"
        success, result = process_serial_data(data)
        self.assertFalse(success)
        self.assertEqual(result, "Invalid data format: Missing start marker $l")

    def test_missing_end_marker(self):
        data = "$l1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0,16.0"
        success, result = process_serial_data(data)
        self.assertFalse(success)
        self.assertEqual(result, "Invalid data format: Missing end marker $r")

    def test_too_few_values(self):
        data = "$l1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0$r" # 15 values
        success, result = process_serial_data(data)
        self.assertFalse(success)
        self.assertEqual(result, "Invalid data format: Expected 16 values, got 15")

    def test_too_many_values(self):
        data = "$l1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0,16.0,17.0$r" # 17 values
        success, result = process_serial_data(data)
        self.assertFalse(success)
        self.assertEqual(result, "Invalid data format: Expected 16 values, got 17")

    def test_non_float_value(self):
        data = "$l1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0,not_a_float,16.0$r"
        success, result = process_serial_data(data)
        self.assertFalse(success)
        self.assertTrue("Error converting values to floats" in result)

    def test_empty_input_string(self):
        data = ""
        success, result = process_serial_data(data)
        self.assertFalse(success)
        self.assertEqual(result, "Empty or None input data")
        
    def test_none_input(self):
        data = None
        success, result = process_serial_data(data)
        self.assertFalse(success)
        self.assertEqual(result, "Empty or None input data")

    def test_whitespace_handling(self):
        # Extra spaces around markers, commas, and values
        data = "  $l  1.0 , 2.1 , 3.2 , 4.3 , 5.4 , 6.5 , 7.6 , 8.7 , 9.8 , 10.9 , 11.0 , 12.1 , 13.2 , 14.3 , 15.4 , 16.5  $r  "
        success, result = process_serial_data(data)
        self.assertTrue(success)
        self.assertEqual(len(result), 16)
        self.assertEqual(result, [1.0, 2.1, 3.2, 4.3, 5.4, 6.5, 7.6, 8.7, 9.8, 10.9, 11.0, 12.1, 13.2, 14.3, 15.4, 16.5])

    def test_data_with_only_markers(self):
        data = "$l$r"
        success, result = process_serial_data(data)
        self.assertFalse(success)
        # The actual error might depend on implementation, but it should fail due to not having 16 values.
        # If splitting "" results in [''], then length is 1.
        self.assertEqual(result, "Invalid data format: Expected 16 values, got 1")
        
    def test_data_with_only_markers_and_spaces(self):
        data = "$l  $r" # Markers with spaces in between
        success, result = process_serial_data(data)
        self.assertFalse(success)
        # After stripping markers and data, `trimmed_data` will be empty. `split(',')` on empty string might give `['']`.
        self.assertEqual(result, "Invalid data format: Expected 16 values, got 1")

if __name__ == '__main__':
    unittest.main()
