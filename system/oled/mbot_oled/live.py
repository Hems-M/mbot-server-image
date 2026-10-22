"""mbot health --live: the health report as a screen that updates every second.

    mbot health --live     refresh every second until Ctrl+C

Shows battery voltage, system (with the Pi 5 fan), robot and network now, the current problems (same rules as
mbot health and the OLED), and an event log of what changed while it runs: the Pico
plugged in or out, the LiDAR or camera starting or stopping, a new IP, a problem
appearing or going away.

The screen is drawn by frame() from plain values, so it can be tested without a robot.
"""

import os
import shutil
import sys
import time
from collections import deque

from .alerts import ERROR, battery_state, current_problems
from .battery import BatteryListener
from .fan import fan_problem, fan_text, find_fan, read_fan
from .status import StatusReader, format_uptime, signal_bars

REFRESH_S = 1.0
TOPICS_EVERY_S = 2.0      # the ROS graph query is cheaper than a status poll, but not free
EVENTS_SHOWN = 8
TOPICS = (("/odom", "Odometry"), ("/scan", "LiDAR"), ("/camera/image_raw", "Camera"))


def snapshot(st, topics, problems):
    """The values whose changes are reported in the event log."""
    return {
        "ip": st.ip,
        "net": st.ssid if st.ip else "",
        "hotspot": bool(st.ip and st.hotspot),
        "pico": st.pico_present,
        "agent": st.agent_active,
        "firmware": st.firmware_talking,
        "viz": st.viz_running,
        "undervolt": st.undervolt_now,
        "topics": {t: topics.get(t, -1) > 0 for t, _ in TOPICS},
        "problems": {a.key: a.title for a in problems},
    }


def changes(old, new):
    """Event log lines for what changed between two snapshots (oldest first)."""
    if old is None:
        return ["Started watching"]
    out = []
    if new["ip"] != old["ip"]:
        if not new["ip"]:
            out.append("Lost the IP address")
        elif new["hotspot"]:
            out.append("Hotspot on, IP %s" % new["ip"])
        else:
            out.append("New IP %s (%s)" % (new["ip"], new["net"] or "wired"))
    elif new["net"] != old["net"] and new["net"]:
        out.append("Connected to %s" % new["net"])
    for key, on, off in (("pico", "Pico connected", "Pico disconnected"),
                         ("agent", "micro-ROS agent started", "micro-ROS agent stopped"),
                         ("firmware", "Firmware data arriving", "Firmware data stopped"),
                         ("viz", "Foxglove bridge started", "Foxglove bridge stopped"),
                         ("undervolt", "Pi power too low (under-voltage)", "Pi power back to normal")):
        if new[key] != old[key]:
            out.append(on if new[key] else off)
    for topic, name in TOPICS:
        if new["topics"][topic] != old["topics"][topic]:
            out.append("%s %s %s" % (name, topic, "started" if new["topics"][topic] else "stopped"))
    for key, title in new["problems"].items():
        if key not in old["problems"]:
            out.append("Problem: %s" % title)
    for key, title in old["problems"].items():
        if key not in new["problems"]:
            out.append("Resolved: %s" % title)
    return out


def bar(frac, width, warn, c):
    frac = max(0.0, min(1.0, frac))
    n = int(round(frac * width))
    ink = c["maize"] + c["bold"] if warn else c["green"]
    return "%s%s%s%s%s" % (ink, "█" * n, c["soft"], "░" * (width - n), c["reset"])


def dot(ok, c):
    return "%s●%s" % (c["green"], c["reset"]) if ok else "%s○%s" % (c["soft"], c["reset"])


