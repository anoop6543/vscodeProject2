import time
import threading
import queue
import logging
from typing import Any, Callable, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - [%(name)s] - %(message)s'
)

class MockTime:
    def now(self):
        return self
    
    def to_msg(self):
        t = time.time()
        sec = int(t)
        nanosec = int((t - sec) * 1e9)
        return {"sec": sec, "nanosec": nanosec}

class Node:
    def __init__(self, node_name: str):
        self.node_name = node_name
        self.logger = logging.getLogger(node_name)
        self.subscriptions = []
        self.publishers = []
        self.timers = []
        self._shutdown = False

    def get_logger(self):
        return self.logger

    def create_subscription(self, msg_type, topic: str, callback: Callable, qos_profile=10):
        sub = Subscription(self, topic, callback)
        self.subscriptions.append(sub)
        MockMiddleware.register_subscription(topic, sub)
        return sub

    def create_publisher(self, msg_type, topic: str, qos_profile=10):
        pub = Publisher(self, topic)
        self.publishers.append(pub)
        return pub

    def create_timer(self, timer_period_sec: float, callback: Callable):
        timer = Timer(timer_period_sec, callback)
        self.timers.append(timer)
        timer.start()
        return timer

    def destroy_node(self):
        self._shutdown = True
        for timer in self.timers:
            timer.cancel()
        self.logger.info("Node destroyed")

    def get_clock(self):
        return MockTime()

class Subscription:
    def __init__(self, node: Node, topic: str, callback: Callable):
        self.node = node
        self.topic = topic
        self.callback = callback

    def handle_message(self, msg: Any):
        self.callback(msg)

class Publisher:
    def __init__(self, node: Node, topic: str):
        self.node = node
        self.topic = topic

    def publish(self, msg: Any):
        # self.node.logger.info(f"Publishing to {self.topic}")
        MockMiddleware.publish(self.topic, msg)

class Timer:
    def __init__(self, period: float, callback: Callable):
        self.period = period
        self.callback = callback
        self._running = True
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True

    def start(self):
        self._thread.start()

    def cancel(self):
        self._running = False
        # self._thread.join() # Don't block on join for simple mock

    def _run(self):
        while self._running:
            time.sleep(self.period)
            if self._running:
                try:
                    self.callback()
                except Exception as e:
                    print(f"Timer callback failed: {e}")

class MockMiddleware:
    _subscriptions: Dict[str, List[Subscription]] = {}
    _lock = threading.Lock()

    @classmethod
    def register_subscription(cls, topic: str, sub: Subscription):
        with cls._lock:
            if topic not in cls._subscriptions:
                cls._subscriptions[topic] = []
            cls._subscriptions[topic].append(sub)

    @classmethod
    def publish(cls, topic: str, msg: Any):
        with cls._lock:
            subs = cls._subscriptions.get(topic, [])
        
        for sub in subs:
            # Run callback in a separate thread or directly? 
            # For simplicity, direct call, but catch exceptions
            try:
                sub.handle_message(msg)
            except Exception as e:
                print(f"Error handling message on {topic}: {e}")

def init(args=None):
    pass

def spin(node: Node):
    # In a real system, this blocks. Here we just sleep to keep main thread alive
    # while timers and threads work.
    try:
        while not node._shutdown:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

def shutdown():
    pass
