import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from glyphs import G
from glyphs_special import SPECIAL, UNI
import pathops
from fontTools.svgLib.path import parse_path
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.fontBuilder import FontBuilder

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "fonts", "Hardlaunch-Regular")
S = 2.0            # figma px -> font units (cap height 347.5 -> 695)
BASE = 347.498
SB = 22.5 * S      # half of the 45px gap between glyphs in the Figma frame
UPM, ASC, DESC = 1000, 800, -200

def outline(name):
    w, rule, d, *yoff = G[name]
    yoff = yoff[0] if yoff else 0.0
    p = pathops.Path()
    p.fillType = pathops.FillType.EVEN_ODD if rule == "evenodd" else pathops.FillType.WINDING
    # flip y, put baseline at 0, scale, add left side bearing
    tp = TransformPen(p.getPen(), (S, 0, 0, -S, SB, (BASE - yoff) * S))
    parse_path(d, tp)
    p.simplify(fix_winding=True)
    return p, round(w * S + 2 * SB)

def special_outline(name):
    v = SPECIAL[name]
    flip = v.startswith("F")
    if flip: v = v[1:]
    p = pathops.Path()
    p.fillType = pathops.FillType.WINDING
    for d in v.split("|"):
        q = pathops.Path(); q.fillType = pathops.FillType.EVEN_ODD
        a = -1 if flip else 1
        parse_path(d, TransformPen(q.getPen(), (a, 0, 0, 1, 347 if flip else 0, 0)))
        q.simplify(fix_winding=True)
        p = pathops.op(p, q, pathops.PathOp.UNION, fix_winding=True)
    bp = BoundsPen(None); p.draw(bp)
    xmin, _, xmax, _ = bp.bounds
    out = pathops.Path()
    p.draw(TransformPen(out.getPen(), (S, 0, 0, -S, SB - xmin * S, 347 * S)))
    out.simplify(fix_winding=True)
    return out, round((xmax - xmin) * S + 2 * SB)

order = [".notdef", "space"] + [chr(c) for c in range(65, 91)] + \
    ["zero","one","two","three","four","five","six","seven","eight","nine","period"] + list(SPECIAL)
charstrings, metrics = {}, {}
for g in order:
    src = "period" if g == ".notdef" else g
    if g == "space":
        pen = T2CharStringPen(0, None); charstrings[g] = pen.getCharString()
        metrics[g] = (round(173.749 * S), 0); continue
    p, adv = special_outline(src) if src in SPECIAL else outline(src)
    pen = T2CharStringPen(adv, None)
    p.draw(pen)
    charstrings[g] = pen.getCharString()
    bp = BoundsPen(None); p.draw(bp)
    metrics[g] = (adv, round(bp.bounds[0]))

cmap = {}
# Fallback first: everything printable we cover maps to the period glyph
ranges = [(0x21, 0x7E), (0xA1, 0x17F), (0x2010, 0x2027), (0x2030, 0x205E), (0x20A0, 0x20C0), (0x2122, 0x2122)]
for a, b in ranges:
    for c in range(a, b + 1):
        cmap[c] = "period"
for c in range(65, 91):
    cmap[c] = chr(c); cmap[c + 32] = chr(c)   # lowercase shares uppercase glyphs
for i, n in enumerate(["zero","one","two","three","four","five","six","seven","eight","nine"]):
    cmap[0x30 + i] = n
cmap[0x2E] = "period"
for n, cps in UNI.items():
    for c in cps: cmap[c] = n
cmap[0x2026] = "period"
cmap[0x20] = "space"; cmap[0xA0] = "space"

fb = FontBuilder(UPM, isTTF=False)
fb.setupGlyphOrder(order)
fb.setupCharacterMap(cmap)
fb.setupCFF("Hardlaunch-Regular", {"FullName": "Hardlaunch Regular"}, charstrings, {})
fb.setupHorizontalMetrics(metrics)
fb.setupHorizontalHeader(ascent=ASC, descent=DESC)
fb.setupNameTable({"familyName": "Hardlaunch", "styleName": "Regular", "fullName": "Hardlaunch Regular", "version": "Version 0.200",
                   "uniqueFontIdentifier": "0.200;NONE;Hardlaunch-Regular", "psName": "Hardlaunch-Regular"})
fb.setupOS2(sTypoAscender=ASC, sTypoDescender=DESC, sTypoLineGap=200, usWinAscent=ASC + 20, usWinDescent=-DESC,
            sCapHeight=round(BASE * S), sxHeight=round(BASE * S), achVendID="NONE", fsType=0)
fb.setupPost()
fb.font["head"].fontRevision = 0.2
fb.font["OS/2"].fsSelection = 0x40  # REGULAR
fb.font["OS/2"].usWeightClass = 400
fb.save(OUT + ".otf")
fb.font.flavor = "woff2"; fb.save(OUT + ".woff2")
print("ok", len(order), "glyphs,", len(cmap), "codepoints")
