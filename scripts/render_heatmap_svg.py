"""Render data/contributions.json as an animated 53-week contribution heatmap SVG.

Boxes slide in on a diagonal, play once on load and freeze (CSS keyframes, which GitHub
plays inside <img>). Includes a Less -> More legend and a stats footer.

Usage: python scripts/render_heatmap_svg.py [--out contrib-heatmap.svg]
Set STATIC=1 to emit the finished frame without animation (for local previews).
"""
import argparse
import datetime as dt
import json
import os

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
#          none -> brightest (level 5 is a neon top end)

WIDTH = 860          # = portrait column (370) + card column (490)
PAD = 22
TITLE_H = 30
LABEL_W = 30
BOX = 12
BG = "#0d1117"
BORDER = "#30363d"
FG = "#c9d1d9"
DIM = "#8b949e"
KEY = "#39d353"
FONT = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

START = 0.3
DIAG_STEP = 0.025    # seconds per diagonal step (week + weekday)


def levels(days):
    """Map counts to 0-5 using quartiles of the non-zero days, plus a neon level for the top 5%."""
    nz = sorted(d["count"] for d in days if d["count"] > 0)
    if not nz:
        return [0] * len(days)

    def q(p):
        return nz[min(len(nz) - 1, int(p * len(nz)))]

    cuts = [q(0.25), q(0.5), q(0.75), q(0.95)]
    out = []
    for d in days:
        c = d["count"]
        if c == 0:
            out.append(0)
        else:
            out.append(1 + sum(c > t for t in cuts))
    return out


def fmt_date(iso):
    if not iso:
        return "-"
    d = dt.date.fromisoformat(iso)
    return f"{d.strftime('%b')} {d.day}"


def build_svg(data, static):
    days = data["days"]
    lv = levels(days)
    first = dt.date.fromisoformat(days[0]["date"])
    offset = (first.weekday() + 1) % 7  # GitHub columns start on Sunday
    weeks = (offset + len(days) + 6) // 7
    step = (WIDTH - 2 * PAD - LABEL_W) / weeks

    head_y = TITLE_H + 30
    grid_top = head_y + 32
    grid_left = PAD + LABEL_W
    grid_bottom = grid_top + 7 * step
    height = round(grid_bottom + 52)

    s = data["stats"]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">',
    ]
    if not static:
        out.append(
            "<style>.c{opacity:0;transform-box:fill-box;transform-origin:center;"
            "animation:drop .5s cubic-bezier(.2,.8,.3,1) forwards}"
            "@keyframes drop{from{opacity:0;transform:translateY(-9px) scale(.6)}to{opacity:1;transform:none}}"
            ".f{opacity:0;animation:fade .6s ease-out forwards}@keyframes fade{to{opacity:1}}</style>"
        )
    out += [
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<circle cx="18" cy="15" r="5" fill="#ff5f56"/><circle cx="34" cy="15" r="5" fill="#ffbd2e"/>'
        f'<circle cx="50" cy="15" r="5" fill="#27c93f"/>',
        f'<text x="{WIDTH / 2}" y="19" text-anchor="middle" font-family="{FONT}" font-size="11" fill="{DIM}">'
        f'{data["user"]}: ~/contributions</text>',
        f'<line x1="0" y1="{TITLE_H}" x2="{WIDTH}" y2="{TITLE_H}" stroke="{BORDER}"/>',
        f'<g font-family="{FONT}">',
        f'<text x="{PAD}" y="{head_y}" font-size="14" fill="{FG}"><tspan fill="{KEY}" font-weight="bold">'
        f'{data["total"]:,}</tspan> contributions in the last year</text>',
        f'<text x="{WIDTH - PAD}" y="{head_y}" font-size="11" fill="{DIM}" text-anchor="end">'
        f'updated {data["fetched_at"][:10]}</text>',
    ]

    # month labels at the first column whose week contains the 1st..7th of a month
    last_month = None
    for w in range(weeks):
        i = max(0, w * 7 - offset)
        if i >= len(days):
            break
        d = dt.date.fromisoformat(days[i]["date"])
        if d.month != last_month and (w == 0 and d.day <= 7 or w > 0):
            if w < weeks - 2:
                out.append(f'<text x="{grid_left + w * step:.1f}" y="{grid_top - 8}" font-size="10" fill="{DIM}">'
                           f'{d.strftime("%b")}</text>')
            last_month = d.month
    for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="{PAD}" y="{grid_top + r * step + BOX - 2:.1f}" font-size="10" fill="{DIM}">{name}</text>')

    for i, (d, l) in enumerate(zip(days, lv)):
        w, r = divmod(offset + i, 7)
        x, y = grid_left + w * step, grid_top + r * step
        anim = "" if static else f' class="c" style="animation-delay:{START + (w + r) * DIAG_STEP:.3f}s"'
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{BOX}" height="{BOX}" rx="2.5" fill="{PALETTE[l]}"{anim}>'
                   f'<title>{d["count"]} on {d["date"]}</title></rect>')

    fade = "" if static else f' class="f" style="animation-delay:{START + (weeks + 7) * DIAG_STEP:.2f}s"'
    fy = grid_bottom + 30
    out.append(f"<g{fade}>")
    out.append(
        f'<text x="{grid_left}" y="{fy}" font-size="12" fill="{DIM}">'
        f'streak <tspan fill="{FG}">{s["current_streak"]}d</tspan> · '
        f'longest <tspan fill="{FG}">{s["longest_streak"]}d</tspan> · '
        f'best day <tspan fill="{FG}">{s["best_day"]["count"]}</tspan> ({fmt_date(s["best_day"]["date"])}) · '
        f'active <tspan fill="{FG}">{s["active_days"]}d</tspan></text>'
    )
    lx = WIDTH - PAD - len(PALETTE) * (BOX + 3) - 34
    out.append(f'<text x="{lx - 8}" y="{fy}" font-size="10" fill="{DIM}" text-anchor="end">Less</text>')
    for j, c in enumerate(PALETTE):
        out.append(f'<rect x="{lx + j * (BOX + 3)}" y="{fy - BOX + 2}" width="{BOX}" height="{BOX}" rx="2.5" fill="{c}"/>')
    out.append(f'<text x="{lx + len(PALETTE) * (BOX + 3) + 5}" y="{fy}" font-size="10" fill="{DIM}">More</text>')
    out += ["</g>", "</g>", "</svg>"]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/contributions.json")
    ap.add_argument("--out", default="contrib-heatmap.svg")
    args = ap.parse_args()
    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(build_svg(data, static=os.environ.get("STATIC") == "1"))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
