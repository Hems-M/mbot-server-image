"""Render GIF and PNG previews of the OLED with made-up status values (development only).

Needs only Pillow and the DejaVu fonts, no OLED, ROS or Raspberry Pi:

    python3 -m mbot_oled.preview --out /tmp/oled-preview

Each scenario is simulated second by second through the real alert engine, so the
previews also show the raise and clear delays.
"""

import argparse
import os
from dataclasses import replace

from PIL import Image, ImageDraw

from .alerts import ERROR, WARNING, Alert
from .pages import Pager
from .render import BYE_S, HEIGHT, WIDTH, Renderer
from .status import Status

FPS = 5

CAMPUS = Status(hostname="mbot-AM-team6-johndoe", ip="35.3.125.94", iface="wlan0",
                mac="d8:3a:dd:12:34:56", wifi_mode="station", ssid="MWireless",
                freq_mhz=5180, signal_dbm=-58, uptime_s=4380, cpu_pct=23, load1=0.52,
                mem_pct=41, temp_c=54, disk_pct=62, power_known=True, pico_present=True,
                agent_active=True, ros_available=True, battery_v=11.92,
                release="rc5 2026-10-16")
HOME = replace(CAMPUS, hostname="mbot-PM-team2-alex", ip="192.168.1.37", ssid="HomeWifi",
               freq_mhz=2437, signal_dbm=-71)
HOTSPOT = replace(CAMPUS, hostname="mbot-0000", ip="192.168.3.1", wifi_mode="ap",
                  ssid="mbot-0000-AP", signal_dbm=0)


def scaled(img, scale):
    """White-on-black OLED pixels, scaled up with a dark gap between pixels."""
    big = img.convert("L").resize((WIDTH * scale, HEIGHT * scale), Image.NEAREST)
    if scale >= 3:
        d = ImageDraw.Draw(big)
        for x in range(0, WIDTH * scale, scale):
            d.line((x, 0, x, HEIGHT * scale), fill=0)
        for y in range(0, HEIGHT * scale, scale):
            d.line((0, y, WIDTH * scale, y), fill=0)
    bordered = Image.new("L", (big.width + 2 * scale, big.height + 2 * scale), 40)
    bordered.paste(big, (scale, scale))
    return bordered


def timeline(status_at, seconds, scale=4):
    pager = Pager(Renderer())
    return [scaled(pager.frame(status_at(i / FPS), i / FPS), scale) for i in range(int(seconds * FPS))]


def save_gif(path, frames):
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(1000 / FPS),
                   loop=0, optimize=True)


def boot_then_hotspot(t):
    st = replace(HOTSPOT, uptime_s=12 + t, pico_present=t > 2, agent_active=t > 3)
    return replace(st, ip="", wifi_mode="", ssid="") if t < 6 else st


def hotspot_then_campus(t):
    # The student runs mwireless-setup at t = 8 s; the campus IP arrives at t = 14 s.
    return replace(HOTSPOT if t < 14 else replace(CAMPUS, hostname="mbot-0000"), uptime_s=600 + t)


def pico_unplugged(t):
    # The USB cable is pulled at t = 4 s and plugged back at t = 40 s.
    gone = 4 <= t < 40
    return replace(HOME, uptime_s=900 + t, pico_present=not gone, agent_active=not gone,
                   battery_v=-1.0 if gone else HOME.battery_v)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="oled-preview")
    ap.add_argument("--scale", type=int, default=4)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    for name, (status_at, seconds) in {
        "boot": (boot_then_hotspot, 12),
        "rotation": (lambda t: replace(CAMPUS, uptime_s=4380 + t), 28),
        "hotspot-to-mwireless": (hotspot_then_campus, 24),
        "pico-unplugged": (pico_unplugged, 54),
    }.items():
        path = os.path.join(args.out, name + ".gif")
        save_gif(path, timeline(status_at, seconds, args.scale))
        print("wrote", path)

    r = Renderer()
    # The drive page and the shutdown animation on their own, at 10 frames per second.
    drive = [scaled(r.drive(CAMPUS, i / 10, i / 10, 11.9), args.scale) for i in range(60)]
    bye = [scaled(r.bye(CAMPUS, i / 10), args.scale) for i in range(int(BYE_S * 10) + 1)]
    bye += [bye[-1]] * 15
    for name, frames in (("drive", drive), ("shutdown", bye)):
        path = os.path.join(args.out, name + ".gif")
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=100, loop=0, optimize=True)
        print("wrote", path)
    pico = Alert("pico", WARNING, "Pico not connected", ("Check the USB-C cable", "from the Pi to the Pico."), "No Pico")
    low = Alert("battery", WARNING, "Battery low", ("8.6 V. Charge the power", "bank soon."), "Battery low 8.6 V")
    power = Alert("power", ERROR, "Pi power too low", ("Check the Pi power cable", "and the power bank."), "Pi power low")
    stills = [
        ("booting", r.boot(replace(HOTSPOT, ip=""), 1.4)),
        ("booting, assembled", r.boot(replace(HOTSPOT, ip=""), 6.0)),
        ("ready on MWireless", r.main(CAMPUS, 0.0, "READY", "11.9 V")),
        ("health page", r.health(CAMPUS, 2.0, 2.0, 11.9)),
        ("health page, filling in", r.health(CAMPUS, 0.2, 0.2, 11.9)),
        ("health page, hot and low", r.health(replace(CAMPUS, temp_c=83, mem_pct=96), 2.0, 2.0, 8.6)),
        ("ready at home", r.main(HOME, 0.0, "READY", "11.6 V")),
        ("hotspot", r.main(HOTSPOT, 0.0, "READY", "12.0 V")),
        ("notice", r.main(CAMPUS, 0.0, "Connected: MWireless")),
        ("problem on main screen", r.main(HOME, 0.0, "", alert=pico, more=1)),
        ("warning card", r.alert_card(HOME, 0.0, pico, 0, 2)),
        ("warning card 2", r.alert_card(HOME, 0.0, low, 1, 2)),
        ("error card", r.alert_card(CAMPUS, 0.0, power, 0, 1)),
        ("error on main screen", r.main(CAMPUS, 0.0, "", alert=power)),
        ("starting", r.main(replace(HOTSPOT, battery_v=-1.0), 0.0, "Starting")),
        ("drive: driving in", r.drive(CAMPUS, 0.8, 0.8, 11.9)),
        ("drive: LiDAR scan", r.drive(CAMPUS, 3.4, 3.4, 11.9)),
        ("drive: driving off", r.drive(CAMPUS, 4.9, 4.9, 11.9)),
        ("shutdown: bye", r.bye(CAMPUS, 0.75)),
        ("shutdown: last frame", r.shutdown(CAMPUS)),
    ]
    cell_w, cell_h = (WIDTH + 2) * args.scale, (HEIGHT + 2) * args.scale + 16
    cols = 3
    sheet = Image.new("L", (cols * cell_w, -(-len(stills) // cols) * cell_h), 255)
    d = ImageDraw.Draw(sheet)
    for i, (label, img) in enumerate(stills):
        x, y = (i % cols) * cell_w, (i // cols) * cell_h
        d.text((x + 4, y + 2), label, fill=0)
        sheet.paste(scaled(img, args.scale), (x, y + 16))
    path = os.path.join(args.out, "all-screens.png")
    sheet.save(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
