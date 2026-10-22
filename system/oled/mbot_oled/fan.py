"""The Raspberry Pi 5 cooler, for mbot health (not shown on the OLED).

The Pi 5 kernel drives the cooler with the pwm-fan driver: hwmon device "pwmfan" with
pwm1 (0 to 255, what the Pi asks for) and fan1_input (rpm measured by the fan's tach
wire). The firmware turns the fan on from about 50 C and faster from 60, 67.5 and 75 C.

A cooler that is missing or stuck shows as pwm1 above 0 with 0 rpm. That is only visible
once the Pi asks the fan to turn, so a cool Pi with a missing fan looks the same as a
cool Pi with a fan that is off; the problem shows up as it warms up, before throttling
at 80 C or more.
"""

import glob
import os

from .alerts import WARNING, Alert

HWMON = "/sys/class/hwmon"


def find_fan(root=HWMON):
    """Directory of the pwm-fan hwmon device, or "" if there is none."""
    for d in sorted(glob.glob(os.path.join(root, "hwmon*"))):
        try:
            with open(os.path.join(d, "name"), encoding="ascii") as f:
                if f.read().strip() == "pwmfan":
                    return d
        except OSError:
            continue
    return ""


def _int(path):
    try:
        with open(path, encoding="ascii") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return -1


def read_fan(d):
    """(pwm 0..255 or -1, rpm or -1) from a pwm-fan hwmon directory."""
    if not d:
        return -1, -1
    return _int(os.path.join(d, "pwm1")), _int(os.path.join(d, "fan1_input"))


def fan_problem(samples):
    """Alert if every sample (at least 2, a second or more apart) has power but 0 rpm."""
    if len(samples) < 2:
        return None
    if all(pwm > 0 and rpm == 0 for pwm, rpm in samples):
        return Alert("fan", WARNING, "Fan not spinning",
                     ("The Pi asks the cooler to turn but it reports 0 rpm.",
                      "Check that the Pi 5 Active Cooler is fitted and its cable is in the FAN socket."),
                     "Fan stopped")
    return None


def fan_text(pwm, rpm):
    """What the fan is doing, in words."""
    if pwm < 0 and rpm < 0:
        return "not found (no pwm-fan device)"
    level = "%d %% power" % round(100 * pwm / 255) if pwm >= 0 else "power unknown"
    if pwm == 0:
        return "off (the Pi is cool; it starts at about 50 °C)"
    if rpm < 0:
        return "on, %s (no speed reading)" % level
    return "%d rpm, %s" % (rpm, level)
