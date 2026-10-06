"""Convert source-prepped.png into a self-typing, monochrome ASCII portrait SVG.

Each row is revealed by a left-to-right clip wipe with a block cursor riding the edge,
staggered top to bottom. It prints once and freezes (SMIL, which GitHub plays inside <img>).

Usage: python scripts/make_ascii_svg.py [--src source-prepped.png] [--out portrait-ascii.svg]
Set STATIC=1 to emit the finished frame without animation (for local previews).
"""
import argparse
import os

import numpy as np
from PIL import Image

# Glyphs from sparse to dense. Drawn light-on-dark, so dense = bright.
# The leading space is reserved for the background.
RAMP = " .`:-=+*cs#%@"

WIDTH = 370          # matches the README column width, so 1 unit = 1 px
PAD = 16
TITLE_H = 30
COLS = 84
CELL_ASPECT = 0.55   # glyph width / line height
FG = "#c9d1d9"
BG = "#0d1117"
BORDER = "#30363d"
DIM = "#8b949e"
FONT = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

ROW_STAGGER = 0.045  # seconds between row starts
ROW_WIPE = 0.32      # seconds per row wipe
CONTRAST = 7.0       # steepness of the tone S-curve
START = 0.3


def load_grid(path):
    im = Image.open(path).convert("LA")
    gray = np.array(im)[..., 0].astype(np.float32)
    alpha = np.array(im)[..., 1].astype(np.float32) / 255.0

    # trim empty margins around the subject
    ys, xs = np.where(alpha > 0.5)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    gray, alpha = gray[y0:y1, x0:x1], alpha[y0:y1, x0:x1]

    h, w = gray.shape
    rows = max(1, round(h / w * COLS * CELL_ASPECT))
    g = np.array(Image.fromarray(gray.astype(np.uint8)).resize((COLS, rows), Image.BOX), dtype=np.float32)
    a = np.array(Image.fromarray((alpha * 255).astype(np.uint8)).resize((COLS, rows), Image.BOX), dtype=np.float32) / 255

    # S-curve: pushes mid-tones apart so features separate instead of turning to mush
    t = 1 / (1 + np.exp(-CONTRAST * (g / 255.0 - 0.5)))
    t = (t - t.min()) / max(t.max() - t.min(), 1e-6)

    lines = []
    for r in range(rows):
        chars = []
        for c in range(COLS):
            if a[r, c] < 0.45:
                chars.append(" ")
            else:
                # subject pixels use RAMP[1:] so even the darkest hair keeps a faint dot
                chars.append(RAMP[1 + int(round(t[r, c] * (len(RAMP) - 2)))])
        lines.append("".join(chars))
    return lines


def esc(s):
    # non-breaking spaces survive every SVG renderer; plain spaces collapse
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&#160;")


def span(line, cw):
    """x range covered by a row's non-blank glyphs."""
    first = len(line) - len(line.lstrip())
    last = len(line.rstrip())
    return PAD + first * cw, PAD + last * cw


def build_svg(lines, static):
    cw = (WIDTH - 2 * PAD) / COLS
    lh = cw / CELL_ASPECT
    fs = cw / 0.6
    top = TITLE_H + PAD
    height = round(top + len(lines) * lh + PAD)
    text_w = COLS * cw

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<circle cx="18" cy="15" r="5" fill="#ff5f56"/><circle cx="34" cy="15" r="5" fill="#ffbd2e"/>'
        f'<circle cx="50" cy="15" r="5" fill="#27c93f"/>',
        f'<text x="{WIDTH / 2}" y="19" text-anchor="middle" font-family="{FONT}" font-size="11" fill="{DIM}">matt@github: ~/portrait</text>',
        f'<line x1="0" y1="{TITLE_H}" x2="{WIDTH}" y2="{TITLE_H}" stroke="{BORDER}"/>',
    ]
    if not static:
        out.append("<defs>")
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            x0, x1 = span(line, cw)
            y = top + i * lh
            begin = START + i * ROW_STAGGER
            out.append(
                f'<clipPath id="r{i}"><rect x="{x0:.2f}" y="{y:.2f}" width="0" height="{lh + 0.5:.2f}">'
                f'<animate attributeName="width" from="0" to="{x1 - x0:.2f}" begin="{begin:.3f}s" dur="{ROW_WIPE}s" fill="freeze"/>'
                f"</rect></clipPath>"
            )
        out.append("</defs>")

    out.append(f'<g font-family="{FONT}" font-size="{fs:.2f}" fill="{FG}">')
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        y = top + i * lh
        baseline = y + lh * 0.78
        clip = "" if static else f' clip-path="url(#r{i})"'
        out.append(
            f'<text x="{PAD}" y="{baseline:.2f}" textLength="{text_w:.2f}" lengthAdjust="spacing"{clip}>{esc(line)}</text>'
        )
    out.append("</g>")

    if not static:
        # block cursor riding the wipe edge of each row
        out.append(f'<g fill="{FG}">')
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            x0, x1 = span(line, cw)
            y = top + i * lh
            begin = START + i * ROW_STAGGER
            out.append(
                f'<rect x="{x0:.2f}" y="{y + 1:.2f}" width="{cw:.2f}" height="{lh - 1:.2f}" opacity="0">'
                f'<set attributeName="opacity" to="0.85" begin="{begin:.3f}s"/>'
                f'<animate attributeName="x" from="{x0:.2f}" to="{x1:.2f}" begin="{begin:.3f}s" dur="{ROW_WIPE}s" fill="freeze"/>'
                f'<set attributeName="opacity" to="0" begin="{begin + ROW_WIPE:.3f}s"/>'
                f"</rect>"
            )
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out) + "\n", height


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="source-prepped.png")
    ap.add_argument("--out", default="portrait-ascii.svg")
    args = ap.parse_args()

    lines = load_grid(args.src)
    svg, height = build_svg(lines, static=os.environ.get("STATIC") == "1")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {args.out} ({len(lines)} rows x {COLS} cols, {WIDTH}x{height})")


if __name__ == "__main__":
    main()
