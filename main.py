#!/usr/bin/env python3
"""The World Today - one-page front page summing up Saturday 21 November 2026.

Draws a 1024x1024 PNG newspaper front page using ONLY the Python standard
library: masthead, two lead panels, 36 verified stories in six regional
sections, and a world map strip with numbered markers for twelve of the
stories. No PIL, no third-party imports at all: a hand-rolled pixel buffer,
drawing primitives, a hand-drawn 5x7 bitmap font and a struct+zlib PNG
encoder. Deterministic: all text is baked in, no randomness, no network,
no clock reads.

Run:  python3 main.py
Writes entry.png to $MAKEFUN_OUTPUT_DIR (default /output).
"""

import math
import os
import struct
import zlib

W = H = 1024

PAPER = (246, 241, 231)
INK = (20, 20, 20)
NAVY = (16, 36, 62)
RED = (166, 30, 34)
GREY = (90, 90, 90)
RULE = (180, 172, 150)
OCEAN = (168, 200, 221)
LAND = (216, 208, 182)
LAND_EDGE = (150, 142, 110)
SECTION_BG = (255, 255, 255)
WHITE = (255, 255, 255)
GOLD = (255, 214, 120)
CREAM = (250, 246, 236)
BODY_GREY = (60, 60, 60)
DETAIL_GREY = (70, 70, 70)
SEPARATOR = (225, 220, 205)


class Canvas:
    """An RGB pixel buffer with small drawing primitives."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)
        r, g, b = bg
        for i in range(0, len(self.buf), 3):
            self.buf[i] = r
            self.buf[i + 1] = g
            self.buf[i + 2] = b

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i] = c[0]
            self.buf[i + 1] = c[1]
            self.buf[i + 2] = c[2]

    def rect(self, x0, y0, x1, y1, c):
        """Filled rectangle; x1/y1 exclusive, clipped to the canvas."""
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        for y in range(y0, y1):
            base = (y * self.w + x0) * 3
            for x in range(x0, x1):
                i = base + (x - x0) * 3
                self.buf[i] = c[0]
                self.buf[i + 1] = c[1]
                self.buf[i + 2] = c[2]

    def hline(self, x0, x1, y, c):
        self.rect(x0, y, x1, y + 1, c)

    def line(self, x0, y0, x1, y1, c):
        """Bresenham line."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, c):
        """Filled disc of radius r."""
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(r * r - dy * dy))
            self.rect(cx - dx, cy + dy, cx + dx + 1, cy + dy + 1, c)

    def polygon(self, pts, fill, edge):
        """Even-odd scanline fill plus an outline."""
        n = len(pts)
        y0 = int(min(p[1] for p in pts))
        y1 = int(max(p[1] for p in pts))
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, yy0 = pts[i]
                x1, yy1 = pts[(i + 1) % n]
                if (yy0 <= y < yy1) or (yy1 <= y < yy0):
                    t = (y - yy0) / (yy1 - yy0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.rect(int(xs[k]), y, int(xs[k + 1]) + 1, y + 1, fill)
        for i in range(n):
            x0, y0p = pts[i]
            x1, y1p = pts[(i + 1) % n]
            self.line(int(x0), int(y0p), int(x1), int(y1p), edge)


# ------------------------------------------------------------------ font
# Hand-drawn 5x7 bitmap glyphs. Each glyph is 7 rows of 5 bits, written
# left to right, top to bottom. One blank column separates glyphs, so a
# character cell is 6 units wide and 7 units tall, scaled by `scale`.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
}
FONT.update({
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10000", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    "h": ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "10010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    "q": ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11100", "01000", "01000", "01000", "00110"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "|": ("00100", "00100", "00100", "00100", "00100", "00100", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    ">": ("10000", "01000", "00100", "00010", "00100", "01000", "10000"),
    "<": ("00001", "00010", "00100", "01000", "00100", "00010", "00001"),
})

