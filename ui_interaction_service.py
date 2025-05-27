import datetime
import json # For get_latest_logs
import os   # For get_latest_logs
from sim_opc_server import sim_opc_instance # OPC interactions
# from scenarios.pcb_assembly import pcb_assembly_line_instance # This is tricky, avoid direct instance import if possible.
                                                                # How to get scenario status? Perhaps OPC tags or a global registry.
                                                                # For now, scenario_name and status might be hardcoded or fetched via a conventional OPC tag.
import aws_logger_sim # For last_significant_event_timestamp
import file_logger # For paths to other log files
import sim_database_manager as dbm 


# Placeholder for accessing the main simulation scenario instance if needed.
# This is tricky as the service should ideally not be too coupled with one scenario.
# For now, we might pass scenario instances or have scenarios register themselves.
# Let's assume for now that functions will take necessary context or use global/imported instances.

# --- Simulation State Functions ---
def get_simulation_overview() -> dict:
    """
    Returns a high-level overview of the simulation's current state.
    """
    # Try to get scenario info from OPC if set by scenario
    scenario_name_tag = sim_opc_instance.read_tag("System.CurrentScenario")
    scenario_status_tag = sim_opc_instance.read_tag("System.ScenarioStatus")

    # Get timestamp of the last AWS log as a proxy for "last significant event"
    last_event_ts = None
    log_file_path = os.path.join(aws_logger_sim.LOGS_DIR, aws_logger_sim.AWS_SIM_LOG_FILE)
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'rb') as f: # Read in binary to handle seeking from end
                f.seek(-2, os.SEEK_END) # Go to before the last newline
                while f.read(1) != b'\n' and f.tell() > 1:
                    f.seek(-2, os.SEEK_CUR)
                if f.tell() > 1: # Found a newline
                    last_line = f.readline().decode().strip()
                else: # File is probably just one line
                    f.seek(0)
                    last_line = f.readline().decode().strip()
                
                if last_line:
                    last_log_entry = json.loads(last_line)
                    last_event_ts = last_log_entry.get("timestamp")
        except Exception as e:
            # print(f"UI_SERVICE_ERROR: Could not read last AWS log timestamp: {e}")
            pass # Keep last_event_ts as None

    # Overall simulation status could be inferred (e.g., if GantryRobot.Status is Error)
    gantry_status_tag = sim_opc_instance.read_tag("GantryRobot.Status")
    sim_status = "Running" # Default
    if gantry_status_tag and gantry_status_tag['value'] == "Error": # Assuming GantryRobot would set this
        sim_status = "Error"
    elif not scenario_name_tag or not scenario_name_tag['value'] or scenario_name_tag['value'] == "N/A": # If no scenario is active
            sim_status = "Idle"


    return {
        "simulation_status": sim_status,
        "current_scenario_name": scenario_name_tag['value'] if scenario_name_tag else "N/A",
        "scenario_status": scenario_status_tag['value'] if scenario_status_tag else "N/A",
        "last_significant_event_timestamp": last_event_ts if last_event_ts else (datetime.datetime.utcnow().isoformat() + "Z")
    }

