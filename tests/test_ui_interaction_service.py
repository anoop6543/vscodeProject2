import unittest
import sys
import os
import json
import shutil
from datetime import datetime as dt_class, timezone
from unittest.mock import patch, mock_open, ANY, call

# Adjust sys.path to include the parent directory (project root)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Functions and modules to be tested/mocked
import ui_interaction_service as uis
# These are dependencies of uis, so they will be patched via uis.dependency_name
# import sim_database_manager as dbm 
# import sim_opc_server # sim_opc_instance is used
# import file_logger
# import aws_logger_sim as awslog


class TestUiInteractionService(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        self.test_logs_dir_base = "test_ui_service_logs_temp"
        self.test_logs_dir_fl = os.path.join(self.test_logs_dir_base, "file_logger_logs")
        self.test_logs_dir_aws = os.path.join(self.test_logs_dir_base, "aws_sim_logs")

        # Store original paths from imported modules to restore them in tearDown
        self.original_fl_logs_dir = uis.file_logger.LOGS_DIR
        self.original_aws_logs_dir = uis.aws_logger_sim.LOGS_DIR
        self.original_aws_sim_log_file = uis.aws_logger_sim.AWS_SIM_LOG_FILE
        
        # Override LOGS_DIR in the imported modules (uis.file_logger and uis.aws_logger_sim)
        uis.file_logger.LOGS_DIR = self.test_logs_dir_fl
        uis.aws_logger_sim.LOGS_DIR = self.test_logs_dir_aws
        # If AWS_SIM_LOG_FILE is just a basename, this is fine. If it includes LOGS_DIR, it needs careful handling.
        # Assuming AWS_SIM_LOG_FILE is just a basename, so combining with new LOGS_DIR works.

        # Clean up and create fresh directories
        if os.path.exists(self.test_logs_dir_base):
            shutil.rmtree(self.test_logs_dir_base)
        os.makedirs(self.test_logs_dir_fl, exist_ok=True)
        os.makedirs(self.test_logs_dir_aws, exist_ok=True)


    def tearDown(self):
        """Clean up after each test."""
        # Restore original LOGS_DIR values
        uis.file_logger.LOGS_DIR = self.original_fl_logs_dir
        uis.aws_logger_sim.LOGS_DIR = self.original_aws_logs_dir
        uis.aws_logger_sim.AWS_SIM_LOG_FILE = self.original_aws_sim_log_file

        if os.path.exists(self.test_logs_dir_base):
            shutil.rmtree(self.test_logs_dir_base)

    @patch('ui_interaction_service.sim_opc_instance')
    @patch('ui_interaction_service.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    # Patch the constants directly where they are defined if they are top-level module constants
    @patch('ui_interaction_service.aws_logger_sim.AWS_SIM_LOG_FILE', 'test_aws_sim_cloudwatch.log') 
    # LOGS_DIR is already patched in setUp/tearDown for aws_logger_sim within uis module
    def test_get_simulation_overview(self, mock_open_call, mock_os_exists, mock_opc):
        # Scenario 1: Running scenario, last log found
        mock_opc.read_tag.side_effect = lambda tag_id: {
            "System.CurrentScenario": {"value": "PCB_Scenario"},
            "System.ScenarioStatus": {"value": "Running - PCB 2/5"},
            "GantryRobot.Status": {"value": "Moving"}
        }.get(tag_id)
        mock_os_exists.return_value = True
        mock_now_iso = dt_class(2023,1,1,12,0,0, tzinfo=timezone.utc).isoformat()
        mock_open_call().readline().decode().strip.return_value = json.dumps({"timestamp": mock_now_iso})

        overview = uis.get_simulation_overview()
        self.assertEqual(overview["simulation_status"], "Running")
        self.assertEqual(overview["current_scenario_name"], "PCB_Scenario")
        self.assertEqual(overview["scenario_status"], "Running - PCB 2/5")
        self.assertEqual(overview["last_significant_event_timestamp"], mock_now_iso)

        # Scenario 2: Idle, no scenario, Gantry Error
        mock_opc.read_tag.side_effect = lambda tag_id: {
            "System.CurrentScenario": {"value": "N/A"},
            "System.ScenarioStatus": {"value": "Idle"},
            "GantryRobot.Status": {"value": "Error"}
        }.get(tag_id)
        mock_os_exists.return_value = False # No AWS log file
        
        overview_idle_error = uis.get_simulation_overview()
        self.assertEqual(overview_idle_error["simulation_status"], "Error") # Gantry Error overrides Idle
        self.assertEqual(overview_idle_error["current_scenario_name"], "N/A")
        self.assertTrue(isinstance(overview_idle_error["last_significant_event_timestamp"], str)) # Should be recent now()

    @patch('ui_interaction_service.sim_opc_instance')
    def test_get_robot_details(self, mock_opc):
        mock_opc.read_tag.side_effect = lambda tag_id: {
            "GantryRobot.Status": {"value": "Welding"},
            "GantryRobot.AxisX.ActualPosition": {"value": 100.5},
            "GantryRobot.AxisY.ActualPosition": {"value": 200.0},
            "GantryRobot.AxisZ.ActualPosition": {"value": 50.75}
        }.get(tag_id)

        details = uis.get_robot_details("GantryRobot")
        self.assertEqual(details["robot_id"], "GantryRobot")
        self.assertEqual(details["status"], "Welding")
        self.assertEqual(details["current_position"]["x"], 100.5)
        self.assertEqual(details["current_position"]["y"], 200.0)
        self.assertEqual(details["current_position"]["z"], 50.75)
        self.assertEqual(details["gripper_content"], "Unknown") # Placeholder

    @patch('ui_interaction_service.sim_opc_instance')
    def test_get_opc_tag_snapshot(self, mock_opc):
        mock_now = dt_class(2023,1,1,12,0,0, tzinfo=timezone.utc)
        sample_tags = {
            "Tag1": {"value": 10, "timestamp": mock_now, "quality": "Good"},
            "Tag2": {"value": "Active", "timestamp": mock_now, "quality": "Good"},
        }
        mock_opc.get_all_tags.return_value = sample_tags
        mock_opc.read_tag.side_effect = lambda tag_id: sample_tags.get(tag_id)

        # Test getting all tags
        snapshot_all = uis.get_opc_tag_snapshot()
        self.assertEqual(len(snapshot_all), 2)
        self.assertEqual(snapshot_all[0]["tag_id"], "Tag1")
        self.assertEqual(snapshot_all[0]["value"], 10)
        self.assertEqual(snapshot_all[0]["timestamp"], mock_now.isoformat() + "Z")


        # Test getting specific tags
        snapshot_specific = uis.get_opc_tag_snapshot(["Tag2", "NonExistent"])
        self.assertEqual(len(snapshot_specific), 2)
        self.assertEqual(snapshot_specific[0]["tag_id"], "Tag2")
        self.assertEqual(snapshot_specific[0]["value"], "Active")
        self.assertEqual(snapshot_specific[1]["tag_id"], "NonExistent")
        self.assertIsNone(snapshot_specific[1]["value"])
        self.assertEqual(snapshot_specific[1]["quality"], "Bad - Not Found")
        
    @patch('builtins.open', new_callable=mock_open)
    @patch('ui_interaction_service.os.path.exists')
    def test_get_latest_logs(self, mock_os_exists, mock_file_open):
        # Setup paths used by uis.get_latest_logs
        # These constants are within the uis module's scope of file_logger and aws_logger_sim
        uis.file_logger.LOGS_DIR = self.test_logs_dir_fl
        uis.aws_logger_sim.LOGS_DIR = self.test_logs_dir_aws 
        uis.aws_logger_sim.AWS_SIM_LOG_FILE = 'test_aws_sim_cloudwatch.log'

        # Scenario 1: Error log
        mock_os_exists.return_value = True
        sample_error_logs = [{"msg": f"Error {i}"} for i in range(5)]
        mock_file_open().readlines.return_value = [json.dumps(log) + "\n" for log in sample_error_logs]
        
        logs = uis.get_latest_logs("error", 3)
        self.assertEqual(len(logs), 3)
        self.assertEqual(logs[0]["msg"], "Error 2") # Last 3 means index 2,3,4 from 0-4 range
        self.assertEqual(logs[2]["msg"], "Error 4")

        # Scenario 2: File not found
        mock_os_exists.return_value = False
        logs_not_found = uis.get_latest_logs("non_existent_type", 5)
        self.assertEqual(len(logs_not_found), 1)
        self.assertIn("error", logs_not_found[0])
        self.assertTrue("not found" in logs_not_found[0]["error"])

        # Scenario 3: JSON Decode Error
        mock_os_exists.return_value = True
        mock_file_open().readlines.return_value = ["This is not JSON\n", json.dumps({"msg":"good line"})+"\n"]
        logs_json_error = uis.get_latest_logs("error", 2)
        self.assertEqual(len(logs_json_error), 2)
        self.assertIn("error", logs_json_error[0])
        self.assertEqual(logs_json_error[0]["raw_log_line"], "This is not JSON")
        self.assertEqual(logs_json_error[1]["msg"], "good line")

    @patch('ui_interaction_service.dbm')
    def test_get_recipes_summary(self, mock_dbm):
        mock_dbm.get_all_recipes.return_value = [
            {"recipe_id": 1, "name": "R1", "ingredients": ["i1", "i2"], "steps": ["s1"]},
            {"recipe_id": 2, "name": "R2", "ingredients": ["iA"], "steps": ["sA", "sB"]}
        ]
        summary = uis.get_recipes_summary()
        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[0]["name"], "R1")
        self.assertEqual(summary[0]["ingredient_count"], 2)
        self.assertEqual(summary[1]["step_count"], 2)

    @patch('ui_interaction_service.dbm')
    def test_get_production_results_summary(self, mock_dbm):
        mock_data = [{"result_id": 1, "status": "success"}]
        mock_dbm.get_all_results.return_value = mock_data
        summary = uis.get_production_results_summary()
        self.assertEqual(summary, mock_data) # Currently returns data as is

    @patch('ui_interaction_service.dbm')
    def test_get_error_summary(self, mock_dbm):
        mock_data = [{"error_id": 1, "description": "Test error"}]
        mock_dbm.get_all_errors.return_value = mock_data
        summary = uis.get_error_summary()
        self.assertEqual(summary, mock_data)

    @patch('ui_interaction_service.dbm')
    def test_get_kpi_summary(self, mock_dbm):
        mock_data = [{"kpi_id": 1, "OEE": 0.8}]
        mock_dbm.get_all_kpi_records.return_value = mock_data
        summary = uis.get_kpi_summary()
        self.assertEqual(summary, mock_data)

    @patch('ui_interaction_service.awslog')
    @patch('ui_interaction_service.sim_opc_instance')
    def test_set_opc_tag_value(self, mock_opc, mock_awslog):
        # Test successful write
        tag_id = "Test.Tag"
        value = 123
        mock_opc.write_tag.return_value = True
        result = uis.set_opc_tag_value(tag_id, value)
        self.assertTrue(result["success"])
        self.assertIn("successfully written", result["message"])
        mock_opc.write_tag.assert_called_once_with(tag_id, value)
        mock_awslog.log_to_aws_sim.assert_called_once_with(
            "INFO", "ControlAction", f"OPC tag '{tag_id}' set to '{value}'.", ANY
        )

        # Test write failure (tag not found)
        mock_opc.reset_mock()
        mock_awslog.reset_mock()
        mock_opc.write_tag.return_value = False
        mock_opc.read_tag.return_value = None # Simulate tag not existing
        result_not_found = uis.set_opc_tag_value("NotFound.Tag", 456)
        self.assertFalse(result_not_found["success"])
        self.assertIn("Tag not found", result_not_found["message"])
        mock_awslog.log_to_aws_sim.assert_called_once_with(
            "ERROR", "ControlAction", "Failed to set OPC tag 'NotFound.Tag': Tag not found.", ANY
        )
        
        # Test write failure (general error)
        mock_opc.reset_mock()
        mock_awslog.reset_mock()
        mock_opc.write_tag.return_value = False
        mock_opc.read_tag.return_value = {"value": "something"} # Simulate tag exists but write fails for other reason
        result_fail = uis.set_opc_tag_value("Existing.Tag.WriteFail", 789)
        self.assertFalse(result_fail["success"])
        self.assertIn("Write operation failed", result_fail["message"])
        mock_awslog.log_to_aws_sim.assert_called_once_with(
            "ERROR", "ControlAction", "Failed to set OPC tag 'Existing.Tag.WriteFail': Write operation failed.", ANY
        )

if __name__ == '__main__':
    unittest.main()
