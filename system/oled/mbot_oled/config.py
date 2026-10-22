"""Settings from /boot/firmware/mbot_config.txt.

The file is the one students already edit for the hostname and home Wi-Fi. The OLED
reads this optional key:

    oled_animation=on|off   animations (default: on); off shows plain screens

A missing key means the default, so the image can ship the upstream template unchanged.
"""

MBOT_CONFIG = "/boot/firmware/mbot_config.txt"

DEFAULTS = {"oled_animation": "on"}


def parse_config(text):
    """Return the key=value pairs of an mbot_config.txt as a dict of strings."""
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def read_config(path=MBOT_CONFIG):
    """Read the config file. A missing or unreadable file gives the defaults."""
    values = dict(DEFAULTS)
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            values.update(parse_config(f.read()))
    except OSError:
        pass
    return values


def is_on(value):
    return str(value).strip().lower() in ("on", "yes", "true", "1")


def animation_enabled(values):
    return is_on(values.get("oled_animation", DEFAULTS["oled_animation"]))

