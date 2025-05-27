import datetime
# import sim_database_manager as dbm # Not strictly needed if data is passed in

# --- Default Operational Parameters (can be overridden by callers) ---
# These are examples; they might be configured per machine or product in a real system.
DEFAULT_IDEAL_CYCLE_TIME_PER_UNIT_SECONDS = 10.0  # e.g., for performance calculation
DEFAULT_SCHEDULED_TIME_SECONDS = 8 * 60 * 60    # e.g., an 8-hour shift
DEFAULT_FIXED_SIMULATED_REPAIR_TIME_SECONDS = 5 * 60 # 5 minutes (Restored for potential backward compatibility if needed, though new logic prioritizes severity map)
DEFAULT_SEVERITY_REPAIR_TIMES_SECONDS = {
    "low": 1 * 60,        # 1 minute
    "medium": 5 * 60,     # 5 minutes
    "high": 30 * 60,      # 30 minutes
    "critical": 60 * 60,  # 1 hour
    "unknown": 5 * 60     # Fallback for unknown severities
}

# --- KPI Calculation Functions ---

def calculate_cycle_times_and_stats(results_list: list) -> dict:
    """
    Calculates average, min, max cycle times from 'cycle_time_seconds' in results.
    Assumes 'cycle_time_seconds' is present in each result dict.
    Returns a dictionary with 'average_cycle_time', 'min_cycle_time', 'max_cycle_time'.
    Returns 0 for times if no results or no cycle times found.
    """
    cycle_times = [r['cycle_time_seconds'] for r in results_list if 'cycle_time_seconds' in r and r['cycle_time_seconds'] is not None]
    if not cycle_times:
        return {"average_cycle_time": 0.0, "min_cycle_time": 0.0, "max_cycle_time": 0.0, "total_production_time": 0.0}
    
    return {
        "average_cycle_time": sum(cycle_times) / len(cycle_times) if cycle_times else 0.0,
        "min_cycle_time": min(cycle_times) if cycle_times else 0.0,
        "max_cycle_time": max(cycle_times) if cycle_times else 0.0,
        "total_production_time": sum(cycle_times) # Sum of all individual cycle times
    }

def calculate_quality_and_defects(results_list: list) -> dict:
    """
    Calculates total units, good units, defective units, quality rate, and defect rate.
    Args:
        results_list: List of production result dictionaries. Each dict should have a 'status' field.
    Returns:
        dict: {"total_units", "good_units", "defective_units", "quality_rate", "defect_rate"}
              Rates are 0 if total_units is 0.
    """
    total_units = len(results_list)
    if total_units == 0:
        return {"total_units": 0, "good_units": 0, "defective_units": 0, "quality_rate": 0.0, "defect_rate": 0.0}

    good_units = sum(1 for r in results_list if r.get('status') == "success")
    defective_units = total_units - good_units
    
    quality_rate = good_units / total_units if total_units > 0 else 0.0
    defect_rate = defective_units / total_units if total_units > 0 else 0.0
    
    return {
        "total_units": total_units,
        "good_units": good_units,
        "defective_units": defective_units,
        "quality_rate": quality_rate,
        "defect_rate": defect_rate
    }

