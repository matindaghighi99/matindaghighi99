"""Hand-author a neofetch-style info card SVG.

Edit CARD below; each line fades and slides in on a short stagger so the panel looks
like it prints next to the portrait. The card height matches portrait-ascii.svg when it exists.

Usage: python scripts/make_info_card.py [--out info-card.svg]
Set STATIC=1 to emit the finished frame without animation (for local previews).
"""
import argparse
import os
import re

USER = "matt@github"

# ("key", "value") rows; ("", "") is a blank spacer; ("#", "text") is a section heading;
# ("-", "text") is a bullet line; (" ", "text") continues the previous value.
CARD = [
    ("Name", "Matt Daghighi"),
    ("Now", "Founder · Precisa Solutions"),
    ("Does", "Website development · AI software"),
    (" ", "for businesses: leads + customer support"),
    ("Study", "Computer Programming · C++ / OOP"),
    ("", ""),
    ("Langs", "TypeScript · JavaScript · Python · C# · C++"),
    ("Stack", "Node.js · Express · Unity · HTML/CSS"),
    ("Focus", "AI agents · automation · web · games"),
    ("", ""),
    ("#", "Projects"),
    ("-", "Bloom-ai-engine"),
    ("-", "billing-anomaly-detection: ML for billing audits"),
    ("-", "MatinShapeAutomations: AI automation agency"),
    ("-", "gainn, Crania, robots: web builds"),
    ("-", "blackjack: Unity/C# social casino + Node API"),
    ("", ""),
    ("Contact", "github.com/matindaghighi99"),
]

WIDTH = 490
DEFAULT_HEIGHT = 530
PAD_X = 22
TITLE_H = 30
FONT_SIZE = 12.5
LINE_H = 21
BG = "#0d1117"
BORDER = "#30363d"
FG = "#c9d1d9"
DIM = "#8b949e"
KEY = "#39d353"
ACCENT = "#58a6ff"
FONT = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
SWATCHES = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0", "#58a6ff", "#c9d1d9"]

START = 0.6
STAGGER = 0.12


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def portrait_height(path="portrait-ascii.svg"):
    try:
        with open(path, encoding="utf-8") as f:
            m = re.search(r'height="(\d+)"', f.read(400))
            return int(m.group(1)) if m else DEFAULT_HEIGHT
    except OSError:
        return DEFAULT_HEIGHT


def build_svg(height, static):
    key_w = max(len(k) for k, _ in CARD if k not in ("", "#", "-")) + 2
    cw = FONT_SIZE * 0.6

    rows = [("prompt", f"{USER} ~ $ neofetch"), ("title", USER), ("rule", "-" * len(USER))]
    rows += [("card", r) for r in CARD]
    rows += [("", None), ("swatch", None)]

    body = []
    y = TITLE_H + 30
    for i, (kind, data) in enumerate(rows):
        attrs = "" if static else f' class="ln" style="animation-delay:{START + i * STAGGER:.2f}s"'
        line = None
        if kind == "prompt":
            line = f'<text x="{PAD_X}" y="{y}" fill="{DIM}">{esc(data)}</text>'
        elif kind == "title":
            u, h = data.split("@")
            line = (f'<text x="{PAD_X}" y="{y}" font-weight="bold"><tspan fill="{KEY}">{esc(u)}</tspan>'
                    f'<tspan fill="{FG}">@</tspan><tspan fill="{KEY}">{esc(h)}</tspan></text>')
        elif kind == "rule":
            line = f'<text x="{PAD_X}" y="{y}" fill="{DIM}">{data}</text>'
        elif kind == "card":
            k, v = data
            if k == "#":
                line = f'<text x="{PAD_X}" y="{y}" fill="{ACCENT}" font-weight="bold">{esc(v)}</text>'
            elif k == "-":
                name, _, rest = v.partition(":")
                line = (f'<text x="{PAD_X}" y="{y}"><tspan fill="{KEY}">▸ </tspan>'
                        f'<tspan fill="{FG}" font-weight="bold">{esc(name)}</tspan>'
                        f'<tspan fill="{DIM}">{esc(":" + rest) if rest else ""}</tspan></text>')
            elif k:
                line = (f'<text x="{PAD_X}" y="{y}"><tspan fill="{KEY}" font-weight="bold">{esc(k)}</tspan>'
                        f'<tspan fill="{FG}" x="{PAD_X + key_w * cw:.1f}">{esc(v)}</tspan></text>')
        elif kind == "swatch":
            size = 16
            line = "".join(
                f'<rect x="{PAD_X + j * (size + 4)}" y="{y - size + 4}" width="{size}" height="{size}" rx="3" fill="{c}"/>'
                for j, c in enumerate(SWATCHES)
            )
        if line:
            body.append(f"<g{attrs}>{line}</g>")
        y += LINE_H if kind != "card" or data != ("", "") else LINE_H // 2

    if y > height:
        height = y

    style = "" if static else (
        "<style>.ln{opacity:0;animation:in .45s ease-out forwards}"
        "@keyframes in{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}</style>"
    )
    head = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">',
        style,
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<circle cx="18" cy="15" r="5" fill="#ff5f56"/><circle cx="34" cy="15" r="5" fill="#ffbd2e"/>'
        f'<circle cx="50" cy="15" r="5" fill="#27c93f"/>',
        f'<text x="{WIDTH / 2}" y="19" text-anchor="middle" font-family="{FONT}" font-size="11" fill="{DIM}">{USER}: ~/neofetch</text>',
        f'<line x1="0" y1="{TITLE_H}" x2="{WIDTH}" y2="{TITLE_H}" stroke="{BORDER}"/>',
        f'<g font-family="{FONT}" font-size="{FONT_SIZE}" xml:space="preserve">',
    ]
    return "\n".join(head + body + ["</g>", "</svg>"]) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="info-card.svg")
    args = ap.parse_args()
    svg = build_svg(portrait_height(), static=os.environ.get("STATIC") == "1")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
