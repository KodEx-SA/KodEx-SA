import os
import json
import math
import urllib.request
import urllib.error

USERNAME = os.environ.get("GITHUB_USERNAME", "KodEx-SA")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "languages.svg")

EXCLUDE_LANGS = {"HTML", "Markdown", "MDX", "CSS", "SCSS", "Shell"}
MAX_LANGS = 6

COLORS = [
    "#34eb5c",  # brand green
    "#1aab3d",
    "#0d7a2b",
    "#278a47",
    "#4CAF70",
    "#2d5c3a",
]
OTHER_COLOR = "#3a3a3a"


def fetch(url, token):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "lang-svg-generator")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get_language_bytes(username, token):
    totals = {}
    page = 1
    while True:
        url = (
            f"https://api.github.com/users/{username}/repos"
            f"?per_page=100&page={page}&type=owner"
        )
        repos = fetch(url, token)
        if not repos:
            break
        for repo in repos:
            if repo.get("fork"):
                continue
            lang_url = repo.get("languages_url")
            if not lang_url:
                continue
            try:
                langs = fetch(lang_url, token)
                for lang, bytes_count in langs.items():
                    if lang not in EXCLUDE_LANGS:
                        totals[lang] = totals.get(lang, 0) + bytes_count
            except Exception:
                pass
        page += 1
        if len(repos) < 100:
            break
    return totals


def build_svg(lang_data):
    total = sum(lang_data.values())
    if total == 0:
        return None

    sorted_langs = sorted(lang_data.items(), key=lambda x: x[1], reverse=True)
    top = sorted_langs[:MAX_LANGS]
    other_bytes = sum(v for _, v in sorted_langs[MAX_LANGS:])

    segments = []
    for i, (lang, bytes_count) in enumerate(top):
        pct = bytes_count / total
        segments.append({
            "name": lang,
            "pct": pct,
            "color": COLORS[i % len(COLORS)],
        })

    if other_bytes > 0:
        segments.append({
            "name": "Other",
            "pct": other_bytes / total,
            "color": OTHER_COLOR,
        })

    # SVG dimensions
    W, H = 480, 200
    cx, cy, R, thickness = 100, 100, 72, 22

    def arc_path(start_angle, end_angle, r, cx, cy):
        start_rad = math.radians(start_angle - 90)
        end_rad = math.radians(end_angle - 90)
        x1 = cx + r * math.cos(start_rad)
        y1 = cy + r * math.sin(start_rad)
        x2 = cx + r * math.cos(end_rad)
        y2 = cy + r * math.sin(end_rad)
        large = 1 if (end_angle - start_angle) > 180 else 0
        return f"M {x1:.3f},{y1:.3f} A {r},{r} 0 {large},1 {x2:.3f},{y2:.3f}"

    gap_deg = 2.5
    current_angle = 0
    arc_paths = []

    for seg in segments:
        span = seg["pct"] * 360
        if span < gap_deg:
            current_angle += span
            continue
        start = current_angle + gap_deg / 2
        end = current_angle + span - gap_deg / 2
        outer = arc_path(start, end, R, cx, cy)
        inner_start = math.radians(end - 90)
        inner_end = math.radians(start - 90)
        ri = R - thickness
        ix1 = cx + ri * math.cos(inner_start)
        iy1 = cy + ri * math.sin(inner_start)
        ix2 = cx + ri * math.cos(inner_end)
        iy2 = cy + ri * math.sin(inner_end)
        large = 1 if span > 180 else 0
        full = (
            f"{outer} L {ix1:.3f},{iy1:.3f} "
            f"A {ri},{ri} 0 {large},0 {ix2:.3f},{iy2:.3f} Z"
        )
        arc_paths.append((full, seg["color"]))
        current_angle += span

    # Legend rows
    legend_x = 210
    legend_y_start = 28
    row_h = 26
    legend_items = []
    for i, seg in enumerate(segments):
        y = legend_y_start + i * row_h
        pct_str = f"{seg['pct']*100:.1f}%"
        legend_items.append((seg["name"], pct_str, seg["color"], y))

    # Bar row under legend
    bar_y = legend_y_start + len(segments) * row_h + 6
    bar_x = legend_x
    bar_w = 250
    bar_h = 6

    bar_rects = []
    bx = bar_x
    for seg in segments:
        sw = seg["pct"] * bar_w
        if sw > 1:
            bar_rects.append((bx, sw, seg["color"]))
            bx += sw

    # Build SVG string
    lines = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Donut chart of most used programming languages for {USERNAME}">'
    )
    lines.append(
        f'<title>Most Used Languages — {USERNAME}</title>'
    )

    # Background
    lines.append(
        f'<rect width="{W}" height="{H}" rx="12" '
        f'fill="#0d1117" stroke="#21262d" stroke-width="1"/>'
    )

    # Title
    lines.append(
        f'<text x="20" y="22" font-family="monospace" font-size="11" '
        f'fill="#34eb5c" letter-spacing="2" opacity="0.7">MOST USED LANGUAGES</text>'
    )

    # Donut arcs
    for path_d, color in arc_paths:
        lines.append(f'<path d="{path_d}" fill="{color}"/>')

    # Center label
    lines.append(
        f'<text x="{cx}" y="{cy - 6}" text-anchor="middle" font-family="monospace" '
        f'font-size="10" fill="#8b949e">TOP</text>'
    )
    lines.append(
        f'<text x="{cx}" y="{cy + 10}" text-anchor="middle" font-family="monospace" '
        f'font-size="22" font-weight="bold" fill="#34eb5c">{len(segments)}</text>'
    )
    lines.append(
        f'<text x="{cx}" y="{cy + 24}" text-anchor="middle" font-family="monospace" '
        f'font-size="9" fill="#8b949e">LANGS</text>'
    )

    # Legend
    for name, pct_str, color, y in legend_items:
        lines.append(
            f'<circle cx="{legend_x + 5}" cy="{y + 5}" r="5" fill="{color}"/>'
        )
        lines.append(
            f'<text x="{legend_x + 16}" y="{y + 10}" font-family="monospace" '
            f'font-size="12" fill="#e6edf3">{name}</text>'
        )
        lines.append(
            f'<text x="{legend_x + 250}" y="{y + 10}" text-anchor="end" '
            f'font-family="monospace" font-size="12" fill="#34eb5c">{pct_str}</text>'
        )

    # Bar
    bx2 = bar_x
    for bx_val, sw, color in bar_rects:
        lines.append(
            f'<rect x="{bx_val:.2f}" y="{bar_y}" width="{sw:.2f}" height="{bar_h}" '
            f'fill="{color}"/>'
        )
        bx2 += sw

    # Bottom label
    lines.append(
        f'<text x="{legend_x}" y="{bar_y + bar_h + 14}" font-family="monospace" '
        f'font-size="9" fill="#484f58">auto-updated · excludes forks &amp; markup</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


def main():
    print(f"Fetching language stats for: {USERNAME}")
    lang_data = get_language_bytes(USERNAME, TOKEN)

    if not lang_data:
        print("No language data found.")
        return

    print("Language breakdown:")
    total = sum(lang_data.values())
    for lang, b in sorted(lang_data.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {lang}: {b/total*100:.1f}%")

    svg = build_svg(lang_data)
    if svg:
        with open(OUTPUT_PATH, "w") as f:
            f.write(svg)
        print(f"SVG written to: {OUTPUT_PATH}")
    else:
        print("Could not generate SVG.")


if __name__ == "__main__":
    main()
