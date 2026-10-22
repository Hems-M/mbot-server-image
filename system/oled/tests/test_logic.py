"""Alert rules (no false alarms, real problems raised and cleared), config, page choice."""

import os
import sys
import tempfile
import unittest
from dataclasses import replace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mbot_oled import alerts, battery, config, fan  # noqa: E402
from mbot_oled.status import Status  # noqa: E402

try:
    from mbot_oled import pages
    from mbot_oled.render import Renderer
    HAVE_PIL = True
except ImportError:  # Pillow missing on this machine
    HAVE_PIL = False

GOOD = Status(hostname="mbot-AM-team6-johndoe", ip="35.3.12.104", iface="wlan0",
              wifi_mode="station", ssid="MWireless", freq_mhz=5180, signal_dbm=-60,
              uptime_s=600, cpu_pct=10, mem_pct=30, temp_c=50, disk_pct=40,
              pico_present=True, agent_active=True, ros_available=True, battery_v=11.9)


def run(engine, status_at, start, seconds, step=1.0):
    """Feed one status per step; return the alert keys active at the end."""
    t = start
    active = []
    while t <= start + seconds + 1e-9:
        active = engine.update(status_at(t), t)
        t += step
    return [a.key for a in active]


class AlertTests(unittest.TestCase):
    def test_healthy_robot_never_alerts(self):
        e = alerts.AlertEngine()
        self.assertEqual(run(e, lambda t: replace(GOOD, uptime_s=600 + t), 0, 600), [])

    def test_boot_does_not_alert(self):
        # Fresh boot: no IP, no Pico, no agent, no data yet. Nothing may be reported.
        e = alerts.AlertEngine()
        booting = lambda t: replace(GOOD, uptime_s=t, ip="", pico_present=t > 20,
                                    agent_active=t > 25, battery_v=11.9 if t > 30 else -1.0)
        self.assertEqual(run(e, booting, 0, 44), [])

    def test_short_pico_dropout_is_ignored(self):
        # Flashing firmware re-enumerates the Pico for a few seconds.
        e = alerts.AlertEngine()
        flash = lambda t: replace(GOOD, pico_present=not (5 <= t < 15), agent_active=not (5 <= t < 18),
                                  battery_v=-1.0 if 5 <= t < 20 else 11.9)
        self.assertEqual(run(e, flash, 0, 60), [])

    def test_pico_unplugged_is_reported_and_clears(self):
        e = alerts.AlertEngine()
        gone = lambda t: replace(GOOD, pico_present=False, agent_active=False, battery_v=-1.0)
        self.assertEqual(run(e, gone, 0, 25), ["pico"])
        back = run(e, lambda t: GOOD, 26, 5)
        self.assertEqual(back, [])
        self.assertIn("Resolved: Pico not connected", [text for _, text in e.events])

    def test_no_agent_or_firmware_alert_without_pico(self):
        e = alerts.AlertEngine()
        gone = lambda t: replace(GOOD, pico_present=False, agent_active=False, battery_v=-1.0)
        self.assertNotIn("agent", run(e, gone, 0, 120))
        self.assertNotIn("firmware", run(e, gone, 121, 60))

    def test_firmware_silent(self):
        e = alerts.AlertEngine()
        silent = lambda t: replace(GOOD, battery_v=-1.0)
        self.assertEqual(run(e, silent, 0, 15), [])
        self.assertEqual(run(e, silent, 16, 10), ["firmware"])

    def test_agent_restarting_is_ignored_but_stopped_is_reported(self):
        e = alerts.AlertEngine()
        flapping = lambda t: replace(GOOD, agent_active=int(t) % 4 != 0)
        self.assertEqual(run(e, flapping, 0, 120), [])
        stopped = lambda t: replace(GOOD, agent_active=False, battery_v=-1.0)
        self.assertIn("agent", run(e, stopped, 200, 35))

    def test_battery_sag_is_ignored(self):
        # Motors starting pull the voltage down for a few seconds.
        e = alerts.AlertEngine()
        sag = lambda t: replace(GOOD, battery_v=8.4 if int(t) % 10 < 3 else 11.8)
        self.assertEqual(run(e, sag, 0, 300, step=0.2), [])

    def test_battery_low_reported(self):
        e = alerts.AlertEngine()
        low = lambda t: replace(GOOD, battery_v=8.6)
        keys = run(e, low, 0, 60, step=0.5)
        self.assertEqual(keys, ["battery"])
        self.assertEqual(e.update(low(61), 61)[0].title, "Battery low")

    def test_battery_wiring(self):
        for volts, title in ((0.3, "Check power jumper"), (4.8, "Motor power is off")):
            e = alerts.AlertEngine()
            run(e, lambda t, v=volts: replace(GOOD, battery_v=v), 0, 40, step=0.5)
            self.assertEqual(e.update(replace(GOOD, battery_v=volts), 41)[0].title, title)

    def test_battery_needs_enough_samples(self):
        e = alerts.AlertEngine()
        self.assertEqual(run(e, lambda t: replace(GOOD, battery_v=0.2), 0, 30, step=5), [])

    def test_single_undervoltage_blip_is_ignored(self):
        e = alerts.AlertEngine()
        blip = lambda t: replace(GOOD, undervolt_now=(int(t) == 10))
        self.assertEqual(run(e, blip, 0, 120), [])

    def test_repeated_undervoltage_reported_then_clears(self):
        e = alerts.AlertEngine()
        repeated = lambda t: replace(GOOD, undervolt_now=(int(t) % 10 == 0))
        self.assertEqual(run(e, repeated, 0, 40), ["power"])
        self.assertEqual(run(e, lambda t: GOOD, 41, 125), [])

    def test_no_network(self):
        e = alerts.AlertEngine()
        offline = lambda t: replace(GOOD, ip="", uptime_s=100 + t)
        self.assertEqual(run(e, offline, 0, 20), [])
        self.assertEqual(run(e, offline, 21, 15), ["no_network"])

    def test_resources(self):
        e = alerts.AlertEngine()
        full = lambda t: replace(GOOD, disk_pct=96, temp_c=83, mem_pct=97)
        self.assertEqual(sorted(run(e, full, 0, 40)), ["disk", "hot", "memory"])

    def test_errors_sorted_first(self):
        e = alerts.AlertEngine()
        bad = lambda t: replace(GOOD, disk_pct=96, undervolt_now=True)
        run(e, bad, 0, 20)
        self.assertEqual(e.update(bad(21), 21)[0].severity, alerts.ERROR)

    def test_current_problems_without_delay(self):
        self.assertEqual(alerts.current_problems(GOOD), [])
        keys = [a.key for a in alerts.current_problems(replace(GOOD, pico_present=False, agent_active=False))]
        self.assertEqual(keys, ["pico"])

    def test_texts_are_short(self):
        st = replace(GOOD, battery_v=8.6, temp_c=85, disk_pct=99, mem_pct=99, ip="",
                     uptime_s=1000, undervolt_now=True)
        sig = alerts.Signals(battery_median=8.6, undervolt_events=5)
        for rule in alerts.RULES:
            a = rule.check(st, sig) or rule.check(replace(st, pico_present=True, agent_active=False), sig)
            if a:
                self.assertLessEqual(len(a.title), 20, a.title)
                for line in a.detail:
                    self.assertLessEqual(len(line), 26, line)


