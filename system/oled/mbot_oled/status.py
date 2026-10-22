"""System status for the OLED.

Reads /proc and /sys directly instead of starting a process for every value (design
rule 5 in docs/feasibility-review.md, section 11.3). Only Wi-Fi details (iw) and the
agent state (systemctl) need a command, and those run every few seconds.

The parse_* functions take file contents as strings so they can be unit tested.
"""

import fcntl
import glob
import logging
import os
import socket
import struct
import subprocess
import time
from dataclasses import dataclass

log = logging.getLogger(__name__)

AGENT_UNIT = "mbot-microros-agent.service"
PICO_DEVICE = "/dev/mbot_microros"
FOXGLOVE_PORT = 8765
RELEASE_FILE = "/etc/mbot/image-release"
HOTSPOT_PREFIX = "192.168.3."

FAST_PERIOD = 1.0  # /proc, /sys and IP address
SLOW_PERIOD = 5.0  # iw and systemctl


@dataclass
class Status:
    hostname: str = "mbot"
    ip: str = ""            # address shown in the IP strip, "" if none
    iface: str = ""         # interface that has ip
    mac: str = ""           # Wi-Fi MAC address (wlan0)
    wifi_mode: str = ""     # "station", "ap" or ""
    ssid: str = ""
    freq_mhz: int = 0
    signal_dbm: int = 0     # 0 = unknown
    wired: bool = False     # eth0 has an address
    uptime_s: float = 0.0
    cpu_pct: float = -1.0   # -1 = unknown
    load1: float = -1.0
    mem_pct: float = -1.0
    temp_c: float = -1.0
    disk_pct: float = -1.0
    undervolt_now: bool = False
    throttled_now: bool = False
    undervolt_seen: bool = False
    power_known: bool = False
    pico_present: bool = False
    agent_active: bool = False
    viz_running: bool = False
    ros_available: bool = False   # rclpy and mbot_interfaces imported
    battery_v: float = -1.0       # -1 = no message yet or too old
    release: str = ""             # image release, from /etc/mbot/image-release

    @property
    def hotspot(self):
        return self.wifi_mode == "ap" or self.ip.startswith(HOTSPOT_PREFIX)

    @property
    def band(self):
        if self.freq_mhz >= 5900:
            return "6G"
        if self.freq_mhz >= 4900:
            return "5G"
        if self.freq_mhz > 0:
            return "2.4G"
        return ""

    @property
    def firmware_talking(self):
        return self.battery_v >= 0


# ---------------------------------------------------------------- parsers

def parse_uptime(text):
    return float(text.split()[0])


def parse_cpu_times(text):
    """Return (idle, total) jiffies from the first line of /proc/stat."""
    fields = text.splitlines()[0].split()
    values = [int(v) for v in fields[1:]]
    idle = values[3] + (values[4] if len(values) > 4 else 0)  # idle + iowait
    return idle, sum(values[:8])


def cpu_percent(prev, cur):
    idle = cur[0] - prev[0]
    total = cur[1] - prev[1]
    if total <= 0:
        return -1.0
    return max(0.0, min(100.0, 100.0 * (total - idle) / total))


def parse_meminfo(text):
    """Return the percentage of RAM in use (MemTotal minus MemAvailable)."""
    values = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            values[parts[0].rstrip(":")] = int(parts[1])
    total = values.get("MemTotal", 0)
    if total <= 0 or "MemAvailable" not in values:
        return -1.0
    return 100.0 * (total - values["MemAvailable"]) / total


def parse_loadavg(text):
    return float(text.split()[0])


def parse_throttled(text):
    """Decode get_throttled (hex). Returns (undervolt_now, throttled_now, undervolt_seen)."""
    value = int(text.strip(), 16)
    return bool(value & 0x1), bool(value & 0x4), bool(value & 0x10000)


