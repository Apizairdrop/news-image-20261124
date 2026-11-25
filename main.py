#!/usr/bin/env python3
"""news-image-20261124: sum up the world news of Tuesday 24 November 2026
in one 1024x1024 PNG. Python 3.13, standard library only, no network,
fully deterministic (same bytes on every run).

Draws a dense newspaper front page, in code, from the research pack v2:
a masthead naming the day, the verified main story (Nvidia rally fades
24 Nov: NVDA -6% after +31% Mon on Huang's reinstatement, 23 Nov), a
schematic world map with the stories plotted, 15 more lead stories in
four columns, a 24 Nov UTC timeline, 32 wire briefs, and a date-check
footer that dates every older story in-line (ICJ 19 Nov, COP31 22 Nov,
Huang and FIFA hosts 23 Nov). No story is dated 24 Nov unless it
happened or was first reported on 24 Nov.

Rendering is hand-rolled: a 5x7 bitmap font drawn at several scales, a
scanline polygon filler for the map, and a small PNG encoder. Nothing is
read from disk except this file, so the output is byte-identical on
every run.
"""

import hashlib
import os
import struct
import zlib
from math import cos, sin, sqrt

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 242, 232)   # newsprint
INK = (20, 30, 44)        # near-black blue
NAVY = (16, 42, 67)       # masthead bars
RED = (166, 32, 32)       # kickers, map dots
GOLD = (198, 138, 46)     # thin rules
LAND = (206, 196, 176)    # map land
LAND_LINE = (120, 110, 92)
MUTED = (96, 104, 116)
WHITE = (255, 255, 255)
CARD_LINE = (214, 204, 184)

