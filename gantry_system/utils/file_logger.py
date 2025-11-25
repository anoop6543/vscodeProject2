import json
import datetime
import os
import aws_logger_sim as awslog # Added for AWS logging simulation

LOGS_DIR = "logs" # Define the directory for logs
MAX_LOG_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB
MAX_LOG_BACKUPS = 5

def _ensure_logs_dir_exists():
    """Ensures the logs directory exists, creating it if necessary."""
    if not os.path.exists(LOGS_DIR):
        try:
            os.makedirs(LOGS_DIR)
        except OSError as e:
            print(f"Error creating logs directory {LOGS_DIR}: {e}")
            # Potentially raise an error or handle more gracefully

def log_to_file(log_file_name: str, log_entry_dict: dict):
    """
    Appends a log entry (as a JSON string) to the specified log file.
    Each log entry will be on a new line.
    Args:
        log_file_name (str): The base name of the log file (e.g., "error.log").
        log_entry_dict (dict): The dictionary containing the log data.
    """
    _ensure_logs_dir_exists()
    
    file_path = os.path.join(LOGS_DIR, log_file_name)
    
    _perform_log_rotation(file_path) # Call rotation before writing

    try:
        # Add a standard timestamp if not already present (though helpers should add it)
        if "timestamp" not in log_entry_dict:
             log_entry_dict["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

        with open(file_path, "a") as f: # Append mode
            json.dump(log_entry_dict, f)
            f.write("\n") # Newline after each JSON entry
    except IOError as e:
        print(f"Error writing to log file {file_path}: {e}")
    except TypeError as e:
        print(f"Error serializing log entry to JSON: {e}. Entry: {log_entry_dict}")

# --- Helper Functions for Specific Log Types ---

def _perform_log_rotation(file_path: str):
    """
    Performs log rotation if the current log file exceeds MAX_LOG_SIZE_BYTES.
    Rotates files like: app.log -> app.log.1, app.log.1 -> app.log.2, etc.
    Args:
        file_path (str): The full path to the current log file.
    """
    if not os.path.exists(file_path):
        return

    try:
        if os.path.getsize(file_path) < MAX_LOG_SIZE_BYTES:
            return
    except OSError as e:
        print(f"Error checking log file size for {file_path}: {e}")
        return # Cannot determine size, so don't rotate

    # Need to rotate. Start from the oldest backup.
    # First, remove the oldest backup if it would exceed the max number of backups
    oldest_backup_path = f"{file_path}.{MAX_LOG_BACKUPS}"
    if os.path.exists(oldest_backup_path):
        try:
            os.remove(oldest_backup_path)
        except OSError as e:
            print(f"Error removing oldest backup log {oldest_backup_path}: {e}")
            # Continue with rotation if possible

    # Shift existing backups: from .4 to .5, .3 to .4, ..., .1 to .2
    for i in range(MAX_LOG_BACKUPS - 1, 0, -1): # Iterate from MAX_LOG_BACKUPS-1 down to 1
        sfn = f"{file_path}.{i}"
        dfn = f"{file_path}.{i+1}"
        if os.path.exists(sfn):
            try:
                os.rename(sfn, dfn)
            except OSError as e:
                print(f"Error rotating log {sfn} to {dfn}: {e}")
    
    # Rotate current log file to .1
    # Check again if current file_path exists, as it might have been part of a failed rotation above
    if os.path.exists(file_path): 
        try:
            os.rename(file_path, f"{file_path}.1")
        except OSError as e:
            print(f"Error rotating current log {file_path} to {file_path}.1: {e}")

def log_error(machine_id: str, error_code: str, description: str, severity: str, scenario_context: str = None):
    """Logs an error event."""
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "machine_id": machine_id,
        "error_code": error_code,
        "description": description,
        "severity": severity,
    }
    if scenario_context:
        entry["scenario_context"] = scenario_context
    log_to_file("error.log", entry)
    awslog.log_to_aws_sim(
        "INFO",
        "FileLogEvent",
        f"Error event logged to error.log.",
        details={
            "log_file": "error.log",
            "machine_id": machine_id,
            "error_code": error_code,
            "severity": severity
        }
    )

def log_production_result(recipe_id: int, output_quantity: int, status: str, 
                          operator: str, shift: str, recipe_name: str = None, 
                          cycle_time_seconds: float = None):
    """Logs a production result event."""
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "recipe_id": recipe_id,
        "output_quantity": output_quantity,
        "status": status,
        "operator": operator,
        "shift": shift,
    }
    if recipe_name:
        entry["recipe_name"] = recipe_name
    if cycle_time_seconds is not None: # Ensure 0 is logged if passed
        entry["cycle_time_seconds"] = cycle_time_seconds
    log_to_file("production.log", entry)
    awslog.log_to_aws_sim(
        "INFO",
        "FileLogEvent",
        f"Production result logged to production.log.",
        details={
            "log_file": "production.log",
            "recipe_id": recipe_id,
            "status": status,
            "output_quantity": output_quantity
        }
    )

