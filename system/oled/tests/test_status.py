import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mbot_oled import status  # noqa: E402

IW_INFO_STATION = """Interface wlan0
\tifindex 3
\twdev 0x1
\taddr d8:3a:dd:12:34:56
\tssid MWireless
\ttype managed
\twiphy 0
\tchannel 36 (5180 MHz), width: 80 MHz, center1: 5210 MHz
\ttxpower 31.00 dBm
"""

IW_INFO_AP = """Interface wlan0
\taddr d8:3a:dd:12:34:56
\tssid mbot-0000-AP
\ttype AP
\tchannel 44 (5220 MHz), width: 20 MHz, center1: 5220 MHz
"""

IW_LINK = """Connected to 00:11:22:33:44:55 (on wlan0)
\tSSID: MWireless
\tfreq: 5180.0
\tRX: 1234 bytes (10 packets)
\tsignal: -61 dBm
\ttx bitrate: 433.3 MBit/s
"""

PROC_TCP = """  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 00000000:0016 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 1 1
   1: 00000000:223D 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 2 1
"""


class ParserTests(unittest.TestCase):
    def test_uptime(self):
        self.assertAlmostEqual(status.parse_uptime("4380.52 17000.10\n"), 4380.52)

    def test_cpu_percent(self):
        a = status.parse_cpu_times("cpu  100 0 100 800 0 0 0 0 0 0\ncpu0 1 2 3 4\n")
        b = status.parse_cpu_times("cpu  150 0 150 900 0 0 0 0 0 0\n")
        self.assertAlmostEqual(status.cpu_percent(a, b), 50.0)
        self.assertEqual(status.cpu_percent(a, a), -1.0)

    def test_meminfo(self):
        text = "MemTotal:  8000000 kB\nMemFree: 1 kB\nMemAvailable:  6000000 kB\n"
        self.assertAlmostEqual(status.parse_meminfo(text), 25.0)
        self.assertEqual(status.parse_meminfo("MemTotal: 10 kB\n"), -1.0)

    def test_throttled(self):
        self.assertEqual(status.parse_throttled("0x0\n"), (False, False, False))
        self.assertEqual(status.parse_throttled("0x50005\n"), (True, True, True))
        self.assertEqual(status.parse_throttled("0x10000"), (False, False, True))

    def test_iw_info(self):
        self.assertEqual(status.parse_iw_info(IW_INFO_STATION), ("station", "MWireless", 5180))
        self.assertEqual(status.parse_iw_info(IW_INFO_AP), ("ap", "mbot-0000-AP", 5220))
        self.assertEqual(status.parse_iw_info(""), ("", "", 0))

    def test_iw_link(self):
        self.assertEqual(status.parse_iw_link(IW_LINK), ("MWireless", 5180, -61))
        self.assertEqual(status.parse_iw_link("Not connected.\n"), ("", 0, 0))

    def test_port_listening(self):
        self.assertTrue(status.port_listening([PROC_TCP], 8765))
        self.assertTrue(status.port_listening([PROC_TCP], 22))
        self.assertFalse(status.port_listening([PROC_TCP], 8080))

    def test_signal_bars(self):
        self.assertEqual([status.signal_bars(v) for v in (0, -50, -60, -70, -80, -90)], [0, 4, 3, 2, 1, 0])

    def test_uptime_format(self):
        self.assertEqual(status.format_uptime(59), "0m")
        self.assertEqual(status.format_uptime(4380), "1h13m")
        self.assertEqual(status.format_uptime(2 * 86400 + 3 * 3600), "2d03h")

    def test_status_properties(self):
        st = status.Status(ip="192.168.3.1")
        self.assertTrue(st.hotspot)
        self.assertEqual(status.Status(freq_mhz=2437).band, "2.4G")
        self.assertEqual(status.Status(freq_mhz=5180).band, "5G")
        self.assertFalse(status.Status().firmware_talking)


class ReaderTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith("linux"), "reads /proc and /sys")
    def test_poll_on_this_machine(self):
        reader = status.StatusReader()
        st = reader.poll(0.0)
        st = reader.poll(1.5)
        self.assertGreater(st.uptime_s, 0)
        self.assertGreaterEqual(st.mem_pct, 0)
        self.assertGreaterEqual(st.disk_pct, 0)
        self.assertTrue(st.hostname)


if __name__ == "__main__":
    unittest.main()
