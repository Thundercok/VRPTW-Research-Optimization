"""CHRONOGRAPHIC CARTOGRAPHY — drawing kit."""
import cairo, math, random

W, H = 1600.0, 900.0

# ── Palette ────────────────────────────────────────────────────────────────
PARCH   = (0.957, 0.945, 0.918)
PARCH_D = (0.925, 0.910, 0.874)
INK     = (0.071, 0.098, 0.137)
INK_S   = (0.180, 0.216, 0.263)
SLATE   = (0.404, 0.443, 0.486)
SLATE_L = (0.596, 0.616, 0.635)
HAIR    = (0.812, 0.788, 0.741)
VERM    = (0.741, 0.243, 0.098)
VERM_L  = (0.878, 0.514, 0.373)
TEAL    = (0.086, 0.400, 0.365)
TEAL_L  = (0.482, 0.655, 0.612)
WHITE   = (1, 1, 1)

# ── Fonts ──────────────────────────────────────────────────────────────────
DISP = "Big Shoulders"
BODY = "Work Sans"
MONO = "IBM Plex Mono"
SERF = "IBM Plex Serif"

SL = {"n": cairo.FONT_SLANT_NORMAL, "i": cairo.FONT_SLANT_ITALIC}
WT = {"n": cairo.FONT_WEIGHT_NORMAL, "b": cairo.FONT_WEIGHT_BOLD}


def face(c, fam, w="n", s="n"):
    c.select_font_face(fam, SL[s], WT[w])


def _adv(c, ch):
    return c.text_extents(ch)[4]


def tw(c, txt, fam, size, w="n", track=0.0, s="n"):
    """width of tracked text"""
    face(c, fam, w, s)
    c.set_font_size(size)
    if track == 0:
        return c.text_extents(txt)[4]
    return sum(_adv(c, ch) for ch in txt) + track * max(len(txt) - 1, 0)


BAD = set("≫∪ΣσΔ⇒᾿ᵢ∈●▪∼⁻ᵃ")
_seen = set()


def _guard(s):
    for ch in s:
        if ch in BAD and ch not in _seen:
            _seen.add(ch)
            raise SystemExit(f"MISSING GLYPH {ch!r} in: {s!r}")


def txt(c, x, y, s, fam=BODY, size=16, col=INK, w="n", track=0.0,
        align="l", sl="n", alpha=1.0):
    _guard(s)
    face(c, fam, w, sl)
    c.set_font_size(size)
    width = tw(c, s, fam, size, w, track, sl)
    if align == "c":
        x -= width / 2.0
    elif align == "r":
        x -= width
    c.set_source_rgba(*col, alpha)
    if track == 0:
        c.move_to(x, y)
        c.show_text(s)
    else:
        cx = x
        for ch in s:
            c.move_to(cx, y)
            c.show_text(ch)
            cx += _adv(c, ch) + track
    return width


def line(c, x1, y1, x2, y2, col=HAIR, lw=0.7, alpha=1.0, dash=None):
    c.save()
    c.new_path()
    c.set_source_rgba(*col, alpha)
    c.set_line_width(lw)
    if dash:
        c.set_dash(dash)
    c.move_to(x1, y1)
    c.line_to(x2, y2)
    c.stroke()
    c.restore()


def rect(c, x, y, w, h, col=HAIR, lw=0.7, fill=False, alpha=1.0, dash=None):
    c.save()
    c.new_path()
    c.set_source_rgba(*col, alpha)
    c.rectangle(x, y, w, h)
    if fill:
        c.fill()
    else:
        c.set_line_width(lw)
        if dash:
            c.set_dash(dash)
        c.stroke()
    c.restore()


def circ(c, x, y, r, col=INK, lw=0.7, fill=False, alpha=1.0):
    c.save()
    c.new_path()
    c.set_source_rgba(*col, alpha)
    c.arc(x, y, r, 0, 2 * math.pi)
    if fill:
        c.fill()
    else:
        c.set_line_width(lw)
        c.stroke()
    c.restore()


def arc(c, x, y, r, a1, a2, col=HAIR, lw=0.7, alpha=1.0, dash=None):
    c.save()
    c.new_path()
    c.set_source_rgba(*col, alpha)
    c.set_line_width(lw)
    if dash:
        c.set_dash(dash)
    c.arc(x, y, r, math.radians(a1), math.radians(a2))
    c.stroke()
    c.restore()


def bez(c, pts, col=SLATE, lw=1.0, alpha=1.0, dash=None):
    c.save()
    c.new_path()
    c.set_source_rgba(*col, alpha)
    c.set_line_width(lw)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    if dash:
        c.set_dash(dash)
    c.move_to(*pts[0])
    i = 1
    while i + 2 < len(pts) + 1 and i + 2 <= len(pts) - 1 + 1:
        if i + 2 < len(pts):
            c.curve_to(*pts[i], *pts[i + 1], *pts[i + 2])
            i += 3
        else:
            break
    c.stroke()
    c.restore()


