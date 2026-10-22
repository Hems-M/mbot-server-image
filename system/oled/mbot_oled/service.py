"""Main loop of the OLED service (mbot-oled.service).

- Starts early in boot and never waits for the network (design rule 3).
- Keeps running when the OLED is missing or the I2C bus fails: it logs once and tries
  again every RETRY_S seconds (OLED-003).
- Sends a frame to the OLED only when it changed. luma.oled then transfers only the
  changed area, so the I2C bus (100 kHz) is mostly idle on the static main screen.
- Logs to the journal: journalctl -u mbot-oled
"""

import logging
import signal
import sys
import time

from . import __version__
from .battery import BatteryListener
from .config import animation_enabled, read_config
from .pages import Pager
from .render import BYE_S, Renderer
from .status import StatusReader

log = logging.getLogger("mbot_oled")

FRAME_S = 0.2       # 5 frames per second
RETRY_S = 10.0
I2C_PORT = 1
I2C_ADDRESS = 0x3C


class Oled:
    """The SSD1306 on I2C-1. Missing hardware is not an error, only a log line."""

    def __init__(self):
        self.device = None
        self.next_try = 0.0
        self.last = None
        self.missing_logged = False

    def _open(self, now):
        self.next_try = now + RETRY_S
        try:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306
        except ImportError as e:
            if not self.missing_logged:
                log.error("luma.oled not installed: %s", e)
                self.missing_logged = True
            return
        try:
            self.device = ssd1306(i2c(port=I2C_PORT, address=I2C_ADDRESS))
            self.device.persist = True  # keep the last frame on screen after we exit
            self.last = None
            self.missing_logged = False
            log.info("OLED found on I2C-%d at 0x%02X", I2C_PORT, I2C_ADDRESS)
        except Exception as e:  # luma raises DeviceNotFoundError, OSError, ...
            self.device = None
            if not self.missing_logged:
                log.warning("OLED not found on I2C-%d at 0x%02X (%s); retrying every %d s",
                            I2C_PORT, I2C_ADDRESS, e, RETRY_S)
                self.missing_logged = True

    def show(self, img, now):
        if self.device is None:
            if now < self.next_try:
                return
            self._open(now)
            if self.device is None:
                return
        data = img.tobytes()
        if data == self.last:
            return
        try:
            self.device.display(img)
            self.last = data
        except Exception as e:
            log.warning("OLED write failed (%s); reconnecting", e)
            self.device = None
            self.next_try = now + 1.0


def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(levelname)s %(name)s: %(message)s")
    settings = read_config()
    animate = animation_enabled(settings)
    log.info("mbot_oled %s starting (animation %s)", __version__, "on" if animate else "off")

    oled = Oled()
    renderer = Renderer()
    pager = Pager(renderer, animation=animate)
    reader = StatusReader()
    bat = BatteryListener()
    reader.status.ros_available = bat.start()

    # Installed after rclpy.init, so these handlers are the ones that run.
    stop = []
    signal.signal(signal.SIGTERM, lambda *_: stop.append(1))
    signal.signal(signal.SIGINT, lambda *_: stop.append(1))

    t0 = time.monotonic()
    last_ip = None
    st = reader.status
    while not stop:
        now = time.monotonic()
        st = reader.poll(now)
        st.battery_v = bat.volts(now)
        if st.ip != last_ip:
            log.info("IP address: %s (%s)", st.ip or "none", st.iface or "-")
            last_ip = st.ip
        try:
            frame = pager.frame(st, now - t0)
        except Exception:
            log.exception("drawing page %s failed", pager.page)
            frame = renderer.main(st, now - t0, "Display error, see log")
        oled.show(frame, now)
        time.sleep(max(0.0, FRAME_S - (time.monotonic() - now)))

    log.info("stopping")
    if animate and oled.device is not None:
        start = time.monotonic()
        while (since := time.monotonic() - start) < BYE_S:
            oled.show(renderer.bye(st, since), time.monotonic())
            time.sleep(0.1)
    oled.show(renderer.shutdown(st), time.monotonic())
    bat.stop()
