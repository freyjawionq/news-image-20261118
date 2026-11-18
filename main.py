"""THE WORLD IN ONE DAY - a deterministic newspaper front page.

Draws a newspaper-style front page summing up the world news of
Wednesday 18 November 2026 and writes it as entry.png (1024x768) into
the directory named by MAKEFUN_OUTPUT_DIR (default /output).

Standard library only. No clock, no randomness, no network: every run
writes exactly the same bytes. The PNG encoder, the framebuffer, the
drawing primitives and the 5x7 bitmap font are all implemented here.
"""

import math
import os
import struct
import zlib

WIDTH = 1024
HEIGHT = 768

PAPER = (246, 243, 236)
PANEL_BG = (252, 250, 246)
INK = (25, 25, 28)
RED = (160, 32, 32)
GRAY = (110, 108, 100)
PANEL_EDGE = (170, 165, 155)
BLUE = (30, 60, 120)

# ---------------------------------------------------------------------------
# Bitmap font: 5x7 glyphs, '#' is a lit pixel.
# ---------------------------------------------------------------------------

FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "(": ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ")": ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "%": ("##..#", "##.#.", "....#", "...#.", "..#..", ".#.##", "#..##"),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
}

GLYPH_W = 5
GLYPH_H = 7
ADVANCE = 6  # glyph width plus one column of spacing, in glyph pixels


def text_width(text, scale):
    if not text:
        return 0
    return len(text) * ADVANCE * scale - scale