def get_robot_details(robot_id: str) -> dict: # robot_id could be "GantryRobot" or "Robot.placer" etc.
    """
    Returns details for a specific robot, primarily from OPC tags.
    """
    # Normalize robot_id for OPC tag lookup if scenarios use prefixes like "Robot."
    opc_robot_prefix = robot_id if '.' in robot_id else f"{robot_id}" # Adjust if GantryRobot tags are just "GantryRobot.AxisX..."
    # For this simulation, GantryRobot tags are directly "GantryRobot.Status", etc.
    # If a scenario uses "Robot.placer", we need to map that to "GantryRobot" or have specific tags for "Robot.placer"
    # For now, let's assume if robot_id is "GantryRobot", we use it directly.
    # If it's like "Robot.placer", it's conceptual unless such tags are defined.
    if robot_id != "GantryRobot" and not robot_id.startswith("SimPLC.") and not robot_id.startswith("Conveyor."):
        # This might be a specific robot from a scenario, which doesn't have its own root OPC tags in this simple setup
        # We'll default to showing GantryRobot status for any non-PLC/Conveyor specific robot ID for now.
        # A more complex system would have unique OPC paths for each named robot in scenarios.
        opc_robot_prefix_for_status = "GantryRobot" # Default to general Gantry for status
    else:
        opc_robot_prefix_for_status = opc_robot_prefix


    status_tag_id = f"{opc_robot_prefix_for_status}.Status"
    x_pos_tag_id = f"{opc_robot_prefix_for_status}.AxisX.ActualPosition"
    y_pos_tag_id = f"{opc_robot_prefix_for_status}.AxisY.ActualPosition"
    z_pos_tag_id = f"{opc_robot_prefix_for_status}.AxisZ.ActualPosition"

    status_tag = sim_opc_instance.read_tag(status_tag_id)
    x_pos_tag = sim_opc_instance.read_tag(x_pos_tag_id)
    y_pos_tag = sim_opc_instance.read_tag(y_pos_tag_id)
    z_pos_tag = sim_opc_instance.read_tag(z_pos_tag_id)

    # Gripper content is not currently in OPC, so placeholder
    gripper_content = "Unknown" 

    return {
        "robot_id": robot_id,
        "status": status_tag['value'] if status_tag else "Unknown",
        "current_position": {
            "x": x_pos_tag['value'] if x_pos_tag else 0.0,
            "y": y_pos_tag['value'] if y_pos_tag else 0.0,
            "z": z_pos_tag['value'] if z_pos_tag else 0.0,
        },
        "gripper_content": gripper_content, # Placeholder
        "opc_status_tag": status_tag_id,
        "opc_position_tags": {"x": x_pos_tag_id, "y": y_pos_tag_id, "z": z_pos_tag_id}
    }

def get_opc_tag_snapshot(tag_ids: list = None) -> list:
    """
    Returns values of specified OPC tags, or a selection of all key tags.
    Returns a list of tag dictionaries.
    """
    all_tags_data = sim_opc_instance.get_all_tags()
    snapshot = []

    if tag_ids: # User specified specific tags
        for tag_id in tag_ids:
            tag_data = all_tags_data.get(tag_id)
            if tag_data:
                snapshot.append({
                    "tag_id": tag_id,
                    "value": tag_data["value"],
                    "timestamp": tag_data["timestamp"].isoformat() + "Z",
                    "quality": tag_data["quality"]
                })
            else:
                snapshot.append({"tag_id": tag_id, "value": None, "timestamp": None, "quality": "Bad - Not Found"})
    else: # Return all tags (or a predefined subset of key tags if too many)
        for tag_id, tag_data in all_tags_data.items():
            snapshot.append({
                "tag_id": tag_id,
                "value": tag_data["value"],
                "timestamp": tag_data["timestamp"].isoformat() + "Z",
                "quality": tag_data["quality"]
            })
    return snapshot

def get_latest_logs(log_type: str, count: int) -> list:
    """
    Retrieves the last 'count' entries from the specified log file.
    Log types: "error", "production", "kpi", "aws_cloudwatch_sim"
    """
    log_file_map = {
        "error": os.path.join(file_logger.LOGS_DIR, "error.log"),
        "production": os.path.join(file_logger.LOGS_DIR, "production.log"),
        "kpi": os.path.join(file_logger.LOGS_DIR, "kpi.log"),
        "aws_cloudwatch_sim": os.path.join(aws_logger_sim.LOGS_DIR, aws_logger_sim.AWS_SIM_LOG_FILE)
    }

    file_path = log_file_map.get(log_type.lower())
    if not file_path or not os.path.exists(file_path):
        return [{"error": f"Log file for type '{log_type}' not found at {file_path if file_path else 'N/A'}"}]

    lines = []
    try:
        with open(file_path, 'r') as f:
            # Read all lines and then take the last 'count'
            all_lines = f.readlines()
            # Strip newline characters and filter out empty lines
            all_lines = [line.strip() for line in all_lines if line.strip()]
        
        # Get the last 'count' lines
        relevant_lines = all_lines[-count:]
        
        for line in relevant_lines:
            try:
                lines.append(json.loads(line)) # Parse each line as JSON
            except json.JSONDecodeError:
                lines.append({"raw_log_line": line, "error": "Failed to parse JSON"})
        return lines
    except Exception as e:
        # print(f"UI_SERVICE_ERROR: Could not read log file {file_path}: {e}")
        return [{"error": f"Failed to read or parse log file {file_path}: {str(e)}"}]