class BatteryStateTests(unittest.TestCase):
    def test_words(self):
        self.assertEqual(alerts.battery_state(11.9), "")
        self.assertEqual(alerts.battery_state(8.6), "low")
        self.assertEqual(alerts.battery_state(5.0), "motor power off")
        self.assertEqual(alerts.battery_state(0.4), "no jumper")
        self.assertEqual(alerts.battery_state(-1.0), "")


class FanTests(unittest.TestCase):
    def make_hwmon(self, root, name, pwm=None, rpm=None, n=2):
        d = os.path.join(root, "hwmon%d" % n)
        os.makedirs(d)
        for f, v in (("name", name), ("pwm1", pwm), ("fan1_input", rpm)):
            if v is not None:
                with open(os.path.join(d, f), "w") as out:
                    out.write("%s\n" % v)
        return d

    def test_find_and_read(self):
        with tempfile.TemporaryDirectory() as root:
            self.make_hwmon(root, "cpu_thermal", n=0)
            d = self.make_hwmon(root, "pwmfan", pwm=75, rpm=3120)
            self.assertEqual(fan.find_fan(root), d)
            self.assertEqual(fan.read_fan(d), (75, 3120))
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(fan.find_fan(root), "")
            self.assertEqual(fan.read_fan(""), (-1, -1))

    def test_stopped_fan(self):
        self.assertIsNotNone(fan.fan_problem([(75, 0), (75, 0)]))
        self.assertIsNone(fan.fan_problem([(75, 0), (75, 2900)]))   # spinning up
        self.assertIsNone(fan.fan_problem([(0, 0), (0, 0)]))         # off: the Pi is cool
        self.assertIsNone(fan.fan_problem([(75, 0)]))                # one reading is not enough
        self.assertIsNone(fan.fan_problem([(-1, -1), (-1, -1)]))     # no fan device

    def test_never_on_the_oled(self):
        # The OLED uses current_problems and the alert engine; neither knows the fan.
        st = Status(pico_present=True, agent_active=True, uptime_s=600)
        self.assertNotIn("fan", [a.key for a in alerts.current_problems(st)])

    def test_text(self):
        self.assertIn("rpm", fan.fan_text(75, 3120))
        self.assertIn("off", fan.fan_text(0, 0))
        self.assertIn("not found", fan.fan_text(-1, -1))


