import datetime
from gantry_system.utils import aws_logger_sim as awslog # Added for AWS logging simulation

# --- In-Memory "Database" Tables ---
db_recipes = []
db_results = []
db_errors = []
db_kpis = []

# --- ID Counters for ensuring unique IDs ---
next_recipe_id = 1
next_result_id = 1
next_error_id = 1
next_kpi_id = 1

# --- Placeholder for future functions ---

# --- Recipes Table CRUD Functions ---

def create_recipe(name: str, ingredients: list, steps: list) -> int:
    """
    Adds a new recipe to the simulated database.
    Args:
        name (str): Name of the recipe.
        ingredients (list): List of ingredients (e.g., strings or dicts).
        steps (list): List of preparation steps (e.g., strings or dicts).
    Returns:
        int: The unique ID of the newly created recipe.
    """
    global next_recipe_id
    recipe = {
        "recipe_id": next_recipe_id,
        "name": name,
        "ingredients": ingredients,
        "steps": steps,
        "created_at": datetime.datetime.now()
    }
    db_recipes.append(recipe)
    next_recipe_id += 1
    awslog.log_to_aws_sim(
        "DEBUG", 
        "DatabaseAccess", 
        f"Recipe created: id={recipe['recipe_id']}", 
        details={
            "record_type": "Recipe", 
            "id": recipe['recipe_id'], 
            "name": recipe['name']
        }
    )
    return recipe["recipe_id"]

def get_recipe(recipe_id: int) -> dict or None:
    """
    Retrieves a specific recipe by its ID.
    Args:
        recipe_id (int): The ID of the recipe to retrieve.
    Returns:
        dict or None: The recipe dictionary if found, otherwise None.
    """
    for recipe in db_recipes:
        if recipe["recipe_id"] == recipe_id:
            awslog.log_to_aws_sim(
                "DEBUG", 
                "DatabaseAccess", 
                f"Recipe read: id={recipe_id}", 
                details={"record_type": "Recipe", "id": recipe_id}
            )
            return recipe
    awslog.log_to_aws_sim(
        "DEBUG", 
        "DatabaseAccess", 
        f"Recipe read attempt failed: id={recipe_id} not found.", 
        details={"record_type": "Recipe", "id": recipe_id}
    )
    return None

def get_all_recipes() -> list:
    """
    Retrieves all recipes from the simulated database.
    Returns:
        list: A list of all recipe dictionaries.
    """
    return db_recipes

def update_recipe(recipe_id: int, name: str = None, ingredients: list = None, steps: list = None) -> bool:
    """
    Updates specified fields of an existing recipe.
    Args:
        recipe_id (int): The ID of the recipe to update.
        name (str, optional): New name for the recipe.
        ingredients (list, optional): New list of ingredients.
        steps (list, optional): New list of steps.
    Returns:
        bool: True if the update was successful, False otherwise (e.g., recipe not found).
    """
    recipe = get_recipe(recipe_id)
    if recipe:
        if name is not None:
            recipe["name"] = name
        if ingredients is not None:
            recipe["ingredients"] = ingredients
        if steps is not None:
            recipe["steps"] = steps
        awslog.log_to_aws_sim(
            "DEBUG", 
            "DatabaseAccess", 
            f"Recipe updated: id={recipe_id}", 
            details={"record_type": "Recipe", "id": recipe_id}
        )
        return True
    return False

def delete_recipe(recipe_id: int) -> bool:
    """
    Deletes a recipe from the simulated database.
    Args:
        recipe_id (int): The ID of the recipe to delete.
    Returns:
        bool: True if the deletion was successful, False otherwise (e.g., recipe not found).
    """
    recipe = get_recipe(recipe_id)
    if recipe:
        db_recipes.remove(recipe)
        awslog.log_to_aws_sim(
            "DEBUG", 
            "DatabaseAccess", 
            f"Recipe deleted: id={recipe_id}", 
            details={"record_type": "Recipe", "id": recipe_id}
        )
        return True
    return False

