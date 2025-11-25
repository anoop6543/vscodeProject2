import datetime

class SimOpcServer:
    """
    A simple simulation of an OPC UA server holding tags in memory.
    """
    def __init__(self):
        """Initializes the server and populates it with some sample tags."""
        self.tags = {}
        self._initialize_sample_tags()

    def _initialize_sample_tags(self):
        """Helper method to create a set of predefined tags."""
        # Sensor readings
        self.add_tag("SimPLC.S1.Temp", 25.0)
        self.add_tag("SimPLC.S1.Pressure", 101.2)
        self.add_tag("SimPLC.S1.ItemPresent", False)
        
        # Robot state
        self.add_tag("GantryRobot.AxisX.ActualPosition", 0.0)
        self.add_tag("GantryRobot.AxisY.ActualPosition", 0.0)
        self.add_tag("GantryRobot.AxisZ.ActualPosition", 0.0)
        self.add_tag("GantryRobot.Status", "Idle") # e.g., Idle, Moving, Welding, Marking, Error
        
        # Actuator states
        self.add_tag("Conveyor.IsRunning", False)
        
        # System tags
        self.add_tag("System.Heartbeat", 0) # Could be incremented by a background process in a more complex sim

    def add_tag(self, tag_id: str, initial_value, initial_quality: str = "Good"):
        """
        Adds a new tag to the server or updates it if it already exists (though typically used for setup).
        Args:
            tag_id (str): The unique identifier for the tag.
            initial_value: The initial value of the tag.
            initial_quality (str): The initial quality of the tag.
        Returns:
            bool: True if the tag was added/updated, False otherwise.
        """
        if not isinstance(tag_id, str) or not tag_id:
            # print(f"Error: tag_id must be a non-empty string. Got: {tag_id}") # Optional: for debugging
            return False

        self.tags[tag_id] = {
            "value": initial_value,
            "timestamp": datetime.datetime.utcnow(),
            "quality": initial_quality
        }
        return True

    def read_tag(self, tag_id: str) -> dict or None:
        """
        Reads a tag's full data (value, timestamp, quality).
        Args:
            tag_id (str): The ID of the tag to read.
        Returns:
            dict or None: The tag data dictionary if found, otherwise None.
        """
        return self.tags.get(tag_id) # .get is safer than direct access

    def write_tag(self, tag_id: str, value) -> bool:
        """
        Writes a new value to an existing tag. Updates timestamp.
        Args:
            tag_id (str): The ID of the tag to write to.
            value: The new value for the tag.
        Returns:
            bool: True if the write was successful (tag existed), False otherwise.
        """
        if tag_id in self.tags:
            self.tags[tag_id]["value"] = value
            self.tags[tag_id]["timestamp"] = datetime.datetime.utcnow()
            # self.tags[tag_id]["quality"] could also be updated if needed, e.g., based on write success
            return True
        return False # Tag does not exist, write failed

    def get_all_tags(self) -> dict:
        """
        Retrieves a shallow copy of all tags in the server.
        Returns:
            dict: A dictionary containing all tags.
        """
        return self.tags.copy() # Return a copy to prevent external modification of the internal dict

# --- Global instance of the OPC Server ---
# This instance will be imported and used by other modules.
sim_opc_instance = SimOpcServer()

if __name__ == '__main__':
    print("Simulated OPC Server Initialized.")
    print(f"Initial Heartbeat: {sim_opc_instance.read_tag('System.Heartbeat')}")
    
    print("\n--- Testing Tag Operations ---")
    # Read an existing tag
    temp_tag = sim_opc_instance.read_tag("SimPLC.S1.Temp")
    print(f"Read SimPLC.S1.Temp: {temp_tag}")

    # Write to an existing tag
    print("Writing 27.5 to SimPLC.S1.Temp...")
    sim_opc_instance.write_tag("SimPLC.S1.Temp", 27.5)
    temp_tag_updated = sim_opc_instance.read_tag("SimPLC.S1.Temp")
    print(f"Updated SimPLC.S1.Temp: {temp_tag_updated}")

    # Try to write to a non-existent tag
    print("Writing to NonExistent.Tag (should fail silently or log if implemented):")
    write_status = sim_opc_instance.write_tag("NonExistent.Tag", 100)
    print(f"Write status for NonExistent.Tag: {write_status}")
    print(f"Read NonExistent.Tag: {sim_opc_instance.read_tag('NonExistent.Tag')}")

    # Add a new tag after initialization
    print("Adding NewDevice.S1.IsEnabled tag...")
    sim_opc_instance.add_tag("NewDevice.S1.IsEnabled", True)
    new_tag = sim_opc_instance.read_tag("NewDevice.S1.IsEnabled")
    print(f"Read NewDevice.S1.IsEnabled: {new_tag}")

    # Get all tags
    all_current_tags = sim_opc_instance.get_all_tags()
    print(f"\nTotal tags in server: {len(all_current_tags)}")
    # for tag_id, data in all_current_tags.items():
    #     print(f"  {tag_id}: {data}") # Uncomment to see all tags
