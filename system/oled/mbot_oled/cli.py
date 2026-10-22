"""mbot-status (also: mbot health): everything the robot knows about itself, in a terminal.

    mbot-status            full report (about 3 s: it listens to the Pico for a moment)
    mbot-status --brief    problems only
    mbot-status --live     updates every second, with a log of what changed (live.py)

Sections: network, robot, system, services, image, problems.

Uses the same rules as the OLED (alerts.py), without the OLED's delays, so it shows the
state right now. Exit code: 0 no problems, 1 warnings, 2 errors.
"""

import argparse
import logging
import os
import platform
import socket
import struct
import subprocess
import sys
import time

from .alerts import ERROR, JUMPER_MISSING_BELOW, LOW_RANGE, battery_state, current_problems
from .battery import BatteryListener
from .fan import fan_problem, fan_text, find_fan, read_fan
from .status import StatusReader, format_uptime, signal_bars

SERVICES = (
    ("mbot-microros-agent", "link to the Pico"),
    ("mbot-oled", "OLED display"),
    ("mbot-start-network", "Wi-Fi or hotspot at boot"),
    ("NetworkManager", "network"),
    ("ssh.socket", "SSH logins"),
    ("avahi-daemon", "<hostname>.local names"),
)


def palette(enabled):
    """University of Michigan colours (maize and blue), as in the ROBuntu tools."""
    if not enabled:
        return {k: "" for k in ("maize", "blue_bg", "body", "soft", "green", "bold", "reset")}
    return {
        "maize": "\033[38;2;255;203;5m",
        "blue_bg": "\033[48;2;0;39;76m",
        "body": "\033[38;2;248;249;250m",
        "soft": "\033[38;2;190;199;211m",
        "green": "\033[38;5;84m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }


class Printer:
    def __init__(self, color):
        self.c = palette(color)
        self.width = 78

    def banner(self, title, subtitle):
        c = self.c
        line = "  %s  %s" % (title, subtitle)
        print("%s%s%s%s" % (c["blue_bg"], c["maize"] + c["bold"], line.ljust(self.width), c["reset"]))

    def section(self, name):
        c = self.c
        print("\n%s%s%s%s" % (c["maize"], c["bold"], name, c["reset"]))

    def row(self, key, value, hint=""):
        c = self.c
        text = "  %s▌%s %s%-20s%s %s" % (c["maize"], c["reset"], c["soft"], key, c["reset"], value)
        if hint:
            text += "  %s%s%s" % (c["soft"], hint, c["reset"])
        print(text)

    def good(self, text):
        return "%s%s%s" % (self.c["green"], text, self.c["reset"])

    def bad(self, text):
        return "%s%s%s%s" % (self.c["maize"], self.c["bold"], text, self.c["reset"])


def _run(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=3).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _read(path):
    try:
        with open(path, encoding="ascii", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def default_gateway():
    for line in _read("/proc/net/route").splitlines()[1:]:
        parts = line.split()
        if len(parts) > 2 and parts[1] == "00000000":
            return "%s (%s)" % (socket.inet_ntoa(struct.pack("<L", int(parts[2], 16))), parts[0])
    return ""


def internet_reachable():
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=1.5):
            return True
    except OSError:
        return False


def memory_text():
    values = {}
    for line in _read("/proc/meminfo").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            values[parts[0].rstrip(":")] = int(parts[1]) // 1024
    total, avail = values.get("MemTotal", 0), values.get("MemAvailable", 0)
    swap = values.get("SwapTotal", 0) - values.get("SwapFree", 0)
    if not total:
        return "?"
    return "%d %% used  (%d of %d MB, swap %d MB)" % (round(100 * (total - avail) / total), total - avail, total, swap)


def disk_text():
    try:
        fs = os.statvfs("/")
    except OSError:
        return "?"
    total = fs.f_blocks * fs.f_frsize / 1e9
    free = fs.f_bavail * fs.f_frsize / 1e9
    return "%d %% used  (%.1f of %.1f GB, %.1f GB free)" % (round(100 * (total - free) / total), total - free, total, free)


def throttle_flags(reader):
    """Decoded get_throttled bits, now and since boot, or None if unavailable."""
    raw = _read(reader._throttled_file).strip() if reader._throttled_file else ""
    if not raw:
        return None
    v = int(raw, 16)
    return {"undervolt_now": bool(v & 0x1), "throttled_now": bool(v & 0x4),
            "undervolt_boot": bool(v & 0x10000), "throttled_boot": bool(v & 0x40000)}


def collect(wait_s):
    """Read the status twice (CPU use needs two samples) and listen to ROS meanwhile."""
    t0 = time.monotonic()
    reader = StatusReader()
    reader.poll(0.0)
    fan_dir = find_fan()
    fan = [read_fan(fan_dir)]
    bat = BatteryListener(node_name="mbot_status_%d" % os.getpid())
    ros_ok = bat.start()
    # Wait for a battery message (or the deadline); this also gives ROS discovery time.
    while time.monotonic() - t0 < wait_s and (bat.volts() < 0 or time.monotonic() - t0 < 1.5):
        time.sleep(0.2)
    st = reader.poll(10.0)
    st.ros_available = ros_ok
    st.battery_v = bat.volts()
    topics = {name: bat.publishers(name) for name in ("/scan", "/camera/image_raw", "/odom")}
    bat.stop()
    fan.append(read_fan(fan_dir))
    return st, topics, reader, fan


def running(p, count, start_hint):
    if count > 0:
        return p.good("publishing"), ""
    if count == 0:
        return "not running", start_hint
    return "unknown (no ROS)", ""


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mbot-status", description="MBot health check (same checks as the OLED).")
    ap.add_argument("--brief", action="store_true", help="print only the problems")
    ap.add_argument("--no-color", action="store_true", help="plain text")
    ap.add_argument("--live", "-l", "--watch", action="store_true",
                    help="update every second and log what changes, until Ctrl+C")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.ERROR)  # the report says it when ROS is missing
    if args.live:
        from . import live
        return live.run(lambda color: palette(color and not args.no_color))
    color = sys.stdout.isatty() and not args.no_color and not os.environ.get("NO_COLOR")
    p = Printer(color)

    st, topics, reader, fan = collect(wait_s=3.0)
    problems = current_problems(st)
    # The fan check is reported here only, not on the OLED.
    stopped = fan_problem(fan)
    if stopped:
        problems.append(stopped)

    if not args.brief:
        p.banner("MBOT HEALTH", "%s  \u00b7  image %s" % (st.hostname, st.release or "unknown"))

        p.section("NETWORK")
        if st.ip:
            p.row("IP address", "%s  (%s)" % (st.ip, st.iface))
            if st.wifi_mode == "station":
                p.row("Wi-Fi", "%s  \u00b7  %s  \u00b7  %d MHz" % (st.ssid, st.band or "?", st.freq_mhz))
                p.row("Signal", "%d dBm  (%d of 4 bars)" % (st.signal_dbm, signal_bars(st.signal_dbm)))
            elif st.hotspot:
                p.row("Wi-Fi", "Hotspot %s  (laptops join it, robot IP 192.168.3.1)" % st.ssid)
            elif st.wired:
                p.row("Wi-Fi", "not used (Ethernet)")
            p.row("Gateway", default_gateway() or "none")
            online = internet_reachable()
            p.row("Internet", p.good("reachable") if online else "not reachable",
                  "" if online or st.hotspot else "sudo mwireless-setup --status")
            p.row("Log in", "ssh mbot@%s  or  ssh mbot@%s.local" % (st.ip, st.hostname))
        else:
            p.row("IP address", p.bad("none"), "sudo mwireless-setup --status")
        synced = _run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"]) == "yes"
        p.row("Clock", "%s  %s" % (time.strftime("%Y-%m-%d %H:%M"), p.good("synchronized") if synced else "not synchronized"),
              "" if synced else "MWireless needs the right date: timedatectl")
        p.row("Wi-Fi MAC", st.mac or "?")

        p.section("ROBOT")
        p.row("Pico (USB)", p.good("connected") if st.pico_present else p.bad("not found"),
              "" if st.pico_present else "check the USB-C cable")
        p.row("micro-ROS agent", p.good("running") if st.agent_active else p.bad("not running"),
              "" if st.agent_active else "journalctl -u mbot-microros-agent -b")
        if not st.ros_available:
            p.row("Firmware data", "unknown (ROS not available)")
        elif st.firmware_talking:
            p.row("Firmware data", p.good("receiving"), "/battery_adc")
            state = battery_state(st.battery_v)
            p.row("Battery", "%.2f V" % st.battery_v + ("  \u00b7  " + p.bad(state) if state else ""),
                  "low below %.1f V, no jumper below %.1f V" % (LOW_RANGE[1], JUMPER_MISSING_BELOW))
        else:
            p.row("Firmware data", p.bad("none"), "flash mbot_classic_ros.uf2")
        value, hint = running(p, topics["/odom"], "")
        p.row("Odometry  /odom", value, hint)
        value, hint = running(p, topics["/scan"], "ros2 launch mbot_bringup mbot_bringup.launch.py")
        p.row("LiDAR  /scan", value, hint)
        value, hint = running(p, topics["/camera/image_raw"], "ros2 launch mbot_vision camera.launch.py")
        p.row("Camera", value, hint)
        p.row("Foxglove bridge", p.good("running on port 8765") if st.viz_running else "off",
              "" if st.viz_running else "mbot-viz")

        p.section("SYSTEM")
        load = _read("/proc/loadavg").split()[:3]
        cpu = "%d %%" % round(st.cpu_pct) if st.cpu_pct >= 0 else "?"
        p.row("CPU", "%s  \u00b7  load %s (1, 5, 15 min)  \u00b7  %d cores" % (cpu, " ".join(load), os.cpu_count() or 0))
        temp = "%d \u00b0C" % round(st.temp_c) if st.temp_c >= 0 else "?"
        p.row("Temperature", p.bad(temp) if st.temp_c >= 80 else temp, "warning at 80 \u00b0C")
        p.row("Fan", p.bad(fan_text(*fan[-1])) if stopped else fan_text(*fan[-1]))
        p.row("Memory", memory_text())
        p.row("Disk", disk_text())
        flags = throttle_flags(reader)
        if flags:
            now = [n for k, n in (("undervolt_now", "under-voltage"), ("throttled_now", "throttled")) if flags[k]]
            boot = [n for k, n in (("undervolt_boot", "under-voltage"), ("throttled_boot", "throttled")) if flags[k]]
            p.row("Pi power now", p.bad(", ".join(now)) if now else p.good("OK"))
            p.row("Since boot", ", ".join(boot) if boot else p.good("no under-voltage or throttling"))
        p.row("Uptime", format_uptime(st.uptime_s))

        p.section("SERVICES")
        for unit, what in SERVICES:
            state = _run(["systemctl", "is-active", unit]) or "unknown"
            p.row(unit.replace(".socket", ""), p.good(state) if state == "active" else p.bad(state), what)

        p.section("IMAGE")
        os_name = ""
        for line in _read("/etc/os-release").splitlines():
            if line.startswith("PRETTY_NAME="):
                os_name = line.split("=", 1)[1].strip('"')
        p.row("MBot image", st.release or "unknown")
        p.row("Operating system", "%s  \u00b7  kernel %s" % (os_name, platform.release()))
        p.row("ROS 2", "%s  \u00b7  domain %s  \u00b7  discovery %s" % (
            os.environ.get("ROS_DISTRO", "?"), os.environ.get("ROS_DOMAIN_ID", "0"),
            os.environ.get("ROS_AUTOMATIC_DISCOVERY_RANGE", "?")))

    p.section("PROBLEMS")
    if not problems:
        print("  %s None found." % p.good("✔"))
    for a in problems:
        tag = "ERROR  " if a.severity == ERROR else "WARNING"
        print("  %s  %s" % (p.bad("\u25b2 " + tag), a.title))
        print("              %s" % " ".join(a.detail))
    print()
    if any(a.severity == ERROR for a in problems):
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
