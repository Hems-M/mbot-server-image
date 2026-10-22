"""The MBot Classic, drawn from the side in 1-bit pixels.

The sprite is drawn with PIL primitives instead of stored bitmaps, so the wheel spokes
can turn with the distance driven and the LiDAR head can spin. It faces right; flip
the image for a robot driving to the left.

Coordinates are inside a SPRITE_W x SPRITE_H box. The tyre touches y = SPRITE_H - 1.
"""

import math

from PIL import Image, ImageDraw

SPRITE_W = 47
SPRITE_H = 38

WHEEL_CENTER = (14, 29)
WHEEL_RADIUS = 8

# Parts in the order they are put together in the boot animation (bottom to top).
PARTS = ("wheel", "caster", "base", "posts_low", "pi", "deck", "posts_up", "top", "lidar", "camera")


def _wheel(d, angle, dy):
    cx, cy = WHEEL_CENTER[0], WHEEL_CENTER[1] + dy
    r = WHEEL_RADIUS
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=1)
    d.ellipse((cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1), outline=1)  # tyre
    for k in range(3):
        a = angle + k * 2 * math.pi / 3
        d.line((cx, cy, round(cx + 5 * math.cos(a)), round(cy + 5 * math.sin(a))), fill=1)
    d.ellipse((cx - 1, cy - 1, cx + 1, cy + 1), fill=1)


def _caster(d, dy):
    d.line((37, 30 + dy, 37, 32 + dy), fill=1)
    d.ellipse((35, 33 + dy, 39, 37 + dy), outline=1)


def _base(d, dy):
    d.rectangle((2, 22 + dy, 43, 24 + dy), outline=1, fill=1)


def _posts_low(d, dy):
    for x in (4, 41):
        d.line((x, 16 + dy, x, 21 + dy), fill=1)


def _pi(d, dy):
    # Raspberry Pi between the two plates, with USB ports at the back.
    d.rectangle((12, 17 + dy, 32, 20 + dy), outline=1)
    d.rectangle((14, 18 + dy, 17, 19 + dy), fill=1)
    d.rectangle((26, 18 + dy, 30, 19 + dy), fill=1)


def _deck(d, dy):
    d.rectangle((2, 13 + dy, 43, 15 + dy), outline=1, fill=1)


def _posts_up(d, dy):
    for x in (8, 37):
        d.line((x, 9 + dy, x, 12 + dy), fill=1)


def _top(d, dy):
    d.rectangle((6, 7 + dy, 39, 8 + dy), fill=1)


def _lidar(d, angle, dy):
    d.rectangle((15, 1 + dy, 29, 6 + dy), outline=1)
    d.line((16, 4 + dy, 28, 4 + dy), fill=1)
    # The laser window turns with the head: visible on the front half of the turn.
    s = math.sin(angle)
    if s > -0.2:
        x = round(22 + 5 * math.cos(angle))
        d.rectangle((x - 1, 2 + dy, x + 1, 3 + dy), fill=1)


def _camera(d, dy):
    d.rectangle((44, 14 + dy, 46, 18 + dy), outline=1)
    d.point((45, 16 + dy), fill=1)


_STATIC_PARTS = {
    "caster": _caster, "base": _base, "posts_low": _posts_low, "pi": _pi,
    "deck": _deck, "posts_up": _posts_up, "top": _top, "camera": _camera,
}


def mbot_image(wheel_angle=0.0, lidar_angle=0.0, parts=PARTS, drops=None, facing_right=True,
               body_dy=0):
    """Return a 1-bit SPRITE_W x SPRITE_H image of the robot.

    parts: which parts to draw. drops: optional {part: dy} to draw a part higher
    (negative dy) for the assembly animation. body_dy moves everything above the
    wheels down by that many pixels (the robot dipping when it brakes or nods).
    """
    drops = drops or {}
    img = Image.new("1", (SPRITE_W, SPRITE_H), 0)
    d = ImageDraw.Draw(img)
    for part in PARTS:
        if part not in parts:
            continue
        dy = int(drops.get(part, 0))
        if part not in ("wheel", "caster"):
            dy += int(body_dy)
        if part == "wheel":
            _wheel(d, wheel_angle, dy)
        elif part == "lidar":
            _lidar(d, lidar_angle, dy)
        else:
            _STATIC_PARTS[part](d, dy)
    if not facing_right:
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return img


def paste(frame, sprite, x, y):
    """Draw a sprite onto a frame; black sprite pixels stay transparent."""
    frame.paste(1, (int(x), int(y)), mask=sprite)


def assembly(t, step=0.35, fall=18):
    """Parts and drop offsets of the boot animation at time t (seconds).

    Part i starts falling at i * step and lands one step later. Returns (parts, drops,
    done) where done is True once every part has landed.
    """
    parts, drops = [], {}
    for i, part in enumerate(PARTS):
        start = i * step
        if t < start:
            break
        p = min(1.0, (t - start) / step)
        parts.append(part)
        drops[part] = -fall * (1.0 - p) ** 2  # ease out: fast at first, slow landing
    done = t >= len(PARTS) * step
    return parts, drops, done
