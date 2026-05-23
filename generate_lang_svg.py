import os
import json
import math
import urllib.request

USERNAME = os.environ.get("GITHUB_USERNAME", "KodEx-SA")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "languages.svg")

EXCLUDE_LANGS = {"Markdown", "MDX", "Text", "Batchfile", "Makefile"}
MAX_LANGS = 8

LANG_COLORS = {
    "TypeScript":        "#3178C6",
    "JavaScript":        "#F7DF1E",
    "Python":            "#3572A5",
    "C":                 "#A8B9CC",
    "C++":               "#F34B7D",
    "C#":                "#178600",
    "Rust":              "#DEA584",
    "Go":                "#00ADD8",
    "Java":              "#B07219",
    "Kotlin":            "#A97BFF",
    "Swift":             "#F05138",
    "Ruby":              "#CC342D",
    "PHP":               "#4F5D95",
    "HTML":              "#E34C26",
    "CSS":               "#563D7C",
    "SCSS":              "#C6538C",
    "Shell":             "#89E051",
    "PowerShell":        "#012456",
    "Dockerfile":        "#384D54",
    "PLpgSQL":           "#336791",
    "SQL":               "#E38C00",
    "Visual Basic .NET": "#945DB7",
    "Lua":               "#000080",
    "Dart":              "#00B4AB",
    "R":                 "#198CE7",
    "Other":             "#6E7681",
}

FALLBACK_COLORS = [
    "#00c9c9", "#0099aa", "#006e8a", "#00c9ff",
    "#4dd0e1", "#00838f", "#00acc1", "#26c6da",
]


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


def get_color(lang, fallback_index):
    if lang in LANG_COLORS:
        return LANG_COLORS[lang]
    return FALLBACK_COLORS[fallback_index % len(FALLBACK_COLORS)]


def arc_path(start_angle, end_angle, r, cx, cy):
    start_rad = math.radians(start_angle - 90)
    end_rad = math.radians(end_angle - 90)
    x1 = cx + r * math.cos(start_rad)
    y1 = cy + r * math.sin(start_rad)
    x2 = cx + r * math.cos(end_rad)
    y2 = cy + r * math.sin(end_rad)
    large = 1 if (end_angle - start_angle) > 180 else 0
    return f"M {x1:.3f},{y1:.3f} A {r},{r} 0 {large},1 {x2:.3f},{y2:.3f}"


def build_donut_path(start_angle, end_angle, R, thickness, cx, cy):
    outer = arc_path(start_angle, end_angle, R, cx, cy)
    ri = R - thickness
    inner_start_rad = math.radians(end_angle - 90)
    inner_end_rad = math.radians(start_angle - 90)
    ix1 = cx + ri * math.cos(inner_start_rad)
    iy1 = cy + ri * math.sin(inner_start_rad)
    ix2 = cx + ri * math.cos(inner_end_rad)
    iy2 = cy + ri * math.sin(inner_end_rad)
    span = end_angle - start_angle
    large = 1 if span > 180 else 0
    return (
        f"{outer} L {ix1:.3f},{iy1:.3f} "
        f"A {ri},{ri} 0 {large},0 {ix2:.3f},{iy2:.3f} Z"
    )


