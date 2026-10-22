"""MBot OLED status display (D-17, OLED-003 to OLED-006).

Replaces the upstream mbot_ros_oled_display.py on the server image. Draws on the
SSD1306 128x64 OLED: a boot animation until the robot has an IP address, then one main
screen (robot name, IP address, network, READY and battery voltage). Problems are shown
only when they persist (alerts.py), each with what to do about it.

Modules:
    config   - reads /boot/firmware/mbot_config.txt
    status   - system status from /proc, /sys and a few cheap commands
    alerts   - problem rules with raise and clear delays (shared with mbot-status)
    battery  - battery voltage from the firmware (/battery_adc) and its diagnosis
    sprites  - the MBot drawing used by the animations
    render   - draws every screen as a 1-bit PIL image (no hardware needed)
    pages    - decides which screen to show and when
    service  - main loop: talks to the OLED, the status readers and ROS
    cli      - mbot-status: the same checks in a terminal
    preview  - renders GIF previews on a laptop (development only)
"""

__version__ = "2.3.0"