def calculate_mtbf_mttr_downtime(errors_list: list, 
                                 actual_total_run_time_seconds: float, 
                                 # Third arg can be old fixed_repair_time or new severity_map
                                 third_arg=None) -> dict:
    """
    Calculates MTBF, MTTR, and total simulated downtime.
    Prioritizes severity-based calculation if third_arg is a dict (severity_repair_map).
    Otherwise, uses DEFAULT_SEVERITY_REPAIR_TIMES_SECONDS.
    The old fixed_repair_time_per_error (if passed as third_arg and is not a dict) is ignored
    in favor of severity-based calculation.
    Args:
        errors_list: List of error dictionaries. Each error must have a 'severity' field.
        actual_total_run_time_seconds: The total time period considered for calculating MTBF.
        third_arg (dict or any, optional): Can be a severity_repair_map (dict) or an old, ignored argument.
                                          Defaults internally to DEFAULT_SEVERITY_REPAIR_TIMES_SECONDS for calculations.
    Returns:
        dict: {"num_failures", "total_simulated_downtime_seconds", "mtbf_seconds", "mttr_seconds"}
    """
    severity_repair_map_to_use = DEFAULT_SEVERITY_REPAIR_TIMES_SECONDS
    if isinstance(third_arg, dict): # If a custom severity map is explicitly passed
        severity_repair_map_to_use = third_arg
    
    # The old third argument (e.g., DEFAULT_FIXED_SIMULATED_REPAIR_TIME_SECONDS from pcb_assembly.py)
    # will be passed as third_arg. If it's not a dict, it's ignored, and the logic defaults
    # to using severity_repair_map_to_use (which is DEFAULT_SEVERITY_REPAIR_TIMES_SECONDS unless a dict was passed).

    num_failures = len(errors_list)
    total_simulated_downtime_seconds = 0.0
    for error in errors_list:
        severity = error.get("severity", "unknown").lower()
        total_simulated_downtime_seconds += severity_repair_map_to_use.get(severity, severity_repair_map_to_use.get("unknown", 0))
    
    mtbf_seconds = actual_total_run_time_seconds / num_failures if num_failures > 0 else actual_total_run_time_seconds 
    mttr_seconds = total_simulated_downtime_seconds / num_failures if num_failures > 0 else 0.0
    
    return {
        "num_failures": num_failures,
        "total_simulated_downtime_seconds": total_simulated_downtime_seconds,
        "mtbf_seconds": mtbf_seconds,
        "mttr_seconds": mttr_seconds
    }

def calculate_availability(scheduled_time_seconds: float, total_simulated_downtime_seconds: float) -> dict:
    """
    Calculates Availability.
    Args:
        scheduled_time_seconds: Total scheduled time for production.
        total_simulated_downtime_seconds: Total time lost due to failures/repairs.
    Returns:
        dict: {"actual_run_time_seconds", "availability_rate"}
              Returns 0 for rate if scheduled_time is 0.
    """
    if scheduled_time_seconds <= 0:
        return {"actual_run_time_seconds": 0.0, "availability_rate": 0.0}
        
    actual_run_time_seconds = scheduled_time_seconds - total_simulated_downtime_seconds
    actual_run_time_seconds = max(0, actual_run_time_seconds) # Cannot be negative
    
    availability_rate = actual_run_time_seconds / scheduled_time_seconds
    
    return {
        "actual_run_time_seconds": actual_run_time_seconds,
        "availability_rate": availability_rate
    }

def calculate_performance(good_units: int, actual_run_time_for_performance_seconds: float, 
                          ideal_cycle_time_per_unit: float = DEFAULT_IDEAL_CYCLE_TIME_PER_UNIT_SECONDS) -> float:
    """
    Calculates Performance.
    Args:
        good_units: Number of good units produced.
        actual_run_time_for_performance_seconds: Actual time machine was running and supposed to produce.
        ideal_cycle_time_per_unit: The theoretical fastest time to produce one unit.
    Returns:
        float: Performance rate. Returns 0 if actual_run_time or ideal_cycle_time is 0.
    """
    if actual_run_time_for_performance_seconds <= 0 or ideal_cycle_time_per_unit <= 0 or good_units == 0:
        return 0.0
    
    # Potential output = actual_run_time / ideal_cycle_time
    # Performance = actual_output / potential_output 
    # Performance = (good_units / actual_run_time) / (1 / ideal_cycle_time)
    # Performance = (good_units * ideal_cycle_time) / actual_run_time
    
    performance_rate = (good_units * ideal_cycle_time_per_unit) / actual_run_time_for_performance_seconds
    return min(performance_rate, 1.0) # Performance typically capped at 100%

def calculate_oee(availability_rate: float, performance_rate: float, quality_rate: float) -> float:
    """Calculates OEE."""
    return availability_rate * performance_rate * quality_rate