def build_svg(lang_data):
    total = sum(lang_data.values())
    if total == 0:
        return None

    sorted_langs = sorted(lang_data.items(), key=lambda x: x[1], reverse=True)
    top = sorted_langs[:MAX_LANGS]
    other_bytes = sum(v for _, v in sorted_langs[MAX_LANGS:])

    segments = []
    fallback_idx = 0
    for lang, bytes_count in top:
        color = get_color(lang, fallback_idx)
        if lang not in LANG_COLORS:
            fallback_idx += 1
        segments.append({"name": lang, "pct": bytes_count / total, "color": color})

    if other_bytes > 0:
        segments.append({"name": "Other", "pct": other_bytes / total, "color": LANG_COLORS["Other"]})

    W = 540
    legend_rows = len(segments)
    row_h = 28
    padding_top = 48
    padding_bottom = 40
    H = max(240, legend_rows * row_h + padding_top + padding_bottom)

    cx, cy = 108, H // 2
    R, thickness = 82, 26
    gap_deg = 2.0

    current_angle = 0
    arc_paths = []
    for seg in segments:
        span = seg["pct"] * 360
        if span < gap_deg + 0.5:
            current_angle += span
            continue
        start = current_angle + gap_deg / 2
        end = current_angle + span - gap_deg / 2
        path_d = build_donut_path(start, end, R, thickness, cx, cy)
        arc_paths.append((path_d, seg["color"]))
        current_angle += span

    legend_x = 215
    legend_y_start = padding_top - 4
    bar_y = legend_y_start + legend_rows * row_h + 6
    bar_w = 290
    bar_h = 5
    bar_rects = []
    bx = legend_x
    for seg in segments:
        sw = seg["pct"] * bar_w
        if sw >= 1:
            bar_rects.append((bx, sw, seg["color"]))
            bx += sw

    lines = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Donut chart of most used programming languages for {USERNAME}">'
    )
    lines.append(f'<title>Most Used Languages — {USERNAME}</title>')

    # Ocean-themed background
    lines.append(
        f'<rect width="{W}" height="{H}" rx="10" fill="#0a0a0a" stroke="#00c9c9" stroke-width="1"/>'
    )

    # Title
    lines.append(
        f'<text x="20" y="26" font-family="\'Segoe UI\', Ubuntu, sans-serif" font-size="13" '
        f'font-weight="600" fill="#00c9c9" letter-spacing="1">Most Used Languages</text>'
    )
    lines.append(
        f'<line x1="20" y1="33" x2="{W - 20}" y2="33" stroke="#003d4d" stroke-width="0.8"/>'
    )

    for path_d, color in arc_paths:
        lines.append(f'<path d="{path_d}" fill="{color}"/>')

    # Center label
    lines.append(
        f'<text x="{cx}" y="{cy - 12}" text-anchor="middle" font-family="monospace" '
        f'font-size="10" fill="#006e8a">TOP</text>'
    )
    lines.append(
        f'<text x="{cx}" y="{cy + 10}" text-anchor="middle" font-family="monospace" '
        f'font-size="28" font-weight="bold" fill="#00c9c9">{len(segments)}</text>'
    )
    lines.append(
        f'<text x="{cx}" y="{cy + 26}" text-anchor="middle" font-family="monospace" '
        f'font-size="9" fill="#006e8a">LANGS</text>'
    )

    # Vertical divider
    lines.append(
        f'<line x1="195" y1="40" x2="195" y2="{H - 20}" stroke="#003d4d" stroke-width="0.8"/>'
    )

    for i, seg in enumerate(segments):
        y = legend_y_start + i * row_h
        pct_str = f"{seg['pct']*100:.1f}%"
        lines.append(f'<circle cx="{legend_x + 5}" cy="{y + 8}" r="5" fill="{seg["color"]}"/>')
        lines.append(
            f'<text x="{legend_x + 18}" y="{y + 13}" font-family="\'Segoe UI\', Ubuntu, sans-serif" '
            f'font-size="12" fill="#e0f7fa">{seg["name"]}</text>'
        )
        bar_bg_x = legend_x + 155
        mini_w = 115
        lines.append(
            f'<rect x="{bar_bg_x}" y="{y + 4}" width="{mini_w}" height="7" rx="3" fill="#0d2a33"/>'
        )
        fill_w = seg["pct"] * mini_w
        if fill_w >= 1:
            lines.append(
                f'<rect x="{bar_bg_x}" y="{y + 4}" width="{fill_w:.2f}" height="7" '
                f'rx="3" fill="{seg["color"]}"/>'
            )
        lines.append(
            f'<text x="{bar_bg_x + mini_w + 8}" y="{y + 13}" '
            f'font-family="monospace" font-size="11" fill="{seg["color"]}">{pct_str}</text>'
        )

    for bx_val, sw, color in bar_rects:
        lines.append(
            f'<rect x="{bx_val:.2f}" y="{bar_y}" width="{sw:.2f}" height="{bar_h}" fill="{color}"/>'
        )

    lines.append(
        f'<text x="{legend_x}" y="{bar_y + bar_h + 16}" font-family="monospace" '
        f'font-size="9" fill="#004d5c">auto-updated · excludes forks &amp; markup</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


def main():
    print(f"Fetching language stats for: {USERNAME}")
    lang_data = get_language_bytes(USERNAME, TOKEN)
    if not lang_data:
        print("No language data found.")
        return
    total = sum(lang_data.values())
    print("Language breakdown:")
    for lang, b in sorted(lang_data.items(), key=lambda x: x[1], reverse=True):
        print(f"  {lang}: {b/total*100:.1f}%")
    svg = build_svg(lang_data)
    if svg:
        with open(OUTPUT_PATH, "w") as f:
            f.write(svg)
        print(f"\nSVG written to: {OUTPUT_PATH}")
    else:
        print("Could not generate SVG.")


if __name__ == "__main__":
    main()