# --- Results Table CRUD Functions ---

def create_result(recipe_id: int, output_quantity: int, status: str, operator: str, shift: str) -> int:
    """
    Adds a new production result to the simulated database.
    Args:
        recipe_id (int): ID of the recipe used.
        output_quantity (int): Quantity of output produced.
        status (str): Status of the production run (e.g., "success", "failed", "partial").
        operator (str): Name or ID of the operator.
        shift (str): Shift during which production occurred.
    Returns:
        int: The unique ID of the newly created result.
    """
    global next_result_id
    result = {
        "result_id": next_result_id,
        "timestamp": datetime.datetime.now(),
        "recipe_id": recipe_id,
        "output_quantity": output_quantity,
        "status": status,
        "operator": operator,
        "shift": shift
    }
    db_results.append(result)
    next_result_id += 1
    awslog.log_to_aws_sim(
        "DEBUG", 
        "DatabaseAccess", 
        f"Result created: id={result['result_id']}", 
        details={
            "record_type": "Result", 
            "id": result['result_id'], 
            "recipe_id": result['recipe_id'],
            "status": result['status']
        }
    )
    return result["result_id"]

def get_result(result_id: int) -> dict or None:
    """
    Retrieves a specific result by its ID.
    Args:
        result_id (int): The ID of the result to retrieve.
    Returns:
        dict or None: The result dictionary if found, otherwise None.
    """
    for result in db_results:
        if result["result_id"] == result_id:
            return result
    return None

def get_results_by_recipe(recipe_id: int) -> list:
    """
    Retrieves all results associated with a specific recipe ID.
    Args:
        recipe_id (int): The ID of the recipe.
    Returns:
        list: A list of result dictionaries for the given recipe.
    """
    return [result for result in db_results if result["recipe_id"] == recipe_id]

def get_all_results() -> list:
    """
    Retrieves all results from the simulated database.
    Returns:
        list: A list of all result dictionaries.
    """
    return db_results

# --- Errors Table CRUD Functions ---

def create_error(machine_id: str, error_code: str, description: str, severity: str) -> int:
    """
    Adds a new error log to the simulated database.
    Args:
        machine_id (str): ID of the machine where the error occurred (e.g., "GantryRobot1").
        error_code (str): Code identifying the error.
        description (str): Detailed description of the error.
        severity (str): Severity of the error (e.g., "low", "medium", "high", "critical").
    Returns:
        int: The unique ID of the newly created error log.
    """
    global next_error_id
    error_log = {
        "error_id": next_error_id,
        "timestamp": datetime.datetime.now(),
        "machine_id": machine_id,
        "error_code": error_code,
        "description": description,
        "severity": severity
    }
    db_errors.append(error_log)
    next_error_id += 1
    awslog.log_to_aws_sim(
        "DEBUG", 
        "DatabaseAccess", 
        f"Error created: id={error_log['error_id']}", 
        details={
            "record_type": "Error", 
            "id": error_log['error_id'], 
            "machine_id": error_log['machine_id'],
            "error_code": error_log['error_code'],
            "severity": error_log['severity']
        }
    )
    return error_log["error_id"]

def get_error(error_id: int) -> dict or None:
    """
    Retrieves a specific error log by its ID.
    Args:
        error_id (int): The ID of the error log to retrieve.
    Returns:
        dict or None: The error log dictionary if found, otherwise None.
    """
    for error_log in db_errors:
        if error_log["error_id"] == error_id:
            return error_log
    return None

def get_errors_by_machine(machine_id: str) -> list:
    """
    Retrieves all error logs for a specific machine ID.
    Args:
        machine_id (str): The ID of the machine.
    Returns:
        list: A list of error log dictionaries for the given machine.
    """
    return [error_log for error_log in db_errors if error_log["machine_id"] == machine_id]

def get_errors_by_severity(severity: str) -> list:
    """
    Retrieves all error logs of a specific severity.
    Args:
        severity (str): The severity level of errors to retrieve.
    Returns:
        list: A list of error log dictionaries of the given severity.
    """
    return [error_log for error_log in db_errors if error_log["severity"] == severity]

