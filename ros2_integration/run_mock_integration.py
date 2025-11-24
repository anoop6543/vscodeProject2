import sys
import os
import threading
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ros2_integration.mock_rclpy as rclpy
from ros2_integration.gantry_bridge import GantryBridge
from ros2_integration.hazardous_scenario import HazardousScenario

def run_node(node):
    rclpy.spin(node)

def main():
    rclpy.init()
    
    print("--- Starting Mock ROS2 Integration Test ---")
    
    # Create Nodes
    bridge = GantryBridge()
    scenario = HazardousScenario()
    
    # Run nodes in separate threads to simulate independent processes
    t1 = threading.Thread(target=run_node, args=(bridge,))
    t2 = threading.Thread(target=run_node, args=(scenario,))
    
    t1.daemon = True
    t2.daemon = True
    
    t1.start()
    t2.start()
    
    try:
        # Keep main thread alive to let nodes run
        # The scenario takes about 20-25 seconds
        time.sleep(30)
    except KeyboardInterrupt:
        pass
    finally:
        print("\n--- Test Finished ---")
        bridge.destroy_node()
        scenario.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
