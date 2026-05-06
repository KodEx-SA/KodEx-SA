import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta

USERNAME = os.environ.get("GITHUB_USERNAME", "KodEx-SA")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT_PATH = os.environ.get("STREAK_OUTPUT_PATH", "github-streak.svg")


def graphql(query, token):
    data = json.dumps({"query": query}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=data)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "github-streak-svg-generator")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get_contribution_data(username, token):
    # Fetch last 365 days via contributionCalendar
    query = f"""
    {{
      user(login: "{username}") {{
        contributionsCollection {{
          contributionCalendar {{
            totalContributions
            weeks {{
              contributionDays {{
                date
                contributionCount
              }}
            }}
          }}
        }}
      }}
    }}
    """
    result = graphql(query, token)
    cal = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    total = cal["totalContributions"]

    days = []
    for week in cal["weeks"]:
        for day in week["contributionDays"]:
            days.append({
                "date": day["date"],
                "count": day["contributionCount"],
            })

    days.sort(key=lambda d: d["date"])

    # Calculate current streak
    today = datetime.now(timezone.utc).date()
    current_streak = 0
    check_date = today

    # If today has no contributions yet, start from yesterday
    today_str = today.isoformat()
    today_data = next((d for d in days if d["date"] == today_str), None)
    if today_data is None or today_data["count"] == 0:
        check_date = today - timedelta(days=1)

    while True:
        date_str = check_date.isoformat()
        day_data = next((d for d in days if d["date"] == date_str), None)
        if day_data and day_data["count"] > 0:
            current_streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    # Calculate longest streak
    longest_streak = 0
    running = 0
    for day in days:
        if day["count"] > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0

    # First contribution date
    first_contrib = next((d["date"] for d in days if d["count"] > 0), None)

    return {
        "total_contributions": total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "first_contribution": first_contrib,
        "days": days,
    }


def flame_path(cx, cy, size):
    """Simple flame SVG path centered at cx, cy"""
    s = size
    return (
        f"M {cx},{cy - s} "
        f"C {cx + s*0.4},{cy - s*0.6} {cx + s*0.6},{cy - s*0.2} {cx + s*0.3},{cy + s*0.1} "
        f"C {cx + s*0.5},{cy - s*0.1} {cx + s*0.4},{cy + s*0.4} {cx},{cy + s} "
        f"C {cx - s*0.4},{cy + s*0.4} {cx - s*0.5},{cy - s*0.1} {cx - s*0.3},{cy + s*0.1} "
        f"C {cx - s*0.6},{cy - s*0.2} {cx - s*0.4},{cy - s*0.6} {cx},{cy - s} Z"
    )


def mini_bar_graph(days, x, y, w, h):
    """Generate a mini contribution bar graph for last 28 days"""
    recent = days[-28:] if len(days) >= 28 else days
    max_count = max((d["count"] for d in recent), default=1) or 1
    bar_w = w / len(recent)
    rects = []
    for i, day in enumerate(recent):
        bar_h = max(1, (day["count"] / max_count) * h)
        bx = x + i * bar_w
        by = y + h - bar_h
        opacity = 0.3 + 0.7 * (day["count"] / max_count) if day["count"] > 0 else 0.08
        rects.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w - 1:.1f}" height="{bar_h:.1f}" '
            f'rx="1" fill="#34eb5c" opacity="{opacity:.2f}"/>'
        )
    return rects


