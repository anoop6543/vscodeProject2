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
        self.assertAlmostEqual(kpic.calculate_oee(0.0, 0.95, 0.99), 0.0)

    # --- Test calculate_throughput ---
    def test_calculate_throughput_valid(self):
        self.assertAlmostEqual(kpic.calculate_throughput(100, 3600), 100/3600.0)

    def test_calculate_throughput_zero_time(self):
        self.assertAlmostEqual(kpic.calculate_throughput(100, 0), 0.0)

if __name__ == '__main__':
    unittest.main()
