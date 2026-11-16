"""Render the ResolveBench logo set (mark, lockups, cover) with Pillow.

Fully offline: uses Windows system fonts (Segoe UI Semibold + Consolas).
Supersamples 4x then downscales with LANCZOS for clean antialiasing.
Run:  .venv-analysis/Scripts/python.exe brand/make_logo.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__))
SS = 4  # supersample factor

# ---- brand palette ---------------------------------------------------------
INK        = (14, 17, 22)      # #0E1116
PANEL_EDGE = (42, 49, 60)      # #2A313C
OFFWHITE   = (238, 241, 244)   # #EEF1F4
SLATE      = (138, 148, 163)   # #8A94A3
AMBER      = (232, 176, 75)    # #E8B04B
TEAL       = (67, 181, 154)    # #43B59A
COMMIT     = (199, 206, 214)   # #C7CED6

F_WORD = "C:/Windows/Fonts/seguisb.ttf"   # Segoe UI Semibold
F_MONO = "C:/Windows/Fonts/consola.ttf"   # Consolas


def font(path, size):
    return ImageFont.truetype(path, size)


def fit_font(draw, text, path, start_px, max_width):
    """Return the largest font (<= start_px) whose text width fits max_width."""
    size = start_px
    while size > 8:
        f = font(path, size)
        w = draw.textlength(text, font=f)
        if w <= max_width:
            return f
        size -= 2
    return font(path, 8)


def _amber_ring_alpha(d, cx, cy, r, width, color, alpha):
    # draw a translucent ring by compositing
    pass


def draw_mark(img, ox, oy, size, with_tile=True):
    """Draw the mark into img at (ox,oy) occupying size x size px.
    Geometry matches resolvebench_mark.svg (120-unit viewBox)."""
    d = ImageDraw.Draw(img, "RGBA")
    u = size / 120.0  # unit -> px

    def P(x, y):
        return (ox + x * u, oy + y * u)

    if with_tile:
        # rounded tile 6..114, rx 27
        x0, y0 = P(6, 6)
        x1, y1 = P(114, 114)
        d.rounded_rectangle([x0, y0, x1, y1], radius=27 * u,
                            fill=INK, outline=PANEL_EDGE, width=max(1, int(2 * u)))

    # commit boundary line x=60, y 33..87
    lw = max(1, int(2.5 * u))
    d.line([P(60, 33), P(60, 87)], fill=COMMIT, width=lw)
    # round caps
    rc = lw / 2
    for (px, py) in (P(60, 33), P(60, 87)):
        d.ellipse([px - rc, py - rc, px + rc, py + rc], fill=COMMIT)

    # faint amber seal ring (r=15) drawn on a temp layer for opacity
    ring = Image.new("RGBA", img.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    cx, cy = P(40, 60)
    rr = 15 * u
    rd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=AMBER + (115,), width=max(1, int(2 * u)))
    img.alpha_composite(ring)

    # sealed answer dot r=9 (amber, solid)
    d = ImageDraw.Draw(img, "RGBA")
    r9 = 9 * u
    d.ellipse([cx - r9, cy - r9, cx + r9, cy + r9], fill=AMBER)

    # check polyline 69,61 -> 78,71 -> 93,47 (teal), rounded
    cw = int(7 * u)
    pts = [P(69, 61), P(78, 71), P(93, 47)]
    d.line(pts, fill=TEAL, width=cw, joint="curve")
    rc2 = cw / 2
    for (px, py) in pts:
        d.ellipse([px - rc2, py - rc2, px + rc2, py + rc2], fill=TEAL)


def render_icon(px, name, tile=True):
    S = px * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw_mark(img, 0, 0, S, with_tile=tile)
    img = img.resize((px, px), Image.LANCZOS)
    img.save(os.path.join(OUT, name))
    print("wrote", name, f"{px}x{px}")


def render_lockup(name, dark=True, W=1600, H=480, descriptor="ON-CHAIN-COMMITTED AI EVALS"):
    s = SS
    img = Image.new("RGBA", (W * s, H * s), (INK + (255,)) if dark else (OFFWHITE + (255,)))
    d = ImageDraw.Draw(img, "RGBA")
    fg = OFFWHITE if dark else INK
    sub = SLATE

    mark = int(300 * s)
    mx = int(130 * s)
    my = (H * s - mark) // 2
    draw_mark(img, mx, my, mark, with_tile=True)

    tx = mx + mark + int(80 * s)
    avail = W * s - tx - int(90 * s)
    wf = fit_font(d, "ResolveBench", F_WORD, int(150 * s), avail)
    mf = font(F_MONO, int(34 * s))

    wb = d.textbbox((0, 0), "ResolveBench", font=wf)
    wh = wb[3] - wb[1]
    db = d.textbbox((0, 0), descriptor, font=mf)
    dh = db[3] - db[1]
    gap = int(34 * s)
    group_h = wh + gap + dh
    gy = (H * s - group_h) // 2

    # wordmark
    d.text((tx, gy - wb[1]), "ResolveBench", font=wf, fill=fg)
    # descriptor with a short amber tick to its left
    dy = gy + wh + gap
    tick_x = tx + int(2 * s)
    d.rectangle([tick_x, dy, tick_x + int(10 * s), dy + dh], fill=AMBER)
    d.text((tick_x + int(28 * s), dy - db[1]), descriptor, font=mf, fill=sub)

    img = img.resize((W, H), Image.LANCZOS)
    img.convert("RGB").save(os.path.join(OUT, name), quality=95)
    print("wrote", name, f"{W}x{H}")


def render_cover(name, W=1200, H=630, tagline="Commit the answer. Let reality grade it.",
                 footer="github.com/Investorquab/resolvebench    .    Anchored on Base Sepolia    .    $0.00 to run"):
    s = SS
    img = Image.new("RGBA", (W * s, H * s), INK + (255,))
    d = ImageDraw.Draw(img, "RGBA")

    pad = int(84 * s)
    content_w = W * s - 2 * pad

    # faint seal->check echo motif, dim, upper-right, kept well clear of text
    ex = int(W * 0.80) * s
    ey = int(H * 0.17 * s)
    d.ellipse([ex - int(5 * s), ey - int(5 * s), ex + int(5 * s), ey + int(5 * s)], fill=(232, 176, 75, 90))
    d.line([(ex + int(26 * s), ey + int(3 * s)), (ex + int(40 * s), ey + int(17 * s)),
            (ex + int(66 * s), ey - int(16 * s))], fill=(67, 181, 154, 90), width=int(5 * s), joint="curve")

    # mark + wordmark, top
    mark = int(140 * s)
    top = int(80 * s)
    draw_mark(img, pad, top, mark, with_tile=True)
    wf = font(F_WORD, int(88 * s))
    wb = d.textbbox((0, 0), "ResolveBench", font=wf)
    d.text((pad + mark + int(40 * s), top + mark // 2 - (wb[3] - wb[1]) // 2 - wb[1]),
           "ResolveBench", font=wf, fill=OFFWHITE)

    # tagline, large, auto-fit to width
    tf = fit_font(d, tagline, F_WORD, int(72 * s), content_w)
    d.text((pad, int(330 * s)), tagline, font=tf, fill=OFFWHITE)

    # one-line descriptor, auto-fit
    desc = "A pre-registered, on-chain-committed evaluation of AI financial advice."
    df = fit_font(d, desc, F_MONO, int(31 * s), content_w)
    d.text((pad, int(448 * s)), desc, font=df, fill=SLATE)

    # footer mono with amber tick, auto-fit
    ff = fit_font(d, footer, F_MONO, int(27 * s), content_w - int(40 * s))
    fb = d.textbbox((0, 0), footer, font=ff)
    fy = (H - 78) * s - (fb[3] - fb[1])
    d.rectangle([pad, fy, pad + int(12 * s), fy + (fb[3] - fb[1])], fill=AMBER)
    d.text((pad + int(30 * s), fy - fb[1]), footer, font=ff, fill=SLATE)

    img = img.resize((W, H), Image.LANCZOS)
    img.convert("RGB").save(os.path.join(OUT, name), quality=95)
    print("wrote", name, f"{W}x{H}")


if __name__ == "__main__":
    for px in (1024, 512, 256, 128, 64):
        render_icon(px, f"icon_{px}.png", tile=True)
    render_lockup("logo_horizontal_dark.png", dark=True)
    render_lockup("logo_horizontal_light.png", dark=False)
    render_cover("cover_1200x630.png", 1200, 630)
    render_cover("github_social_1280x640.png", 1280, 640)
    print("done.")
