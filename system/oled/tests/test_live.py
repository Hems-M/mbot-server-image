"""mbot health --live: the event log and the screen layout."""

import os
import re
import sys
import unittest
from dataclasses import replace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mbot_oled import alerts, live  # noqa: E402
from mbot_oled.cli import palette  # noqa: E402
from mbot_oled.status import Status  # noqa: E402

GOOD = Status(hostname="mbot-07", ip="35.3.125.94", iface="wlan0", wifi_mode="station", ssid="MWireless",
              freq_mhz=5180, signal_dbm=-58, uptime_s=4380, cpu_pct=23, mem_pct=41, temp_c=54,
              disk_pct=62, power_known=True, pico_present=True, agent_active=True,
              ros_available=True, battery_v=11.92)
TOPICS = {"/odom": 1, "/scan": 0, "/camera/image_raw": 0}
ANSI = re.compile(r"\033\[[0-9;]*m")


class LiveTests(unittest.TestCase):
    def snap(self, st, topics=TOPICS):
        return live.snapshot(st, topics, alerts.current_problems(st))

    def test_first_snapshot(self):
        self.assertEqual(live.changes(None, self.snap(GOOD)), ["Started watching"])

    def test_no_change_no_event(self):
        self.assertEqual(live.changes(self.snap(GOOD), self.snap(replace(GOOD, cpu_pct=80))), [])

    def test_pico_unplugged(self):
        gone = replace(GOOD, pico_present=False, agent_active=False, battery_v=-1.0)
        events = live.changes(self.snap(GOOD), self.snap(gone))
        self.assertIn("Pico disconnected", events)
        self.assertIn("micro-ROS agent stopped", events)
        self.assertIn("Firmware data stopped", events)
        self.assertTrue(any(e.startswith("Problem: Pico not connected") for e in events), events)
        back = live.changes(self.snap(gone), self.snap(GOOD))
        self.assertIn("Pico connected", back)
        self.assertTrue(any(e.startswith("Resolved:") for e in back), back)

    def test_lidar_started(self):
        events = live.changes(self.snap(GOOD), self.snap(GOOD, dict(TOPICS, **{"/scan": 1})))
        self.assertEqual(events, ["LiDAR /scan started"])

    def test_network_change(self):
        hotspot = replace(GOOD, ip="192.168.3.1", wifi_mode="ap", ssid="mbot-07-AP")
        self.assertEqual(live.changes(self.snap(GOOD), self.snap(hotspot)), ["Hotspot on, IP 192.168.3.1"])
        self.assertEqual(live.changes(self.snap(hotspot), self.snap(GOOD)), ["New IP 35.3.125.94 (MWireless)"])

    def test_battery_voltage_only(self):
        text = "\n".join(ANSI.sub("", line) for line in live.frame(
            GOOD, TOPICS, [], [], palette(False), fan=(75, 3120)))
        self.assertIn("11.92 V", text)
        self.assertNotIn(" %  ", text.split("SYSTEM")[0])  # no percentage on the battery line
        self.assertIn("3120 rpm", text)

    def test_frame_fits(self):
        events = [("12:00:%02d" % i, "event %d" % i) for i in range(12)]
        cases = [GOOD, replace(GOOD, battery_v=-1.0, pico_present=False, ip="", ssid="", wifi_mode=""),
                 replace(GOOD, temp_c=85, mem_pct=97, disk_pct=95, undervolt_now=True, hostname="m" * 60)]
        for color in (True, False):
            for st in cases:
                lines = live.frame(st, TOPICS, alerts.current_problems(st), events, palette(color),
                                   width=78, now_text="12:00:00")
                for line in lines:
                    self.assertLessEqual(len(ANSI.sub("", line)), 100, line)
                self.assertEqual(len(ANSI.sub("", lines[0])), 78)
                text = "\n".join(ANSI.sub("", line) for line in lines)
                self.assertIn("EVENTS", text)
                self.assertIn("event 11", text)
                self.assertNotIn("event 3", text)  # only the last 8


if __name__ == "__main__":
    unittest.main()