BLANK = FONT[" "]


def clean(s):
    """Fold characters the bitmap font does not carry to ASCII lookalikes."""
    return s.replace("\u2014", "-").replace("\u2019", "'").replace("\u2018", "'")


def text_width(s, scale):
    if not s:
        return 0
    return len(s) * 6 * scale - scale


def draw_text(cv, x, y, s, colour, scale):
    s = clean(s)
    cx = x
    for ch in s:
        rows = FONT.get(ch, BLANK)
        for row in range(7):
            bits = rows[row]
            for col in range(5):
                if bits[col] == "1":
                    cv.rect(cx + col * scale, y + row * scale,
                            cx + (col + 1) * scale, y + (row + 1) * scale,
                            colour)
        cx += 6 * scale


def wrap(s, scale, max_w):
    """Greedy word wrap; returns list of lines that fit max_w."""
    words = clean(s).split()
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_line(s, scale, max_w):
    """Shorten with an ellipsis until the line fits."""
    s = clean(s)
    if text_width(s, scale) <= max_w:
        return s
    while s and text_width(s + "...", scale) > max_w:
        s = s[:-1]
    return s + "..."


def centre(cv, y, s, colour, scale, x0=0, x1=W):
    draw_text(cv, (x0 + x1 - text_width(s, scale)) // 2, y, s, colour, scale)


# -------------------------------------------------------------------- PNG
def _chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def encode_png(cv):
    """Encode the canvas as a PNG (filter 0 on every row, zlib level 9)."""
    raw = bytearray()
    row_bytes = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.buf[y * row_bytes:(y + 1) * row_bytes]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))

# ---------------------------------------------------------------- stories
# (number, headline, detail) - every story verified against reports
# published 20-21 November 2026.
SECTIONS = [
    ("EUROPE", (31, 78, 121), [
        (1, "Russian missiles land in Poland",
         "Tusk calls it a deliberate provocation"),
        (2, "Night barrage pounds Kyiv",
         "Eight killed as bridges are struck"),
        (3, "UK and EU sign three new deals",
         "Food, carbon markets, youth mobility"),
        (4, "EU approves 1bn euros for Kyiv",
         "Joint buys via Peace Facility by 2027"),
        (5, "Britain pledges 1,000 drones",
         "260m-pound package for Ukraine's defence"),
        (6, "Gen Z rallies sweep 25 nations",
         "Costs, war and climate drive protests"),
    ]),
    ("MIDDLE EAST", (138, 90, 0), [
        (7, "Saudi jets down Houthi missiles",
         "Three intercepted over Riyadh"),
        (8, "Tanker hit in Strait of Hormuz",
         "Fire reported after strike, UKMTO says"),
        (9, "Israeli drones kill seven in Gaza",
         "Strikes hit central Gaza, medics say"),
        (10, "Trump: no rush on Iran decision",
         "May not decide until 2027, he says"),
        (11, "US Senate rejects Iran war powers",
         "Bid to curb strikes fails 51-48"),
        (12, "Gaza children mark Children's Day",
         "Displaced children celebrate amid war"),
    ]),
    ("AMERICAS", (30, 107, 52), [
        (13, "Wall Street slides into correction",
         "S&P falls 3.7% as AI shares plunge"),
        (14, "Trump pardons Pete Rose",
         "Posthumous pardon for late star"),
        (15, "Mamdani: close Rikers by 2032",
         "New York mayor-elect sets jail date"),
        (16, "Palisades Fire arsonist convicted",
         "LA jury finds Rinderknecht guilty"),
        (17, "Trump threatens tax on AI centres",
         "US firms warned over building abroad"),
        (18, "US sanctions Comancheros, mafia",
         "Assets blocked in crime sweep"),
    ]),
    ("ASIA-PACIFIC", (15, 118, 110), [
        (19, "World Court: Myanmar guilty",
         "Rohingya genocide ruling at The Hague"),
        (20, "Cyclone Akvan hits Odisha coast",
         "Storm crosses near Gopalpur"),
        (21, "India A crush Nepal by 306 runs",
         "Rising Stars Asia Cup, Doha"),
        (22, "India fight back in Wellington",
         "159 for 1 at stumps on day two"),
        (23, "UAE Bulls win T10 final",
         "Beat Yas Lions by 24 runs, Abu Dhabi"),
        (24, "Nepal's new PM faces India test",
         "Balendra Shah's first foreign trial"),
    ]),
    ("AFRICA", (180, 83, 9), [
        (25, "600 women killed in South Africa",
         "Deaths in three months, figures show"),
        (26, "ANC battles to hold key cities",
         "Election setback shakes ruling party"),
        (27, "Mourners drown in Nigeria boat",
         "Four killed as boat capsizes"),
        (28, "Egypt seals $2.3bn IMF deal",
         "Staff pact unlocks final funds"),
        (29, "US group wins Kenya mining deal",
         "Mrima Hill minerals beat China bid"),
        (30, "Migrant boat sinks off Senegal",
         "Dozens missing, rescuers search"),
    ]),
    ("CLIMATE, TECH & SPORT", (91, 33, 182), [
        (31, "COP31 talks stall in Antalya",
         "Draft drops fossil fuels, overtime looms"),
        (32, "Anthropic's maths breakthrough",
         "AI solves big problem as shares slide"),
        (33, "US pushes tougher AI chip rules",
         "Lawmakers target China exports"),
        (34, "Banks hit by vendor cyberattack",
         "JPMorgan, Visa, Mastercard affected"),
        (35, "Price undisputed champion",
         "Lauren Price takes welterweight crown"),
        (36, "Alcaraz unbeaten at ATP Finals",
         "Beats Cobolli in Turin group"),
    ]),
]

