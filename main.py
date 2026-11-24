#!/usr/bin/env python3
"""news-image-20261124: sum up the world news of Tuesday 24 November 2026
in one 1024x1024 PNG. Python 3.13, standard library only, no network,
fully deterministic (same bytes on every run).

Draws a dense newspaper front page, in code, from the research pack:
a masthead naming the day, the verified main story (Huang reinstated at
Nvidia, shares +31%, 23 Nov), a schematic world map with the stories
plotted, 15 more lead stories in four columns, a 17-24 Nov UTC timeline,
32 wire briefs, and a date-check footer that dates every older story
in-line (ICJ 19 Nov, Kerch Bridge 17 Nov, BepiColombo 22 Nov, Huang and
Iran sanctions 23 Nov). No story is dated 24 Nov unless it happened or
was first reported on 24 Nov.

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
    (-115.1, 36.2, "LAS VEGAS", -64, 4),
    (114.0, 22.5, "SHENZHEN", -20, -12),
    (36.5, 45.3, "KERCH", -8, -12),
    (20.0, 32.1, "BENGHAZI", -10, 10),
    (51.4, 35.7, "TEHRAN", -8, -12),
    (30.7, 36.9, "ANTALYA", -52, -4),
    (82.2, 26.8, "AYODHYA", -16, 12),
    (174.8, -41.3, "WELLINGTON", -58, -12),
    (34.5, 31.5, "GAZA", 8, -12),
    (-9.1, 38.7, "LISBON", -34, -12),
    (93.0, 20.0, "RAKHINE", -12, -14),
    (30.5, 50.5, "KYIV", -26, -12),
    (56.5, 26.5, "HORMUZ", -8, 12),
    (7.7, 45.0, "TURIN", -6, -12),
    (-17.4, 14.7, "DAKAR", -30, 8),
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
    "kicker": "TECHNOLOGY - UNITED STATES - 23 NOV 2026",
    "headline": ["HUANG REINSTATED AS NVIDIA CEO",
                 "SHARES SOAR 31%"],
    "summary": ("BOARD VOTES UNANIMOUSLY ON 23 NOV AFTER DIRECT PRESSURE "
                "FROM PRESIDENT TRUMP. VP VANCE LEANED ON THE BOARD; "
                "NASDAQ +6.5%, S&P +4.7%."),
    "source": "CNN / THE HINDU BUSINESSLINE",
}

# (headline, summary, source + date) - leads 2..16, in research-pack order.
LEADS = [
    ("TRUMP HITS IRAN'S FINANCIAL LIFELINE",
     "TREASURY HITS 25+ HOUSES; $14.7B.",
     "TREASURY - 23 NOV"),
    ("COP31 ENDS WITH NO DEAL IN ANTALYA",
     "NO PACT AGREED; TALKS MAY SUSPEND.",
     "BBC - 23-24 NOV"),
    ("RUSSIAN WARSHIP SUNK OFF LIBYA",
     "MERKURY SUNK; KYIV CLAIMS IT.",
     "NAVAL NEWS - 22 NOV"),
    ("ICJ: ROHINGYA GENOCIDE VERDICT",
     "MYANMAR GUILTY 9-6; CASE FROM 2019.",
     "ICJ - 19 NOV"),
    ("TRUMP, XI AND PUTIN MEET AT APEC",
     "FIRST TRILATERAL ON APEC SIDELINES.",
     "APEC - 24 NOV"),
    ("KERCH BRIDGE HIT; KYIV ANSWERS",
     "BRIDGE STRUCK 17 NOV; 8 KILLED.",
     "CNN - 17 NOV"),
    ("EU UNVEILS NEW RUSSIA SANCTIONS",
     "NEW PACKAGE; CHINA BANS DRONE PARTS.",
     "EU COMM. - 24 NOV"),
    ("TWO TANKERS HIT IN STRAIT OF HORMUZ",
     "ADNOC VESSEL HIT; ONE CREW MISSING.",
     "UKMTO - 22-23 NOV"),
    ("BITCOIN REBOUNDS PAST $62,800",
     "BTC +3.4% AFTER $55,100 LOW.",
     "THESTREET - 23 NOV"),
    ("WAYMO PULLED FROM ALL US FREEWAYS",
     "DRIVERLESS TAXIS OFF FREEWAYS.",
     "COMPANY - 23 NOV"),
    ("BEPICOLOMBO REACHES MERCURY",
     "ESA/JAXA PROBE IN MERCURY ORBIT.",
     "ESA/JAXA - 22 NOV"),
    ("INDIA-NEPAL RAIL LINK OPENS",
     "MODI, NEPAL PM FLAG OFF EXPRESS.",
     "JAGRANJOSH - 24 NOV"),
    ("PANT 128 SETS ASIAN RECORD",
     "PANT SCORES 128 VS NZ IN WELLINGTON.",
     "JAGRANJOSH - 24 NOV"),
    ("VERSTAPPEN WINS VEGAS GP",
     "ALCARAZ INTO ATP FINAL.",
     "SPORTS - 23 NOV"),
    ("BANTEN FACTORY FIRE RESCUE",
     "RESCUE CONTINUES; 34 STILL MISSING.",
     "NEWS WIRES - 23 NOV"),
]

MARKETS = [
    "MARKETS - 23 NOV",
    "NASDAQ +6.5%",
    "S&P +4.7%",
    "GOLD $3,661",
    "BRENT $89.34",
]

# (date, label) - one tick per day, 17-24 Nov 2026.
TIMELINE = [
    ("17 NOV", "KERCH"),
    ("19 NOV", "ICJ RULING"),
    ("20 NOV", "FOIP 3.0"),
    ("21 NOV", "BTC LOW"),
    ("22 NOV", "BEPICOLOMBO"),
    ("23 NOV", "HUANG +31%"),
    ("24 NOV", "EU SANCTIONS"),
]

# 32 wire briefs, each at most 34 chars so it fits two lines in a
# five-column grid.
BRIEFS = [
    "TRUMP-KIM TALKS IGNORED (WSJ)",
    "GAZA TAINTED FOR DECADES",
    "TALIBAN ERASE WOMEN'S NAMES",
    "IRAN SHOWS LAUNCHER",
    "UK PM FEARS NEW IRAN STRIKE",
    "FINLAND SUMMONS RUSSIAN ENVOY",
    "RUSSIAN SHIP AFIRE",
    "DRONE STRIKE IN KYIV REGION",
    "ZAPORIZHZHIA HIT; 3 KILLED",
    "UK BACKS WINTER TRUCE",
    "LISBON MARCH ON COSTS",
    "MYANMAR SLAMS ASEAN DECISION",
    "SEOUL PICKS NEW MINISTERS",
    "DHAKA MAY JAIL HASINA",
    "COLOMBIA ACTS VS STARLINK",
    "JAPAN DEFENCE BUDGET PAST 9TN",
    "CHINA PUSHES $167B DAM",
    "AFRICOM CHIEF TOURS W. AFRICA",
    "220M CHRISTIANS PERSECUTED",
    "UN SLAMS SUDAN DRONE STRIKES",
    "MIGRANT BOAT SINKS; 4 DEAD",
    "GHANA WIN AMPUTEE CUP",
    "S. AFRICA EX-DEPUTY DIES",
    "ETHIOPIA JABS 11M KIDS",
    "ODISHA CYBER COMMAND CENTRE",
    "FERRARI UNVEILS 296 CHALLENGE",
    "INDIA HOCKEY BEATS NZ 1-0",
    "FIFA PICKS 2031 HOSTS",
    "SUPERMOON MEETS PLEIADES",
    "DOJ MOVES TO SEIZE $1B USDC",
    "CHAINFLIP LOSES $12.6M",
    "ANTHROPIC STOCK FALLS 9.13%",
]

FOOTER_DATE = ("TUESDAY 24 NOVEMBER 2026. STORIES DATED 17-24 NOV AS MARKED: "
               "ICJ 19 NOV, KERCH 17 NOV, BEPICOLOMBO 22 NOV, "
               "HUANG + IRAN SANCTIONS 23 NOV.")
FOOTER_SOURCES = ("SOURCES: CNN, BBC, WALL STREET JOURNAL, NAVAL NEWS, ICJ, US TREASURY, "
                  "UKMTO, THE HINDU BUSINESSLINE, THESTREET, JAGRANJOSH, PANAPRESS, "
                  "BLOOMBERG, COINGLASS.")

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
    cv.text_at(RX, 64, "32 BRIEFS - 7 REGIONS", 2, MUTED, align="right")
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
