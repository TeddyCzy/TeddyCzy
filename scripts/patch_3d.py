#!/usr/bin/env python3
"""Fix up the third-party 3D contribution calendar SVG.

Two things need correcting in the upstream output:

1. It reads the calendar with the Actions App token, which is UTC-aligned
   and therefore drops the current day for an account east of UTC. Left
   alone it prints a total that disagrees with the streak card sitting
   right above it on the profile.
2. It always renders star and fork counters, which there is no setting to
   turn off.

Both live in a small footer group, so rewrite that rather than fork the
action. Star/fork counts carry a <title> child; the contribution total
does not -- that is what tells them apart.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_streak import fetch_days  # noqa: E402

STAR_FORK = re.compile(
    r'<g transform="translate\(\d+, 802\), scale\(2\)">'
    r"<path[^>]*></path></g>"
    r"<text[^>]*>\d+<title>\d+</title></text>"
)
TOTAL = re.compile(r'(text-anchor="end" fill="rgb\(255,200,55\)">)(\d+)(</text>)')
DATE_RANGE = re.compile(r"(>)(\d{4}-\d{2}-\d{2} / \d{4}-\d{2}-\d{2})(<)")


def patch(path, total, first, last):
    with open(path, encoding="utf-8") as f:
        svg = f.read()

    svg, n_counters = STAR_FORK.subn("", svg)
    svg, n_total = TOTAL.subn(rf"\g<1>{total:,}\g<3>", svg)
    svg, n_range = DATE_RANGE.subn(rf"\g<1>{first} / {last}\g<3>", svg)

    # Upstream changed shape if these don't match; fail loudly rather than
    # quietly shipping a card with the wrong number on it.
    if (n_counters, n_total, n_range) != (2, 1, 1):
        raise SystemExit(
            f"{path}: expected (2,1,1) substitutions, got "
            f"({n_counters},{n_total},{n_range}) -- upstream SVG changed"
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"patched {path}: total={total:,}, dropped star/fork counters")


if __name__ == "__main__":
    login = os.environ.get("GH_LOGIN") or sys.exit("GH_LOGIN required")
    token = os.environ.get("GH_TOKEN") or sys.exit("GH_TOKEN required")
    targets = sys.argv[1:] or sys.exit("usage: patch_3d.py <svg> [svg ...]")

    total, days = fetch_days(login, token)
    first, last = days[0][0], days[-1][0]

    for path in targets:
        patch(path, total, first, last)