LEADS = [
    ("LEAD  |  EUROPE", "RUSSIAN MISSILES LAND IN POLAND",
     "Two cruise missiles and a jet drone crash near allied drills in "
     "south-east Poland. Tusk calls it a deliberate provocation; NATO's "
     "Rutte calls it a grave violation. No casualties."),
    ("LEAD  |  UKRAINE", "KYIV POUNDED IN NIGHT BARRAGE",
     "Russia's massive missile and drone attack kills eight in the "
     "capital and hits three bridges. A double-tap strike on Kryvyi Rih "
     "kills a child and a rescuer."),
]

# (story number, lon, lat, badge dx, badge dy) for the map markers.
# Badges in crowded Europe are offset from the true point with a leader line.
MARKERS = [
    (1, 19.0, 52.0, 0, 16), (2, 30.5, 50.5, 18, -10),
    (3, 4.4, 50.8, -4, 18), (5, -0.1, 51.5, -20, -12),
    (7, 46.7, 24.7, 14, 16), (8, 56.0, 26.5, 14, -10),
    (9, 34.5, 31.5, -26, 16), (13, -74.0, 40.7, 0, 0),
    (19, 4.3, 52.1, 18, -14), (20, 85.5, 19.8, 0, 0),
    (25, 28.0, -26.2, 0, 0), (31, 30.7, 36.9, 26, 4),
]

# Coarse continent outlines (lon, lat), equirectangular.
NORTH_AMERICA = [(-168, 66), (-140, 70), (-125, 72), (-110, 73), (-95, 80),
                 (-85, 70), (-75, 72), (-60, 60), (-55, 47), (-65, 44),
                 (-70, 42), (-75, 35), (-80, 26), (-85, 29), (-90, 21),
                 (-95, 18), (-100, 16), (-105, 20), (-115, 28), (-125, 40),
                 (-125, 49), (-140, 60), (-155, 58), (-165, 60)]
GREENLAND = [(-55, 60), (-45, 60), (-40, 65), (-30, 68), (-25, 70),
             (-35, 76), (-55, 76), (-60, 70)]