class BatteryListenerTests(unittest.TestCase):
    def test_stale_value(self):
        b = battery.BatteryListener()
        self.assertEqual(b.volts(100.0), -1.0)
        b._volts, b._stamp = 12.1, 100.0
        self.assertEqual(b.volts(101.0), 12.1)
        self.assertEqual(b.volts(100.0 + battery.STALE_AFTER_S + 0.1), -1.0)


class ConfigTests(unittest.TestCase):
    TEMPLATE = ("mbot_hostname=mbot-0000\nmbot_ap_password=iloverobots\n"
                "new_wifi_ssid=HomeWifiSSID\nnew_wifi_password=HomeWifiPassword\nautostart=run\n")

    def test_template_means_animation_on(self):
        values = config.parse_config(self.TEMPLATE)
        self.assertEqual(values["mbot_hostname"], "mbot-0000")
        self.assertTrue(config.animation_enabled({**config.DEFAULTS, **values}))

    def test_off(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write(self.TEMPLATE + "oled_animation = off\n")
        try:
            self.assertFalse(config.animation_enabled(config.read_config(f.name)))
        finally:
            os.unlink(f.name)

    def test_missing_file(self):
        self.assertTrue(config.animation_enabled(config.read_config("/nonexistent/mbot_config.txt")))


@unittest.skipUnless(HAVE_PIL, "needs Pillow")
class PagerTests(unittest.TestCase):
    def test_boot_then_main_only(self):
        p = pages.Pager(Renderer())
        no_ip = replace(GOOD, ip="", uptime_s=10)
        self.assertEqual(p.current(no_ip, 0.0), "boot")
        self.assertEqual(p.current(no_ip, 30.0), "boot")
        seen = {p.current(GOOD, 31.0 + i * 0.5) for i in range(240)}
        self.assertEqual(seen, {"main", "health", "drive"})

    def test_no_drive_page_without_animation(self):
        p = pages.Pager(Renderer(), animation=False)
        p.current(GOOD, 5.0)
        seen = {p.current(GOOD, 5.0 + i * 0.5) for i in range(240)}
        self.assertEqual(seen, {"main", "health"})

    def test_boot_gives_up_without_network(self):
        p = pages.Pager(Renderer())
        no_ip = replace(GOOD, ip="", uptime_s=10)
        self.assertEqual(p.current(no_ip, pages.BOOT_MAX_S + 1), "main")

    def test_alert_cards_alternate_with_main(self):
        p = pages.Pager(Renderer())
        p.current(GOOD, 5.0)
        gone = replace(GOOD, pico_present=False, agent_active=False, battery_v=-1.0)
        seen = [p.current(gone, 5.0 + i * 0.5) for i in range(120)]
        self.assertIn("alert:0", seen)
        self.assertIn("main", seen[-20:])

    def test_summary(self):
        p = pages.Pager(Renderer())
        status, right = p.summary(GOOD)
        self.assertEqual(status, "READY")
        self.assertTrue(right.endswith("11.9 V"), right)
        self.assertEqual(p.summary(replace(GOOD, battery_v=-1.0, uptime_s=30))[0], "Starting")

    def test_network_change_notice(self):
        p = pages.Pager(Renderer())
        hotspot = replace(GOOD, ip="192.168.3.1", wifi_mode="ap", ssid="mbot-0000-AP")
        p.current(hotspot, 5.0)
        p.current(hotspot, 6.0)
        p.current(GOOD, 7.0)
        self.assertEqual(p._notice[0], "Connected: MWireless")


if __name__ == "__main__":
    unittest.main()
