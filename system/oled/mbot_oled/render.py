"""Draws the OLED screens as 128x64 1-bit PIL images (no hardware needed).

Every screen uses the same grid:

    y  0..11   header: robot name, connection icon
    y 12       rule
    y 14..46   body: the IP address and the network on the main screen
    y 49..63   status line: READY and the battery voltage, or the current problem

The main screen alternates with the health page (battery, temperature, CPU, RAM, disk)
and the MBot animation. Every screen shows the IP address: large on the main screen,
in the status line on the others. Alert cards are added to the rotation only while a
problem is active (see alerts.py).

The SSD1306 is a one-colour display, so warnings and errors differ in shape, not colour:
a warning is an outlined triangle on a steady inverted line, an error is a filled disc
on a line that flashes.

Text is drawn antialiased and then cut to 1 bit. Drawing straight into a 1-bit image
rounds every glyph advance and leaves uneven gaps between letters.
"""

from PIL import Image, ImageDraw, ImageFont

from . import sprites
from .alerts import ERROR, battery_state
from .status import format_uptime, signal_bars

WIDTH, HEIGHT = 128, 64
STATUS_Y = 49
FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
THRESHOLD = 110
GROUND_Y = STATUS_Y - 3   # floor line of the animation pages
DRIVE_S = 6.0             # one drive-in, scan, drive-off cycle
BYE_S = 2.0               # shutdown animation


def _font(name, size):
    try:
        return ImageFont.truetype(FONT_DIR + name, size)
    except OSError:
        return ImageFont.load_default()


