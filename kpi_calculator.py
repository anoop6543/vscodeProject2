import datetime
from typing import List, Dict, Any, Optional, Tuple, Union, Sequence, Mapping

import sim_database_manager as dbm

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

# Loss categories for production loss analysis
LOSS_CATEGORIES = {
    "AVAILABILITY_LOSSES": [
        "breakdown",
        "setup",
        "changeover",
        "maintenance"
    ],
    "PERFORMANCE_LOSSES": [
        "small_stops",
        "reduced_speed",
        "idle_time"
    ],
    "QUALITY_LOSSES": [
        "defects",
        "rework",
        "yield_loss",
        "startup_rejects"
    ]
}

# Six Big Losses categories (standard in TPM)
SIX_BIG_LOSSES = {
    "DOWNTIME_LOSSES": [
        "breakdowns",
        "setup_and_adjustments"
    ],
    "SPEED_LOSSES": [
        "small_stops",
        "reduced_speed"
    ],
    "QUALITY_LOSSES": [
        "startup_rejects",
        "production_rejects"
    ]
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

def calculate_teep(oee: float, loading_factor: float) -> float:
    """
    Calculates Total Effective Equipment Performance (TEEP).
    TEEP extends OEE by considering all available time (24/7), not just scheduled time.
    
    Args:
        oee: Overall Equipment Effectiveness (0.0 to 1.0)
        loading_factor: Ratio of scheduled time to total available time (0.0 to 1.0)
                       E.g., 8-hour shift out of 24 hours = 8/24 = 0.333
    
    Returns:
        float: TEEP value (0.0 to 1.0)
    """
    if loading_factor <= 0 or loading_factor > 1.0:
        return 0.0
    return oee * loading_factor

def calculate_equipment_utilization(
    actual_run_time_seconds: float,
    available_time_seconds: float,
    time_period_description: str = "shift"
) -> Dict[str, Union[float, str]]:
    """
    Calculates equipment utilization metrics.
    
    Args:
        actual_run_time_seconds: Time the equipment was actually running (seconds)
        available_time_seconds: Total time available (seconds) - often calendar time (24/7)
        time_period_description: Description of the time period for context
        
    Returns:
        dict: Utilization metrics including:
             - utilization_rate: Percentage of available time that equipment ran
             - idle_time_seconds: Time equipment was idle
             - idle_percentage: Percentage of available time that equipment was idle
             - time_period: Description of the time period (for context)
    """
    if available_time_seconds <= 0:
        return {
            "utilization_rate": 0.0,
            "idle_time_seconds": 0.0,
            "idle_percentage": 0.0,
            "time_period": time_period_description
        }
    
    # Ensure actual run time doesn't exceed available time
    actual_run_time_seconds = min(actual_run_time_seconds, available_time_seconds)
    
    # Calculate utilization rate
    utilization_rate = actual_run_time_seconds / available_time_seconds
    
    # Calculate idle time
    idle_time_seconds = available_time_seconds - actual_run_time_seconds
    idle_percentage = idle_time_seconds / available_time_seconds
    
    return {
        "utilization_rate": utilization_rate,
        "idle_time_seconds": idle_time_seconds,
        "idle_percentage": idle_percentage,
        "time_period": time_period_description
    }

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

def calculate_first_pass_yield(total_units: int, reworked_units: int) -> float:
    """
    Calculates First Pass Yield (FPY).
    FPY is the percentage of units that pass through the production process correctly 
    the first time without requiring any rework.
    
    Args:
        total_units: Total number of units processed
        reworked_units: Number of units that required rework/repair
    
    Returns:
        float: First Pass Yield as a decimal (0.0 to 1.0)
    """
    if total_units <= 0:
        return 0.0
    
    # Units that passed first time = total units - reworked units
    fpy = (total_units - reworked_units) / total_units
    return max(0.0, min(1.0, fpy))  # Ensure FPY is between 0 and 1

def analyze_production_losses(
    scheduled_time_seconds: float,
    losses_dict: Dict[str, Union[int, float]],
    ideal_cycle_time_per_unit: float = DEFAULT_IDEAL_CYCLE_TIME_PER_UNIT_SECONDS,
    total_units: int = 0,
    defective_units: int = 0
) -> dict:
    """
    Analyzes production losses in terms of the Six Big Losses or customized loss categories.
    
    Args:
        scheduled_time_seconds: Total scheduled production time in seconds
        losses_dict: Dictionary with loss category and time in seconds
                    Example: {"breakdown": 300, "setup": 600, "small_stops": 120, ...}
        ideal_cycle_time_per_unit: Ideal time to produce one unit
        total_units: Total units produced
        defective_units: Number of defective units
        
    Returns:
        dict: Analysis of losses including:
             - Total loss time by category (availability, performance, quality)
             - Percentage of total scheduled time lost to each category
             - Top loss contributors
    """
    if scheduled_time_seconds <= 0:
        return {"error": "Scheduled time must be greater than zero"}
    
    # Initialize loss category totals
    loss_totals = {
        "availability_losses": 0.0,
        "performance_losses": 0.0,
        "quality_losses": 0.0,
        "unclassified_losses": 0.0
    }
    
    # Calculate loss times by category
    for loss_type, loss_time in losses_dict.items():
        if loss_type.lower() in [l.lower() for l in LOSS_CATEGORIES["AVAILABILITY_LOSSES"]]:
            loss_totals["availability_losses"] += loss_time
        elif loss_type.lower() in [l.lower() for l in LOSS_CATEGORIES["PERFORMANCE_LOSSES"]]:
            loss_totals["performance_losses"] += loss_time
        elif loss_type.lower() in [l.lower() for l in LOSS_CATEGORIES["QUALITY_LOSSES"]]:
            loss_totals["quality_losses"] += loss_time
        else:
            loss_totals["unclassified_losses"] += loss_time
    
    # If defective units are provided, add quality loss time estimate
    if ideal_cycle_time_per_unit > 0 and defective_units > 0:
        # Estimate time lost to quality issues (time to produce defective units)
        quality_loss_time = defective_units * ideal_cycle_time_per_unit
        loss_totals["quality_losses"] += quality_loss_time
        losses_dict["defects"] = losses_dict.get("defects", 0) + quality_loss_time
    
    # Calculate total loss time
    total_loss_time = sum(loss_totals.values())
    
    # Calculate percentages of scheduled time
    loss_percentages = {
        category: (time / scheduled_time_seconds * 100) if scheduled_time_seconds > 0 else 0 
        for category, time in loss_totals.items()
    }
    
    # Find top loss contributors
    sorted_losses = sorted(losses_dict.items(), key=lambda x: x[1], reverse=True)
    top_losses = sorted_losses[:5]  # Top 5 loss contributors
    
    return {
        "loss_times": loss_totals,
        "loss_percentages": loss_percentages,
        "total_loss_time": total_loss_time,
        "total_loss_percentage": (total_loss_time / scheduled_time_seconds * 100) if scheduled_time_seconds > 0 else 0,
        "top_loss_contributors": top_losses,
        "detailed_losses": losses_dict
    }

def calculate_time_based_kpis(
    time_periods: Sequence[Tuple[datetime.datetime, datetime.datetime]],
    results_by_period: Sequence[List[Dict[str, Any]]],
    errors_by_period: Sequence[List[Dict[str, Any]]],
    scheduled_times_seconds: Sequence[Union[int, float]],
    ideal_cycle_time_per_unit: float = DEFAULT_IDEAL_CYCLE_TIME_PER_UNIT_SECONDS
) -> Dict[str, List[Any]]:
    """
    Calculates KPIs across multiple time periods for trend analysis.
    
    Args:
        time_periods: List of (start_time, end_time) tuples defining each period
        results_by_period: List of production results for each period
        errors_by_period: List of errors for each period
        scheduled_times_seconds: List of scheduled times (seconds) for each period
        ideal_cycle_time_per_unit: Ideal cycle time per unit
        
    Returns:
        dict: KPIs by time period with the following metrics as lists:
             - period_labels: Formatted time period strings
             - oee: Overall Equipment Effectiveness for each period
             - availability_rate: Availability rate for each period
             - performance_rate: Performance rate for each period
             - quality_rate: Quality rate for each period
             - mtbf: Mean Time Between Failures for each period (seconds)
             - mttr: Mean Time To Repair for each period (seconds)
             - throughput: Units per hour for each period
    """
    if len(time_periods) != len(results_by_period) or len(time_periods) != len(errors_by_period) or len(time_periods) != len(scheduled_times_seconds):
        raise ValueError("All input lists must have the same length (one per time period)")
    
    # Initialize result containers
    period_labels = []
    availability_rates = []
    performance_rates = []
    quality_rates = []
    oee_values = []
    mtbf_values = []
    mttr_values = []
    throughput_values = []
    first_pass_yield_values = []  # Assuming we have rework data
    
    # Calculate KPIs for each period
    for i, ((start_time, end_time), results, errors, scheduled_time) in enumerate(
        zip(time_periods, results_by_period, errors_by_period, scheduled_times_seconds)
    ):
        # Generate period label (e.g., "2023-01-01 08:00 - 16:00")
        period_label = f"{start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%H:%M')}"
        period_labels.append(period_label)
        
        # Calculate quality metrics
        quality_stats = calculate_quality_and_defects(results)
        quality_rates.append(quality_stats["quality_rate"])
        
        # Calculate downtime and availability
        actual_run_time = end_time.timestamp() - start_time.timestamp()  # Convert to seconds
        mtbf_stats = calculate_mtbf_mttr_downtime(errors, actual_run_time)
        mtbf_values.append(mtbf_stats["mtbf_seconds"])
        mttr_values.append(mtbf_stats["mttr_seconds"])
        
        availability_stats = calculate_availability(scheduled_time, mtbf_stats["total_simulated_downtime_seconds"])
        availability_rates.append(availability_stats["availability_rate"])
        
        # Calculate performance
        performance_rate = calculate_performance(
            quality_stats["good_units"],
            availability_stats["actual_run_time_seconds"],
            ideal_cycle_time_per_unit
        )
        performance_rates.append(performance_rate)
        
        # Calculate OEE
        oee = calculate_oee(
            availability_stats["availability_rate"],
            performance_rate,
            quality_stats["quality_rate"]
        )
        oee_values.append(oee)
        
        # Calculate throughput (units per hour)
        throughput = calculate_throughput(quality_stats["good_units"], scheduled_time) * 3600  # Convert to units/hour
        throughput_values.append(throughput)
        
        # Assume we have rework data (placeholder - in a real system, we would get this from actual data)
        reworked_units = len([r for r in results if r.get('reworked', False)])
        fpy = calculate_first_pass_yield(quality_stats["total_units"], reworked_units)
        first_pass_yield_values.append(fpy)
    
    # Return all KPIs by time period
    return {
        "period_labels": period_labels,
        "oee": oee_values,
        "availability_rate": availability_rates,
        "performance_rate": performance_rates,
        "quality_rate": quality_rates,
        "mtbf_seconds": mtbf_values,
        "mttr_seconds": mttr_values,
        "throughput_per_hour": throughput_values,
        "first_pass_yield": first_pass_yield_values
    }

def calculate_ore(
    availability_rate: float,
    performance_rate: float,
    quality_rate: float,
    material_efficiency: float,
    labor_utilization: float
) -> Dict[str, float]:
    """
    Calculates Overall Resource Effectiveness (ORE), which extends OEE by considering
    additional resources like labor and materials.
    
    Args:
        availability_rate: Equipment availability (0.0 to 1.0)
        performance_rate: Equipment performance (0.0 to 1.0)
        quality_rate: Quality rate (0.0 to 1.0)
        material_efficiency: Efficiency of material usage (0.0 to 1.0)
        labor_utilization: Efficiency of labor utilization (0.0 to 1.0)
        
    Returns:
        dict: ORE metrics including overall ORE and component factors
    """
    # Validate inputs
    for rate, name in [
        (availability_rate, "availability_rate"),
        (performance_rate, "performance_rate"),
        (quality_rate, "quality_rate"),
        (material_efficiency, "material_efficiency"),
        (labor_utilization, "labor_utilization")
    ]:
        if rate < 0.0 or rate > 1.0:
            raise ValueError(f"{name} must be between 0.0 and 1.0")
    
    # Calculate base OEE
    oee = availability_rate * performance_rate * quality_rate
    
    # Calculate ORE as OEE * material efficiency * labor utilization
    ore = oee * material_efficiency * labor_utilization
    
    return {
        "overall_resource_effectiveness": ore,
        "oee": oee,
        "availability_rate": availability_rate,
        "performance_rate": performance_rate,
        "quality_rate": quality_rate,
        "material_efficiency": material_efficiency,
        "labor_utilization": labor_utilization
    }

def analyze_six_big_losses(
    losses_dict: Mapping[str, Union[int, float]],
    scheduled_time_seconds: float,
    ideal_cycle_time_per_unit: float,
    total_units: int,
    defective_units_breakdown: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Analyzes the Six Big Losses from TPM (Total Productive Maintenance):
    1. Breakdowns
    2. Setup and Adjustments
    3. Small Stops
    4. Reduced Speed
    5. Startup Rejects
    6. Production Rejects
    
    Args:
        losses_dict: Dictionary with loss categories and times (seconds)
        scheduled_time_seconds: Total scheduled production time
        ideal_cycle_time_per_unit: Ideal cycle time per unit
        total_units: Total units produced
        defective_units_breakdown: Optional breakdown of defective units by type
                                  (e.g., {'startup_rejects': 5, 'production_rejects': 10})
        
    Returns:
        dict: Analysis of the six big losses with time and percentage impact
    """
    if scheduled_time_seconds <= 0:
        return {"error": "Scheduled time must be greater than zero"}
    
    # Initialize result structure
    six_losses = {
        "breakdowns": 0.0,
        "setup_and_adjustments": 0.0,
        "small_stops": 0.0,
        "reduced_speed": 0.0,
        "startup_rejects": 0.0,
        "production_rejects": 0.0
    }
    
    # Map from provided loss categories to the six big losses
    loss_mapping = {
        # Downtime Losses
        "breakdown": "breakdowns",
        "equipment_failure": "breakdowns",
        "unplanned_maintenance": "breakdowns",
        "setup": "setup_and_adjustments",
        "changeover": "setup_and_adjustments",
        "adjustment": "setup_and_adjustments",
        # Speed Losses
        "small_stops": "small_stops",
        "minor_stoppage": "small_stops",
        "idling": "small_stops",
        "jams": "small_stops",
        "reduced_speed": "reduced_speed",
        "slow_cycle": "reduced_speed",
        # Quality Losses are handled separately with defective_units_breakdown
    }
    
    # Process losses from the provided dictionary
    for loss_type, loss_time in losses_dict.items():
        if loss_type.lower() in loss_mapping:
            mapped_category = loss_mapping[loss_type.lower()]
            six_losses[mapped_category] += loss_time
    
    # Handle quality losses if defective units breakdown is provided
    if defective_units_breakdown:
        if ideal_cycle_time_per_unit > 0:
            # Convert defective units to time loss
            for reject_type, count in defective_units_breakdown.items():
                if reject_type.lower() == "startup_rejects":
                    six_losses["startup_rejects"] += count * ideal_cycle_time_per_unit
                elif reject_type.lower() in ["production_rejects", "quality_rejects"]:
                    six_losses["production_rejects"] += count * ideal_cycle_time_per_unit
    
    # Calculate total loss time
    total_loss_time = sum(six_losses.values())
    
    # Calculate loss percentages
    loss_percentages = {
        loss: (time / scheduled_time_seconds * 100) if scheduled_time_seconds > 0 else 0
        for loss, time in six_losses.items()
    }
    
    # Sort losses from most to least impactful
    sorted_losses = sorted(six_losses.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "six_big_losses": six_losses,
        "loss_percentages": loss_percentages,
        "total_loss_time": total_loss_time,
        "total_loss_percentage": (total_loss_time / scheduled_time_seconds * 100),
        "sorted_losses": sorted_losses
    }

def store_kpi_results_to_database(
    machine_id: str,
    availability_rate: float,
    performance_rate: float,
    quality_rate: float,
    oee: float,
    cycle_time_seconds: Optional[float] = None,
    defect_rate: Optional[float] = None,
    additional_metrics: Optional[Dict[str, Any]] = None
) -> int:
    """
    Stores calculated KPI metrics in the simulated database.
    
    Args:
        machine_id: Identifier for the machine or production line
        availability_rate: Calculated availability rate (0.0 to 1.0)
        performance_rate: Calculated performance rate (0.0 to 1.0)
        quality_rate: Calculated quality rate (0.0 to 1.0)
        oee: Calculated Overall Equipment Effectiveness (0.0 to 1.0)
        cycle_time_seconds: Optional average cycle time
        defect_rate: Optional defect rate
        additional_metrics: Optional dictionary with additional metrics to store
                           e.g., {'mtbf_seconds': 3600, 'mttr_seconds': 120}
        
    Returns:
        int: The ID of the newly created KPI record in the database
    """
    # Store basic KPI metrics in the database
    kpi_id = dbm.create_kpi_record(
        machine_id=machine_id,
        oee=oee,
        availability=availability_rate,
        performance=performance_rate,
        quality=quality_rate,
        cycle_time=cycle_time_seconds if cycle_time_seconds is not None else 0.0,
        defect_rate=defect_rate if defect_rate is not None else 0.0
    )
    
    # If there are additional metrics, we would need to extend the database schema
    # This is a placeholder for future extension - for now, we'll just return the ID
    if additional_metrics:
        # In a real implementation, we might update the KPI record with additional fields
        # or store in a related table
        pass
    
    return kpi_id

def get_historical_kpi_data(
    machine_id: str,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves historical KPI data for a machine from the database within a specified time range.
    
    Args:
        machine_id: Identifier for the machine or production line
        start_date: Optional start date for filtering data
        end_date: Optional end date for filtering data
        
    Returns:
        List[Dict]: List of KPI records matching the criteria
    """
    # Get all KPI records for the machine
    kpi_records = dbm.get_kpi_records_by_machine(machine_id)
    
    # Filter by date range if specified
    if start_date or end_date:
        filtered_records = []
        for record in kpi_records:
            timestamp = record.get("timestamp")
            if timestamp:
                if start_date and timestamp < start_date:
                    continue
                if end_date and timestamp > end_date:
                    continue
            filtered_records.append(record)
        return filtered_records
    
    return kpi_records

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
      # Additional sample data for new functions
    sample_losses: Dict[str, Union[int, float]] = {
        "breakdown": 600.0,       # 10 minutes
        "setup": 300.0,           # 5 minutes
        "small_stops": 120.0,     # 2 minutes
        "reduced_speed": 180.0,   # 3 minutes
    }

    # Original calculations
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
    test_scheduled_time = 60 * 60 # 1 hour
    mtbf_stats = calculate_mtbf_mttr_downtime(sample_errors, test_scheduled_time) 
    print(mtbf_stats)
    total_downtime = mtbf_stats["total_simulated_downtime_seconds"]

    print(f"\n--- Availability Stats ---")
    availability_stats = calculate_availability(test_scheduled_time, total_downtime)
    print(availability_stats)
    availability_rate = availability_stats["availability_rate"]
    actual_run_time = availability_stats["actual_run_time_seconds"]

    print(f"\n--- Performance Stats ---")
    performance_rate = calculate_performance(good_units, actual_run_time, DEFAULT_IDEAL_CYCLE_TIME_PER_UNIT_SECONDS)
    print(f"Performance Rate: {performance_rate:.2%}")
    print(f"\n--- OEE ---")
    oee = calculate_oee(availability_rate, performance_rate, quality_rate)
    print(f"OEE: {oee:.2%}")

    print(f"\n--- Throughput (units per scheduled hour) ---")
    throughput_per_hour = calculate_throughput(good_units, test_scheduled_time) * 3600
    print(f"Throughput: {throughput_per_hour:.2f} units/hour (based on {test_scheduled_time/3600:.2f} scheduled hours)")
    
    # New KPI calculations
    print(f"\n--- TEEP (Total Effective Equipment Performance) ---")
    loading_factor = 8 / 24  # 8-hour shift out of 24 hours
    teep = calculate_teep(oee, loading_factor)
    print(f"TEEP: {teep:.2%} (with loading factor of {loading_factor:.2%})")
    
    print(f"\n--- First Pass Yield ---")
    reworked_units = 1  # Assume 1 unit required rework
    fpy = calculate_first_pass_yield(quality_stats["total_units"], reworked_units)
    print(f"First Pass Yield: {fpy:.2%} (with {reworked_units} reworked unit(s) out of {quality_stats['total_units']} total)")
    
    print(f"\n--- Equipment Utilization ---")
    day_seconds = 24 * 60 * 60  # 24-hour day
    utilization = calculate_equipment_utilization(actual_run_time, day_seconds, "day")
    print(f"Equipment Utilization: {utilization['utilization_rate']:.2%}")
    idle_time_hours = float(utilization['idle_time_seconds']) / 3600
    print(f"Idle Time: {idle_time_hours:.2f} hours ({utilization['idle_percentage']:.2%})")
    
    print(f"\n--- Production Loss Analysis ---")
    loss_analysis = analyze_production_losses(
        test_scheduled_time, 
        sample_losses,
        DEFAULT_IDEAL_CYCLE_TIME_PER_UNIT_SECONDS,
        quality_stats["total_units"],
        quality_stats["defective_units"]
    )
    print(f"Total Loss Time: {loss_analysis['total_loss_time']/60:.2f} minutes ({loss_analysis['total_loss_percentage']:.2%} of scheduled time)")
    print(f"Loss Breakdown:")
    for category, percentage in loss_analysis['loss_percentages'].items():
        if percentage > 0:
            print(f"  - {category}: {percentage:.2f}%")
    
    print(f"\n--- Six Big Losses Analysis ---")
    six_losses_analysis = analyze_six_big_losses(
        sample_losses,
        test_scheduled_time,
        DEFAULT_IDEAL_CYCLE_TIME_PER_UNIT_SECONDS,
        quality_stats["total_units"],
        {"startup_rejects": 0, "production_rejects": 1}
    )
    print(f"Six Big Losses Analysis:")
    for loss, time in six_losses_analysis['sorted_losses']:
        if time > 0:
            print(f"  - {loss}: {time/60:.2f} minutes ({six_losses_analysis['loss_percentages'][loss]:.2f}%)")
    
    print(f"\n--- Overall Resource Effectiveness (ORE) ---")
    material_efficiency = 0.92  # 92% material efficiency
    labor_utilization = 0.85    # 85% labor utilization
    ore = calculate_ore(
        availability_rate,
        performance_rate,
        quality_rate,
        material_efficiency,
        labor_utilization
    )
    print(f"Overall Resource Effectiveness: {ore['overall_resource_effectiveness']:.2%}")
    print(f"OEE Component: {ore['oee']:.2%}")
    print(f"Material Efficiency: {ore['material_efficiency']:.2%}")
    print(f"Labor Utilization: {ore['labor_utilization']:.2%}")
    
    # Database integration
    print(f"\n--- Database Integration ---")
    machine_id = "GantryRobot01"
    kpi_id = store_kpi_results_to_database(
        machine_id=machine_id,
        availability_rate=availability_rate,
        performance_rate=performance_rate,
        quality_rate=quality_rate,
        oee=oee,
        cycle_time_seconds=avg_cycle_time,
        defect_rate=quality_stats["defect_rate"]
    )
    print(f"Stored KPI results to database with ID: {kpi_id}")
    
    # Time-based KPI analysis
    print(f"\n--- Time-Based KPI Calculations (Trend Analysis) ---")
    time_periods = [
        (datetime.datetime(2023, 1, 1, 8, 0), datetime.datetime(2023, 1, 1, 16, 0)),
        (datetime.datetime(2023, 1, 2, 8, 0), datetime.datetime(2023, 1, 2, 16, 0))
    ]
    results_by_period = [
        sample_results,  # Use the same sample data for both periods for simplicity
        sample_results   # In a real scenario, these would be different
    ]
    errors_by_period = [
        sample_errors,   # Use the same sample data for both periods for simplicity
        sample_errors    # In a real scenario, these would be different
    ]
    scheduled_times_seconds = [
        8 * 60 * 60,  # 8 hours in seconds
        8 * 60 * 60   # 8 hours in seconds
    ]

    try:
        trend_kpis = calculate_time_based_kpis(
            time_periods, 
            results_by_period, 
            errors_by_period, 
            scheduled_times_seconds
        )
        print(f"Successfully calculated KPI trends for {len(time_periods)} periods")
    except Exception as e:
        print(f"Error calculating time-based KPIs: {e}")