def build_svg(data):
    W, H = 480, 200

    cs = data["current_streak"]
    ls = data["longest_streak"]
    tc = data["total_contributions"]
    first = data["first_contribution"] or "N/A"

    lines = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="GitHub Streak for {USERNAME}">'
    )
    lines.append(f'<title>GitHub Streak — {USERNAME}</title>')

    # Background
    lines.append(
        f'<rect width="{W}" height="{H}" rx="12" fill="#0d1117" stroke="#21262d" stroke-width="1"/>'
    )

    # Title
    lines.append(
        f'<text x="20" y="26" font-family="monospace" font-size="11" '
        f'fill="#34eb5c" letter-spacing="2" opacity="0.85">CONTRIBUTION STREAK — {USERNAME.upper()}</text>'
    )
    lines.append(
        f'<line x1="20" y1="33" x2="{W-20}" y2="33" stroke="#21262d" stroke-width="0.8"/>'
    )

    # --- Left panel: Current streak with flame ---
    panel_mid = 115
    flame_cx, flame_cy = panel_mid, 95

    # Glow circle behind flame
    lines.append(
        f'<circle cx="{flame_cx}" cy="{flame_cy + 10}" r="42" '
        f'fill="#34eb5c" opacity="0.04"/>'
    )
    # Flame shape (outer)
    lines.append(
        f'<path d="{flame_path(flame_cx, flame_cy, 38)}" fill="#F7A325" opacity="0.9"/>'
    )
    # Flame inner highlight
    lines.append(
        f'<path d="{flame_path(flame_cx, flame_cy + 8, 22)}" fill="#FFD166" opacity="0.7"/>'
    )

    # Current streak number over flame
    lines.append(
        f'<text x="{flame_cx}" y="{flame_cy + 8}" text-anchor="middle" '
        f'font-family="monospace" font-size="28" font-weight="bold" fill="#ffffff">{cs}</text>'
    )
    lines.append(
        f'<text x="{flame_cx}" y="{flame_cy + 22}" text-anchor="middle" '
        f'font-family="monospace" font-size="8" fill="#ffffffaa">DAY STREAK</text>'
    )

    # Label below flame
    lines.append(
        f'<text x="{flame_cx}" y="{H - 20}" text-anchor="middle" font-family="monospace" '
        f'font-size="10" fill="#8b949e">CURRENT STREAK</text>'
    )

    # Vertical divider
    lines.append(
        f'<line x1="200" y1="40" x2="200" y2="{H - 14}" stroke="#21262d" stroke-width="0.8"/>'
    )

    # --- Right panel: Stats + mini graph ---
    rx = 215

    # Longest streak
    lines.append(
        f'<text x="{rx}" y="58" font-family="monospace" font-size="10" fill="#8b949e">LONGEST STREAK</text>'
    )
    lines.append(
        f'<text x="{rx}" y="80" font-family="monospace" font-size="26" '
        f'font-weight="bold" fill="#34eb5c">{ls} <tspan font-size="12" fill="#8b949e">days</tspan></text>'
    )

    lines.append(
        f'<line x1="{rx}" y1="88" x2="{W - 20}" y2="88" stroke="#21262d" stroke-width="0.5"/>'
    )

    # Total contributions
    lines.append(
        f'<text x="{rx}" y="104" font-family="monospace" font-size="10" fill="#8b949e">TOTAL CONTRIBUTIONS</text>'
    )
    lines.append(
        f'<text x="{rx}" y="124" font-family="monospace" font-size="22" '
        f'font-weight="bold" fill="#34eb5c">{tc:,}</text>'
    )

    lines.append(
        f'<line x1="{rx}" y1="130" x2="{W - 20}" y2="130" stroke="#21262d" stroke-width="0.5"/>'
    )

    # Mini bar graph — last 28 days
    bar_rects = mini_bar_graph(data["days"], rx, 136, W - rx - 20, 32)
    for r in bar_rects:
        lines.append(r)

    lines.append(
        f'<text x="{rx}" y="{H - 8}" font-family="monospace" font-size="9" '
        f'fill="#484f58">last 28 days · since {first}</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


def main():
    print(f"Fetching streak data for: {USERNAME}")
    data = get_contribution_data(USERNAME, TOKEN)
    print(f"  Current streak:  {data['current_streak']} days")
    print(f"  Longest streak:  {data['longest_streak']} days")
    print(f"  Total contrib:   {data['total_contributions']}")
    svg = build_svg(data)
    with open(OUTPUT_PATH, "w") as f:
        f.write(svg)
    print(f"SVG written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
