"""Which screen to show, and when.

    boot    from service start until the robot has an IP address (at most BOOT_MAX_S)
    main    robot name, IP address, network, READY with battery
    health  battery gauge, temperature, CPU, RAM, disk (animated when it appears)
    drive   the MBot drives in, scans with the LiDAR and drives off (animation on only)
    alert   one card per active problem, only while the problem lasts

Rotation: main, health, drive, then the alert cards (if any), and again.

Short notices (a new network, a problem that went away, the Pico plugged back in) are
shown on the status line of the main screen for NOTICE_S seconds.

Times are seconds since the service started, so screens can be tested and previewed.
"""

from .alerts import AlertEngine
from .render import DRIVE_S

BOOT_MIN_S = 4.0       # the assembly animation needs about 3.5 s
BOOT_MAX_S = 150.0     # show the main screen anyway after this, with or without an IP
MAIN_S = 8.0           # main screen time per cycle
HEALTH_S = 5.0         # health page time per cycle
ALERT_S = 4.0          # time per alert card
NOTICE_S = 6.0
STARTUP_GRACE_S = 120  # before this uptime "no data yet" means "still starting"


class Pager:
    def __init__(self, renderer, animation=True, engine=None):
        self.r = renderer
        self.animation = animation
        self.engine = engine or AlertEngine()
        self.phase = "boot"
        self.page = "boot"
        self.alerts = []
        self._cycle_start = 0.0
        self._notice = ("", 0.0)
        self._last_net = None
        self._pico_seen = None
        self._page_since = 0.0

    def battery(self, st):
        """Battery voltage for display: the 30 s median once there is enough data, else -1."""
        if not st.firmware_talking:
            return -1.0
        return self.engine.battery_median if self.engine.battery_median >= 0 else st.battery_v

    def summary(self, st):
        """Status line text while nothing is wrong."""
        if st.firmware_talking:
            return "READY", "%.1f V" % self.battery(st)
        if st.uptime_s < STARTUP_GRACE_S:
            return "Starting", ""
        return "Online", ""

    def notice(self, t, text):
        self._notice = (text, t + NOTICE_S)

    def _track_events(self, st, t):
        net = (st.ip, st.ssid if st.ip else "")
        if self._last_net is not None and net != self._last_net and st.ip and self.phase != "boot":
            if st.hotspot:
                self.notice(t, "Hotspot on")
            elif st.ssid:
                self.notice(t, "Connected: " + st.ssid)
            else:
                self.notice(t, "New IP address")
        self._last_net = net
        if self._pico_seen is False and st.pico_present and self.phase != "boot":
            self.notice(t, "Pico connected")
        self._pico_seen = st.pico_present
        while self.engine.events:
            _, text = self.engine.events.popleft()
            self.notice(t, text)

    def current(self, st, t):
        """Update the state for time t and return the screen name: boot, main, health,
        drive or alert:<n>."""
        self.alerts = self.engine.update(st, t)
        self._track_events(st, t)
        if self.phase == "boot":
            if (st.ip and t >= BOOT_MIN_S) or t >= BOOT_MAX_S:
                self.phase = "run"
                self._cycle_start = t
            else:
                return "boot"
        drive = DRIVE_S if self.animation else 0.0
        cycle = MAIN_S + HEALTH_S + drive + ALERT_S * len(self.alerts)
        pos = (t - self._cycle_start) % cycle
        if pos < MAIN_S:
            return "main"
        if pos < MAIN_S + HEALTH_S:
            self._page_since = pos - MAIN_S
            return "health"
        if pos < MAIN_S + HEALTH_S + drive:
            self._page_since = pos - MAIN_S - HEALTH_S
            return "drive"
        return "alert:%d" % int((pos - MAIN_S - HEALTH_S - drive) // ALERT_S)

    def frame(self, st, t):
        name = self.current(st, t)
        self.page = name
        if name == "boot":
            return self.r.boot(st, t, animate=self.animation)
        if name == "health":
            return self.r.health(st, t, self._page_since, self.battery(st), animate=self.animation)
        if name == "drive":
            return self.r.drive(st, t, self._page_since, self.battery(st))
        if name.startswith("alert:"):
            i = min(int(name.split(":")[1]), len(self.alerts) - 1)
            return self.r.alert_card(st, t, self.alerts[i], i, len(self.alerts))
        if self.alerts:
            return self.r.main(st, t, "", alert=self.alerts[0], more=len(self.alerts) - 1)
        text, until = self._notice
        if text and t < until:
            return self.r.main(st, t, text)
        status, right = self.summary(st)
        return self.r.main(st, t, status, right)