def get_all_errors() -> list:
    """
    Retrieves all error logs from the simulated database.
    Returns:
        list: A list of all error log dictionaries.
    """
    return db_errors

# --- KPIs Table CRUD Functions ---

def create_kpi_record(machine_id: str, oee: float, availability: float, performance: float, quality: float, cycle_time: float, defect_rate: float) -> int:
    """
    Adds a new KPI record to the simulated database.
    Args:
        machine_id (str): ID of the machine for which KPIs are recorded.
        oee (float): Overall Equipment Effectiveness.
        availability (float): Availability percentage.
        performance (float): Performance percentage.
        quality (float): Quality percentage.
        cycle_time (float): Cycle time for the machine or process.
        defect_rate (float): Defect rate.
    Returns:
        int: The unique ID of the newly created KPI record.
    """
    global next_kpi_id
    kpi_record = {
        "kpi_id": next_kpi_id,
        "timestamp": datetime.datetime.now(),
        "machine_id": machine_id,
        "OEE": oee, # Note: User spec used OEE, matching case here
        "availability": availability,
        "performance": performance,
        "quality": quality,
        "cycle_time": cycle_time,
        "defect_rate": defect_rate
    }
    db_kpis.append(kpi_record)
    next_kpi_id += 1
    awslog.log_to_aws_sim(
        "DEBUG", 
        "DatabaseAccess", 
        f"KPI record created: id={kpi_record['kpi_id']}", 
        details={
            "record_type": "KPI", 
            "id": kpi_record['kpi_id'], 
            "machine_id": kpi_record['machine_id'],
            "OEE": kpi_record['OEE']
        }
    )
    return kpi_record["kpi_id"]

def get_kpi_record(kpi_id: int) -> dict or None:
    """
    Retrieves a specific KPI record by its ID.
    Args:
        kpi_id (int): The ID of the KPI record to retrieve.
    Returns:
        dict or None: The KPI record dictionary if found, otherwise None.
    """
    for record in db_kpis:
        if record["kpi_id"] == kpi_id:
            return record
    return None

def get_kpi_records_by_machine(machine_id: str) -> list:
    """
    Retrieves all KPI records for a specific machine ID.
    Args:
        machine_id (str): The ID of the machine.
    Returns:
        list: A list of KPI record dictionaries for the given machine.
    """
    return [record for record in db_kpis if record["machine_id"] == machine_id]

def get_all_kpi_records() -> list:
    """
    Retrieves all KPI records from the simulated database.
    Returns:
        list: A list of all KPI record dictionaries.
    """
    return db_kpis

