"""Battery voltage from the MBot firmware and what it means.

The firmware publishes /battery_adc (mbot_interfaces/BatteryADC, best effort, about
4 Hz); volts[3] is the battery voltage measured on the control board. mbot_interfaces
comes from the system underlay /opt/mbot/ros, so this works before a student builds
anything (finding W3).

Only the voltage is shown, no percentage: the voltage sags under load and the pack's
curve is not known. What the voltage means (wiring problem, low battery) is decided
in alerts.py (battery_state).
"""

import logging
import threading
import time

log = logging.getLogger(__name__)

TOPIC = "battery_adc"
STALE_AFTER_S = 5.0   # no message for this long: show "no data"

class BatteryListener:
    """Subscribes to /battery_adc in a background thread. Works without ROS too."""

    def __init__(self, node_name="mbot_oled"):
        self.node_name = node_name
        self.available = False
        self._volts = -1.0
        self._stamp = 0.0
        self._lock = threading.Lock()
        self._rclpy = None
        self._node = None
        self._executor = None
        self._thread = None
        self._running = False

    def start(self):
        try:
            import rclpy
            from rclpy.qos import QoSProfile, QoSReliabilityPolicy
            from mbot_interfaces.msg import BatteryADC
        except ImportError as e:
            log.warning("battery voltage not available (ROS import failed: %s)", e)
            return False
        try:
            # The service handles SIGTERM itself (shutdown screen), so rclpy must not.
            try:
                from rclpy.signals import SignalHandlerOptions
                rclpy.init(args=None, signal_handler_options=SignalHandlerOptions.NO)
            except ImportError:
                rclpy.init(args=None)
            from rclpy.executors import SingleThreadedExecutor
            self._node = rclpy.create_node(self.node_name)
            qos = QoSProfile(depth=5, reliability=QoSReliabilityPolicy.BEST_EFFORT)
            self._node.create_subscription(BatteryADC, TOPIC, self._callback, qos)
            self._executor = SingleThreadedExecutor()
            self._executor.add_node(self._node)
        except Exception as e:  # rclpy raises several types; the OLED must keep running
            log.warning("battery voltage not available (ROS start failed: %s)", e)
            return False
        self._rclpy = rclpy
        self._running = True
        # Our own spin loop with a stop flag: stop() can then join the thread before
        # rclpy shuts down. Shutting down under a running rclpy.spin() aborts the process.
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        self.available = True
        log.info("subscribed to /%s", TOPIC)
        return True

    def _spin(self):
        while self._running:
            try:
                self._executor.spin_once(timeout_sec=0.5)
            except Exception as e:
                if self._running:
                    log.warning("ROS spin stopped: %s", e)
                return

    def _callback(self, msg):
        with self._lock:
            self._volts = float(msg.volts[3])
            self._stamp = time.monotonic()

    def volts(self, now=None):
        """Latest voltage, or -1 if there is none or it is older than STALE_AFTER_S."""
        now = time.monotonic() if now is None else now
        with self._lock:
            if self._stamp and now - self._stamp <= STALE_AFTER_S:
                return self._volts
        return -1.0

    def publishers(self, topic):
        """Number of publishers on a topic, or -1 if ROS is not available."""
        if self._node is None:
            return -1
        try:
            return self._node.count_publishers(topic)
        except Exception:
            return -1

    def stop(self):
        if self._rclpy is None:
            return
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        for step in (lambda: self._executor.shutdown(timeout_sec=1.0),
                     lambda: self._node.destroy_node(),
                     lambda: self._rclpy.shutdown()):
            try:
                step()
            except Exception:
                pass