SOUTH_AMERICA = [(-80, 10), (-75, 11), (-70, 12), (-62, 10), (-55, 5),
                 (-50, 0), (-40, -5), (-35, -8), (-40, -20), (-48, -28),
                 (-55, -35), (-65, -45), (-70, -52), (-73, -50), (-73, -40),
                 (-72, -20), (-78, -5), (-80, 2)]
AFRICA = [(-17, 15), (-10, 30), (-5, 35), (10, 37), (20, 32), (30, 31),
          (35, 28), (40, 15), (43, 11), (48, 11), (51, 10), (45, 0),
          (40, -10), (35, -20), (30, -30), (20, -35), (15, -30), (12, -18),
          (12, -5), (9, 4), (-8, 4), (-13, 8), (-17, 12)]
EUROPE = [(-10, 36), (-9, 43), (-2, 48), (-5, 50), (0, 51), (5, 53),
          (8, 57), (10, 59), (18, 56), (21, 55), (24, 58), (28, 60),
          (30, 62), (32, 68), (40, 68), (45, 66), (40, 60), (35, 55),
          (30, 50), (28, 45), (23, 40), (19, 42), (12, 44), (8, 44),
          (3, 42), (0, 40), (-2, 37), (-9, 37)]
ASIA = [(30, 62), (40, 68), (55, 68), (70, 72), (90, 75), (110, 76),
        (130, 72), (150, 70), (170, 66), (178, 65), (170, 60), (160, 55),
        (158, 50), (150, 45), (140, 40), (135, 35), (130, 33), (127, 35),
        (122, 38), (120, 30), (115, 22), (110, 20), (108, 12), (105, 9),
        (100, 8), (97, 15), (92, 21), (88, 22), (85, 19), (80, 15),
        (77, 8), (75, 12), (72, 20), (66, 25), (62, 25), (57, 26),
        (52, 28), (50, 30), (48, 30), (44, 29), (40, 32), (36, 36),
        (33, 36), (30, 36), (28, 40), (30, 45), (30, 55)]
AUSTRALIA = [(113, -22), (114, -30), (115, -35), (120, -34), (129, -32),
             (135, -35), (140, -38), (145, -38), (150, -37), (153, -32),
             (150, -23), (146, -19), (142, -15), (142, -11), (137, -12),
             (135, -15), (132, -12), (130, -13), (126, -14), (122, -17),
             (118, -20)]
CONTINENTS = [NORTH_AMERICA, GREENLAND, SOUTH_AMERICA, AFRICA, EUROPE,
              ASIA, AUSTRALIA]

# ------------------------------------------------------------------ draw
def frame(cv, x0, y0, x1, y1, c):
    """1px outline rectangle (x1/y1 inclusive, like the old PIL outlines)."""
    cv.hline(x0, x1 + 1, y0, c)
    cv.hline(x0, x1 + 1, y1, c)
    cv.rect(x0, y0, x0 + 1, y1 + 1, c)
    cv.rect(x1, y0, x1 + 1, y1 + 1, c)


def draw_masthead(cv):
    cv.rect(0, 0, W, 108, NAVY)
    cv.rect(0, 104, W, 108, RED)
    centre(cv, 14, "THE WORLD TODAY", CREAM, 8)
    centre(cv, 74, "SATURDAY  21  NOVEMBER  2026", GOLD, 4)
    draw_text(cv, 18, 116, "36 STORIES  |  SIX REGIONS  |  ONE DAY",
              GREY, 2)
    right = "ALL STORIES REPORTED 20-21 NOVEMBER 2026"
    draw_text(cv, W - 18 - text_width(right, 2), 116, right, GREY, 2)


