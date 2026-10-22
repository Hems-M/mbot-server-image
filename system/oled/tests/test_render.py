"""Every screen renders at the right size and keeps text inside the screen."""

import os
import sys
import unittest
from dataclasses import replace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from mbot_oled import alerts, preview, sprites
    from mbot_oled.render import BYE_S, DRIVE_S, HEIGHT, STATUS_Y, WIDTH, Renderer
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


@unittest.skipUnless(HAVE_PIL, "needs Pillow")
class RenderTests(unittest.TestCase):
    def setUp(self):
        self.r = Renderer()
        base = preview.CAMPUS
        self.statuses = [
            base, preview.HOME, preview.HOTSPOT,
            replace(base, ip="", wifi_mode="", ssid=""),
            replace(base, hostname="m" * 40, ssid="S" * 32, ip="255.255.255.255"),
            replace(base, ip="10.0.0.5", iface="eth0", wifi_mode="", ssid="", wired=True),
            replace(base, battery_v=-1, ros_available=False, release=""),
        ]
        self.alerts = [
            alerts.Alert("pico", alerts.WARNING, "Pico not connected", ("Check the USB-C cable", "from the Pi to the Pico.")),
            alerts.Alert("power", alerts.ERROR, "Pi power too low", ("Check the Pi power cable", "and the power bank.")),
        ]

    def check(self, img):
        self.assertEqual(img.size, (WIDTH, HEIGHT))
        self.assertEqual(img.mode, "1")
        self.assertIsNotNone(img.getbbox(), "screen is blank")

    def test_all_screens(self):
        for st in self.statuses:
            for t in (0.0, 1.3, 7.9, 301.0):
                self.check(self.r.main(st, t, "READY", "11.9 V"))
                self.check(self.r.main(st, t, "", alert=self.alerts[0], more=1))
                for i, a in enumerate(self.alerts):
                    self.check(self.r.alert_card(st, t, a, i, len(self.alerts)))
                self.check(self.r.health(st, t, t, 11.9))
                self.check(self.r.health(st, t, 0.1, -1.0))
                self.check(self.r.boot(st, t, animate=True))
                self.check(self.r.boot(st, t, animate=False))
                self.check(self.r.drive(st, t, t % DRIVE_S, 11.9))
                self.check(self.r.drive(st, t, t % DRIVE_S, -1.0))
                self.check(self.r.bye(st, t % BYE_S))
            self.check(self.r.shutdown(st))

    def test_network_line_is_the_ssid_only(self):
        self.assertEqual(self.r.network_text(preview.CAMPUS), "MWireless")
        self.assertEqual(self.r.network_text(preview.HOME), "HomeWifi")

    def test_status_line_separator_on_main(self):
        img = self.r.main(preview.CAMPUS, 0.0, "READY", "11.9 V")
        self.assertEqual(img.crop((0, STATUS_Y, WIDTH, STATUS_Y + 1)).getbbox(), (0, 0, WIDTH, 1))

    def test_problem_inverts_status_line(self):
        img = self.r.main(preview.CAMPUS, 0.0, "", alert=self.alerts[0])
        lit = sum(img.crop((0, STATUS_Y + 1, WIDTH, HEIGHT)).getdata())
        self.assertGreater(lit, WIDTH * 8)  # mostly white

    def test_ip_shown_in_every_running_screen(self):
        # The IP is drawn in the body of the main screen and in the status line of cards.
        main = self.r.main(preview.CAMPUS, 0.0, "READY")
        self.assertIsNotNone(main.crop((0, 14, WIDTH, 34)).getbbox())
        card = self.r.alert_card(preview.CAMPUS, 0.0, self.alerts[0], 0, 1)
        self.assertIsNotNone(card.crop((0, STATUS_Y + 1, WIDTH, HEIGHT)).getbbox())
        # Health and drive pages: the status line starts with the IP, the same pixels
        # as the IP-only status line of an alert card.
        ip_only = self.r.alert_card(preview.CAMPUS, 1.0, self.alerts[0], 0, 1)
        ip_box = (0, STATUS_Y + 1, 70, HEIGHT)
        for img in (self.r.health(preview.CAMPUS, 1.0, 2.0, 11.9),
                    self.r.drive(preview.CAMPUS, 1.0, 2.0, 11.9)):
            self.assertEqual(img.crop(ip_box).tobytes(), ip_only.crop(ip_box).tobytes())

    def test_long_ip_is_never_cut(self):
        st = replace(preview.CAMPUS, ip="255.255.255.255", uptime_s=9 * 86400)
        img = self.r.health(st, 1.0, 2.0, 11.9)
        ref, d = self.r.new()
        self.r.status_line(ref, d, 1.0, st.ip)
        box = (0, STATUS_Y, WIDTH - 6, HEIGHT)
        self.assertEqual(img.crop(box).tobytes(), ref.crop(box).tobytes())

    def test_error_flashes_warning_does_not(self):
        warn, err = self.alerts
        lit = lambda img: sum(img.crop((0, STATUS_Y + 1, WIDTH, HEIGHT)).getdata())
        self.assertGreater(lit(self.r.main(preview.CAMPUS, 0.9, "", alert=warn)), WIDTH * 8)
        self.assertGreater(lit(self.r.main(preview.CAMPUS, 0.5, "", alert=err)), WIDTH * 8)
        self.assertLess(lit(self.r.main(preview.CAMPUS, 0.9, "", alert=err)), WIDTH * 4)

    def test_text_fits(self):
        long = "x" * 60
        self.assertLessEqual(self.r.width(self.r.body, self.r.fit(long, self.r.body, 100)), 100)

    def test_boot_animation_moves(self):
        st = replace(preview.HOTSPOT, ip="")
        self.assertNotEqual(self.r.boot(st, 1.0).tobytes(), self.r.boot(st, 1.4).tobytes())

    def test_drive_animation_moves(self):
        frames = {self.r.drive(preview.CAMPUS, s, s, 11.9).tobytes() for s in (0.4, 1.0, 2.4, 3.0, 4.6, 5.4)}
        self.assertEqual(len(frames), 6)

    def test_drive_scan_draws_walls(self):
        # While scanning, the walls at both screen edges appear.
        img = self.r.drive(preview.CAMPUS, 3.5, 3.5, 11.9)
        self.assertIsNotNone(img.crop((0, 0, 3, STATUS_Y - 4)).getbbox())
        self.assertIsNotNone(img.crop((WIDTH - 3, 0, WIDTH, STATUS_Y - 4)).getbbox())
        moving = self.r.drive(preview.CAMPUS, 0.5, 0.5, 11.9)
        self.assertIsNone(moving.crop((WIDTH - 3, 0, WIDTH, STATUS_Y - 4)).getbbox())

    def test_bye_ends_on_the_shutdown_frame(self):
        st = preview.CAMPUS
        self.assertNotEqual(self.r.bye(st, 0.0).tobytes(), self.r.bye(st, 1.0).tobytes())
        self.assertEqual(self.r.bye(st, BYE_S).tobytes(), self.r.shutdown(st).tobytes())
        self.assertEqual(self.r.bye(st, BYE_S - 0.05).tobytes(), self.r.shutdown(st).tobytes())

    def test_main_screen_is_static(self):
        # Nothing on the main screen moves except the heartbeat pixel and long names.
        st = replace(preview.HOME, hostname="mbot-07")
        a = self.r.main(st, 10.2, "READY", "11.9 V").tobytes()
        b = self.r.main(st, 10.7, "READY", "11.9 V").tobytes()
        self.assertEqual(a, b)

    def test_low_battery_is_marked(self):
        # Voltage only: a low voltage shows "low" inverted in the header, no percentage.
        ok = self.r.health(preview.CAMPUS, 1.0, 2.0, 11.9)
        low = self.r.health(preview.CAMPUS, 1.0, 2.0, 8.6)
        lit = lambda img: sum(img.crop((90, 0, WIDTH, 11)).getdata())
        self.assertGreater(lit(low), lit(ok) * 2)

    def test_health_fills_in(self):
        start = self.r.health(preview.CAMPUS, 0.0, 0.0, 11.9)
        done = self.r.health(preview.CAMPUS, 2.0, 2.0, 11.9)
        self.assertNotEqual(start.tobytes(), done.tobytes())
        lit = lambda img: sum(img.crop((0, 40, WIDTH, 46)).getdata())
        self.assertGreater(lit(done), lit(start))  # bars are fuller at the end

    def test_assembly_finishes(self):
        parts, _, done = sprites.assembly(0.0)
        self.assertEqual(parts, ["wheel"])
        self.assertFalse(done)
        parts, drops, done = sprites.assembly(10.0)
        self.assertEqual(tuple(parts), sprites.PARTS)
        self.assertTrue(done)
        self.assertTrue(all(v == 0 for v in drops.values()))


if __name__ == "__main__":
    unittest.main()
