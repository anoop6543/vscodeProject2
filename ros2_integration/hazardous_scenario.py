import sys
import os
import json
import time
import threading

try:
    import rclpy
    from rclpy.node import Node
except ImportError:
    print("rclpy not found, using mock_rclpy")
    import ros2_integration.mock_rclpy as rclpy
    from ros2_integration.mock_rclpy import Node

class HazardousScenario(Node):
    def __init__(self):
        super().__init__('hazardous_scenario')
        self.get_logger().info("Initializing HazardousScenario Node...")
        
        self.cmd_pub = self.create_publisher(str, '/gantry/command', 10)
        
        # Start the scenario in a separate thread so we don't block the node's spin loop
        self.scenario_thread = threading.Thread(target=self.run_scenario)
        self.scenario_thread.start()

    def publish_command(self, action, params):
        msg = json.dumps({"action": action, "params": params})
        self.get_logger().info(f"Sending command: {msg}")
        self.cmd_pub.publish(msg)

    def run_scenario(self):
        # Allow some time for connections to establish
        time.sleep(2)
        self.get_logger().info("--- Starting Hazardous Material Handling Scenario ---")

        # Step 1: Move to Containment Unit
        self.get_logger().info("Step 1: Moving to Containment Unit...")
        self.publish_command("MOVE_TO", {
            "position": [100, 200, 50],
            "orientation": [0, 0]
        })
        time.sleep(5) # Wait for move

        # Step 2: Pick up Radioactive Canister
        self.get_logger().info("Step 2: Picking up Radioactive Canister...")
        self.publish_command("PICK_AND_PLACE", {
            "object_type": "Cylinder",
            "pick_pos": [100, 200, 20],
            "place_pos": [500, 100, 20] # Shielded AGV location
        })
        time.sleep(10) # Wait for pick and place

        # Step 3: Return to Safe Home Position
        self.get_logger().info("Step 3: Returning to Safe Home...")
        self.publish_command("MOVE_TO", {
            "position": [0, 0, 100],
            "orientation": [0, 0]
        })
        time.sleep(5)

        self.get_logger().info("--- Scenario Completed ---")
        # In a real scenario, we might shut down or wait for next trigger
        # Here we can signal shutdown
        self.get_logger().info("Scenario finished. Shutting down node.")
        # We can't easily call rclpy.shutdown() from here in a real node without issues,
        # but for the mock it's fine, or we just let the main loop handle it.

def main(args=None):
    rclpy.init(args=args)
    node = HazardousScenario()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