def draw_leads(cv):
    y0, h = 136, 128
    w = (W - 32 - 10) // 2
    for i, (kicker, head, body) in enumerate(LEADS):
        x0 = 16 + i * (w + 10)
        cv.rect(x0, y0, x0 + w, y0 + h, SECTION_BG)
        frame(cv, x0, y0, x0 + w - 1, y0 + h - 1, RULE)
        cv.rect(x0, y0, x0 + w, y0 + 24, RED)
        draw_text(cv, x0 + 10, y0 + 5, kicker, WHITE, 2)
        lines = wrap(head, 3, w - 20)
        yy = y0 + 30
        for line in lines[:2]:
            draw_text(cv, x0 + 10, yy, line, INK, 3)
            yy += 24
        blines = wrap(body, 2, w - 20)
        yy = y0 + 30 + 2 * 24 + 4
        for line in blines[:3]:
            draw_text(cv, x0 + 10, yy, line, BODY_GREY, 2)
            yy += 16


def draw_sections(cv):
    y0 = 274
    col_w = (W - 32 - 2 * 10) // 3
    row_h = 262
    for idx, (name, colour, stories) in enumerate(SECTIONS):
        col, row = idx % 3, idx // 3
        x0 = 16 + col * (col_w + 10)
        yy0 = y0 + row * (row_h + 10)
        cv.rect(x0, yy0, x0 + col_w, yy0 + row_h, SECTION_BG)
        frame(cv, x0, yy0, x0 + col_w - 1, yy0 + row_h - 1, RULE)
        cv.rect(x0, yy0, x0 + col_w, yy0 + 28, colour)
        draw_text(cv, x0 + 10, yy0 + 6, name, WHITE, 2)
        y = yy0 + 34
        for num, head, detail in stories:
            num_s = "%d." % num
            draw_text(cv, x0 + 8, y, num_s, RED, 2)
            nx = x0 + 8 + text_width("36. ", 2) + 2
            tw = x0 + col_w - 8 - nx
            draw_text(cv, nx, y, fit_line(head, 2, tw), INK, 2)
            draw_text(cv, nx, y + 17, fit_line(detail, 2, tw), DETAIL_GREY, 2)
            y += 37
            if num != stories[-1][0]:
                cv.hline(x0 + 8, x0 + col_w - 8, y - 3, SEPARATOR)


def draw_map(cv):
    y0 = 818
    h = 158
    cv.rect(16, y0, W - 16, y0 + h, OCEAN)
    frame(cv, 16, y0, W - 17, y0 + h - 1, RULE)
    draw_text(cv, 26, y0 + 6, "THE DAY ON THE MAP  -  12 STORIES MARKED",
              NAVY, 2)
    mx0, my0, mw, mh = 24, y0 + 26, W - 48, h - 32

    def proj(lon, lat):
        x = mx0 + (lon + 170.0) / 360.0 * mw
        y = my0 + (80.0 - lat) / 135.0 * mh
        return (x, y)

    for poly in CONTINENTS:
        pts = [proj(lon, lat) for lon, lat in poly]
        cv.polygon(pts, LAND, LAND_EDGE)
    for num, lon, lat, dx, dy in MARKERS:
        x, y = proj(lon, lat)
        ix, iy = int(x), int(y)
        bx, by = ix + dx, iy + dy
        cv.disc(ix, iy, 2, INK)
        if dx or dy:
            cv.line(ix, iy, bx, by, INK)
        cv.disc(bx, by, 12, WHITE)
        cv.disc(bx, by, 11, RED)
        label = str(num)
        lw = text_width(label, 2)
        draw_text(cv, bx - lw // 2, by - 7, label, WHITE, 2)


def main():
    cv = Canvas(W, H, PAPER)
    draw_masthead(cv)
    draw_leads(cv)
    draw_sections(cv)
    draw_map(cv)
    centre(cv, 984, "Compiled from published reports of 20-21 November 2026  |  "
           "The World Today  |  One day, one page", GREY, 2)
    cv.hline(16, W - 16, 980, RULE)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(cv)
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
