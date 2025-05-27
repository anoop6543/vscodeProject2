import unittest
import sys
import os
from datetime import datetime as dt # Alias for clarity in tests
from unittest.mock import patch

# Adjust sys.path to include the parent directory (project root)
# This allows importing sim_database_manager which is in the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sim_database_manager as dbm

class TestSimDatabaseManager(unittest.TestCase):

    def setUp(self):
        """Reset the in-memory database state before each test."""
        dbm.db_recipes.clear()
        dbm.db_results.clear()
        dbm.db_errors.clear()
        dbm.db_kpis.clear()
        dbm.next_recipe_id = 1
        dbm.next_result_id = 1
        dbm.next_error_id = 1
        dbm.next_kpi_id = 1

    # --- Recipe Tests ---
    def test_create_recipe(self):
        recipe_id = dbm.create_recipe("Test Recipe", ["Ing1", "Ing2"], ["Step1", "Step2"])
        self.assertEqual(recipe_id, 1)
        self.assertEqual(len(dbm.db_recipes), 1)
        recipe = dbm.db_recipes[0]
        self.assertEqual(recipe["name"], "Test Recipe")
        self.assertEqual(recipe["ingredients"], ["Ing1", "Ing2"])
        self.assertIsInstance(recipe["created_at"], dt)

    def test_get_recipe(self):
        recipe_id = dbm.create_recipe("Recipe 1", [], [])
        retrieved = dbm.get_recipe(recipe_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["recipe_id"], recipe_id)
        non_existent = dbm.get_recipe(999)
        self.assertIsNone(non_existent)

    def test_get_all_recipes(self):
        self.assertEqual(dbm.get_all_recipes(), [])
        dbm.create_recipe("Recipe A", [], [])
        dbm.create_recipe("Recipe B", [], [])
        recipes = dbm.get_all_recipes()
        self.assertEqual(len(recipes), 2)

    def test_update_recipe(self):
        recipe_id = dbm.create_recipe("Old Name", ["Old Ing"], ["Old Step"])
        updated = dbm.update_recipe(recipe_id, name="New Name", ingredients=["New Ing"], steps=["New Step"])
        self.assertTrue(updated)
        recipe = dbm.get_recipe(recipe_id)
        self.assertEqual(recipe["name"], "New Name")
        self.assertEqual(recipe["ingredients"], ["New Ing"])
        self.assertEqual(recipe["steps"], ["New Step"])
        
        # Partial update
        updated_partial = dbm.update_recipe(recipe_id, name="Partially New Name")
        self.assertTrue(updated_partial)
        recipe_partial = dbm.get_recipe(recipe_id)
        self.assertEqual(recipe_partial["name"], "Partially New Name")
        self.assertEqual(recipe_partial["ingredients"], ["New Ing"]) # Should remain from previous update

        self.assertFalse(dbm.update_recipe(999, name="Ghost"))

    def test_delete_recipe(self):
        recipe1_id = dbm.create_recipe("To Delete", [], [])
        dbm.create_recipe("To Keep", [], [])
        self.assertTrue(dbm.delete_recipe(recipe1_id))
        self.assertIsNone(dbm.get_recipe(recipe1_id))
        self.assertEqual(len(dbm.db_recipes), 1)
        self.assertFalse(dbm.delete_recipe(999))

    # --- Results Tests ---
    def test_create_result(self):
        recipe_id = dbm.create_recipe("For Results", [], [])
        result_id = dbm.create_result(recipe_id, 100, "success", "Op1", "Shift1")
        self.assertEqual(result_id, 1)
        self.assertEqual(len(dbm.db_results), 1)
        result = dbm.db_results[0]
        self.assertEqual(result["recipe_id"], recipe_id)
        self.assertEqual(result["output_quantity"], 100)
        self.assertIsInstance(result["timestamp"], dt)

    def test_get_result(self):
        recipe_id = dbm.create_recipe("For Results", [], [])
        result_id = dbm.create_result(recipe_id, 100, "success", "Op1", "Shift1")
        retrieved = dbm.get_result(result_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["result_id"], result_id)
        self.assertIsNone(dbm.get_result(999))

    def test_get_results_by_recipe(self):
        recipe1_id = dbm.create_recipe("Recipe 1", [], [])
        recipe2_id = dbm.create_recipe("Recipe 2", [], [])
        dbm.create_result(recipe1_id, 10, "success", "OpA", "S1")
        dbm.create_result(recipe1_id, 20, "failed", "OpA", "S1")
        dbm.create_result(recipe2_id, 30, "success", "OpB", "S2")
        
        results_r1 = dbm.get_results_by_recipe(recipe1_id)
        self.assertEqual(len(results_r1), 2)
        results_r2 = dbm.get_results_by_recipe(recipe2_id)
        self.assertEqual(len(results_r2), 1)
        self.assertEqual(dbm.get_results_by_recipe(999), [])

    def test_get_all_results(self):
        self.assertEqual(dbm.get_all_results(), [])
        recipe_id = dbm.create_recipe("For Results", [], [])
        dbm.create_result(recipe_id, 10, "success", "OpA", "S1")
        dbm.create_result(recipe_id, 20, "failed", "OpA", "S1")
        self.assertEqual(len(dbm.get_all_results()), 2)

    # --- Errors Tests ---
    def test_create_error(self):
        error_id = dbm.create_error("Machine1", "E101", "Test Error", "high")
        self.assertEqual(error_id, 1)
        self.assertEqual(len(dbm.db_errors), 1)
        error = dbm.db_errors[0]
        self.assertEqual(error["machine_id"], "Machine1")
        self.assertEqual(error["severity"], "high")
        self.assertIsInstance(error["timestamp"], dt)

    def test_get_error(self):
        error_id = dbm.create_error("Machine1", "E101", "Test Error", "high")
        retrieved = dbm.get_error(error_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["error_id"], error_id)
        self.assertIsNone(dbm.get_error(999))

    def test_get_errors_by_machine(self):
        dbm.create_error("MachineA", "E01", "DescA", "low")
        dbm.create_error("MachineB", "E02", "DescB", "medium")
        dbm.create_error("MachineA", "E03", "DescC", "high")
        machine_a_errors = dbm.get_errors_by_machine("MachineA")
        self.assertEqual(len(machine_a_errors), 2)
        self.assertEqual(dbm.get_errors_by_machine("MachineC"), [])

    def test_get_errors_by_severity(self):
        dbm.create_error("M1", "E01", "D1", "high")
        dbm.create_error("M2", "E02", "D2", "medium")
        dbm.create_error("M3", "E03", "D3", "high")
        high_errors = dbm.get_errors_by_severity("high")
        self.assertEqual(len(high_errors), 2)
        self.assertEqual(dbm.get_errors_by_severity("critical"), [])

    def test_get_all_errors(self):
        self.assertEqual(dbm.get_all_errors(), [])
        dbm.create_error("M1", "E01", "D1", "high")
        dbm.create_error("M2", "E02", "D2", "medium")
        self.assertEqual(len(dbm.get_all_errors()), 2)

    # --- KPIs Tests ---
    def test_create_kpi_record(self):
        kpi_id = dbm.create_kpi_record("MachineX", 0.8, 0.9, 0.88, 0.95, 10.0, 0.05)
        self.assertEqual(kpi_id, 1)
        self.assertEqual(len(dbm.db_kpis), 1)
        kpi = dbm.db_kpis[0]
        self.assertEqual(kpi["machine_id"], "MachineX")
        self.assertEqual(kpi["OEE"], 0.8)
        self.assertIsInstance(kpi["timestamp"], dt)

    def test_get_kpi_record(self):
        kpi_id = dbm.create_kpi_record("MachineX", 0.8, 0.9, 0.88, 0.95, 10.0, 0.05)
        retrieved = dbm.get_kpi_record(kpi_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["kpi_id"], kpi_id)
        self.assertIsNone(dbm.get_kpi_record(999))

    def test_get_kpi_records_by_machine(self):
        dbm.create_kpi_record("MachineAlpha", 0.7, 0.8, 0.9, 0.95, 12.0, 0.02)
        dbm.create_kpi_record("MachineBeta", 0.8, 0.85, 0.92, 0.96, 11.0, 0.01)
        dbm.create_kpi_record("MachineAlpha", 0.75, 0.82, 0.91, 0.97, 11.5, 0.015)
        alpha_kpis = dbm.get_kpi_records_by_machine("MachineAlpha")
        self.assertEqual(len(alpha_kpis), 2)
        self.assertEqual(dbm.get_kpi_records_by_machine("MachineGamma"), [])

    def test_get_all_kpi_records(self):
        self.assertEqual(dbm.get_all_kpi_records(), [])
        dbm.create_kpi_record("MAlpha", 0.7, 0.8, 0.9, 0.95, 12.0, 0.02)
        dbm.create_kpi_record("MBeta", 0.8, 0.85, 0.92, 0.96, 11.0, 0.01)
        self.assertEqual(len(dbm.get_all_kpi_records()), 2)

    # --- ID Incrementation Test ---
    def test_id_incrementation(self):
        r1 = dbm.create_recipe("R1", [], [])
        r2 = dbm.create_recipe("R2", [], [])
        self.assertNotEqual(r1, r2)
        self.assertEqual(dbm.next_recipe_id, 3)

        res1 = dbm.create_result(r1, 1, "s", "o", "s")
        res2 = dbm.create_result(r1, 1, "s", "o", "s")
        self.assertNotEqual(res1, res2)
        self.assertEqual(dbm.next_result_id, 3)

        err1 = dbm.create_error("M1", "E1", "D1", "S1")
        err2 = dbm.create_error("M1", "E1", "D1", "S1")
        self.assertNotEqual(err1, err2)
        self.assertEqual(dbm.next_error_id, 3)

        kpi1 = dbm.create_kpi_record("M1", .1,.1,.1,.1,.1,.1)
        kpi2 = dbm.create_kpi_record("M1", .1,.1,.1,.1,.1,.1)
        self.assertNotEqual(kpi1, kpi2)
        self.assertEqual(dbm.next_kpi_id, 3)
        
    # --- Timestamping Test ---
    @patch('sim_database_manager.datetime.datetime')
    def test_timestamps_are_set(self, mock_dt):
        mock_now = dt(2023, 1, 1, 12, 0, 0)
        mock_dt.now.return_value = mock_now

        recipe_id = dbm.create_recipe("Timed Recipe", [], [])
        recipe = dbm.get_recipe(recipe_id)
        self.assertEqual(recipe['created_at'], mock_now)

        result_id = dbm.create_result(recipe_id, 1, "s", "o", "s")
        result = dbm.get_result(result_id)
        self.assertEqual(result['timestamp'], mock_now)

        error_id = dbm.create_error("M_Time", "ETime", "DTime", "STime")
        error = dbm.get_error(error_id)
        self.assertEqual(error['timestamp'], mock_now)

        kpi_id = dbm.create_kpi_record("M_Time_KPI", .1,.1,.1,.1,.1,.1)
        kpi = dbm.get_kpi_record(kpi_id)
        self.assertEqual(kpi['timestamp'], mock_now)

if __name__ == '__main__':
    unittest.main()
