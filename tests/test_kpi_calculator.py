import unittest
import sys
import os
from datetime import datetime as dt_class # Alias for clarity

# Adjust sys.path to include the parent directory (project root)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import kpi_calculator as kpic

class TestKpiCalculator(unittest.TestCase):

    def setUp(self):
        """Define sample data for reuse in tests."""
        self.sample_results_basic = [
            {"status": "success", "cycle_time_seconds": 10.0},
            {"status": "success", "cycle_time_seconds": 11.0},
            {"status": "failed", "cycle_time_seconds": 12.0}, # Defective, but cycle time recorded
            {"status": "success", "cycle_time_seconds": 9.0},
        ]
        self.sample_results_missing_data = [
            {"status": "success"}, # Missing cycle_time_seconds
            {"status": "success", "cycle_time_seconds": None},
            {"status": "failed"}
        ]
        self.sample_errors = [
            {"severity": "low"},
            {"severity": "medium"},
            {"severity": "medium"},
            {"severity": "high"},
            {"severity": "critical"},
            {"severity": "unknown_severity_type"} # Test fallback
        ]

    # --- Test calculate_cycle_times_and_stats ---
    def test_calculate_cycle_times_and_stats_valid(self):
        stats = kpic.calculate_cycle_times_and_stats(self.sample_results_basic)
        self.assertAlmostEqual(stats["average_cycle_time"], (10.0 + 11.0 + 12.0 + 9.0) / 4)
        self.assertAlmostEqual(stats["min_cycle_time"], 9.0)
        self.assertAlmostEqual(stats["max_cycle_time"], 12.0)
        self.assertAlmostEqual(stats["total_production_time"], 10.0 + 11.0 + 12.0 + 9.0)

    def test_calculate_cycle_times_and_stats_missing_or_none(self):
        stats = kpic.calculate_cycle_times_and_stats(self.sample_results_missing_data)
        self.assertEqual(stats["average_cycle_time"], 0.0)
        self.assertEqual(stats["min_cycle_time"], 0.0)
        self.assertEqual(stats["max_cycle_time"], 0.0)
        self.assertEqual(stats["total_production_time"], 0.0)
        
        stats_with_one_valid = kpic.calculate_cycle_times_and_stats([{"cycle_time_seconds": 10.0}])
        self.assertEqual(stats_with_one_valid["average_cycle_time"], 10.0)


    def test_calculate_cycle_times_and_stats_empty(self):
        stats = kpic.calculate_cycle_times_and_stats([])
        self.assertEqual(stats["average_cycle_time"], 0.0)
        self.assertEqual(stats["min_cycle_time"], 0.0)
        self.assertEqual(stats["max_cycle_time"], 0.0)
        self.assertEqual(stats["total_production_time"], 0.0)

    # --- Test calculate_quality_and_defects ---
    def test_calculate_quality_all_success(self):
        results = [{"status": "success"}] * 10
        stats = kpic.calculate_quality_and_defects(results)
        self.assertEqual(stats["total_units"], 10)
        self.assertEqual(stats["good_units"], 10)
        self.assertEqual(stats["defective_units"], 0)
        self.assertAlmostEqual(stats["quality_rate"], 1.0)
        self.assertAlmostEqual(stats["defect_rate"], 0.0)

    def test_calculate_quality_mixed(self):
        results = [
            {"status": "success"}, {"status": "success"},
            {"status": "failed"}, {"status": "partial_failure"} # Non-success
        ]
        stats = kpic.calculate_quality_and_defects(results)
        self.assertEqual(stats["total_units"], 4)
        self.assertEqual(stats["good_units"], 2)
        self.assertEqual(stats["defective_units"], 2)
        self.assertAlmostEqual(stats["quality_rate"], 0.5)
        self.assertAlmostEqual(stats["defect_rate"], 0.5)

    def test_calculate_quality_empty(self):
        stats = kpic.calculate_quality_and_defects([])
        self.assertEqual(stats["total_units"], 0)
        self.assertEqual(stats["good_units"], 0)
        self.assertEqual(stats["defective_units"], 0)
        self.assertAlmostEqual(stats["quality_rate"], 0.0)
        self.assertAlmostEqual(stats["defect_rate"], 0.0)

    # --- Test calculate_mtbf_mttr_downtime ---
    def test_calculate_mtbf_mttr_downtime_valid(self):
        run_time = 3600.0  # 1 hour
        stats = kpic.calculate_mtbf_mttr_downtime(self.sample_errors, run_time)
        self.assertEqual(stats["num_failures"], 6)
        
        expected_downtime = (
            kpic.DEFAULT_SEVERITY_REPAIR_TIMES_SECONDS["low"] +
            kpic.DEFAULT_SEVERITY_REPAIR_TIMES_SECONDS["medium"] * 2 +
            kpic.DEFAULT_SEVERITY_REPAIR_TIMES_SECONDS["high"] +
            kpic.DEFAULT_SEVERITY_REPAIR_TIMES_SECONDS["critical"] +
            kpic.DEFAULT_SEVERITY_REPAIR_TIMES_SECONDS["unknown"] # Fallback for "OTHER_SEV"
        )
        self.assertAlmostEqual(stats["total_simulated_downtime_seconds"], expected_downtime)
        self.assertAlmostEqual(stats["mtbf_seconds"], run_time / 6)
        self.assertAlmostEqual(stats["mttr_seconds"], expected_downtime / 6)

    def test_calculate_mtbf_mttr_downtime_custom_map(self):
        run_time = 3600.0
        custom_map = {"low": 30, "medium": 120, "high": 600, "critical": 1200, "unknown": 120}
        stats = kpic.calculate_mtbf_mttr_downtime(self.sample_errors, run_time, custom_map)
        expected_downtime = custom_map["low"] + custom_map["medium"] * 2 + custom_map["high"] + custom_map["critical"] + custom_map["unknown"]
        self.assertAlmostEqual(stats["total_simulated_downtime_seconds"], expected_downtime)

    def test_calculate_mtbf_mttr_downtime_no_errors(self):
        run_time = 3600.0
        stats = kpic.calculate_mtbf_mttr_downtime([], run_time)
        self.assertEqual(stats["num_failures"], 0)
        self.assertAlmostEqual(stats["total_simulated_downtime_seconds"], 0.0)
        self.assertAlmostEqual(stats["mtbf_seconds"], run_time) # MTBF is the total run time
        self.assertAlmostEqual(stats["mttr_seconds"], 0.0)

    def test_calculate_mtbf_mttr_downtime_zero_run_time(self):
        stats = kpic.calculate_mtbf_mttr_downtime(self.sample_errors, 0)
        self.assertEqual(stats["num_failures"], 6)
        self.assertAlmostEqual(stats["mtbf_seconds"], 0.0)

    # --- Test calculate_availability ---
    def test_calculate_availability_valid(self):
        stats = kpic.calculate_availability(3600, 600) # 1 hour scheduled, 10 mins downtime
        self.assertAlmostEqual(stats["actual_run_time_seconds"], 3000.0)
        self.assertAlmostEqual(stats["availability_rate"], 3000.0 / 3600.0)

    def test_calculate_availability_zero_scheduled_time(self):
        stats = kpic.calculate_availability(0, 600)
        self.assertAlmostEqual(stats["actual_run_time_seconds"], 0.0)
        self.assertAlmostEqual(stats["availability_rate"], 0.0)

    def test_calculate_availability_downtime_exceeds_scheduled(self):
        stats = kpic.calculate_availability(3600, 4000)
        self.assertAlmostEqual(stats["actual_run_time_seconds"], 0.0) # Should not be negative
        self.assertAlmostEqual(stats["availability_rate"], 0.0)

    # --- Test calculate_performance ---
    def test_calculate_performance_valid(self):
        # (100 units * 10s/unit) / 1200s run time = 1000 / 1200 = 0.8333
        rate = kpic.calculate_performance(100, 1200, 10.0)
        self.assertAlmostEqual(rate, (100 * 10.0) / 1200)

    def test_calculate_performance_zero_run_time(self):
        self.assertAlmostEqual(kpic.calculate_performance(100, 0, 10.0), 0.0)

    def test_calculate_performance_zero_ideal_cycle_time(self):
        self.assertAlmostEqual(kpic.calculate_performance(100, 1200, 0), 0.0)
        
    def test_calculate_performance_zero_good_units(self):
        self.assertAlmostEqual(kpic.calculate_performance(0, 1200, 10.0), 0.0)

    def test_calculate_performance_capped_at_one(self):
        # Actual production faster than ideal (e.g., ideal time too high)
        rate = kpic.calculate_performance(100, 800, 10.0) # (100*10)/800 = 1.25
        self.assertAlmostEqual(rate, 1.0)

    # --- Test calculate_oee ---
    def test_calculate_oee(self):
        self.assertAlmostEqual(kpic.calculate_oee(0.9, 0.95, 0.99), 0.9 * 0.95 * 0.99)
        self.assertAlmostEqual(kpic.calculate_oee(0.0, 0.95, 0.99), 0.0)    # --- Test calculate_throughput ---
    def test_calculate_throughput_valid(self):
        self.assertAlmostEqual(kpic.calculate_throughput(100, 3600), 100/3600.0)
        
    def test_calculate_throughput_zero_time(self):
        self.assertAlmostEqual(kpic.calculate_throughput(100, 0), 0.0)

    # --- Test calculate_teep ---
    def test_calculate_teep_valid(self):
        self.assertAlmostEqual(kpic.calculate_teep(0.8, 0.5), 0.4)  # 80% OEE, 50% loading = 40% TEEP
        
    def test_calculate_teep_zero_loading(self):
        self.assertAlmostEqual(kpic.calculate_teep(0.8, 0), 0.0)
        
    def test_calculate_teep_invalid_loading(self):
        self.assertAlmostEqual(kpic.calculate_teep(0.8, 1.2), 0.0)  # Loading > 1.0 is invalid
        
    # --- Test calculate_first_pass_yield ---
    def test_calculate_first_pass_yield_valid(self):
        self.assertAlmostEqual(kpic.calculate_first_pass_yield(100, 20), 0.8)  # 80 out of 100 passed first time
        
    def test_calculate_first_pass_yield_perfect(self):
        self.assertAlmostEqual(kpic.calculate_first_pass_yield(100, 0), 1.0)  # All passed first time
        
    def test_calculate_first_pass_yield_all_rework(self):
        self.assertAlmostEqual(kpic.calculate_first_pass_yield(100, 100), 0.0)  # None passed first time
        
    def test_calculate_first_pass_yield_zero_units(self):
        self.assertAlmostEqual(kpic.calculate_first_pass_yield(0, 0), 0.0)
        
    def test_calculate_first_pass_yield_more_rework_than_total(self):
        # This is an edge case - more rework than total shouldn't happen in reality
        self.assertAlmostEqual(kpic.calculate_first_pass_yield(10, 15), 0.0)
        
    # --- Test calculate_equipment_utilization ---
    def test_calculate_equipment_utilization_valid(self):
        result = kpic.calculate_equipment_utilization(4 * 3600, 8 * 3600, "shift")  # 4 hours actual run time in 8 hour shift
        self.assertEqual(float(result["utilization_rate"]), 0.5)
        self.assertEqual(float(result["idle_time_seconds"]), 4 * 3600)
        self.assertEqual(float(result["idle_percentage"]), 0.5)
        self.assertEqual(result["time_period"], "shift")
        
    def test_calculate_equipment_utilization_full(self):
        result = kpic.calculate_equipment_utilization(8 * 3600, 8 * 3600)
        self.assertEqual(float(result["utilization_rate"]), 1.0)
        self.assertEqual(float(result["idle_percentage"]), 0.0)
        
    def test_calculate_equipment_utilization_zero_available(self):
        result = kpic.calculate_equipment_utilization(3600, 0)
        self.assertEqual(float(result["utilization_rate"]), 0.0)
        
    def test_calculate_equipment_utilization_exceed_available(self):
        # Run time exceeding available time should be capped at available time
        result = kpic.calculate_equipment_utilization(10 * 3600, 8 * 3600)
        self.assertEqual(float(result["utilization_rate"]), 1.0)
        
    # --- Test calculate_ore ---
    def test_calculate_ore_valid(self):
        result = kpic.calculate_ore(0.9, 0.85, 0.95, 0.8, 0.75)
        expected_oee = 0.9 * 0.85 * 0.95
        expected_ore = expected_oee * 0.8 * 0.75
        self.assertAlmostEqual(result["oee"], expected_oee)
        self.assertAlmostEqual(result["overall_resource_effectiveness"], expected_ore)
        
    def test_calculate_ore_invalid_input(self):
        with self.assertRaises(ValueError):
            kpic.calculate_ore(0.9, 0.85, 0.95, 1.2, 0.75)  # Material efficiency > 1.0
            
    # --- Test analyze_production_losses ---
    def test_analyze_production_losses_valid(self):
        losses = {
            "breakdown": 600.0,
            "setup": 300.0,
            "small_stops": 120.0,
            "reduced_speed": 180.0
        }
        result = kpic.analyze_production_losses(3600, losses, 10.0, 100, 5)
        self.assertAlmostEqual(result["total_loss_time"], 1200 + 50)  # 1200 from losses dict + 50 from defective units
        
    def test_analyze_production_losses_zero_scheduled(self):
        losses = {"breakdown": 600.0}
        result = kpic.analyze_production_losses(0, losses)
        self.assertEqual(result["error"], "Scheduled time must be greater than zero")
        
    # --- Test analyze_six_big_losses ---
    def test_analyze_six_big_losses_valid(self):
        losses = {
            "breakdown": 600.0,
            "setup": 300.0,
            "small_stops": 120.0,
            "reduced_speed": 180.0
        }
        defect_breakdown = {"startup_rejects": 2, "production_rejects": 3}
        result = kpic.analyze_six_big_losses(losses, 3600, 10.0, 100, defect_breakdown)
        
        # Check that breakdowns were mapped correctly
        self.assertAlmostEqual(result["six_big_losses"]["breakdowns"], 600)
        
        # Check that setup was mapped correctly
        self.assertAlmostEqual(result["six_big_losses"]["setup_and_adjustments"], 300)
        
        # Check defective units conversions
        self.assertAlmostEqual(result["six_big_losses"]["startup_rejects"], 2 * 10.0)
        self.assertAlmostEqual(result["six_big_losses"]["production_rejects"], 3 * 10.0)
        
    def test_analyze_six_big_losses_zero_scheduled(self):
        result = kpic.analyze_six_big_losses({}, 0, 10.0, 0)
        self.assertEqual(result["error"], "Scheduled time must be greater than zero")
        
    # --- Test calculate_time_based_kpis ---
    def test_calculate_time_based_kpis_valid(self):
        # Create sample data for two time periods
        time_periods = [
            (dt_class(2023, 1, 1, 8, 0), dt_class(2023, 1, 1, 16, 0)),
            (dt_class(2023, 1, 2, 8, 0), dt_class(2023, 1, 2, 16, 0))
        ]
        
        results_period1 = [{"status": "success", "cycle_time_seconds": 10.0, "reworked": False}] * 8
        results_period2 = [{"status": "success", "cycle_time_seconds": 9.0, "reworked": False}] * 10
        
        errors_period1 = [{"severity": "medium"}] * 2
        errors_period2 = [{"severity": "low"}] * 1
        
        results_by_period = [results_period1, results_period2]
        errors_by_period = [errors_period1, errors_period2]
        scheduled_times = [8 * 3600, 8 * 3600]
        
        result = kpic.calculate_time_based_kpis(
            time_periods, 
            results_by_period, 
            errors_by_period, 
            scheduled_times
        )
        
        # Check that we got back the expected number of periods
        self.assertEqual(len(result["period_labels"]), 2)
        self.assertEqual(len(result["oee"]), 2)
        
    def test_calculate_time_based_kpis_mismatched_lengths(self):
        with self.assertRaises(ValueError):
            kpic.calculate_time_based_kpis(
                [(dt_class(2023, 1, 1, 8, 0), dt_class(2023, 1, 1, 16, 0))],
                [[]],
                [[]],
                [8 * 3600, 8 * 3600]  # Mismatched length
            )
            
    # --- Test database integration functions ---
    def test_store_kpi_results_to_database(self):
        # This test depends on the sim_database_manager module
        # We'll do a basic test that the function doesn't raise exceptions
        try:
            kpi_id = kpic.store_kpi_results_to_database(
                machine_id="test_machine",
                availability_rate=0.9,
                performance_rate=0.85,
                quality_rate=0.95,
                oee=0.9 * 0.85 * 0.95,
                cycle_time_seconds=10.5,
                defect_rate=0.05
            )
            self.assertIsNotNone(kpi_id)
        except Exception as e:
            self.fail(f"store_kpi_results_to_database raised exception: {e}")
            
    def test_get_historical_kpi_data(self):
        # This test depends on the sim_database_manager module
        # We'll do a basic test that the function doesn't raise exceptions
        try:
            # First store some data
            kpic.store_kpi_results_to_database(
                machine_id="test_machine_history",
                availability_rate=0.9,
                performance_rate=0.85,
                quality_rate=0.95,
                oee=0.9 * 0.85 * 0.95
            )
            
            # Now retrieve it
            data = kpic.get_historical_kpi_data("test_machine_history")
            self.assertIsInstance(data, list)
            
            # At least one record should be returned
            self.assertGreaterEqual(len(data), 1)
        except Exception as e:
            self.fail(f"get_historical_kpi_data raised exception: {e}")

if __name__ == '__main__':
    unittest.main()
