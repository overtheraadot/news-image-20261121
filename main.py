#!/usr/bin/env python3
"""The World Today - one-page front page summing up Saturday 21 November 2026.

Draws a 1024x1024 PNG newspaper front page with PIL only: masthead, two
lead panels, 36 verified stories in six regional sections, and a world map
strip with numbered markers for twelve of the stories. Deterministic: all
text is baked in, no randomness, no network, no clock reads.

Run:  python3 main.py
Writes entry.png to $MAKEFUN_OUTPUT_DIR (default /output).
"""

import os

from PIL import Image, ImageDraw, ImageFont

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


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def text_w(draw, s, f):
    box = draw.textbbox((0, 0), s, font=f)
    return box[2] - box[0]


def wrap(draw, s, f, max_w):
    """Greedy word wrap; returns list of lines that fit max_w."""
    words = s.split()
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_w(draw, trial, f) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_line(draw, s, f, max_w):
    """Shorten with an ellipsis until the line fits."""
    if text_w(draw, s, f) <= max_w:
        return s
    while s and text_w(draw, s + "...", f) > max_w:
        s = s[:-1]
    return s + "..."


def centre(draw, y, s, f, colour, x0=0, x1=W):
    draw.text(((x0 + x1 - text_w(draw, s, f)) // 2, y), s, font=f, fill=colour)


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


def draw_masthead(d):
    d.rectangle([0, 0, W, 108], fill=NAVY)
    d.rectangle([0, 104, W, 108], fill=RED)
    centre(d, 12, "THE WORLD TODAY", font(62), (250, 246, 236))
    centre(d, 76, "SATURDAY  21  NOVEMBER  2026", font(26), (255, 214, 120))
    d.text((18, 116), "36 STORIES  |  SIX REGIONS  |  ONE DAY",
           font=font(13), fill=GREY)
    right = "ALL STORIES REPORTED 20-21 NOVEMBER 2026"
    d.text((W - 18 - text_w(d, right, font(13)), 116), right,
           font=font(13), fill=GREY)


def draw_leads(d):
    y0, h = 136, 128
    w = (W - 32 - 10) // 2
    for i, (kicker, head, body) in enumerate(LEADS):
        x0 = 16 + i * (w + 10)
        d.rectangle([x0, y0, x0 + w, y0 + h], fill=SECTION_BG,
                    outline=RULE, width=1)
        d.rectangle([x0, y0, x0 + w, y0 + 24], fill=RED)
        d.text((x0 + 10, y0 + 5), kicker, font=font(14), fill=(255, 255, 255))
        lines = wrap(d, head, font(21), w - 20)
        yy = y0 + 30
        for line in lines[:2]:
            d.text((x0 + 10, yy), line, font=font(21), fill=INK)
            yy += 24
        blines = wrap(d, body, font(13), w - 20)
        yy = y0 + 30 + 2 * 24 + 4
        for line in blines[:3]:
            d.text((x0 + 10, yy), line, font=font(13), fill=(60, 60, 60))
            yy += 16


def draw_sections(d):
    y0 = 274
    col_w = (W - 32 - 2 * 10) // 3
    row_h = 262
    f_head = font(15)
    f_body = font(13)
    for idx, (name, colour, stories) in enumerate(SECTIONS):
        col, row = idx % 3, idx // 3
        x0 = 16 + col * (col_w + 10)
        yy0 = y0 + row * (row_h + 10)
        d.rectangle([x0, yy0, x0 + col_w, yy0 + row_h], fill=SECTION_BG,
                    outline=RULE, width=1)
        d.rectangle([x0, yy0, x0 + col_w, yy0 + 28], fill=colour)
        d.text((x0 + 10, yy0 + 6), name, font=font(15), fill=(255, 255, 255))
        y = yy0 + 34
        for num, head, detail in stories:
            num_s = "%d." % num
            d.text((x0 + 8, y), num_s, font=f_head, fill=RED)
            nx = x0 + 8 + text_w(d, "36. ", f_head) + 2
            tw = x0 + col_w - 8 - nx
            head = fit_line(d, head, f_head, tw)
            d.text((nx, y), head, font=f_head, fill=INK)
            d.text((nx, y + 17), fit_line(d, detail, f_body, tw),
                   font=f_body, fill=(70, 70, 70))
            y += 37
            if num != stories[-1][0]:
                d.line([x0 + 8, y - 3, x0 + col_w - 8, y - 3], fill=(225, 220, 205))


def draw_map(d):
    y0 = 818
    h = 158
    d.rectangle([16, y0, W - 16, y0 + h], fill=OCEAN, outline=RULE, width=1)
    d.text((26, y0 + 6), "THE DAY ON THE MAP  -  12 STORIES MARKED",
           font=font(14), fill=NAVY)
    mx0, my0, mw, mh = 24, y0 + 26, W - 48, h - 32

    def proj(lon, lat):
        x = mx0 + (lon + 170.0) / 360.0 * mw
        y = my0 + (80.0 - lat) / 135.0 * mh
        return (x, y)

    for poly in CONTINENTS:
        pts = [proj(lon, lat) for lon, lat in poly]
        d.polygon(pts, fill=LAND, outline=LAND_EDGE)
    f_num = font(12)
    for num, lon, lat, dx, dy in MARKERS:
        x, y = proj(lon, lat)
        bx, by = x + dx, y + dy
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=INK)
        if dx or dy:
            d.line([x, y, bx, by], fill=INK, width=1)
        d.ellipse([bx - 10, by - 10, bx + 10, by + 10], fill=RED,
                  outline=(255, 255, 255), width=1)
        label = str(num)
        lw = text_w(d, label, f_num)
        d.text((bx - lw / 2, by - 7), label, font=f_num, fill=(255, 255, 255))


def main():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    draw_masthead(d)
    draw_leads(d)
    draw_sections(d)
    draw_map(d)
    centre(d, 984, "Compiled from published reports of 20-21 November 2026  |  "
           "The World Today  |  One day, one page", font(12), GREY)
    d.line([16, 980, W - 16, 980], fill=RULE)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    img.save(os.path.join(out_dir, "entry.png"), format="PNG",
             optimize=True)


if __name__ == "__main__":
    main()