def frame(st, topics, problems, events, c, fan=(-1, -1), width=78, now_text=""):
    """The screen as a list of lines. fan: (pwm, rpm) of the Pi 5 cooler."""
    lines = []
    head = "  MBOT HEALTH  LIVE   %s  ·  %s  ·  %s" % (st.hostname, st.ip or "no IP", now_text)
    lines.append("%s%s%s%s" % (c["blue_bg"], c["maize"] + c["bold"], head[:width].ljust(width), c["reset"]))

    def label(name):
        return "%s%s%-9s%s" % (c["maize"], c["bold"], name, c["reset"])

    lines.append("")
    if st.firmware_talking:
        state = battery_state(st.battery_v)
        word = "%s%s%s" % (c["maize"] + c["bold"], state, c["reset"]) if state else "%sOK%s" % (c["green"], c["reset"])
        lines.append("%s %6.2f V   %s" % (label("BATTERY"), st.battery_v, word))
    else:
        lines.append("%s %sno data from the Pico%s" % (label("BATTERY"), c["soft"], c["reset"]))

    def gauge(name, value, unit, frac, warn, extra=""):
        shown = "%3d %s" % (round(value), unit) if value >= 0 else "  ? " + unit
        return "%-5s %s  %s%s" % (name, shown.ljust(6), bar(frac if value >= 0 else 0, 30, warn, c), extra)

    load = ""
    try:
        with open("/proc/loadavg", encoding="ascii") as f:
            load = "  load " + " ".join(f.read().split()[:3])
    except OSError:
        pass
    lines.append("%s %s" % (label("SYSTEM"), gauge("CPU", st.cpu_pct, "%", st.cpu_pct / 100.0, False, load)))
    lines.append("%s %s" % (" " * 9, gauge("Temp", st.temp_c, "°C", (st.temp_c - 30) / 55.0, st.temp_c >= 80)))
    lines.append("%s %s" % (" " * 9, gauge("RAM", st.mem_pct, "%", st.mem_pct / 100.0, st.mem_pct >= 95)))
    lines.append("%s %s" % (" " * 9, gauge("Disk", st.disk_pct, "%", st.disk_pct / 100.0, st.disk_pct >= 92)))
    stopped = any(a.key == "fan" for a in problems)
    fan_line = fan_text(*fan)
    lines.append("%s Fan   %s" % (" " * 9, "%s%s%s" % (c["maize"] + c["bold"], fan_line, c["reset"])
                                     if stopped else fan_line))
    if st.power_known:
        power = "%sunder-voltage now%s" % (c["maize"] + c["bold"], c["reset"]) if st.undervolt_now else "OK"
        lines.append("%s Power %s   %sup %s%s" % (" " * 9, power, c["soft"], format_uptime(st.uptime_s), c["reset"]))
    else:
        lines.append("%s %sup %s%s" % (" " * 9, c["soft"], format_uptime(st.uptime_s), c["reset"]))

    lines.append("")
    lines.append("%s %s Pico   %s Agent   %s Firmware data   %s Foxglove" % (
        label("ROBOT"), dot(st.pico_present, c), dot(st.agent_active, c),
        dot(st.firmware_talking, c), dot(st.viz_running, c)))
    lines.append("%s %s" % (" " * 9, "   ".join(
        "%s %s %s" % (dot(topics.get(t, -1) > 0, c), name, t) for t, name in TOPICS)))

    if st.ip and st.wifi_mode == "station":
        net = "%s  ·  %d dBm (%d of 4 bars)" % (st.ssid, st.signal_dbm, signal_bars(st.signal_dbm))
    elif st.ip and st.hotspot:
        net = "Hotspot %s" % st.ssid
    elif st.ip and st.wired:
        net = "Ethernet"
    else:
        net = "%snot connected%s" % (c["maize"] + c["bold"], c["reset"])
    lines.append("%s %s  ·  %s" % (label("NETWORK"), st.ip or "no IP", net))

    lines.append("")
    if problems:
        for i, a in enumerate(problems):
            tag = "ERROR  " if a.severity == ERROR else "WARNING"
            lines.append("%s %s%s %s%s  %s" % (label("PROBLEMS" if i == 0 else ""), c["maize"], "▲", tag,
                                               c["reset"], a.title))
            lines.append("%s           %s%s%s" % (" " * 9, c["soft"], " ".join(a.detail), c["reset"]))
    else:
        lines.append("%s %s✔ none%s" % (label("PROBLEMS"), c["green"], c["reset"]))

    lines.append("")
    lines.append(label("EVENTS"))
    for stamp, text in list(events)[-EVENTS_SHOWN:]:
        lines.append("  %s%s%s  %s" % (c["soft"], stamp, c["reset"], text))
    lines.append("")
    lines.append("%sCtrl+C to quit  ·  refreshes every second  ·  full report: mbot health%s" % (
        c["soft"], c["reset"]))
    return lines


def run(palette):
    """Draw the live screen until Ctrl+C. Returns the exit code."""
    if not sys.stdout.isatty():
        print("mbot health --live needs a terminal. Use mbot health for a report.", file=sys.stderr)
        return 2
    c = palette(not os.environ.get("NO_COLOR"))
    reader = StatusReader()
    fan_dir = find_fan()
    fan = deque(maxlen=3)   # the last 3 readings, a second apart
    reader.poll(time.monotonic())
    bat = BatteryListener(node_name="mbot_status_live_%d" % os.getpid())
    ros_ok = bat.start()
    events = deque(maxlen=50)
    last = None
    topics, topics_at = {}, 0.0
    out = sys.stdout
    out.write("\033[?1049h\033[?25l")  # own screen, no cursor
    try:
        while True:
            now = time.monotonic()
            st = reader.poll(now)
            st.ros_available = ros_ok
            st.battery_v = bat.volts(now)
            if now - topics_at >= TOPICS_EVERY_S:
                topics = {t: bat.publishers(t) for t, _ in TOPICS}
                topics_at = now
            fan.append(read_fan(fan_dir))
            problems = current_problems(st)
            stopped = fan_problem(list(fan)) if len(fan) == fan.maxlen else None
            if stopped:   # mbot health only, never the OLED
                problems.append(stopped)
            snap = snapshot(st, topics, problems)
            for text in changes(last, snap):
                events.append((time.strftime("%H:%M:%S"), text))
            last = snap
            width = min(100, shutil.get_terminal_size((80, 24)).columns - 1)
            lines = frame(st, topics, problems, events, c, fan[-1], width, time.strftime("%H:%M:%S"))
            out.write("\033[H" + "".join(line + "\033[K\n" for line in lines) + "\033[J")
            out.flush()
            time.sleep(max(0.1, REFRESH_S - (time.monotonic() - now)))
    except KeyboardInterrupt:
        pass
    finally:
        out.write("\033[?25h\033[?1049l")
        out.flush()
        bat.stop()
    for stamp, text in events:
        print("%s  %s" % (stamp, text))
    return 0