def log_kpi(machine_id: str, oee: float, availability: float, performance: float, 
            quality: float, cycle_time: float, defect_rate: float,
            mtbf: float = None, mttr: float = None, throughput: float = None):
    """Logs a set of KPI metrics."""
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "machine_id": machine_id,
        "OEE": oee,
        "availability": availability,
        "performance": performance,
        "quality": quality,
        "cycle_time": cycle_time,
        "defect_rate": defect_rate,
    }
    if mtbf is not None:
        entry["MTBF"] = mtbf
    if mttr is not None:
        entry["MTTR"] = mttr
    if throughput is not None:
        entry["throughput"] = throughput
    log_to_file("kpi.log", entry)
    awslog.log_to_aws_sim(
        "INFO",
        "FileLogEvent",
        f"KPI data logged to kpi.log.",
        details={
            "log_file": "kpi.log",
            "machine_id": machine_id,
            "OEE": oee # Example key KPI field
        }
    )

if __name__ == '__main__':
    print("File logger module. Testing log creation and rotation...")
    
    # Temporarily set a small log size for testing rotation
    # Note: This change is local to this test block. 
    # The global MAX_LOG_SIZE_BYTES will still be 1MB for actual use.
    # To properly test, you might need to pass MAX_LOG_SIZE_BYTES to _perform_log_rotation
    # or make it a parameter of log_to_file for testing.
    # For this subtask, we'll assume manual verification or simple loop.

    print(f"Testing rotation for error.log (MAX_LOG_SIZE_BYTES={MAX_LOG_SIZE_BYTES}, MAX_LOG_BACKUPS={MAX_LOG_BACKUPS})")
    # Create dummy data to exceed log size quickly (if MAX_LOG_SIZE_BYTES is small for testing)
    # For actual 1MB, this loop would need to be very large.
    # This is more of a conceptual test for the main block.
    # Real testing for rotation should be in unit tests with mocked os functions.
    
    # To demonstrate rotation, one might temporarily set MAX_LOG_SIZE_BYTES to a small value (e.g., 1024)
    # and then run this script. For submission, we'll keep it as is.
    # temp_max_log_size = MAX_LOG_SIZE_BYTES
    # MAX_LOG_SIZE_BYTES = 1024 # Temporarily override for test
    
    if MAX_LOG_SIZE_BYTES < 20000: # Only run if set small for a quick visual test (e.g. 1KB or 10KB)
        print(f"MAX_LOG_SIZE_BYTES is {MAX_LOG_SIZE_BYTES} which is small enough for loop test.")
        # Each log entry is around 150-200 bytes.
        # For 1KB, need ~5-7 entries. For 10KB, ~50-70 entries.
        num_entries_for_rotation_test = (MAX_LOG_SIZE_BYTES // 150) * (MAX_LOG_BACKUPS + 2) # Generate enough to rotate a few times
        print(f"Generating {num_entries_for_rotation_test} log entries to test rotation...")
        for i in range(num_entries_for_rotation_test): 
            log_error(machine_id="RotationTest001", error_code=f"ERR-{i:03d}", 
                      description="This is a test log entry for rotation testing purposes to fill up the log file.", severity="low", 
                      scenario_context="rotation_test_loop")
        print(f"Multiple error logs created in {os.path.join(LOGS_DIR, 'error.log')} to test rotation.")
    else:
        print("MAX_LOG_SIZE_BYTES is large, skipping extensive rotation test in main block.")
        # Just create one of each as before
        log_error(machine_id="TestMachine001", error_code="INIT_FAIL", 
                  description="Initialization sequence failed.", severity="critical", 
                  scenario_context="startup_test")
        log_production_result(recipe_id=101, output_quantity=500, status="success", 
                              operator="TestOp", shift="Night", recipe_name="TestRecipe", 
                              cycle_time_seconds=15.5)
        log_kpi(machine_id="Line1Overall", oee=0.75, availability=0.8, performance=0.95, 
                quality=0.99, cycle_time=25.0, defect_rate=0.01, mtbf=120.5, throughput=1000)
    
    # MAX_LOG_SIZE_BYTES = temp_max_log_size # Restore if changed
    
    print("Sample logs created. Check the 'logs' directory.")
