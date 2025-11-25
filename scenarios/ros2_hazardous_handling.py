import sys
import os
import logging
import time
import random
import threading
import queue
from typing import Dict, Any, Tuple

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gantry_system.core.gantry_robot import GantryRobot, ObjectType
from gantry_system.core.sim_opc_server import sim_opc_instance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler("logs/ros2_hazardous.log"),
        logging.StreamHandler()
    ]
)

class MockROS2Node:
    """
    Simulates a ROS2 Node.
    Can 'publish' messages to a topic and 'subscribe' to topics.
    """
    def __init__(self, node_name: str):
        self.node_name = node_name
        self.subscriptions = {} # topic -> callback
        self.logger = logging.getLogger(f"ROS2Node-{node_name}")
        self.logger.info("Node initialized")

    def subscribe(self, topic: str, callback):
        self.subscriptions[topic] = callback
        self.logger.info(f"Subscribed to {topic}")

    def publish(self, topic: str, message: Dict[str, Any]):
        self.logger.info(f"Publishing to {topic}: {message}")
        # In a real system, this would go to the middleware.
        # Here, we need a way to route it to other nodes.
        # For simplicity, we'll use a global message router or just direct injection if we know the bridge.
        # To keep it decoupled, let's use a simple EventBus pattern or just pass the bridge instance if needed.
        # But to be more "ROS-like", let's assume a global 'ROS Network' singleton or similar.
        ROSNetwork.transmit(topic, message)

    def receive_message(self, topic: str, message: Dict[str, Any]):
        if topic in self.subscriptions:
            self.subscriptions[topic](message)

class ROSNetwork:
    """
    Simulates the ROS2 Middleware/Network.
    """
    _nodes = []

    @classmethod
    def register_node(cls, node: MockROS2Node):
        cls._nodes.append(node)

    @classmethod
    def transmit(cls, topic: str, message: Dict[str, Any]):
        for node in cls._nodes:
            node.receive_message(topic, message)

class ROS2Bridge(MockROS2Node):
    """
    Bridges the GantryRobot to the ROS2 network.
    Subscribes to commands and controls the robot.
    Publishes robot status.
    """
    def __init__(self, robot: GantryRobot):
        super().__init__("GantryBridge")
        self.robot = robot
        self.subscribe("/gantry/command", self.handle_command)
        self.running = True
        self.status_thread = threading.Thread(target=self.publish_status_loop)
        self.status_thread.start()

    def handle_command(self, msg: Dict[str, Any]):
        """
        Handle incoming ROS2 commands.
        Expected msg format: {"action": str, "params": dict}
        """
        self.logger.info(f"Received command: {msg}")
        action = msg.get("action")
        params = msg.get("params", {})

        if action == "MOVE_TO":
            pos = params.get("position") # (x, y, z)
            orient = params.get("orientation", (0, 0))
            if pos:
                self.logger.info(f"Executing MOVE_TO {pos}")
                self.robot.move_to(pos, orient)
                self.publish("/gantry/result", {"status": "SUCCESS", "action": action})
        
        elif action == "PICK":
            obj_type_str = params.get("object_type")
            pick_pos = params.get("pick_pos")
            place_pos = params.get("place_pos")
            
            # Map string to Enum
            obj_type = None
            for ot in ObjectType:
                if ot.value == obj_type_str:
                    obj_type = ot
                    break
            
            if obj_type and pick_pos and place_pos:
                self.logger.info(f"Executing PICK_AND_PLACE for {obj_type}")
                self.robot.pick_and_place(obj_type, pick_pos, place_pos)
                self.publish("/gantry/result", {"status": "SUCCESS", "action": action})
            else:
                self.logger.error("Invalid parameters for PICK")
                self.publish("/gantry/result", {"status": "ERROR", "message": "Invalid params"})

    def publish_status_loop(self):
        """
        Periodically publish robot status (joint states).
        """
        while self.running:
            # Create a JointState message
            joint_state_msg = {
                "header": {"timestamp": time.time()},
                "name": ["X", "Y", "Z", "Extend", "Retract", "Rotate", "Tilt", "Gripper"],
                "position": [m.position for m in self.robot.motors],
                "velocity": [], # Not simulated
                "effort": []    # Not simulated
            }
            self.publish("/gantry/joint_states", joint_state_msg)
            time.sleep(1.0) # 1Hz status update

    def shutdown(self):
        self.running = False
        self.status_thread.join()

def run_scenario():
    # 1. Initialize System
    robot = GantryRobot()
    bridge = ROS2Bridge(robot)
    ROSNetwork.register_node(bridge)

    # 2. Initialize External Controller (Safety System)
    controller = MockROS2Node("SafetyController")
    ROSNetwork.register_node(controller)

    # Helper to print received status
    def on_joint_state(msg):
        # Reduce log noise, just print occasionally or debug
        # print(f"[Controller] Received JointState: X={msg['position'][0]:.1f}, Y={msg['position'][1]:.1f}")
        pass
    
    def on_result(msg):
        print(f"[Controller] Received Result: {msg}")

    controller.subscribe("/gantry/joint_states", on_joint_state)
    controller.subscribe("/gantry/result", on_result)

    print("\n--- Starting Hazardous Material Handling Scenario ---\n")
    time.sleep(1)

    # 3. Execute Workflow
    
    # Step A: Move to Containment Unit
    print("\n[Scenario] Step 1: Moving to Containment Unit...")
    controller.publish("/gantry/command", {
        "action": "MOVE_TO",
        "params": {
            "position": (100, 200, 50),
            "orientation": (0, 0)
        }
    })
    time.sleep(3) # Wait for move

    # Step B: Pick up Radioactive Canister
    # We'll treat "Cylinder" as our canister
    print("\n[Scenario] Step 2: Picking up Radioactive Canister...")
    controller.publish("/gantry/command", {
        "action": "PICK",
        "params": {
            "object_type": "Cylinder",
            "pick_pos": (100, 200, 20),
            "place_pos": (500, 100, 20) # Shielded AGV location
        }
    })
    
    # Wait enough time for pick and place operation
    time.sleep(8) 

    # Step C: Return to Safe Home Position
    print("\n[Scenario] Step 3: Returning to Safe Home...")
    controller.publish("/gantry/command", {
        "action": "MOVE_TO",
        "params": {
            "position": (0, 0, 100),
            "orientation": (0, 0)
        }
    })
    time.sleep(3)

    print("\n--- Scenario Completed ---\n")
    bridge.shutdown()

if __name__ == "__main__":
    run_scenario()
