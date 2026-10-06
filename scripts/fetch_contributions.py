"""Scrape the public contribution calendar (no token needed) into data/contributions.json.

GitHub serves the calendar fragment used by the profile page at
https://github.com/users/<user>/contributions. Each day is a
<td class="ContributionCalendar-day" data-date=... data-level=...>, and its count lives
in a <tool-tip for="<td id>"> such as "3 contributions on May 2nd." or "No contributions on ...".

Usage: python scripts/fetch_contributions.py [--user matindaghighi99] [--html saved.html]
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import OrderedDict

import requests
from bs4 import BeautifulSoup

DEFAULT_USER = os.environ.get("GH_USER", "matindaghighi99")
OUT = "data/contributions.json"


def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    tips = {t.get("for"): t.get_text(" ", strip=True) for t in soup.find_all("tool-tip")}

    days = []
    for td in soup.select("td.ContributionCalendar-day[data-date]"):
        text = tips.get(td.get("id"), "")
        m = re.match(r"([\d,]+) contributions?", text)
        if m:
            count = int(m.group(1).replace(",", ""))
        elif text.startswith("No contributions"):
            count = 0
        else:
            # no tooltip: fall back to GitHub's 0-4 intensity so the cell still shows
            count = int(td.get("data-level", 0))
        days.append({"date": td["data-date"], "count": count, "level": int(td.get("data-level", 0))})

    days.sort(key=lambda d: d["date"])
    total = sum(d["count"] for d in days)
    heading = soup.find(string=re.compile(r"contributions?\s+in the last year"))
    if heading:
        m = re.search(r"([\d,]+)", heading)
        if m:
            total = int(m.group(1).replace(",", ""))
    return days, total


def stats(days):
    today = dt.date.today().isoformat()
    past = [d for d in days if d["date"] <= today]

    longest = run = 0
    for d in past:
        run = run + 1 if d["count"] else 0
        longest = max(longest, run)

    # current streak: today may still be empty, so start from yesterday in that case
    current = 0
    seq = past[:-1] if past and past[-1]["count"] == 0 else past
    for d in reversed(seq):
        if not d["count"]:
            break
        current += 1

    best = max(past, key=lambda d: d["count"], default={"date": None, "count": 0})
    monthly = OrderedDict()
    for d in past:
        monthly[d["date"][:7]] = monthly.get(d["date"][:7], 0) + d["count"]
    active = sum(1 for d in past if d["count"])
    return {
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "active_days": active,
        "monthly": monthly,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=DEFAULT_USER)
    ap.add_argument("--html", help="parse a saved HTML file instead of fetching")
    args = ap.parse_args()

    if args.html:
        with open(args.html, encoding="utf-8") as f:
            html = f.read()
    else:
        r = requests.get(
            f"https://github.com/users/{args.user}/contributions",
            headers={"User-Agent": "profile-heatmap (+https://github.com/%s)" % args.user},
            timeout=30,
        )
        r.raise_for_status()
        html = r.text

    days, total = parse(html)
    if len(days) < 300:
        # never overwrite a good graph with an empty one if GitHub changes its markup
        sys.exit(f"error: parsed only {len(days)} days; calendar markup may have changed")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    data = {
        "user": args.user,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "total": total,
        "stats": stats(days),
        "days": days,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    print(f"wrote {OUT}: {len(days)} days, {total} contributions")


if __name__ == "__main__":
    main()
