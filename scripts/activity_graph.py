"""Render a self-contained 31-day GitHub contribution activity graph."""

from datetime import timedelta
from math import ceil


THEMES = {
    "dark": {
        "bg": "#1a1b27", "text": "#c0caf5", "muted": "#8b8b8b",
        "grid": "#2d3748", "line": "#70a5fd", "point": "#bf91f3",
    },
    "light": {
        "bg": "#fffefe", "text": "#151515", "muted": "#464646",
        "grid": "#e4e2e2", "line": "#0366d6", "point": "#fb8c00",
    },
}
FONT = "'Segoe UI', Ubuntu, sans-serif"


def _ticks(maximum):
    if maximum <= 1:
        return [0, 1]
    step = max(1, ceil(maximum / 4))
    top = ceil(maximum / step) * step
    return list(range(0, top + 1, step))


def render_activity(days, theme_name, as_of=None):
    """Return a 31-day SVG ending no later than the optional ``as_of`` date."""
    if not days:
        raise ValueError("days must not be empty")
    if theme_name not in THEMES:
        raise ValueError(f"unknown theme: {theme_name}")

    theme = THEMES[theme_name]
    end = min(days[-1][0], as_of) if as_of is not None else days[-1][0]
    start = end - timedelta(days=30)
    supplied = dict(days)
    window = [(start + timedelta(days=i), supplied.get(start + timedelta(days=i), 0))
              for i in range(31)]
    ticks = _ticks(max(n for _, n in window))
    top = ticks[-1]

    width, height = 880, 300
    left, right, plot_top, bottom = 62, 24, 66, 252
    plot_width, plot_height = width - left - right, bottom - plot_top

    def x(index):
        return left + index * plot_width / 30

    def y(count):
        return bottom - count * plot_height / top

    coords = [(x(i), y(count)) for i, (_, count) in enumerate(window)]
    line_points = " ".join(f"{px:.1f},{py:.1f}" for px, py in coords)
    area_points = f"{left},{bottom} {line_points} {x(30):.1f},{bottom}"

    grid = []
    for value in ticks:
        py = y(value)
        grid.append(
            f'<line x1="{left}" y1="{py:.1f}" x2="{width-right}" y2="{py:.1f}" '
            f'stroke="{theme["grid"]}"/><text class="y-label" x="{left-12}" y="{py+4:.1f}" '
            f'text-anchor="end" fill="{theme["muted"]}" font-size="12">{value}</text>'
        )

    labels = []
    for index in (0, 6, 12, 18, 24, 30):
        day = window[index][0]
        anchor = "start" if index == 0 else "end" if index == 30 else "middle"
        labels.append(
            f'<text class="x-label" x="{x(index):.1f}" y="276" text-anchor="{anchor}" '
            f'fill="{theme["muted"]}" font-size="12">{day.isoformat()}</text>'
        )

    circles = []
    for (day, count), (px, py) in zip(window, coords):
        noun = "contribution" if count == 1 else "contributions"
        circles.append(
            f'<circle class="day-point" data-date="{day.isoformat()}" data-count="{count}" '
            f'cx="{px:.1f}" cy="{py:.1f}" r="3.2" fill="{theme["point"]}">'
            f'<title>{day.isoformat()}: {count} {noun}</title></circle>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">Contribution Graph</title>
  <desc id="desc">Daily GitHub contributions from {start.isoformat()} to {end.isoformat()}.</desc>
  <rect width="{width}" height="{height}" rx="6" fill="{theme['bg']}"/>
  <g font-family="{FONT}">
    <text x="{left}" y="36" fill="{theme['text']}" font-size="20" font-weight="600">Contribution Graph</text>
    {''.join(grid)}
    <polygon points="{area_points}" fill="{theme['line']}" fill-opacity="0.18"/>
    <polyline points="{line_points}" fill="none" stroke="{theme['line']}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
    {''.join(circles)}
    {''.join(labels)}
  </g>
</svg>
'''
