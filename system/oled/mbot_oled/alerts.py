"""Problem detection for the OLED and for mbot-status.

The OLED must never cry wolf. Every rule therefore needs its condition to hold without a
break for `raise_after` seconds before it is shown, and to be false for `clear_after`
seconds before it goes away. Short glitches (the Pico re-enumerating after a flash, the
agent restarting, the battery voltage sagging while the motors start) never reach the
screen. Battery rules use the median of the last 30 s of readings for the same reason.

Each alert has a short title and one or two lines that say what to do.
"""

import statistics
from collections import deque
from dataclasses import dataclass

ERROR = "error"
WARNING = "warning"
SEVERITY_ORDER = {ERROR: 0, WARNING: 1}

BATTERY_WINDOW_S = 30.0
BATTERY_MIN_SAMPLES = 20
UNDERVOLT_WINDOW_S = 60.0
UNDERVOLT_MIN_EVENTS = 3

# Battery voltage ranges (the old LCM OLED service used the same ones).
JUMPER_MISSING_BELOW = 1.5
UNPOWERED_RANGE = (3.5, 5.5)
LOW_RANGE = (7.0, 9.0)


def battery_state(volts):
    """Short word for a battery voltage: "", "low", "motor power off", "no jumper"."""
    if volts < 0:
        return ""
    if volts < JUMPER_MISSING_BELOW:
        return "no jumper"
    if UNPOWERED_RANGE[0] <= volts <= UNPOWERED_RANGE[1]:
        return "motor power off"
    if LOW_RANGE[0] <= volts < LOW_RANGE[1]:
        return "low"
    return ""


@dataclass(frozen=True)
class Alert:
    key: str
    severity: str
    title: str          # alert card title
    detail: tuple = ()  # up to two lines: what to do
    short: str = ""     # status line of the main screen

    @property
    def label(self):
        return self.short or self.title


@dataclass
class Signals:
    """Values derived from the recent history, not from one status sample."""
    battery_median: float = -1.0
    undervolt_events: int = 0


def _battery_alerts(st, sig):
    v = sig.battery_median
    if v < 0:
        return None
    if v < JUMPER_MISSING_BELOW:
        return Alert("battery", WARNING, "Check power jumper",
                     ("Battery reads 0 V. Fit the", "jumper cap on the board."), "Check jumper")
    if UNPOWERED_RANGE[0] < v < UNPOWERED_RANGE[1]:
        return Alert("battery", WARNING, "Motor power is off",
                     ("Barrel plug unplugged", "or power bank switched off."), "Motor power off")
    if LOW_RANGE[0] <= v < LOW_RANGE[1]:
        return Alert("battery", WARNING, "Battery low",
                     ("%.1f V. Charge the power" % v, "bank soon."), "Battery low %.1f V" % v)
    return None


@dataclass(frozen=True)
class Rule:
    key: str
    raise_after: float
    clear_after: float
    check: object  # (status, signals) -> Alert or None