def parse_iw_info(text):
    """Parse "iw dev wlan0 info". Returns (mode, ssid, freq_mhz)."""
    mode, ssid, freq = "", "", 0
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("type "):
            kind = line.split(None, 1)[1].strip()
            mode = "ap" if kind == "AP" else ("station" if kind == "managed" else kind)
        elif line.startswith("ssid "):
            ssid = line.split(None, 1)[1]
        elif line.startswith("channel ") and "(" in line:
            try:
                freq = int(line.split("(", 1)[1].split()[0])
            except (IndexError, ValueError):
                pass
    return mode, ssid, freq


def parse_iw_link(text):
    """Parse "iw dev wlan0 link". Returns (ssid, freq_mhz, signal_dbm); empty if not connected."""
    ssid, freq, signal = "", 0, 0
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("SSID:"):
            ssid = line.split(":", 1)[1].strip()
        elif line.startswith("freq:"):
            try:
                freq = int(float(line.split(":", 1)[1].split()[0]))
            except (IndexError, ValueError):
                pass
        elif line.startswith("signal:"):
            try:
                signal = int(float(line.split(":", 1)[1].split()[0]))
            except (IndexError, ValueError):
                pass
    return ssid, freq, signal


def port_listening(texts, port):
    """True if any /proc/net/tcp or tcp6 text has a socket listening on port."""
    want = ":%04X" % port
    for text in texts:
        for line in text.splitlines()[1:]:
            parts = line.split()
            if len(parts) > 3 and parts[1].endswith(want) and parts[3] == "0A":
                return True
    return False


def signal_bars(dbm):
    """Wi-Fi signal as 0 to 4 bars."""
    if dbm == 0:
        return 0
    for bars, limit in ((4, -55), (3, -65), (2, -75), (1, -85)):
        if dbm >= limit:
            return bars
    return 0


def format_uptime(seconds):
    seconds = int(seconds)
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    if days:
        return "%dd%02dh" % (days, hours)
    if hours:
        return "%dh%02dm" % (hours, minutes)
    return "%dm" % minutes


# ---------------------------------------------------------------- readers

def _read(path):
    with open(path, encoding="ascii", errors="replace") as f:
        return f.read()