# --- Historical/Aggregated Data Functions ---
def get_recipes_summary() -> list:
    """
    Returns a summary list of available recipes (ID, name, ingredient/step counts).
    """
    all_recipes = dbm.get_all_recipes()
    summary_list = []
    for recipe in all_recipes:
        summary_list.append({
            "recipe_id": recipe.get("recipe_id"),
            "name": recipe.get("name"),
            "ingredient_count": len(recipe.get("ingredients", [])),
            "step_count": len(recipe.get("steps", []))
        })
    # awslog.log_to_aws_sim("DEBUG", "UIService", "Fetched recipes summary.", {"count": len(summary_list)}) # Optional AWS log
    return summary_list

def get_production_results_summary(filters: dict = None) -> list:
    """
    Returns production results, optionally filtered.
    Filters are conceptual for now (e.g., date_range, recipe_id, status).
    Returns all results for this initial implementation.
    """
    # print(f"UI_SERVICE: get_production_results_summary with filters {filters} (filters not implemented yet)") # Placeholder print
    all_results = dbm.get_all_results()
    # Basic filtering example (can be expanded later):
    # if filters:
    #     if "recipe_id" in filters:
    #         all_results = [r for r in all_results if r.get("recipe_id") == filters["recipe_id"]]
    #     if "status" in filters:
    #         all_results = [r for r in all_results if r.get("status") == filters["status"]]
    #     # Date range filtering would require parsing 'timestamp' (datetime objects)
    
    # awslog.log_to_aws_sim("DEBUG", "UIService", "Fetched production results summary.", {"filter_count": len(all_results), "filters_applied": filters if filters else "None"})
    return all_results # Returns list of full result dicts for now

def get_error_summary(filters: dict = None) -> list:
    """
    Returns error logs, optionally filtered.
    Filters are conceptual for now. Returns all errors.
    """
    # print(f"UI_SERVICE: get_error_summary with filters {filters} (filters not implemented yet)")
    all_errors = dbm.get_all_errors()
    # Add basic filtering examples similar to get_production_results_summary if desired
    # e.g., by machine_id, severity, date_range
    # awslog.log_to_aws_sim("DEBUG", "UIService", "Fetched error summary.", {"filter_count": len(all_errors), "filters_applied": filters if filters else "None"})
    return all_errors # Returns list of full error dicts

def get_kpi_summary(filters: dict = None) -> list:
    """
    Returns KPI records, optionally filtered.
    Filters are conceptual for now. Returns all KPI records.
    """
    # print(f"UI_SERVICE: get_kpi_summary with filters {filters} (filters not implemented yet)")
    all_kpis = dbm.get_all_kpi_records()
    # Add basic filtering examples if desired
    # e.g., by machine_id, date_range
    # awslog.log_to_aws_sim("DEBUG", "UIService", "Fetched KPI summary.", {"filter_count": len(all_kpis), "filters_applied": filters if filters else "None"})
    return all_kpis # Returns list of full KPI dicts

# --- Conceptual Simulation Control Functions (Design only, no implementation) ---
# def start_scenario(scenario_name: str, params: dict) -> bool: pass
# def pause_simulation() -> bool: pass
# def resume_simulation() -> bool: pass
# def set_opc_tag_value(tag_id: str, value: any) -> bool: pass