def smooth(c, pts, col=SLATE, lw=1.0, alpha=1.0, dash=None, t=0.32):
    """Catmull-Rom -> bezier through pts."""
    if len(pts) < 2:
        return
    c.save()
    c.new_path()
    c.set_source_rgba(*col, alpha)
    c.set_line_width(lw)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    if dash:
        c.set_dash(dash)
    p = [pts[0]] + list(pts) + [pts[-1]]
    c.move_to(*pts[0])
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) * t / 1.5, p1[1] + (p2[1] - p0[1]) * t / 1.5)
        c2 = (p2[0] - (p3[0] - p1[0]) * t / 1.5, p2[1] - (p3[1] - p1[1]) * t / 1.5)
        c.curve_to(*c1, *c2, *p2)
    c.stroke()
    c.restore()


def arrowhead(c, x, y, ang, size=6.0, col=INK, alpha=1.0):
    c.save()
    c.new_path()
    c.translate(x, y)
    c.rotate(ang)
    c.set_source_rgba(*col, alpha)
    c.move_to(0, 0)
    c.line_to(-size, -size * 0.42)
    c.line_to(-size, size * 0.42)
    c.close_path()
    c.fill()
    c.restore()


def tickfield(c, x, y, w, n, h=5.0, col=HAIR, lw=0.7, alpha=1.0, every=5, hl=9.0):
    """horizontal measurement rule"""
    for i in range(n + 1):
        tx = x + w * i / n
        th = hl if i % every == 0 else h
        line(c, tx, y, tx, y - th, col, lw, alpha)


def vtickfield(c, x, y, h, n, w=5.0, col=HAIR, lw=0.7, alpha=1.0, every=5, wl=9.0):
    for i in range(n + 1):
        ty = y + h * i / n
        twd = wl if i % every == 0 else w
        line(c, x, ty, x + twd, ty, col, lw, alpha)


def dotgrid(c, x, y, w, h, sx, sy, r=0.55, col=HAIR, alpha=1.0):
    j = 0
    py = y
    while py <= y + h + 0.1:
        px = x
        while px <= x + w + 0.1:
            circ(c, px, py, r, col, fill=True, alpha=alpha)
            px += sx
        py += sy
        j += 1


# ── Page furniture ─────────────────────────────────────────────────────────
M = 68.0   # frame margin


def ground(c, grain=True, seed=7):
    rect(c, 0, 0, W, H, PARCH, fill=True)
    if grain:
        rnd = random.Random(seed)
        for _ in range(2300):
            gx, gy = rnd.uniform(0, W), rnd.uniform(0, H)
            circ(c, gx, gy, rnd.uniform(0.25, 0.8), PARCH_D, fill=True,
                 alpha=rnd.uniform(0.18, 0.55))


def frame(c, folio=None, cat=None, rule_top=None):
    rect(c, M, M, W - 2 * M, H - 2 * M, HAIR, lw=0.7)
    k = 13.0
    for (cx, cy, dx, dy) in [(M, M, 1, 1), (W - M, M, -1, 1),
                             (M, H - M, 1, -1), (W - M, H - M, -1, -1)]:
        line(c, cx, cy + dy * k, cx + dx * k, cy + dy * k, HAIR, 0.7)
        line(c, cx + dx * k, cy, cx + dx * k, cy + dy * k, HAIR, 0.7)
    if cat:
        txt(c, M + 16, M - 14, cat, MONO, 8.5, SLATE_L, track=1.9)
    if folio:
        txt(c, W - M - 16, M - 14, folio, MONO, 8.5, SLATE_L, track=1.9, align="r")


def footer(c, left, right=None, n=None):
    y = H - M + 22
    txt(c, M + 16, y, left, MONO, 8.0, SLATE_L, track=1.7)
    if right:
        txt(c, W - M - 16, y, right, MONO, 8.0, SLATE_L, track=1.7, align="r")


def eyebrow(c, x, y, s, col=VERM, size=9.0, track=2.6, tick=True):
    if tick:
        line(c, x, y - 3.5, x + 13, y - 3.5, col, 1.6)
        x += 21
    return txt(c, x, y, s, MONO, size, col, track=track)


def kicker(c, x, y, s, col=SLATE, size=9.5, track=2.4):
    return txt(c, x, y, s, MONO, size, col, track=track)


def heading(c, x, y, s, size=62, col=INK, track=1.0, align="l"):
    return txt(c, x, y, s, DISP, size, col, w="b", track=track, align=align)


def para(c, x, y, lines, size=15.5, lead=23, col=INK_S, fam=BODY, w="n",
         align="l", track=0.0, sl="n"):
    for i, ln in enumerate(lines):
        txt(c, x, y + i * lead, ln, fam, size, col, w=w, align=align,
            track=track, sl=sl)
    return y + (len(lines) - 1) * lead


def label_box(c, x, y, s, col=INK, pad=6.0, size=8.5, track=1.8, fillcol=None,
              lw=0.7):
    wd = tw(c, s, MONO, size, track=track)
    h = size + 2 * pad * 0.62
    if fillcol:
        rect(c, x, y - h + pad * 0.42, wd + 2 * pad, h, fillcol, fill=True)
    rect(c, x, y - h + pad * 0.42, wd + 2 * pad, h, col, lw=lw)
    txt(c, x + pad, y, s, MONO, size, col, track=track)
    return wd + 2 * pad


def bigno(c, x, y, s, size=118, col=INK, align="l"):
    return txt(c, x, y, s, DISP, size, col, w="b", track=-1.0, align=align)


def newpage(surface, c):
    c.show_page()
