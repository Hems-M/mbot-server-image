# system/oled

New OLED status service for the MBot server image (D-17, tasks OLED-003 to OLED-006).
It replaces the upstream `mbot_ros_oled_display.py` on the robot. The upstream script is still copied to `/usr/local/etc/` unchanged, but no unit starts it.

Status: PROVISIONAL, version 2.3.0 (rc7: battery voltage only, fan check in `mbot health`). Previews and 67 unit tests pass. Version 1 ran on a robot (rc2, rc3), 2.0.0 on rc4; **2.1.0 is not tested on an OLED yet** (OLED-008).

## What the screen shows

Design: one main screen with what a student needs to connect, a health page with the numbers, the MBot animation, and alert cards only while a real problem lasts. The IP address is on every screen after boot. Previews: `results/oled-preview/`.

| Screen | When | Content |
|--------|------|---------|
| Boot | From power-on until the robot has an IP (max. 150 s) | The MBot is put together part by part, "Starting up", a sweeping progress bar. Status line: "Waiting for network" |
| Main | 8 s per cycle | Robot name (scrolls if long) with Wi-Fi bars, `AP` or `ETH`; the IP address in large digits; the network name (SSID), or the hotspot name; status line `READY` with the battery voltage, `Starting`, or the current problem (inverted, with an icon) |
| Health | 5 s per cycle | Top: battery icon and voltage; "low", "motor power off" or "no jumper" inverted with the icon blinking when the voltage says so. Body: temperature, CPU, RAM and disk gauges that fill up when the page appears; a value past its limit is shown inverted. Status line: IP and uptime |
| MBot | 6 s per cycle, only with animation on | The MBot drives in (wheels turn with the distance), brakes, scans: rings leave the LiDAR and the walls appear where they hit; then it drives off with speed lines. Status line: IP and battery voltage |
| Alert card | 4 s per active problem | `WARNING` or `ERROR`, title, what to do, IP in the status line |
| Shutdown | 2 s when the service stops | "Bye!" is typed in, the LiDAR slows down, the robot nods, "Shutting down", two z's. The last frame stays on the OLED. Skipped when no OLED is connected or animation is off |
| Notices | 6 s on the main status line | "Connected: MWireless", "Hotspot on", "Pico connected", "Resolved: ..." |

A blinking pixel at the bottom right shows the display is live.

The SSD1306 module on the MBot is one colour (white). Colour cannot be set in software, so warnings and errors differ in shape: a warning has an outlined triangle and a steady inverted status line; an error has a filled disc, and its status line and card header flash (normal for 0.2 s every second).

### Alerts (alerts.py)

An alert appears only after its condition has held without a break for the raise delay, and goes away after it has been false for the clear delay. `mbot health` runs the same rules without delays.

| Alert | Severity | Condition | Raise / clear |
|-------|----------|-----------|---------------|
| No network | error | no IP on any interface, uptime at least 90 s | 30 s / 5 s |
| Pi power too low | error | under-voltage seen at least 3 times in 60 s | at once / 60 s |
| ROS link stopped | error | Pico present but micro-ROS agent not active | 30 s / 5 s |
| Pico not connected | warning | `/dev/mbot_microros` missing, uptime at least 45 s | 20 s / 3 s |
| No data from Pico | warning | Pico and agent up, no `/battery_adc` message, uptime at least 90 s | 20 s / 3 s |
| Battery (jumper, motor power off, low) | warning | 30 s median below 1.5 V, between 3.5 and 5.5 V, or between 7.0 and 9.0 V (at least 20 readings) | 10 s / 10 s |
| Pi running hot | warning | temperature at least 80 C | 30 s / 30 s |
| Disk almost full | warning | at least 92 % | 10 s / 10 s |
| Memory almost full | warning | at least 95 % | 20 s / 10 s |

Only the battery voltage is shown, no percentage (rc7): the voltage sags under load and the pack's discharge curve is not known, so a percentage would mislead. The Pi 5 fan is checked by `mbot health` only (`fan.py`), not on the OLED.

`oled_animation=off` in `/boot/firmware/mbot_config.txt` turns off the boot animation, the gauge fill-in, the MBot page and the shutdown animation.

## Files

| Path | Content |
|------|---------|
| `mbot_oled/status.py` | Status from `/proc`, `/sys`, `iw` and `systemctl` (no process per value) |
| `mbot_oled/battery.py` | `/battery_adc` subscription |
| `mbot_oled/fan.py` | Pi 5 cooler check for `mbot health` (not the OLED) |
| `mbot_oled/alerts.py` | Problem rules with raise and clear delays (shared with `mbot health`) |
| `mbot_oled/cli.py` | `mbot-status` / `mbot health`: the full report in a terminal |
| `mbot_oled/live.py` | `mbot health --live`: the same, every second, with an event log |
| `mbot_oled/sprites.py` | The MBot Classic in 1-bit pixels |
| `mbot_oled/render.py` | Draws every screen (no hardware needed) |
| `mbot_oled/pages.py` | Which screen, when; notices |
| `mbot_oled/service.py` | Main loop, OLED connection with retry |
| `mbot_oled/preview.py` | GIF previews for review |
| `tests/` | Unit tests |

Installed by `image/build/30-mbot-system.sh` to `/opt/mbot/oled`. Unit: `system/systemd/mbot-oled.service`.

## Develop without a robot

Needs Pillow and the DejaVu fonts (`python3-pil fonts-dejavu-core` on Ubuntu 24.04):

```bash
cd system/oled
python3 -m unittest discover -s tests
python3 -m mbot_oled.preview --out /tmp/oled-preview
```

The last run's previews are in `results/oled-preview/`.

## On the robot

```bash
systemctl status mbot-oled
journalctl -u mbot-oled -b
sudo systemctl restart mbot-oled
i2cdetect -y 1        # the OLED answers at 3c
```