RULES = (
    Rule("no_network", 30, 5, lambda st, sig: Alert(
        "no_network", ERROR, "No network",
        ("No Wi-Fi and no hotspot.", "Check mbot_config.txt."), "No network")
        if st.uptime_s >= 90 and not st.ip else None),
    Rule("power", 0, 60, lambda st, sig: Alert(
        "power", ERROR, "Pi power too low",
        ("Check the Pi power cable", "and the power bank."), "Pi power low")
        if sig.undervolt_events >= UNDERVOLT_MIN_EVENTS else None),
    Rule("agent", 30, 5, lambda st, sig: Alert(
        "agent", ERROR, "ROS link stopped",
        ("micro-ROS agent is not", "running. Run mbot-status."), "ROS link stopped")
        if st.pico_present and not st.agent_active else None),
    Rule("pico", 20, 3, lambda st, sig: Alert(
        "pico", WARNING, "Pico not connected",
        ("Check the USB-C cable", "from the Pi to the Pico."), "No Pico")
        if st.uptime_s >= 45 and not st.pico_present else None),
    Rule("firmware", 20, 3, lambda st, sig: Alert(
        "firmware", WARNING, "No data from Pico",
        ("Flash the ROS firmware:", "mbot_classic_ros.uf2"), "No Pico data")
        if (st.uptime_s >= 90 and st.pico_present and st.agent_active
            and st.ros_available and not st.firmware_talking) else None),
    Rule("battery", 10, 10, _battery_alerts),
    Rule("hot", 30, 30, lambda st, sig: Alert(
        "hot", WARNING, "Pi running hot",
        ("CPU at %d °C." % round(st.temp_c), "Check the fan and airflow."),
        "Pi hot %d \u00b0C" % round(st.temp_c))
        if st.temp_c >= 80 else None),
    Rule("disk", 10, 10, lambda st, sig: Alert(
        "disk", WARNING, "Disk almost full",
        ("%d %% used. Delete old" % round(st.disk_pct), "bags and build folders."),
        "Disk %d %% full" % round(st.disk_pct))
        if st.disk_pct >= 92 else None),
    Rule("memory", 20, 10, lambda st, sig: Alert(
        "memory", WARNING, "Memory almost full",
        ("Stop programs and nodes", "you are not using."), "Memory full")
        if st.mem_pct >= 95 else None),
)


def current_problems(st, sig=None):
    """Alerts whose condition holds right now, without any debouncing (for mbot-status)."""
    sig = sig or Signals(battery_median=st.battery_v,
                         undervolt_events=UNDERVOLT_MIN_EVENTS if st.undervolt_now else 0)
    found = [a for a in (rule.check(st, sig) for rule in RULES) if a]
    return sorted(found, key=lambda a: SEVERITY_ORDER[a.severity])


class AlertEngine:
    """Feeds status samples through the rules with raise and clear delays."""

    def __init__(self):
        self._battery = deque()     # (time, volts)
        self._undervolt = deque()   # times an under-voltage sample was seen
        self._true_since = {}       # rule key -> time the condition became true
        self._false_since = {}      # rule key -> time the condition became false
        self._active = {}           # rule key -> Alert currently shown
        self.events = deque(maxlen=8)  # (time, text) for short notices on screen
        self.battery_median = -1.0     # smoothed voltage for display, -1 if not enough data

    def signals(self, st, now):
        if st.battery_v >= 0:
            self._battery.append((now, st.battery_v))
        while self._battery and now - self._battery[0][0] > BATTERY_WINDOW_S:
            self._battery.popleft()
        if st.undervolt_now:
            self._undervolt.append(now)
        while self._undervolt and now - self._undervolt[0] > UNDERVOLT_WINDOW_S:
            self._undervolt.popleft()
        median = -1.0
        if len(self._battery) >= BATTERY_MIN_SAMPLES:
            median = statistics.median(v for _, v in self._battery)
        self.battery_median = median
        return Signals(battery_median=median, undervolt_events=len(self._undervolt))

    def update(self, st, now):
        """Evaluate every rule; returns the active alerts, most severe first."""
        sig = self.signals(st, now)
        for rule in RULES:
            alert = rule.check(st, sig)
            if alert:
                self._false_since.pop(rule.key, None)
                start = self._true_since.setdefault(rule.key, now)
                if rule.key in self._active or now - start >= rule.raise_after:
                    self._active[rule.key] = alert  # refresh text (voltage, temperature)
            else:
                self._true_since.pop(rule.key, None)
                if rule.key in self._active:
                    start = self._false_since.setdefault(rule.key, now)
                    if now - start >= rule.clear_after:
                        cleared = self._active.pop(rule.key)
                        self._false_since.pop(rule.key, None)
                        self.events.append((now, "Resolved: " + cleared.title))
        return sorted(self._active.values(), key=lambda a: SEVERITY_ORDER[a.severity])