if __name__ == '__main__':
    print("sim_database_manager.py initialized with Recipe CRUD functions.")

    # Test recipe creation
    recipe1_id = create_recipe("Pasta Carbonara", ["Spaghetti", "Eggs", "Pancetta", "Parmesan", "Pepper"], ["Cook spaghetti", "Fry pancetta", "Mix eggs and cheese", "Combine all"])
    recipe2_id = create_recipe("Simple Salad", ["Lettuce", "Tomato", "Cucumber", "Olive Oil", "Vinegar"], ["Chop vegetables", "Dress with oil and vinegar"])
    print(f"Created recipe ID {recipe1_id} and {recipe2_id}")

    # Test get_all_recipes
    all_recipes = get_all_recipes()
    print(f"All recipes: {all_recipes}")

    # Test get_recipe
    retrieved_recipe = get_recipe(recipe1_id)
    print(f"Retrieved recipe {recipe1_id}: {retrieved_recipe}")

    # Test update_recipe
    update_status = update_recipe(recipe1_id, name="Authentic Carbonara")
    print(f"Update status for recipe {recipe1_id}: {update_status}")
    retrieved_recipe_updated = get_recipe(recipe1_id)
    print(f"Updated recipe {recipe1_id}: {retrieved_recipe_updated}")
    
    update_status_failed = update_recipe(999, name="Ghost Recipe") # Non-existent
    print(f"Update status for non-existent recipe 999: {update_status_failed}")

    # Test delete_recipe
    delete_status = delete_recipe(recipe2_id)
    print(f"Delete status for recipe {recipe2_id}: {delete_status}")
    print(f"All recipes after deletion: {get_all_recipes()}")

    delete_status_failed = delete_recipe(999) # Non-existent
    print(f"Delete status for non-existent recipe 999: {delete_status_failed}")

    print("\n--- Testing Results Functions ---")
    # Assume recipe1_id is available from Recipe tests, or create a dummy one if running standalone
    if 'recipe1_id' not in locals(): # Simple check if recipe tests ran
        recipe1_id = create_recipe("Test Recipe for Results", ["i1"], ["s1"]) 
        print(f"Created temporary recipe with ID {recipe1_id} for results testing.")

    result1_id = create_result(recipe1_id, 100, "success", "OperatorA", "Shift1")
    result2_id = create_result(recipe1_id, 50, "partial", "OperatorB", "Shift2")
    print(f"Created result ID {result1_id} and {result2_id} for recipe {recipe1_id}")

    retrieved_result = get_result(result1_id)
    print(f"Retrieved result {result1_id}: {retrieved_result}")

    results_for_recipe = get_results_by_recipe(recipe1_id)
    print(f"Results for recipe {recipe1_id}: {results_for_recipe}")

    all_results = get_all_results()
    print(f"All results: {all_results}")

    # Test with a recipe ID that might not have results (if recipes can be created without results)
    recipe_no_results_id = create_recipe("No Results Recipe", [], [])
    results_for_empty_recipe = get_results_by_recipe(recipe_no_results_id)
    print(f"Results for recipe {recipe_no_results_id} (should be empty): {results_for_empty_recipe}")

    print("\n--- Testing Error Functions ---")
    error1_id = create_error("GantryRobot1", "E-101", "Failed to pick object", "medium")
    error2_id = create_error("Feeder2", "F-003", "Component jam", "high")
    error3_id = create_error("GantryRobot1", "E-102", "Positioning accuracy out of range", "medium")
    print(f"Created error IDs {error1_id}, {error2_id}, and {error3_id}")

    retrieved_error = get_error(error1_id)
    print(f"Retrieved error {error1_id}: {retrieved_error}")

    errors_for_gantry = get_errors_by_machine("GantryRobot1")
    print(f"Errors for GantryRobot1: {errors_for_gantry}")

    high_severity_errors = get_errors_by_severity("high")
    print(f"High severity errors: {high_severity_errors}")
    
    medium_severity_errors = get_errors_by_severity("medium")
    print(f"Medium severity errors: {medium_severity_errors}")

    all_errors = get_all_errors()
    print(f"All errors: {all_errors}")

    print("\n--- Testing KPI Functions ---")
    kpi1_id = create_kpi_record("GantryRobot1", oee=0.85, availability=0.90, performance=0.95, quality=0.99, cycle_time=10.5, defect_rate=0.01)
    kpi2_id = create_kpi_record("Feeder2", oee=0.90, availability=0.92, performance=0.98, quality=0.995, cycle_time=5.2, defect_rate=0.005)
    kpi3_id = create_kpi_record("GantryRobot1", oee=0.83, availability=0.88, performance=0.94, quality=0.99, cycle_time=10.7, defect_rate=0.012) # Another for GantryRobot1
    print(f"Created KPI record IDs {kpi1_id}, {kpi2_id}, and {kpi3_id}")

    retrieved_kpi = get_kpi_record(kpi1_id)
    print(f"Retrieved KPI record {kpi1_id}: {retrieved_kpi}")

    kpis_for_gantry = get_kpi_records_by_machine("GantryRobot1")
    print(f"KPI records for GantryRobot1: {kpis_for_gantry}")

    all_kpis = get_all_kpi_records()
    print(f"All KPI records: {all_kpis}")
