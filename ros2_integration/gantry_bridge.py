import sys
import os
import json
import threading

# Add parent directory to path to import SimpleGantrySimulation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import rclpy
    from rclpy.node import Node
except ImportError:
    # Fallback to mock if rclpy is not installed
    print("rclpy not found, using mock_rclpy")
    import ros2_integration.mock_rclpy as rclpy
    from ros2_integration.mock_rclpy import Node

from gantry_system.core.gantry_robot import GantryRobot, ObjectType

class GantryBridge(Node):
    def __init__(self):
        super().__init__('gantry_bridge')
        self.get_logger().info("Initializing GantryBridge...")
        
        # Initialize the actual robot controller
        self.robot = GantryRobot()
        
        # Publishers
        self.status_pub = self.create_publisher(str, '/gantry/status', 10)
        self.joint_pub = self.create_publisher(str, '/gantry/joint_states', 10)
        
        # Subscribers
        self.cmd_sub = self.create_subscription(
            str, 
            '/gantry/command', 
            self.command_callback, 
            10
        )
        
        # Timers
        self.create_timer(1.0, self.publish_status)
        
        self.get_logger().info("GantryBridge Initialized and Ready.")

    def publish_status(self):
        # Publish Joint States (Simplified as JSON for this prototype)
        # In real ROS2, this would be sensor_msgs/msg/JointState
        joint_state = {
            "timestamp": self.get_clock().now().to_msg()['sec'],
            "position": [m.position for m in self.robot.motors]
        }
        self.joint_pub.publish(json.dumps(joint_state))
        
        # Publish General Status
        # We can infer status from OPC tags or internal state if exposed.
        # For now, let's assume "Idle" unless we are executing a command.
        # Note: The GantryRobot class prints to stdout, but doesn't easily expose 'busy' state 
        # except via the OPC tag "GantryRobot.Status". 
        # Since we don't have a direct read back from OPC here easily without importing that module,
        # we will just publish a heartbeat.
        self.status_pub.publish(json.dumps({"status": "ACTIVE"}))

    def command_callback(self, msg):
        try:
            # Expecting JSON command
            # msg is a string in our mock/simple setup
            if hasattr(msg, 'data'): # Real ROS2 msg
                data = msg.data
            else: # Mock string
                data = msg
                
            cmd = json.loads(data)
            self.get_logger().info(f"Received command: {cmd}")
            
            action = cmd.get("action")
            params = cmd.get("params", {})
            
            # Execute in a separate thread to not block the ROS spin loop
            t = threading.Thread(target=self.execute_command, args=(action, params))
            t.start()
            
        except Exception as e:
            self.get_logger().error(f"Failed to process command: {e}")

    def execute_command(self, action, params):
        self.get_logger().info(f"Executing {action}...")
        try:
            if action == "MOVE_TO":
                pos = params.get("position")
                orient = params.get("orientation", (0, 0))
                self.robot.move_to(tuple(pos), tuple(orient))
                
            elif action == "PICK_AND_PLACE":
                obj_type_str = params.get("object_type")
                pick_pos = params.get("pick_pos")
                place_pos = params.get("place_pos")
                
                # Convert string to Enum
                obj_type = None
                for ot in ObjectType:
                    if ot.value == obj_type_str:
                        obj_type = ot
                        break
                
                if obj_type:
                    self.robot.pick_and_place(obj_type, tuple(pick_pos), tuple(place_pos))
                else:
                    self.get_logger().error(f"Unknown ObjectType: {obj_type_str}")

            elif action == "ARC_MOVE":
                start = params.get("start_point")
                end = params.get("end_point")
                center = params.get("center_point")
                speed = params.get("speed", 500)
                self.robot.arc_move(tuple(start), tuple(end), tuple(center), speed)

            else:
                self.get_logger().warn(f"Unknown action: {action}")
                
            self.get_logger().info(f"Finished {action}")
            
        except Exception as e:
            self.get_logger().error(f"Error during execution: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = GantryBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
