#!/usr/bin/env python3
"""Generate streak stat cards (light + dark) from the GitHub contribution calendar.

Self-hosted replacement for streak-stats.demolab.com, whose public instance
times out behind GitHub's camo image proxy (persistent 504).
"""

import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

API = "https://api.github.com/graphql"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_days(login, token):
    """Return (total, [(date, count), ...]) for roughly the last year.

    The window ends a day in the future on purpose. A GitHub App
    installation token (what Actions hands us as GITHUB_TOKEN) gets a
    UTC-aligned calendar, which silently drops the current day for an
    account east of UTC; reaching past "now" pulls that day back in.
    GitHub clamps the range, so asking for tomorrow is harmless.
    """
    to = datetime.now(timezone.utc) + timedelta(days=1)
    frm = to - timedelta(days=365)  # the API rejects windows over a year

    body = json.dumps(
        {
            "query": QUERY,
            "variables": {
                "login": login,
                "from": frm.isoformat(),
                "to": to.isoformat(),
            },
        }
    ).encode()

    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "streak-card-generator",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)

    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")

    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [
        (date.fromisoformat(d["date"]), d["contributionCount"])
        for w in cal["weeks"]
        for d in w["contributionDays"]
    ]
    days.sort()
    return cal["totalContributions"], days


def streaks(days):
    """Compute (current, current_range, longest, longest_range).

    "Today" is the last day the calendar itself reports, never the system
    clock -- the runner is UTC while the calendar follows the account's
    timezone, and trusting the clock drops a day.
    """
    best = cur = 0
    best_span = cur_span = None
    for d, n in days:
        if n > 0:
            cur += 1
            cur_span = (d, d) if cur_span is None else (cur_span[0], d)
            if cur > best:
                best, best_span = cur, cur_span
        else:
            cur, cur_span = 0, None

    # Walk backwards from the calendar's own final day for the live streak.
    counts = dict(days)
    running, span_end, span_start = 0, None, None
    cursor = days[-1][0]
    if counts.get(cursor, 0) == 0:
        cursor -= timedelta(days=1)  # today may simply not have happened yet
    while counts.get(cursor, 0) > 0:
        if span_end is None:
            span_end = cursor
        span_start = cursor
        running += 1
        cursor -= timedelta(days=1)

    cur_range = (span_start, span_end) if running else None
    return running, cur_range, best, best_span


def fmt_range(span, last_day):
    if not span:
        return "—"
    a, b = span
    # Spell out the year whenever the span reaches back past Jan 1, otherwise
    # a year-long range reads as if it started this year.
    left = a.strftime("%b %-d, %Y") if a.year != last_day.year else a.strftime("%b %-d")
    if b == last_day:
        return f"{left} - Present"
    right = b.strftime("%b %-d") if a.year == b.year else b.strftime("%b %-d, %Y")
    return left if a == b else f"{left} - {right}"


THEMES = {
    "dark": {
        "bg": "#1a1b27",
        "ring": "#70a5fd",
        "fire": "#bf91f3",
        "num": "#38bdae",
        "label": "#70a5fd",
        "date": "#8b8b8b",
        "divider": "#2d3748",
    },
    "light": {
        "bg": "#fffefe",
        "ring": "#fb8c00",
        "fire": "#fb8c00",
        "num": "#151515",
        "label": "#0366d6",
        "date": "#464646",
        "divider": "#e4e2e2",
    },
}

FONT = "'Segoe UI', Ubuntu, sans-serif"

FIRE = (
    '<path d="M -12 -0.5 C -12 -5 -8 -6 -8 -10 C -6 -8 -4 -5 -5 -1 '
    'C -4 -2 -2 -4 -2 -7 C 0 -4 2 -1 2 2 C 2 7 -2 10 -5 10 '
    'C -9 10 -12 6 -12 -0.5 Z" fill="{fire}" stroke="none"/>'
)


def card(total, cur, cur_span, best, best_span, span_all, theme_name):
    t = THEMES[theme_name]
    last_day = span_all[1]
    # 880 matches the snake SVG, which is exactly the README content width.
    # Anything narrower renders as a stranded box next to the full-bleed
    # graph below it.
    w, h = 880, 210
    col = w / 3

    def block(cx, num, label, span, big=False):
        parts = []
        if big:
            parts.append(
                f'<circle cx="{cx}" cy="90" r="52" fill="none" '
                f'stroke="{t["ring"]}" stroke-width="5"/>'
            )
            parts.append(
                f'<g transform="translate({cx}, 34) scale(1.35)">'
                + FIRE.format(fire=t["fire"])
                + "</g>"
            )
        parts.append(
            f'<text x="{cx}" y="{102 if big else 95}" text-anchor="middle" '
            f'fill="{t["num"]}" font-family="{FONT}" '
            f'font-size="{34 if big else 36}" font-weight="700">{num}</text>'
        )
        parts.append(
            f'<text x="{cx}" y="{166 if big else 132}" text-anchor="middle" '
            f'fill="{t["label"]}" font-family="{FONT}" font-size="16" '
            f'font-weight="600">{label}</text>'
        )
        parts.append(
            f'<text x="{cx}" y="{188 if big else 154}" text-anchor="middle" '
            f'fill="{t["date"]}" font-family="{FONT}" font-size="13">{span}</text>'
        )
        return "\n    ".join(parts)

    body = "\n    ".join(
        [
            block(col * 0.5, f"{total:,}", "Total Contributions",
                  fmt_range(span_all, last_day)),
            block(col * 1.5, str(cur), "Current Streak",
                  fmt_range(cur_span, last_day), big=True),
            block(col * 2.5, str(best), "Longest Streak",
                  fmt_range(best_span, last_day)),
        ]
    )

    dividers = "".join(
        f'<line x1="{col*i}" y1="42" x2="{col*i}" y2="178" '
        f'stroke="{t["divider"]}" stroke-width="1"/>'
        for i in (1, 2)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
  <rect width="{w}" height="{h}" rx="6" fill="{t['bg']}"/>
  {dividers}
    {body}
</svg>
"""


if __name__ == "__main__":
    login = os.environ.get("GH_LOGIN") or sys.exit("GH_LOGIN required")
    token = os.environ.get("GH_TOKEN") or sys.exit("GH_TOKEN required")
    outdir = os.environ.get("OUT_DIR", "dist")

    total, days = fetch_days(login, token)
    if not days:
        sys.exit("no contribution days returned")

    span_all = (days[0][0], days[-1][0])
    cur, cur_span, best, best_span = streaks(days)

    os.makedirs(outdir, exist_ok=True)
    for name in ("dark", "light"):
        suffix = "-dark" if name == "dark" else ""
        path = os.path.join(outdir, f"streak{suffix}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(card(total, cur, cur_span, best, best_span, span_all, name))
        print(f"wrote {path}")

    print(f"calendar covers {span_all[0]} .. {span_all[1]}")
    print(f"total={total} current={cur} longest={best}")
