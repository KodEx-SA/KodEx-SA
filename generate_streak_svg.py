import os
import json
import math
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
            days.append({"date": day["date"], "count": day["contributionCount"]})
    days.sort(key=lambda d: d["date"])

    today = datetime.now(timezone.utc).date()
    today_str = today.isoformat()
    today_data = next((d for d in days if d["date"] == today_str), None)
    check_date = today if (today_data and today_data["count"] > 0) else today - timedelta(days=1)

    current_streak = 0
    while True:
        ds = check_date.isoformat()
        d = next((x for x in days if x["date"] == ds), None)
        if d and d["count"] > 0:
            current_streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    longest_streak, running = 0, 0
    for day in days:
        if day["count"] > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0

    first_contrib = next((d["date"] for d in days if d["count"] > 0), None)

    return {
        "total_contributions": total,
        "current_streak":      current_streak,
        "longest_streak":      longest_streak,
        "first_contribution":  first_contrib,
        "days":                days,
    }


def build_svg(data):
    W, H = 495, 195

    cs = data["current_streak"]
    ls = data["longest_streak"]
    tc = data["total_contributions"]
    first = data["first_contribution"] or "N/A"

    # 28-day mini bar data
    recent = data["days"][-28:] if len(data["days"]) >= 28 else data["days"]
    max_c = max((d["count"] for d in recent), default=1) or 1

    lines = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="GitHub Streak for {USERNAME}">'
    )
    lines.append(f'<title>GitHub Streak — {USERNAME}</title>')

    # Card background
    lines.append(f'<rect width="{W}" height="{H}" rx="12" fill="#0d1117" stroke="#30363d" stroke-width="1"/>')

    # Header bar
    lines.append(f'<rect width="{W}" height="42" rx="12" fill="#161b22"/>')
    lines.append(f'<rect y="30" width="{W}" height="12" fill="#161b22"/>')
    lines.append(f'<line x1="0" y1="42" x2="{W}" y2="42" stroke="#30363d" stroke-width="0.8"/>')

    # Title
    lines.append(
        f'<text x="18" y="27" font-family="monospace" font-size="12" '
        f'font-weight="bold" fill="#34eb5c" letter-spacing="1">Contribution Streak</text>'
    )

    # "since" pill
    lines.append(f'<rect x="{W-126}" y="13" width="110" height="18" rx="9" fill="#1f2937" stroke="#30363d" stroke-width="0.8"/>')
    lines.append(
        f'<text x="{W-71}" y="26" text-anchor="middle" font-family="monospace" '
        f'font-size="10" fill="#6e7681">since {first}</text>'
    )

    # ── Three equal columns ──────────────────────────────
    col_w = W // 3
    body_y = 42
    body_h = H - 42
    mid_y = body_y + body_h // 2

    # Dividers
    lines.append(f'<line x1="{col_w}" y1="{body_y+12}" x2="{col_w}" y2="{H-12}" stroke="#21262d" stroke-width="0.8"/>')
    lines.append(f'<line x1="{col_w*2}" y1="{body_y+12}" x2="{col_w*2}" y2="{H-12}" stroke="#21262d" stroke-width="0.8"/>')

    # ── Col 1: Current streak with ring ──
    c1x = col_w // 2
    ring_r = 34
    ring_cx, ring_cy = c1x, mid_y - 4

    # Background ring
    lines.append(
        f'<circle cx="{ring_cx}" cy="{ring_cy}" r="{ring_r}" '
        f'fill="none" stroke="#21262d" stroke-width="5"/>'
    )
    # Progress arc — full circle if streak > 0, else empty
    if cs > 0:
        # Arc representing min(cs/30, 1.0) of circle
        fraction = min(cs / 30.0, 1.0)
        angle = fraction * 360
        if angle >= 359.9:
            lines.append(
                f'<circle cx="{ring_cx}" cy="{ring_cy}" r="{ring_r}" '
                f'fill="none" stroke="#f7a325" stroke-width="5"/>'
            )
        else:
            rad = math.radians(angle - 90)
            ex = ring_cx + ring_r * math.cos(rad)
            ey = ring_cy + ring_r * math.sin(rad)
            large = 1 if angle > 180 else 0
            lines.append(
                f'<path d="M {ring_cx},{ring_cy - ring_r} A {ring_r},{ring_r} 0 {large},1 {ex:.2f},{ey:.2f}" '
                f'fill="none" stroke="#f7a325" stroke-width="5" stroke-linecap="round"/>'
            )

    # Flame emoji center
    lines.append(
        f'<text x="{ring_cx}" y="{ring_cy - 4}" text-anchor="middle" font-size="16">🔥</text>'
    )
    lines.append(
        f'<text x="{ring_cx}" y="{ring_cy + 14}" text-anchor="middle" font-family="monospace" '
        f'font-size="20" font-weight="bold" fill="#f7a325">{cs}</text>'
    )
    lines.append(
        f'<text x="{ring_cx}" y="{H - 10}" text-anchor="middle" font-family="monospace" '
        f'font-size="9" fill="#6e7681" letter-spacing="0.5">CURRENT STREAK</text>'
    )

    # ── Col 2: Longest streak ──
    c2x = col_w + col_w // 2
    lines.append(
        f'<text x="{c2x}" y="{mid_y - 22}" text-anchor="middle" font-family="monospace" '
        f'font-size="9" fill="#6e7681" letter-spacing="0.5">LONGEST STREAK</text>'
    )
    lines.append(
        f'<text x="{c2x}" y="{mid_y + 10}" text-anchor="middle" font-family="monospace" '
        f'font-size="30" font-weight="bold" fill="#58a6ff">{ls}</text>'
    )
    lines.append(
        f'<text x="{c2x}" y="{mid_y + 26}" text-anchor="middle" font-family="monospace" '
        f'font-size="11" fill="#6e7681">days</text>'
    )

    # ── Col 3: Total contributions + mini graph ──
    c3x = col_w * 2
    graph_x = c3x + 12
    graph_w = col_w - 24
    graph_y = body_y + 16
    graph_h = 42

    # Mini bar graph
    bar_w = graph_w / len(recent)
    for i, day in enumerate(recent):
        if day["count"] == 0:
            opacity = 0.07
            bh = 2
        else:
            opacity = 0.35 + 0.65 * (day["count"] / max_c)
            bh = max(3, (day["count"] / max_c) * graph_h)
        bx = graph_x + i * bar_w
        by = graph_y + graph_h - bh
        lines.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{max(1, bar_w-1):.1f}" '
            f'height="{bh:.1f}" rx="1" fill="#34eb5c" opacity="{opacity:.2f}"/>'
        )

    lines.append(
        f'<text x="{c3x + col_w//2}" y="{graph_y + graph_h + 16}" text-anchor="middle" '
        f'font-family="monospace" font-size="9" fill="#6e7681">28-DAY ACTIVITY</text>'
    )

    # Total count
    lines.append(
        f'<text x="{c3x + col_w//2}" y="{H - 30}" text-anchor="middle" font-family="monospace" '
        f'font-size="22" font-weight="bold" fill="#34eb5c">{tc:,}</text>'
    )
    lines.append(
        f'<text x="{c3x + col_w//2}" y="{H - 10}" text-anchor="middle" font-family="monospace" '
        f'font-size="9" fill="#6e7681" letter-spacing="0.5">TOTAL CONTRIBUTIONS</text>'
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