def calculate_throughput(good_units: int, total_time_seconds: float) -> float:
    """
    Calculates Throughput (units per second).
    Args:
        good_units: Number of good units produced.
        total_time_seconds: Total time period (e.g., scheduled time).
    Returns:
        float: Throughput in units per second. Returns 0 if total_time_seconds is 0.
    """
    if total_time_seconds <= 0:
        return 0.0
    return good_units / total_time_seconds

if __name__ == '__main__':
    print("KPI Calculator Module. Running sample calculations...")

    # Sample data
    sample_results = [
        {"result_id": 1, "status": "success", "cycle_time_seconds": 9.5},
        {"result_id": 2, "status": "success", "cycle_time_seconds": 10.0},
        {"result_id": 3, "status": "failed", "cycle_time_seconds": 12.0}, # Defective but still took time
        {"result_id": 4, "status": "success", "cycle_time_seconds": 10.5},
    ]
    sample_errors = [
        {"error_id": 1, "description": "Jam", "severity": "medium"}, 
        {"error_id": 2, "description": "Sensor fail", "severity": "high"},
        {"error_id": 3, "description": "Minor glitch", "severity": "low"},
        {"error_id": 4, "description": "Unknown issue", "severity": "OTHER_SEV"}, # Test fallback
    ]

    print(f"--- Cycle Time Stats ---")
    cycle_stats = calculate_cycle_times_and_stats(sample_results)
    print(cycle_stats)
    avg_cycle_time = cycle_stats["average_cycle_time"]


    print(f"\n--- Quality & Defect Stats ---")
    quality_stats = calculate_quality_and_defects(sample_results)
    print(quality_stats)
    quality_rate = quality_stats["quality_rate"]
    good_units = quality_stats["good_units"]

    print(f"\n--- MTBF/MTTR/Downtime Stats ---")
    # For MTBF/Downtime, we need a run time. Let's use scheduled time as a proxy for this example run time.
    # In a real scenario, actual_total_run_time_seconds for MTBF would be scheduled_time - (downtime not related to these errors)
    # Here, we calculate downtime from these errors, then actual_run_time, then availability.
    
    # Step 1: Calculate downtime from errors
    # Assume this is for a period where scheduled time was DEFAULT_SCHEDULED_TIME_SECONDS
    # but for this small sample, let's use a smaller scheduled time for illustration
    test_scheduled_time = 60 * 60 # 1 hour
    
    # Using default severity_repair_map from the function
    mtbf_stats = calculate_mtbf_mttr_downtime(sample_errors, test_scheduled_time) 
    print(mtbf_stats)
    total_downtime = mtbf_stats["total_simulated_downtime_seconds"]

    print(f"\n--- Availability Stats ---")
    availability_stats = calculate_availability(test_scheduled_time, total_downtime)
    print(availability_stats)
    availability_rate = availability_stats["availability_rate"]
    actual_run_time = availability_stats["actual_run_time_seconds"] # This is the time machine was truly running

    print(f"\n--- Performance Stats ---")
    # Use actual_run_time for performance calculation's run time.
    # Use DEFAULT_IDEAL_CYCLE_TIME_PER_UNIT_SECONDS or a specific one for the product.
    performance_rate = calculate_performance(good_units, actual_run_time, DEFAULT_IDEAL_CYCLE_TIME_PER_UNIT_SECONDS)
    print(f"Performance Rate: {performance_rate:.2%}")
    
    print(f"\n--- OEE ---")
    oee = calculate_oee(availability_rate, performance_rate, quality_rate)
    print(f"OEE: {oee:.2%}")

    print(f"\n--- Throughput (units per scheduled hour) ---")
    throughput_per_hour = calculate_throughput(good_units, test_scheduled_time) * 3600
    print(f"Throughput: {throughput_per_hour:.2f} units/hour (based on {test_scheduled_time/3600:.2f} scheduled hours)")
