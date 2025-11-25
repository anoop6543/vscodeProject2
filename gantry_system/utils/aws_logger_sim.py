import json
import datetime
import os

LOGS_DIR = "logs"  # Should be consistent with file_logger.py if it also uses this
AWS_SIM_LOG_FILE = "aws_sim_cloudwatch.log"

def _ensure_logs_dir_exists():
    """Ensures the logs directory exists, creating it if necessary."""
    # This function might be duplicated from file_logger.py.
    # Consider refactoring to a common utility if this project grows.
    if not os.path.exists(LOGS_DIR):
        try:
            os.makedirs(LOGS_DIR)
            print(f"Created logs directory: {LOGS_DIR}") # Log this action
        except OSError as e:
            print(f"Error creating logs directory {LOGS_DIR}: {e}")
            # Depending on severity, might raise error or try to log to current dir

def log_to_aws_sim(level: str, category: str, message: str, details: dict = None):
    """
    Formats a log entry and appends it as a JSON string to the
    simulated AWS CloudWatch log file.

    Args:
        level (str): Log level (e.g., "INFO", "ERROR", "DEBUG").
        category (str): Category for filtering (e.g., "RobotOperation", "SystemEvent").
        message (str): The main log message.
        details (dict, optional): Additional structured data for the log entry.
    """
    _ensure_logs_dir_exists()
    
    log_file_path = os.path.join(LOGS_DIR, AWS_SIM_LOG_FILE)
    
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "log_level": level.upper(),
        "category": category,
        "message": message
    }
    
    if details is not None and isinstance(details, dict):
        log_entry["details"] = details
    elif details is not None:
        # If details is not a dict, log its string representation under a generic key
        log_entry["details"] = {"raw": str(details)} 

    try:
        with open(log_file_path, "a") as f: # Append mode
            json.dump(log_entry, f)
            f.write("\n") # Newline after each JSON entry
    except IOError as e:
        # Fallback to console if file logging fails
        print(f"CRITICAL: Error writing to AWS sim log file {log_file_path}: {e}")
        print(f"FALLBACK_AWS_SIM_LOG: {json.dumps(log_entry)}")
    except TypeError as e:
        # Fallback to console if serialization fails
        print(f"CRITICAL: Error serializing AWS sim log entry to JSON: {e}. Entry: {log_entry}")
        # Attempt to dump a more resilient version of the entry
        fallback_entry_str = f'{{"timestamp":"{log_entry.get("timestamp")}", "log_level":"{log_entry.get("log_level")}", "category":"{log_entry.get("category")}", "message":"Serialization Error - see console for original message", "original_message_type": "{type(message).__name__}"}}'
        print(f"FALLBACK_AWS_SIM_LOG: {fallback_entry_str}")


if __name__ == '__main__':
    print("AWS Logger Simulator Module. Testing log creation...")
    
    _ensure_logs_dir_exists() # Call it directly for testing this part too

    log_to_aws_sim("INFO", "SystemEvent", "Simulation started.", details={"simulation_id": "sim_12345", "version": "1.0.2"})
    log_to_aws_sim("DEBUG", "DatabaseAccess", "Querying recipes table.", details={"query": "SELECT * FROM recipes"})
    log_to_aws_sim("WARNING", "RobotOperation", "Gripper pressure low.", details={"robot_id": "Gantry1", "gripper_pressure": 25.5})
    log_to_aws_sim("ERROR", "SystemError", "Failed to connect to OPC server.", details={"opc_url": "opc.tcp://localhost:4840", "error_code": 503})
    log_to_aws_sim("CRITICAL", "RobotError", "Robot arm collision detected!", {"robot_id": "Gantry1", "axis": "X", "position": 100.5})
    log_to_aws_sim("INFO", "KPIUpdate", "KPIs calculated for Line1.", {"oee": 0.85, "items_produced": 1000})
    log_to_aws_sim("INFO", "ScenarioLifecycle", "PCB Assembly Scenario Completed.", {"pcb_count": 5, "duration_seconds": 123.45})
    log_to_aws_sim("INFO", "FileLogEvent", "Error logged to error.log", {"original_error_code": "E-101"})
    log_to_aws_sim("INFO", "General", "A log entry with non-dict details.", "This is a string detail")


    print(f"Simulated AWS logs written to {os.path.join(LOGS_DIR, AWS_SIM_LOG_FILE)}")
    print("Please check the file content.")