def wrap_text(text, max_width, scale):
    """Greedy word wrap: returns the list of lines that fit max_width."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if text_width(trial, scale) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Framebuffer and drawing primitives.
# ---------------------------------------------------------------------------

class Canvas:
    def __init__(self, width, height, color):
        self.width = width
        self.height = height
        self.pixels = bytearray(width * height * 3)
        self.fill_rect(0, 0, width, height, color)

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.pixels[i] = color[0]
            self.pixels[i + 1] = color[1]
            self.pixels[i + 2] = color[2]

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.width + x0) * 3
            self.pixels[i:i + len(row)] = row

    def rect_outline(self, x, y, w, h, color, thick=1):
        self.fill_rect(x, y, w, thick, color)
        self.fill_rect(x, y + h - thick, w, thick, color)
        self.fill_rect(x, y, thick, h, color)
        self.fill_rect(x + w - thick, y, thick, h, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        half = thick // 2
        while True:
            self.fill_rect(x0 - half, y0 - half, thick, thick, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def fill_circle(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            dx = math.isqrt(r * r - dy * dy)
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def circle_outline(self, cx, cy, r, color, thick=1):
        steps = max(24, int(2 * math.pi * r) + 1)
        for i in range(steps):
            a = 2 * math.pi * i / steps
            x = int(round(cx + r * math.cos(a)))
            y = int(round(cy + r * math.sin(a)))
            half = thick // 2
            self.fill_rect(x - half, y - half, thick, thick, color)

    def ellipse_outline(self, cx, cy, rx, ry, color):
        steps = max(24, int(2 * math.pi * max(rx, ry)) + 1)
        for i in range(steps):
            a = 2 * math.pi * i / steps
            x = int(round(cx + rx * math.cos(a)))
            y = int(round(cy + ry * math.sin(a)))
            self.set_pixel(x, y, color)

    def draw_text(self, x, y, text, scale, color):
        cx = x
        for ch in text.upper():
            glyph = FONT.get(ch, FONT[" "])
            for row in range(GLYPH_H):
                bits = glyph[row]
                for col in range(GLYPH_W):
                    if bits[col] == "#":
                        self.fill_rect(cx + col * scale, y + row * scale,
                                       scale, scale, color)
            cx += ADVANCE * scale
        return cx - scale

    def draw_text_centered(self, y, text, scale, color):
        w = text_width(text, scale)
        return self.draw_text((self.width - w) // 2, y, text, scale, color)


# ---------------------------------------------------------------------------
# Small panel icons, drawn with the primitives above.
# ---------------------------------------------------------------------------

def icon_globe(cv, x, y, s):
    c = x + s // 2
    r = s // 2 - 1
    cv.circle_outline(c, y + s // 2, r, BLUE, 2)
    cv.ellipse_outline(c, y + s // 2, r, max(2, r // 3), BLUE)
    cv.ellipse_outline(c, y + s // 2, max(2, r // 3), r, BLUE)
    cv.line(x + 1, y + s // 2, x + s - 1, y + s // 2, BLUE, 1)


def icon_rocket(cv, x, y, s):
    cx = x + s // 2
    top = y + 1
    body_top = top + s // 4
    body_bot = y + s - s // 4
    # nose cone
    for i in range(s // 4):
        w = max(1, (i * (s // 3)) // max(1, s // 4))
        cv.fill_rect(cx - w // 2, top + i, w, 1, RED)
    # body
    cv.fill_rect(cx - s // 6, body_top, s // 3, body_bot - body_top, BLUE)
    # porthole
    cv.fill_circle(cx, (body_top + body_bot) // 2, max(2, s // 10), PAPER)
    # fins
    for i in range(s // 5):
        cv.fill_rect(cx - s // 6 - 1 - i // 2, body_bot - s // 5 + i, 2, 1, RED)
        cv.fill_rect(cx + s // 6 - 1 + i // 2, body_bot - s // 5 + i, 2, 1, RED)
    # flame
    for i in range(s // 5):
        w = max(1, s // 6 - i)
        cv.fill_rect(cx - w // 2, body_bot + i, w, 1, RED)


def icon_ballot(cv, x, y, s):
    box_y = y + s // 2
    # paper above the slot
    cv.rect_outline(x + s // 3, y + 1, s // 3, s // 3, INK, 1)
    cv.line(x + s // 3 + 2, y + s // 6, x + s // 2, y + s // 3 - 2, RED, 1)
    cv.line(x + s // 2, y + s // 3 - 2, x + 2 * s // 3 - 2, y + 3, RED, 1)
    # box
    cv.rect_outline(x + 2, box_y, s - 4, s // 2 - 1, BLUE, 2)
    cv.fill_rect(x + s // 4, box_y + 3, s // 2, 2, INK)


def icon_storm(cv, x, y, s):
    cx = x + s // 2
    cy = y + s // 2
    turns = 3
    steps = 90
    for i in range(steps + 1):
        a = turns * 2 * math.pi * i / steps
        r = (s // 2 - 1) * i / steps
        px = int(round(cx + r * math.cos(a)))
        py = int(round(cy + r * math.sin(a)))
        cv.fill_rect(px - 1, py - 1, 2, 2, BLUE)
    cv.fill_circle(cx, cy, 2, RED)


ICON_FOR = {"a": icon_globe, "b": icon_rocket, "e": icon_ballot,
            "h": icon_storm}

# ---------------------------------------------------------------------------
# Page content: the world news of Wednesday 18 November 2026, as reported
# during that day (sources are listed in SOURCES.md).
# ---------------------------------------------------------------------------

MASTHEAD = "THE WORLD IN ONE DAY"
DATELINE = "WEDNESDAY 18 NOVEMBER 2026"
LEAD_HEAD = "US STRIKES IRAN MISSILE SITE ON QESHM"
LEAD_SUB = "IRAN FIRES DRONES AT BAHRAIN AND KUWAIT IN REPLY"

PANELS = [
    ("a", "TRUMP LANDS IN SHENZHEN FOR SUMMIT",
     "THREE-WAY TALKS WITH XI AND PUTIN SET FOR THURSDAY"),
    ("b", "VOYAGER 1 REACHES ONE LIGHT-DAY",
     "FIRST HUMAN-MADE OBJECT TO CROSS THE MARK, SAYS NASA"),
    ("c", "US LOSES MEASLES-FREE STATUS",
     "5,412 CASES IN 2026, MOST SINCE 1991; STATUS HELD 26 YEARS"),
    ("d", "CONGO EBOLA PASSES 11,000 CASES",
     "OUTBREAK DOUBLES IN THREE MONTHS, SECOND-LARGEST EVER"),
    ("e", "PELTOLA WIN SEALS SENATE FOR DEMOCRATS",
     "ALASKA FLIP GIVES A 56-44 MAJORITY"),
    ("f", "UKRAINE HITS KERCH BRIDGE SECOND DAY",
     "ROAD SPAN PARTLY COLLAPSES INTO THE STRAIT"),
    ("g", "RUSSIAN MILITARY PLANE CRASH KILLS 19",
     "AIRCRAFT COMES DOWN IN SIBERIA"),
    ("h", "CYCLONE XAVIER HITS COOK ISLANDS",
     "CATEGORY 5 STORM MAKES LANDFALL IN THE NORTH"),
]

FOOTER = "SOURCES IN SOURCES.MD - DRAWN BY PROGRAM, NO PHOTOS"


def draw_panel(cv, x, y, w, h, key, head, sub):
    cv.fill_rect(x, y, w, h, PANEL_BG)
    cv.rect_outline(x, y, w, h, PANEL_EDGE, 1)
    cv.fill_rect(x, y, w, 3, RED)
    head_lines = wrap_text(head, w - 20, 2)
    ty = y + 10
    for line_text in head_lines:
        cv.draw_text(x + 10, ty, line_text, 2, INK)
        ty += (GLYPH_H + 2) * 2
    ty += 2
    for line_text in wrap_text(sub, w - 20, 1):
        cv.draw_text(x + 10, ty, line_text, 1, GRAY)
        ty += GLYPH_H + 2
    icon = ICON_FOR.get(key)
    if icon is not None:
        icon(cv, x + w - 40, y + h - 40, 30)


def render():
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    # page frame
    cv.rect_outline(12, 12, WIDTH - 24, HEIGHT - 24, INK, 2)
    cv.rect_outline(19, 19, WIDTH - 38, HEIGHT - 38, GRAY, 1)
    # masthead
    cv.draw_text_centered(34, MASTHEAD, 7, INK)
    cv.fill_rect(40, 100, WIDTH - 80, 3, RED)
    cv.fill_rect(40, 106, WIDTH - 80, 1, INK)
    cv.draw_text_centered(114, DATELINE, 3, RED)
    cv.fill_rect(40, 142, WIDTH - 80, 1, INK)
    # lead story
    cv.draw_text_centered(154, LEAD_HEAD, 4, INK)
    cv.draw_text_centered(196, LEAD_SUB, 2, RED)
    cv.fill_rect(40, 224, WIDTH - 80, 2, INK)
    cv.fill_circle(WIDTH // 2, 225, 3, RED)
    # story panels: two columns, four rows
    col_x = (40, 520)
    col_w = 464
    row_y = (234, 360, 486, 612)
    row_h = 116
    for i, (key, head, sub) in enumerate(PANELS):
        px = col_x[i % 2]
        py = row_y[i // 2]
        draw_panel(cv, px, py, col_w, row_h, key, head, sub)
    # footer
    cv.draw_text_centered(731, FOOTER, 2, GRAY)
    return cv


# ---------------------------------------------------------------------------
# PNG writer: signature, IHDR, one IDAT of filter-0 scanlines, IEND.
# ---------------------------------------------------------------------------

def png_chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def encode_png(cv):
    raw = bytearray()
    stride = cv.width * 3
    for y in range(cv.height):
        raw.append(0)
        start = y * stride
        raw += cv.pixels[start:start + stride]
    ihdr = struct.pack(">IIBBBBB", cv.width, cv.height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + png_chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(render())
    with open(os.path.join(out_dir, "entry.png"), "wb") as fh:
        fh.write(data)


if __name__ == "__main__":
    main()