# ---------------------------------------------------------------- 5x7 font
# Glyphs are 7 rows of 5 cells, '#' = ink. Designed for this entry: all
# text is upper-case, so only capitals, digits and punctuation are needed.
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
    "N": ("#...#", "##..#", "#.#.#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
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
    ".": (".....", ".....", ".....", ".....", ".....", ".....", "..#.."),
    ",": (".....", ".....", ".....", ".....", ".....", "..#..", ".#..."),
    ":": (".....", "..#..", ".....", ".....", ".....", "..#..", "....."),
    ";": (".....", "..#..", ".....", ".....", "..#..", "..#..", ".#..."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": ("....#", "...#.", "...#.", "..#..", "..#..", ".#...", "#...."),
    "%": ("#...#", "#..#.", "...#.", "..#..", ".#...", "#..#.", "#...#"),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "+": (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    "=": (".....", ".....", ".###.", ".....", ".###.", ".....", "....."),
    "&": (".###.", "#...#", "#.#.#", ".#.#.", "#.#.#", "#..#.", ".##.#"),
    "$": ("..#..", ".####", "#.#.#", ".###.", "..#.#", "####.", "..#.."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "*": (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
    "<": ("....#", "...#.", "..#..", ".#...", "..#..", "...#.", "....#"),
    ">": ("#....", ".#...", "..#..", "...#.", "..#..", ".#...", "#...."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "[": (".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    "]": (".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
}


def text_width(s, scale):
    """Pixel width of s at scale (6 cells advance per glyph)."""
    return len(s) * 6 * scale


def wrap(text, max_chars):
    """Greedy word wrap to lines of at most max_chars characters."""
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            while len(w) > max_chars:  # hard-split an over-long word
                lines.append(w[:max_chars])
                w = w[max_chars:]
            if not cur:
                cur = w
            elif len(cur) + 1 + len(w) <= max_chars:
                cur += " " + w
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set_px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def fill_rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def hline(self, x0, x1, y, c):
        if x1 < x0:
            x0, x1 = x1, x0
        self.fill_rect(x0, y, x1 - x0 + 1, 1, c)

    def vline(self, x, y0, y1, c):
        if y1 < y0:
            y0, y1 = y1, y0
        self.fill_rect(x, y0, 1, y1 - y0 + 1, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set_px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def rect(self, x, y, w, h, c):
        self.hline(x, x + w - 1, y, c)
        self.hline(x, x + w - 1, y + h - 1, c)
        self.vline(x, y, y + h - 1, c)
        self.vline(x + w - 1, y, y + h - 1, c)

    def filled_circle(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = int(sqrt(r * r - dy * dy))
            self.hline(cx - dx, cx + dx, cy + dy, c)

    def circle(self, cx, cy, r, c):
        steps = max(8, int(2 * 3.14159 * r))
        prev = None
        for i in range(steps + 1):
            a = 2 * 3.14159 * i / steps
            p = (int(cx + r * cos(a)), int(cy + r * sin(a)))
            if prev is not None:
                self.line(prev[0], prev[1], p[0], p[1], c)
            prev = p

    def fill_polygon(self, pts, c):
        """Scanline fill of a simple polygon (integer coords)."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.hline(int(xs[k]), int(xs[k + 1]), y, c)

    def draw_text(self, x, y, s, scale, c, bold=False):
        """Draw upper-case text; unknown chars render as space.

        Bold draws each ink cell one pixel larger in both directions,
        so strokes thicken uniformly instead of smearing sideways.
        """
        s = s.upper()
        cell = scale + 1 if bold else scale
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for gy in range(7):
                row = glyph[gy]
                for gx in range(5):
                    if row[gx] == "#":
                        self.fill_rect(x + gx * scale, y + gy * scale,
                                       cell, cell, c)
            x += 6 * scale
        return x

    def text_at(self, x, y, s, scale, c, align="left", bold=False):
        w = text_width(s, scale)
        if align == "center":
            x -= w // 2
        elif align == "right":
            x -= w
        return self.draw_text(x, y, s, scale, c, bold=bold)

    def rule(self, x, y, w, c=INK, thick=1):
        self.fill_rect(x, y, w, thick, c)


# ---------------------------------------------------------------- PNG out
def write_png(cv, path):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return png

# ---------------------------------------------------------------- world map
# Schematic continents as (lon, lat) polygons, equirectangular. Rough
# outlines only: the strip is labelled a schematic map, and the red dots
# mark where the stories happened.
CONTINENTS = [
    # North America
    [(-168, 66), (-150, 70), (-130, 71), (-110, 73), (-95, 80), (-85, 66),
     (-75, 62), (-65, 60), (-55, 52), (-60, 46), (-70, 42), (-75, 35),
     (-81, 26), (-87, 21), (-97, 16), (-105, 20), (-114, 29), (-124, 40),
     (-140, 60), (-160, 58)],
    # South America
    [(-79, 9), (-72, 12), (-62, 10), (-52, 5), (-44, -3), (-35, -8),
     (-40, -20), (-48, -28), (-58, -35), (-65, -45), (-70, -52), (-73, -40),
     (-72, -20), (-77, -12), (-81, -5)],
    # Europe
    [(-11, 36), (-9, 43), (-2, 48), (2, 51), (8, 57), (18, 56), (21, 55),
     (24, 58), (28, 60), (30, 70), (25, 71), (15, 69), (10, 64), (5, 60),
     (-5, 57), (-10, 50)],
    # Africa
    [(-6, 35), (0, 36), (10, 37), (20, 32), (32, 31), (35, 28), (39, 21),
     (43, 12), (48, 11), (51, 10), (41, 0), (40, -10), (35, -18),
     (32, -26), (26, -34), (20, -35), (17, -29), (14, -22), (12, -10),
     (9, 4), (4, 6), (-8, 4), (-13, 8), (-17, 15), (-16, 20), (-15, 27),
     (-10, 31)],
    # Asia (incl. Middle East)
    [(28, 71), (40, 68), (55, 69), (70, 72), (90, 75), (110, 74),
     (130, 72), (150, 70), (162, 66), (170, 66), (178, 65), (170, 60),
     (162, 58), (156, 51), (142, 45), (140, 38), (130, 33), (127, 35),
     (122, 28), (120, 22), (112, 22), (108, 18), (105, 9), (100, 7),
     (97, 16), (92, 21), (88, 22), (80, 13), (77, 8), (72, 20), (66, 25),
     (61, 25), (57, 26), (52, 28), (48, 30), (44, 29), (40, 36), (36, 36),
     (30, 36), (28, 41), (28, 45), (28, 55)],
    # Australia
    [(114, -22), (122, -14), (130, -12), (136, -12), (142, -11), (146, -19),
     (150, -23), (153, -27), (150, -37), (146, -39), (140, -38),
     (135, -35), (129, -32), (124, -33), (118, -35), (114, -30)],
    # United Kingdom
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (-1, 51)],
    # Japan
    [(130, 31), (133, 34), (137, 35), (140, 38), (142, 42), (144, 44),
     (141, 45), (140, 40), (137, 37), (133, 34)],
    # Indonesia
    [(95, 5), (100, 0), (105, -5), (110, -7), (115, -8), (120, -10),
     (125, -9), (130, -3), (135, -4), (140, -8), (135, -2), (128, 0),
     (120, 0), (112, -7)],
    # New Zealand
    [(167, -45), (170, -42), (173, -41), (175, -38), (178, -38),
     (176, -40), (174, -42), (171, -44)],
    # Madagascar
    [(44, -16), (47, -15), (50, -16), (50, -20), (47, -25), (44, -25),
     (43, -20)],
]

# (lon, lat, label, label dx, label dy) - dots mark the lead stories.
# Labels are drawn at scale 1; dx/dy keep them off the dot and off land.
MAP_DOTS = [
    (-100.0, 38.0, "USA", -8, -12),
    (-74.0, 4.6, "COLOMBIA", -52, 4),
    (-88.9, 13.7, "EL SALVADOR", -58, -12),
    (-1.0, 52.0, "UK", -4, -12),
    (31.0, 49.0, "KYIV", -26, -12),
    (20.0, 32.1, "BENGHAZI", -10, 10),
    (34.5, 31.5, "GAZA", 8, -12),
    (46.7, 24.6, "RIYADH", -52, 4),
    (44.2, 15.3, "ADEN", -34, 10),
    (56.5, 26.5, "HORMUZ", -8, 12),
    (32.8, 39.9, "ANKARA", -48, -12),
    (25.0, -2.0, "CONGO", -12, -12),
    (-17.4, 14.7, "DAKAR", -30, 8),
    (90.4, 23.8, "DHAKA", -12, -12),
    (96.0, 21.9, "MYANMAR", -52, -12),
    (106.8, -6.2, "JAKARTA", -52, 4),
    (105.8, 21.0, "HANOI", -8, -12),
    (116.4, 39.9, "BEIJING", -52, -12),
    (127.0, 37.5, "SEOUL", -8, -12),
    (139.7, 35.7, "TOKYO", -34, 4),
]

# ---------------------------------------------------------------- content
# All facts from the research pack; every date is the date the story
# happened or was first reported. Headlines and summaries are capped so
# they fit their columns (headlines <= 42 chars, summaries <= 42 chars
# in the 4-column lead grid; main story is full width). Every wrapped
# line is at most 19 characters so it fits its 239px column at scale 2
# (12px per character); briefs wrap at 15 characters for their 190px
# columns.
MAIN = {
    "kicker": "MARKETS - UNITED STATES - 24 NOV 2026",
    "headline": ["NVIDIA RALLY FADES",
                 "NVDA -6% AFTER +31%"],
    "summary": ("NVDA -6% TUE AFTER +31% MON ON HUANG REINSTATEMENT AS CEO "
                "ON 23 NOV AFTER TRUMP PRESSURE. NASDAQ -1.5%, S&P -0.5%, "
                "DOW +0.9%."),
    "source": "REUTERS / INVESTOPEDIA / CNA",
}

# (headline, summary, source + date) - leads 2..16, in research-pack order.
LEADS = [
    ("HUAWEI GUILTY ON 10 OF 12",
     "TRADE-SECRET THEFT, BANK FRAUD.",
     "24 NOV 20:41 UTC"),
    ("FOUR TANKERS HIT IN HORMUZ",
     "IRGC: MINES HIT 4 TANKERS; FIRE.",
     "24 NOV 00:00 UTC"),
    ("UKRAINE HITS RUSSIAN SHIPS",
     "DRONES OFF LIBYA; CORVETTE SUNK.",
     "REUTERS - 24 NOV"),
    ("SENEGAL AFCON TITLE RESTORED",
     "CAS OVERTURNS CAF; 1-0 STANDS.",
     "REUTERS - 24 NOV"),
    ("FIFA NAMES 2031 + 2035 HOSTS",
     "USA + 3 HOST 2031; UK HOSTS 2035.",
     "FIFA / AP - 23 NOV"),
    ("ISRAEL KILLS HAMAS SECURITY",
     "GEN. ABU NAHEL +6 KILLED IN GAZA.",
     "REUTERS - 24 NOV"),
    ("SAUDI PIF TOWER HIT IN RIYADH",
     "DRONE WOUNDS 11+; 2ND IN A WEEK.",
     "24 NOV 14:27 UTC"),
    ("HOUTHIS 60 KM FROM ADEN",
     "READY TO ATTACK; LINE BUILT.",
     "24 NOV"),
    ("COLOMBIA: HOSTAGES + CAR BOMB",
     "25 HELD; CAR BOMB WOUNDS 23.",
     "24 NOV"),
    ("TURKISH HELICOPTER CRASH",
     "AS-532 DOWN; 5 CREW KILLED.",
     "24 NOV 19:52 UTC"),
    ("HANOI RESTAURANT BLAST",
     "GAS LEAK BLAST KILLS 6+.",
     "24 NOV"),
    ("INDONESIA VP SUCCESSION",
     "PRABOWO NAMES 2 TO REPLACE GIBRAN.",
     "24 NOV 02:38 UTC"),
    ("PENTAGON REBUKES CANADA",
     "ONLY 41.9% OF FLEET FLYABLE.",
     "24 NOV 01:03 UTC"),
    ("COP31 COLLAPSES, NO DEAL",
     "LONGEST COP ENDS IN ANTALYA.",
     "AP - SUN 22 NOV"),
    ("ICJ: MYANMAR GUILTY",
     "GENOCIDE VS ROHINGYA, 9-6.",
     "ICJ - THU 19 NOV"),
]

MARKETS = [
    "MARKETS - TUE 24 NOV",
    "DOW +0.9% 50,018",
    "S&P -0.5% 7,201",
    "NASDAQ -1.5% 23,734",
    "NVDA -6% BTC 59.5K",
]

# (time, label) - first-reported UTC times on 24 Nov 2026.
TIMELINE = [
    ("00:00", "HORMUZ"),
    ("02:38", "JAKARTA"),
    ("08:14", "LIBYA"),
    ("11:40", "GAZA"),
    ("14:27", "RIYADH"),
    ("19:52", "ANKARA"),
    ("20:41", "HUAWEI"),
]

# 32 wire briefs, each at most 30 chars so it fits two lines in a
# five-column grid.
BRIEFS = [
    "VANCE + RUBIO MEET QATAR PM",
    "US BLACKLISTS MEGASPEED + 6",
    "NATO VOWS SPACE DEFENCE",
    "ZELENSKY SEEKS 4-PARTY TALKS",
    "ZAPORIZHZHIA HIT; 2 KILLED",
    "7 BACK EU VISA CURBS ON RUSSIA",
    "UN PROBE CALL ON BENGHAZI",
    "700K+ RUSSIANS KILLED IN WAR",
    "HAFTAR VISITS TURKEY 1ST TIME",
    "UK SANCTIONS HOUTHIS + 4",
    "GAZA MENINGITIS ALERT",
    "IRAQ SEIZES KURD OILFIELDS",
    "DR CONGO PLANE MISSING",
    "CHINA SENTENCES SPY TO DEATH",
    "EL CHAPO ISIDRO CAPTURED",
    "BUKELE: 3 SOLDIERS KILLED",
    "S. KOREA SCRAMBLES JETS",
    "HASINA TO RETURN 16 DEC",
    "MALAYSIA TO RETURN MIGRANTS",
    "CHINA EASES MINERAL CURBS",
    "SOLOMONS TO SWAP CHINA PACT",
    "RUSSIA WARNS ESTONIA",
    "ZAMBIA OPP. CHIEF CHARGED",
    "DHAKA GARMENT PAY PROTEST",
    "TAIWAN VOTES SATURDAY",
    "NORWAY SENDS DESNA TO KYIV",
    "S. KOREA PAYS TO CATCH CHEATS",
    "MICROSOFT CODE RED OUTAGE",
    "US CONFIDENCE AT 2-YEAR HIGH",
    "HERRO 32 AS BUCKS END SKID",
    "BITCOIN $59.5K; NOV -25%",
    "ANTHROPIC -6.5% BELOW IPO",
]

FOOTER_DATE = ("TUESDAY 24 NOVEMBER 2026. STORIES DATED AS MARKED: "
               "COP31 COLLAPSE 22 NOV; HUANG REINSTATEMENT + FIFA HOSTS "
               "23 NOV; ICJ MYANMAR RULING 19 NOV; ALL OTHER HEADLINES "
               "FIRST REPORTED 24 NOV 2026 (UTC TIMES SHOWN).")
FOOTER_SOURCES = ("SOURCES: DAILY SUMMARY OF (30 STORIES, 64 SOURCES), "
                  "REUTERS, AP, JUST SECURITY, FIFA, CAS, INVESTOPEDIA, "
                  "CNA, UN NEWS, BBC, KYIV INDEPENDENT.")

# ---------------------------------------------------------------- layout
MX = 16            # side margin
CW = 992           # content width (1024 - 2*16)
RX = MX + CW       # right edge (1008)


def draw_masthead(cv):
    cv.fill_rect(0, 0, W, 6, NAVY)
    # Small globe pictogram at the left of the masthead.
    gx, gy, gr = 46, 33, 21
    cv.circle(gx, gy, gr, NAVY)
    cv.circle(gx, gy, gr - 7, NAVY)
    cv.line(gx - gr, gy, gx + gr, gy, NAVY)
    cv.line(gx, gy - gr, gx, gy + gr, NAVY)
    cv.text_at(W // 2, 14, "THE WORLD IN ONE DAY", 5, INK, align="center",
               bold=True)
    cv.text_at(RX, 30, "VOL. I - NO. 328", 2, MUTED, align="right")
    cv.text_at(MX, 64, "16 LEAD STORIES", 2, MUTED)
    cv.text_at(W // 2, 60, "TUESDAY, 24 NOVEMBER 2026", 3, INK,
               align="center", bold=True)
    cv.text_at(RX, 64, "32 BRIEFS - 10 REGIONS", 2, MUTED, align="right")
    cv.rule(MX, 86, CW, GOLD, 2)


def draw_main(cv):
    y = 94
    cv.draw_text(MX, y, MAIN["kicker"], 2, RED, bold=True)
    y = 112
    for ln in MAIN["headline"]:
        cv.draw_text(MX, y, ln, 4, INK, bold=True)
        y += 30
    y = 176
    for ln in wrap(MAIN["summary"], 78):
        cv.draw_text(MX, y, ln, 2, INK)
        y += 15
    cv.draw_text(MX, 210, MAIN["source"], 2, MUTED)
    cv.rule(MX, 232, CW, NAVY, 2)


def draw_map(cv):
    cv.draw_text(MX, 240, "THE WORLD TODAY - WHERE THE NEWS HAPPENED",
                 2, INK, bold=True)
    cv.text_at(RX, 240, "RED DOTS MARK THE STORIES", 2, RED, align="right")
    x0, y0, mw, mh = MX, 258, CW, 88
    cv.rect(x0, y0, mw, mh, CARD_LINE)

    def proj(lon, lat):
        return (x0 + int((lon + 170) / 360.0 * mw),
                y0 + int((75 - lat) / 135.0 * mh))

    for poly in CONTINENTS:
        pts = [proj(lon, lat) for lon, lat in poly]
        cv.fill_polygon(pts, LAND)
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            cv.line(a[0], a[1], b[0], b[1], LAND_LINE)
    for lon, lat, label, dx, dy in MAP_DOTS:
        px, py = proj(lon, lat)
        cv.filled_circle(px, py, 4, WHITE)
        cv.filled_circle(px, py, 3, RED)
        cv.draw_text(px + dx, py + dy, label, 1, INK)
    cv.rule(MX, 354, CW, NAVY, 2)


def draw_leads(cv):
    cv.draw_text(MX, 362, "THE DAY IN FULL - 15 MORE STORIES", 2, INK,
                 bold=True)
    cv.text_at(RX, 362, "ALL DATES AS REPORTED", 2, MUTED, align="right")
    col_w, gap, row_h, y0 = 239, 12, 76, 380
    # Light column and row separators.
    for r in range(1, 4):
        cv.rule(MX, y0 + r * row_h, CW, CARD_LINE, 1)
    for c in range(1, 4):
        x = MX + c * (col_w + gap) - gap // 2
        cv.vline(x, y0, y0 + 4 * row_h - 2, CARD_LINE)
    for idx, (head, summ, src) in enumerate(LEADS):
        r, c = divmod(idx, 4)
        x = MX + c * (col_w + gap)
        y = y0 + r * row_h
        for ln in wrap(head, 19)[:2]:
            cv.draw_text(x, y, ln, 2, INK, bold=True)
            y += 15
        for ln in wrap(summ, 19)[:2]:
            cv.draw_text(x, y, ln, 2, INK)
            y += 15
        cv.draw_text(x, y, src, 2, RED)
    # 16th cell: the markets box.
    x = MX + 3 * (col_w + gap)
    y = y0 + 3 * row_h
    cv.rect(x - 4, y - 4, col_w + 8, row_h + 2, NAVY)
    cv.draw_text(x, y, MARKETS[0], 2, RED, bold=True)
    y += 15
    for ln in MARKETS[1:]:
        cv.draw_text(x, y, ln, 2, INK)
        y += 15
    cv.rule(MX, 692, CW, NAVY, 2)


def draw_timeline(cv):
    n = len(TIMELINE)
    centers = [MX + int((i + 0.5) * CW / n) for i in range(n)]
    for cx, (date, label) in zip(centers, TIMELINE):
        cv.text_at(cx, 700, date, 2, RED, align="center", bold=True)
    cv.rule(MX, 722, CW, INK, 2)
    for cx in centers:
        cv.filled_circle(cx, 723, 4, RED)
    for cx, (date, label) in zip(centers, TIMELINE):
        cv.text_at(cx, 732, label, 2, INK, align="center")
    cv.rule(MX, 752, CW, NAVY, 2)


def draw_briefs(cv):
    cv.draw_text(MX, 760, "THE WIRE - 32 BRIEFS FROM AROUND THE WORLD",
                 2, INK, bold=True)
    cols, col_w, gap, row_h, y0 = 5, 190, 10, 28, 778
    per_col = [7, 7, 6, 6, 6]
    i = 0
    for c in range(cols):
        x = MX + c * (col_w + gap)
        for r in range(per_col[c]):
            brief = BRIEFS[i]
            i += 1
            y = y0 + r * row_h
            cv.filled_circle(x + 3, y + 5, 2, RED)
            for ln in wrap(brief, 15)[:2]:
                cv.draw_text(x + 10, y, ln, 2, INK)
                y += 14
    cv.rule(MX, 980, CW, GOLD, 2)


def draw_footer(cv):
    y = 988
    for ln in wrap(FOOTER_DATE, 165):
        cv.draw_text(MX, y, ln, 1, INK)
        y += 9
    for ln in wrap(FOOTER_SOURCES, 165):
        cv.draw_text(MX, y, ln, 1, MUTED)
        y += 9
    cv.fill_rect(0, 1018, W, 6, NAVY)
    return y


def build():
    cv = Canvas(W, H, PAPER)
    draw_masthead(cv)
    draw_main(cv)
    draw_map(cv)
    draw_leads(cv)
    draw_timeline(cv)
    draw_briefs(cv)
    end_y = draw_footer(cv)
    return cv, end_y


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv, end_y = build()
    path = os.path.join(out_dir, "entry.png")
    png = write_png(cv, path)
    size = len(png)
    sha = hashlib.sha256(png).hexdigest()
    print("wrote %s (%dx%d, %d bytes, sha256 %s)" % (path, W, H, size, sha))
    print("footer ends at y=%d (canvas height %d)" % (end_y, H))
    assert size <= 1048576, "image over 1 MiB"
    assert end_y <= 1018, "layout overflowed the page"


if __name__ == "__main__":
    main()