class Renderer:
    def __init__(self):
        self.header = _font("DejaVuSans-Bold.ttf", 10)
        self.ip_fonts = [_font("DejaVuSans-Bold.ttf", s) for s in (17, 15, 13, 11)]
        self.body = _font("DejaVuSans.ttf", 9)
        self.label = _font("DejaVuSans-Bold.ttf", 9)
        self.title = _font("DejaVuSans-Bold.ttf", 11)
        self.brand = _font("DejaVuSans-Bold.ttf", 14)

    # ------------------------------------------------------------ primitives

    @staticmethod
    def new():
        img = Image.new("1", (WIDTH, HEIGHT), 0)
        return img, ImageDraw.Draw(img)

    @staticmethod
    def width(font, text):
        return font.getlength(text)

    def fit(self, text, font, max_w):
        if self.width(font, text) <= max_w:
            return text
        while text and self.width(font, text + "…") > max_w:
            text = text[:-1]
        return text + "…"

    def text(self, img, xy, text, font, fill=1):
        """Draw text antialiased, cut it to 1 bit, and paste it in the given colour."""
        if not text:
            return
        x, y = xy
        _, _, right, bottom = font.getbbox(text)
        scratch = Image.new("L", (int(right) + 3, int(bottom) + 2), 0)
        ImageDraw.Draw(scratch).text((x - int(x), 0), text, font=font, fill=255)
        mask = scratch.point(lambda v: 255 if v >= THRESHOLD else 0).convert("1")
        img.paste(fill, (int(x), int(y)), mask)

    def centered(self, img, y, text, font, max_w=WIDTH - 2):
        text = self.fit(text, font, max_w)
        self.text(img, ((WIDTH - self.width(font, text)) / 2, y), text, font)

    def marquee(self, img, x, y, h, max_w, text, font, t, speed=16.0, hold=2.0):
        """Text that scrolls when it does not fit (long course hostnames)."""
        w = self.width(font, text)
        if w <= max_w:
            self.text(img, (x, y), text, font)
            return
        gap = 20
        period = w + gap
        phase = t % (hold + period / speed)
        offset = 0 if phase < hold else (phase - hold) * speed
        strip = Image.new("1", (int(max_w), h), 0)
        self.text(strip, (-offset, 0), text, font)
        self.text(strip, (-offset + period, 0), text, font)
        img.paste(strip, (x, y))

    # ------------------------------------------------------------ icons

    @staticmethod
    def icon_wifi(d, x, y, bars):
        """Four signal bars, bottom at y+9. Missing bars are a one-pixel stub."""
        for i in range(4):
            bx = x + i * 3
            h = 3 + 2 * i
            top = y + 9 - h if i < bars else y + 9
            d.rectangle((bx, top, bx + 1, y + 9), fill=1)

    def icon_tag(self, img, d, x_right, y, text):
        """Small framed label at the right edge, for example AP or ETH."""
        w = int(self.width(self.label, text)) + 5
        d.rounded_rectangle((x_right - w, y, x_right, y + 10), radius=2, outline=1)
        self.text(img, (x_right - w + 3, y), text, self.label)
        return w

    @staticmethod
    def icon_warning(d, x, y, fill=1):
        """Warning triangle, 9x8."""
        d.polygon([(x + 4, y), (x + 8, y + 7), (x, y + 7)], outline=fill)
        d.line((x + 4, y + 2, x + 4, y + 4), fill=fill)
        d.point((x + 4, y + 6), fill=fill)

    @staticmethod
    def icon_error(d, x, y, fill=1):
        """Error disc with an exclamation mark, 8x8."""
        d.ellipse((x, y, x + 7, y + 7), fill=fill)
        d.rectangle((x + 3, y + 1, x + 4, y + 4), fill=1 - fill)
        d.rectangle((x + 3, y + 6, x + 4, y + 6), fill=1 - fill)

    def icon_battery(self, d, x, y, blink_off=False):
        """Battery outline 24x10 with a terminal nub and a plus sign (no charge level)."""
        if blink_off:
            return
        d.rectangle((x, y, x + 22, y + 9), outline=1)
        d.rectangle((x + 23, y + 3, x + 24, y + 6), fill=1)
        d.line((x + 9, y + 4, x + 13, y + 4), fill=1)
        d.line((x + 11, y + 2, x + 11, y + 6), fill=1)

    @staticmethod
    def bar(d, x, y, w, frac):
        """Gauge: 1-pixel frame, filled to frac (0..1)."""
        d.rectangle((x, y, x + w - 1, y + 4), outline=1)
        fill = int(round((w - 2) * max(0.0, min(1.0, frac))))
        if fill > 0:
            d.rectangle((x + 1, y + 1, x + fill, y + 3), fill=1)

    # ------------------------------------------------------------ shared parts

    def header_bar(self, img, d, st, t):
        """Robot name on the left, connection icon on the right, rule below."""
        right = WIDTH - 1
        if st.wifi_mode == "station" and st.ssid:
            self.icon_wifi(d, right - 10, 0, signal_bars(st.signal_dbm))
            used = 14
        elif st.ip and st.hotspot:
            used = self.icon_tag(img, d, right, 0, "AP") + 3
        elif st.ip and st.wired:
            used = self.icon_tag(img, d, right, 0, "ETH") + 3
        else:
            used = 0
        self.marquee(img, 0, 0, 12, WIDTH - used - 2, st.hostname, self.header, t)
        d.line((0, 12, WIDTH - 1, 12), fill=1)

    def network_text(self, st):
        if st.wifi_mode == "station" and st.ssid:
            return st.ssid
        if st.ip and st.hotspot:
            return "Hotspot  " + (st.ssid or "")
        if st.ip and st.wired:
            return "Ethernet"
        if st.ip:
            return st.iface
        return "Not connected"

    def status_line(self, img, d, t, text, right="", alert=None, heartbeat=True):
        """Bottom line. Inverted with an icon while a problem is active."""
        y = STATUS_Y
        # An error flashes: normal for 0.2 s of every second. A warning stays inverted.
        if alert and not (alert.severity == ERROR and int(t * 5) % 5 == 4):
            d.rectangle((0, y + 1, WIDTH - 1, HEIGHT - 1), fill=1)
            ink = 0
        else:
            d.line((0, y, WIDTH - 1, y), fill=1)
            ink = 1
        x = 2
        if alert and alert.severity == ERROR:
            self.icon_error(d, x, y + 4, fill=ink)
            x += 11
        elif alert:
            self.icon_warning(d, x, y + 4, fill=ink)
            x += 12
        beat_w = 5 if heartbeat else 0
        right_w = int(self.width(self.label, right)) + 3 if right else 0
        self.text(img, (x, y + 2), self.fit(text, self.label, WIDTH - x - right_w - beat_w - 2),
                  self.label, ink)
        if right:
            self.text(img, (WIDTH - beat_w - right_w, y + 2), right, self.label, ink)
        if heartbeat and int(t) % 2 == 0:
            # Blinks once a second: shows that the display is live, not frozen.
            d.rectangle((WIDTH - 3, y + 7, WIDTH - 2, y + 8), fill=ink)

    def ip_line(self, img, d, st, t, right=""):
        """Status line with the IP address. right is dropped if both do not fit."""
        ip = st.ip or "No IP address"
        if right and self.width(self.label, ip) + self.width(self.label, right) + 14 > WIDTH:
            right = ""
        self.status_line(img, d, t, ip, right)

    # ------------------------------------------------------------ screens

    def main(self, st, t, status_text, status_right="", alert=None, more=0):
        """The main screen. With an alert, the status line shows it (and how many more)."""
        img, d = self.new()
        self.header_bar(img, d, st, t)
        if st.ip:
            shift = int(t // 300) % 3 - 1  # move by 1 px every 5 min against burn-in
            font = next((f for f in self.ip_fonts if self.width(f, st.ip) <= WIDTH - 4), self.ip_fonts[-1])
            y = 15 if font is self.ip_fonts[0] else 17
            self.text(img, ((WIDTH - self.width(font, st.ip)) / 2 + shift, y), st.ip, font)
        else:
            self.centered(img, 18, "No IP address", self.title)
        self.centered(img, 36, self.network_text(st), self.body)
        if alert:
            self.status_line(img, d, t, alert.label, "+%d" % more if more else "", alert=alert)
        else:
            self.status_line(img, d, t, status_text, status_right)
        return img

    def health(self, st, t, since, volts=-1.0, animate=True):
        """Health page. Gauges fill up during the first 0.8 s after the page appears."""
        img, d = self.new()
        k = 1.0
        if animate:
            p = max(0.0, min(1.0, since / 0.8))
            k = 1 - (1 - p) ** 3  # ease out

        # Header: battery icon and voltage. On the right "Battery", or what is wrong
        # (low, motor power off, no jumper) inverted, with the icon blinking.
        state = battery_state(volts)
        self.icon_battery(d, 0, 1, blink_off=bool(state) and int(t * 2) % 2 == 1)
        if volts >= 0:
            self.text(img, (30, 0), "%.1f V" % volts, self.header)
            if state:
                w = self.width(self.label, state)
                d.rectangle((WIDTH - 5 - w, 0, WIDTH - 1, 10), fill=1)
                self.text(img, (WIDTH - 3 - w, 0), state, self.label, 0)
            else:
                self.text(img, (WIDTH - 1 - self.width(self.body, "Battery"), 1), "Battery", self.body)
        else:
            self.text(img, (30, 1), "No battery data", self.body)
        d.line((0, 12, WIDTH - 1, 12), fill=1)

        # 2 x 2 gauges. A value past its warning limit is shown inverted.
        cells = (
            ("Temp", st.temp_c, "%d \u00b0C", (st.temp_c - 30) / 55.0, st.temp_c >= 80),
            ("CPU", st.cpu_pct, "%d %%", st.cpu_pct / 100.0, False),
            ("RAM", st.mem_pct, "%d %%", st.mem_pct / 100.0, st.mem_pct >= 95),
            ("Disk", st.disk_pct, "%d %%", st.disk_pct / 100.0, st.disk_pct >= 92),
        )
        for i, (name, value, fmt, frac, warn) in enumerate(cells):
            x = 0 if i % 2 == 0 else 67
            y = 14 if i < 2 else 31
            self.text(img, (x, y), name, self.body)
            shown = fmt % round(value * k) if value >= 0 else "?"
            vw = self.width(self.label, shown)
            vx = x + 59 - vw
            if warn:
                d.rectangle((vx - 2, y, x + 60, y + 9), fill=1)
            self.text(img, (vx, y), shown, self.label, 0 if warn else 1)
            self.bar(d, x, y + 11, 61, frac * k if value >= 0 else 0)

        self.ip_line(img, d, st, t, "up " + format_uptime(st.uptime_s))
        return img

    @staticmethod
    def _drive_x(s):
        """Robot position on the drive page s seconds into the page."""
        if s < 1.6:  # drive in, braking at the end
            p = s / 1.6
            return -sprites.SPRITE_W + (40 + sprites.SPRITE_W) * (1 - (1 - p) ** 3)
        if s < 3.8:  # stop and scan
            return 40.0
        p = min(1.0, (s - 3.8) / 2.2)  # drive off, speeding up
        return 40.0 + (WIDTH + 4 - 40) * p * p

    def drive(self, st, t, since, volts=-1.0):
        """The MBot drives in, stops, maps the walls with its LiDAR and drives off."""
        img, d = self.new()
        s = since % DRIVE_S
        x = self._drive_x(s)
        speed = (self._drive_x(min(DRIVE_S, s + 0.05)) - x) / 0.05
        travelled = x + sprites.SPRITE_W
        y = GROUND_Y - sprites.SPRITE_H + 1
        head = (x + 22, y + 3)

        # Floor: a line with a tick every 8 px.
        d.line((0, GROUND_Y, WIDTH - 1, GROUND_Y), fill=1)
        for fx in range(4, WIDTH, 8):
            d.point((fx, GROUND_Y + 1), fill=1)

        # Scan: rings leave the LiDAR every 0.6 s. Where a ring meets a wall, that part
        # of the wall appears, a little more with every ring (the map being built).
        if 1.9 <= s < 3.8:
            walls = (1, WIDTH - 2)
            rings = Image.new("1", (WIDTH, HEIGHT), 0)
            rd = ImageDraw.Draw(rings)
            for k in range(3):
                r = (s - 1.9 - 0.6 * k) * 70 + 32  # starts just outside the robot
                if r < 32:
                    continue
                if r < 72:
                    box = (head[0] - r, head[1] - r, head[0] + r, head[1] + r)
                    rd.arc(box, 145, 215, fill=1)
                    rd.arc(box, 325, 360, fill=1)
                    rd.arc(box, 0, 35, fill=1)
                for wx in walls:
                    if r >= abs(wx - head[0]):
                        half = 4 * (k + 1)
                        d.line((wx, max(0, head[1] - half), wx, min(GROUND_Y, head[1] + half)), fill=1)
                        d.rectangle((wx - 1, head[1] - 1, wx + 1, head[1] + 1), fill=1)
            # Rings stop at the floor.
            img.paste(1, (0, 0, WIDTH, GROUND_Y), rings.crop((0, 0, WIDTH, GROUND_Y)))

        # Speed lines behind the robot while it moves fast.
        if speed > 30:
            length = min(16, int(speed / 8))
            for i, dy in enumerate((13, 20, 28)):
                tail = x - 3 - 3 * (i % 2)
                d.line((tail - length, y + dy, tail, y + dy), fill=1)

        dip = 1 if 1.6 <= s < 1.8 or 3.8 <= s < 3.95 else 0  # body dips when it brakes and starts
        robot = sprites.mbot_image(wheel_angle=travelled / sprites.WHEEL_RADIUS,
                                   lidar_angle=t * 5.2, body_dy=dip)
        sprites.paste(img, robot, x, y)
        d.rectangle((0, GROUND_Y + 2, WIDTH - 1, STATUS_Y - 1), fill=0)
        self.ip_line(img, d, st, t, "%.1f V" % volts if volts >= 0 else "")
        return img

    def alert_card(self, st, t, alert, index, total):
        img, d = self.new()
        if alert.severity == ERROR and int(t * 5) % 5 == 4:
            # Flash: the error header is outlined for 0.2 s of every second.
            d.rectangle((0, 0, WIDTH - 1, 12), outline=1)
            self.icon_error(d, 3, 2, fill=1)
            self.text(img, (14, 0), "ERROR", self.header, 1)
            ink = 1
        elif alert.severity == ERROR:
            d.rectangle((0, 0, WIDTH - 1, 12), fill=1)
            self.icon_error(d, 3, 2, fill=0)
            self.text(img, (14, 0), "ERROR", self.header, 0)
            ink = 0
        else:
            d.rectangle((0, 0, WIDTH - 1, 12), outline=1)
            self.icon_warning(d, 3, 2, fill=1)
            self.text(img, (15, 0), "WARNING", self.header, 1)
            ink = 1
        if total > 1:
            count = "%d of %d" % (index + 1, total)
            self.text(img, (WIDTH - 4 - self.width(self.label, count), 1), count, self.label, ink)
        self.text(img, (2, 15), self.fit(alert.title, self.title, WIDTH - 4), self.title)
        for i, line in enumerate(alert.detail[:2]):
            self.text(img, (2, 29 + i * 10), self.fit(line, self.body, WIDTH - 4), self.body)
        self.status_line(img, d, t, st.ip or "No IP address", heartbeat=True)
        return img

    def boot(self, st, t, animate=True):
        """While Linux starts: the MBot is put together part by part."""
        img, d = self.new()
        x0 = 4
        if animate:
            parts, drops, done = sprites.assembly(t)
            robot = sprites.mbot_image(lidar_angle=t * 9.0 if done else 0.0, parts=parts, drops=drops)
            sprites.paste(img, robot, 2, STATUS_Y - sprites.SPRITE_H - 2)
            x0 = 56
        self.text(img, (x0, 4), "MBot", self.brand)
        self.text(img, (x0, 22), "Starting up", self.body)
        # Indeterminate progress bar: a block sweeping across a frame.
        bar_w = WIDTH - x0 - 4
        d.rectangle((x0, 35, x0 + bar_w, 40), outline=1)
        block = 14
        travel = bar_w - block - 4
        pos = int((t * 40) % (2 * travel))
        if pos > travel:
            pos = 2 * travel - pos
        d.rectangle((x0 + 2 + pos, 37, x0 + 2 + pos + block, 38), fill=1)
        self.status_line(img, d, t, "Network ready" if st.ip else "Waiting for network", heartbeat=False)
        return img

    def bye(self, st, t):
        """Shutdown animation (BYE_S seconds): the MBot says bye and falls asleep."""
        img, d = self.new()
        x, y = 4, GROUND_Y - sprites.SPRITE_H + 1
        d.line((0, GROUND_Y, x + sprites.SPRITE_W + 4, GROUND_Y), fill=1)

        # The LiDAR slows down and stops within 0.8 s; the robot nods once.
        spin = min(t, 0.8)
        robot = sprites.mbot_image(lidar_angle=5.2 * (spin - spin * spin / 1.6),
                                   body_dy=1 if 0.7 <= t < 0.9 else 0)
        sprites.paste(img, robot, x, y)

        # "Bye!" is typed in, then "Shutting down" wipes in from the left.
        word = "Bye!"[:max(0, min(4, int((t - 0.1) / 0.15) + 1))] if t >= 0.1 else ""
        self.text(img, (62, 9), word, self.brand)
        if t >= 0.9:
            self.text(img, (62, 30), "Shutting down", self.body)
            wipe = 62 + int(66 * min(1.0, (t - 0.9) / 0.4))
            if wipe < WIDTH:
                d.rectangle((wipe, 30, WIDTH - 1, 41), fill=0)

        # Two z's float up from the LiDAR and stay there.
        for start, (zx, zy), font in ((1.2, (x + 33, 1), self.body), (1.5, (x + 40, -1), self.label)):
            if t >= start:
                rise = int(4 * (1 - min(1.0, (t - start) / 0.3)))
                self.text(img, (zx, zy + rise), "z" if font is self.body else "Z", font)

        # No heartbeat: this frame stays on the OLED after the service has stopped.
        self.status_line(img, d, t, st.hostname, heartbeat=False)
        return img

    def shutdown(self, st):
        """Last frame, left on the OLED after the service stops."""
        return self.bye(st, BYE_S)