def _ipv4_address(ifname):
    """IPv4 address of an interface, or "" (ioctl SIOCGIFADDR, no process started)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        packed = struct.pack("256s", ifname.encode()[:15])
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, packed)[20:24])
    except OSError:
        return ""
    finally:
        s.close()


def _run(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=2).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _find_throttled_file():
    # Raspberry Pi firmware driver; the path differs between Pi models and kernels.
    patterns = ("/sys/devices/platform/*/get_throttled",
                "/sys/devices/platform/*/*/get_throttled",
                "/sys/devices/platform/*/*/*/get_throttled")
    for pattern in patterns:
        found = glob.glob(pattern)
        if found:
            return found[0]
    return ""


def _find_undervolt_alarm():
    # Mainline raspberrypi-hwmon driver: in0_lcrit_alarm is 1 while under-voltage.
    for name_file in glob.glob("/sys/class/hwmon/hwmon*/name"):
        try:
            if _read(name_file).strip() == "rpi_volt":
                alarm = os.path.join(os.path.dirname(name_file), "in0_lcrit_alarm")
                if os.path.exists(alarm):
                    return alarm
        except OSError:
            continue
    return ""


class StatusReader:
    """Keeps a Status up to date. Call poll() often; it limits its own work."""

    def __init__(self):
        self.status = Status()
        self._next_fast = 0.0
        self._next_slow = 0.0
        self._cpu_prev = None
        self._throttled_file = _find_throttled_file()
        self._undervolt_alarm = "" if self._throttled_file else _find_undervolt_alarm()
        self.status.power_known = bool(self._throttled_file or self._undervolt_alarm)
        try:
            self.status.release = _read(RELEASE_FILE).strip().splitlines()[0]
        except (OSError, IndexError):
            self.status.release = ""
        try:
            self.status.mac = _read("/sys/class/net/wlan0/address").strip()
        except OSError:
            self.status.mac = ""

    def poll(self, now=None):
        now = time.monotonic() if now is None else now
        if now >= self._next_fast:
            self._next_fast = now + FAST_PERIOD
            self._fast()
        if now >= self._next_slow:
            self._next_slow = now + SLOW_PERIOD
            self._slow()
        return self.status

    def _fast(self):
        st = self.status
        st.hostname = socket.gethostname()
        for name, func in (("uptime", self._uptime), ("cpu", self._cpu),
                           ("mem", self._mem), ("temp", self._temp),
                           ("disk", self._disk), ("power", self._power),
                           ("ip", self._ip)):
            try:
                func()
            except (OSError, ValueError, IndexError) as e:
                log.debug("status %s: %s", name, e)
        st.pico_present = os.path.exists(PICO_DEVICE)

    def _slow(self):
        st = self.status
        mode, ap_ssid, ap_freq = parse_iw_info(_run(["iw", "dev", "wlan0", "info"]))
        st.wifi_mode = mode
        if mode == "station":
            st.ssid, st.freq_mhz, st.signal_dbm = parse_iw_link(_run(["iw", "dev", "wlan0", "link"]))
            if not st.ssid:
                st.wifi_mode = ""
        elif mode == "ap":
            st.ssid, st.freq_mhz, st.signal_dbm = ap_ssid, ap_freq, 0
        else:
            st.ssid, st.freq_mhz, st.signal_dbm = "", 0, 0
        st.agent_active = _run(["systemctl", "is-active", AGENT_UNIT]).strip() == "active"
        texts = []
        for path in ("/proc/net/tcp", "/proc/net/tcp6"):
            try:
                texts.append(_read(path))
            except OSError:
                pass
        st.viz_running = port_listening(texts, FOXGLOVE_PORT)

    def _uptime(self):
        self.status.uptime_s = parse_uptime(_read("/proc/uptime"))

    def _cpu(self):
        cur = parse_cpu_times(_read("/proc/stat"))
        if self._cpu_prev is not None:
            self.status.cpu_pct = cpu_percent(self._cpu_prev, cur)
        self._cpu_prev = cur
        self.status.load1 = parse_loadavg(_read("/proc/loadavg"))

    def _mem(self):
        self.status.mem_pct = parse_meminfo(_read("/proc/meminfo"))

    def _temp(self):
        self.status.temp_c = int(_read("/sys/class/thermal/thermal_zone0/temp").strip()) / 1000.0

    def _disk(self):
        fs = os.statvfs("/")
        total = fs.f_blocks * fs.f_frsize
        free = fs.f_bavail * fs.f_frsize
        self.status.disk_pct = 100.0 * (total - free) / total if total else -1.0

    def _power(self):
        st = self.status
        if self._throttled_file:
            st.undervolt_now, st.throttled_now, st.undervolt_seen = parse_throttled(_read(self._throttled_file))
        elif self._undervolt_alarm:
            st.undervolt_now = _read(self._undervolt_alarm).strip() == "1"
            st.undervolt_seen = st.undervolt_seen or st.undervolt_now

    def _ip(self):
        st = self.status
        names = sorted(n for n in os.listdir("/sys/class/net")
                       if n != "lo" and not n.startswith(("docker", "veth", "br-", "virbr")))
        # Wi-Fi first (that is how students reach the robot), then Ethernet, then the rest.
        order = [n for n in ("wlan0", "eth0") if n in names] + [n for n in names if n not in ("wlan0", "eth0")]
        st.ip, st.iface, st.wired = "", "", False
        for name in order:
            ip = _ipv4_address(name)
            if name == "eth0" and ip:
                st.wired = True
            if ip and not st.ip:
                st.ip, st.iface = ip, name