if __name__ == '__main__':
    print("UI Interaction Service Module - Placeholder Implementation")
    print("\n--- Testing Implemented Functions ---")
    # Simulate that a scenario has set these OPC tags
    sim_opc_instance.write_tag("System.CurrentScenario", "PCB Assembly")
    sim_opc_instance.write_tag("System.ScenarioStatus", "Processing PCB 2/5")
    sim_opc_instance.write_tag("GantryRobot.Status", "Moving")
    sim_opc_instance.write_tag("GantryRobot.AxisX.ActualPosition", 100.5)

    print(f"get_simulation_overview(): {json.dumps(get_simulation_overview(), indent=2)}")
    print(f"get_robot_details('GantryRobot'): {json.dumps(get_robot_details('GantryRobot'), indent=2)}")
    # Test with a scenario-specific name if needed (current logic defaults to GantryRobot for positions)
    # print(f"get_robot_details('Robot.placer'): {json.dumps(get_robot_details('Robot.placer'), indent=2)}") 
    print(f"get_opc_tag_snapshot(['SimPLC.S1.Temp', 'GantryRobot.Status', 'NonExistent.Tag']): {json.dumps(get_opc_tag_snapshot(['SimPLC.S1.Temp', 'GantryRobot.Status', 'NonExistent.Tag']), indent=2)}")
    print(f"get_opc_tag_snapshot (all): {json.dumps(get_opc_tag_snapshot(), indent=2)}")
    
    # Create some dummy log files for get_latest_logs demonstration
    if not os.path.exists(file_logger.LOGS_DIR): os.makedirs(file_logger.LOGS_DIR)
    with open(os.path.join(file_logger.LOGS_DIR, "error.log"), "w") as f:
        for i in range(5): f.write(json.dumps({"timestamp": datetime.datetime.utcnow().isoformat()+"Z", "msg": f"Error line {i+1}"}) + "\n")
    with open(os.path.join(aws_logger_sim.LOGS_DIR, aws_logger_sim.AWS_SIM_LOG_FILE), "w") as f:
        for i in range(3): f.write(json.dumps({"timestamp": datetime.datetime.utcnow().isoformat()+"Z", "msg": f"AWS log line {i+1}"}) + "\n")
        
    print(f"get_latest_logs('error', 3): {json.dumps(get_latest_logs('error', 3), indent=2)}")
    print(f"get_latest_logs('aws_cloudwatch_sim', 5): {json.dumps(get_latest_logs('aws_cloudwatch_sim', 5), indent=2)}") # Ask for 5, get 3
    print(f"get_latest_logs('non_existent_log', 5): {json.dumps(get_latest_logs('non_existent_log', 5), indent=2)}")


    print("\n--- Testing Placeholder Functions (Historical/Aggregated) ---")
    # print(f"get_recipes_summary(): {get_recipes_summary()}")
    # print(f"get_production_results_summary(): {get_production_results_summary()}")
    # print(f"get_error_summary(): {get_error_summary()}")
    # print(f"get_kpi_summary(): {get_kpi_summary()}")
    # print("\nNote: These are placeholder outputs for historical data. Full implementation to follow.")

    print("\n--- Testing Implemented Historical/Aggregated Data Functions ---")
    print("Populating some sample data in DB Manager first...")
    # import sim_database_manager as dbm # Already imported at module level
    
    # Clear existing data for a clean test run of this main block
    dbm.db_recipes.clear()
    dbm.db_results.clear()
    dbm.db_errors.clear()
    dbm.db_kpis.clear()
    dbm.next_recipe_id = 1
    dbm.next_result_id = 1
    dbm.next_error_id = 1
    dbm.next_kpi_id = 1

    # Create sample data
    recipe_ui_test_id = dbm.create_recipe("UI Test Recipe", ["ui_ing1"], ["ui_step1"])
    recipe_ui_test_id2 = dbm.create_recipe("UI Test Recipe 2", ["ui_ingA", "ui_ingB"], ["ui_s1", "ui_s2"])
    
    dbm.create_result(recipe_ui_test_id, 10, "success", "UI_Op", "UI_Shift")
    dbm.create_result(recipe_ui_test_id2, 5, "failed", "UI_Op2", "UI_Shift_Night")
    
    dbm.create_error("UI_Machine_1", "UI_E01", "UI test error 1", "medium")
    dbm.create_error("UI_Machine_2", "UI_E02", "UI test error 2", "high")
    
    dbm.create_kpi_record("UI_Machine_1", 0.75, 0.8, 0.9, 0.95, 20, 0.05)
    dbm.create_kpi_record("UI_Machine_2", 0.65, 0.7, 0.85, 0.90, 25, 0.1)
    print("Sample data populated.")

    print(f"get_recipes_summary(): {json.dumps(get_recipes_summary(), indent=2)}")
    print(f"get_production_results_summary(): {json.dumps(get_production_results_summary(), indent=2, default=str)}") # default=str for datetime
    print(f"get_error_summary(): {json.dumps(get_error_summary(), indent=2, default=str)}")
    print(f"get_kpi_summary(): {json.dumps(get_kpi_summary(), indent=2, default=str)}")
    print("\nNote: Full filtering for summary functions is not yet implemented.")
