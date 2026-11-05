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
    longest_start, longest_end = None, None
    run_start = None
    for day in days:
        if day["count"] > 0:
            if running == 0:
                run_start = day["date"]
            running += 1
            if running > longest_streak:
                longest_streak = running
                longest_start = run_start
                longest_end = day["date"]
        else:
            running = 0

    streak_end_date   = datetime.now(timezone.utc).date()
    streak_start_date = streak_end_date - timedelta(days=max(0, current_streak - 1))

    first_contrib = next((d["date"] for d in days if d["count"] > 0), None)

    return {
        "total_contributions": total,
        "current_streak":      current_streak,
        "longest_streak":      longest_streak,
        "first_contribution":  first_contrib,
        "streak_start":        streak_start_date.isoformat() if current_streak > 0 else None,
        "streak_end":          streak_end_date.isoformat(),
        "longest_start":       longest_start,
        "longest_end":         longest_end,
    }


def fmt_date_short(d):
    """Format YYYY-MM-DD to 'May 6' (no year)"""
    if not d:
        return "N/A"
    dt = datetime.strptime(d, "%Y-%m-%d")
    return dt.strftime("%b %-d")


def fmt_date_long(d):
    """Format YYYY-MM-DD to 'Jan 13, 2024'"""
    if not d:
        return "N/A"
    dt = datetime.strptime(d, "%Y-%m-%d")
    return dt.strftime("%b %-d, %Y")


def build_svg(data):
    cs  = data["current_streak"]
    ls  = data["longest_streak"]
    tc  = data["total_contributions"]

    total_range   = f"{fmt_date_long(data['first_contribution'])} - Present"
    streak_range  = (
        f"{fmt_date_short(data['streak_start'])} - {fmt_date_short(data['streak_end'])}"
        if cs > 0 else "No active streak"
    )
    longest_range = (
        f"{fmt_date_short(data['longest_start'])} - {fmt_date_short(data['longest_end'])}"
        if ls > 0 else "No streaks yet"
    )

    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'
    style='isolation: isolate' viewBox='0 0 495 195' width='495px' height='195px' direction='ltr'>
    <style>
        @keyframes currstreak {{
            0%   {{ font-size: 3px;  opacity: 0.2; }}
            80%  {{ font-size: 34px; opacity: 1;   }}
            100% {{ font-size: 28px; opacity: 1;   }}
        }}
        @keyframes fadein {{
            0%   {{ opacity: 0; }}
            100% {{ opacity: 1; }}
        }}
    </style>
    <defs>
        <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>
            <stop offset='0' stop-color='#04070d'/>
            <stop offset='0.6' stop-color='#071a24'/>
            <stop offset='1' stop-color='#04070d'/>
        </linearGradient>
        <pattern id='grid' width='24' height='24' patternUnits='userSpaceOnUse'>
            <path d='M24 0H0V24' fill='none' stroke='#00e5ff' stroke-opacity='0.06'/>
        </pattern>
        <linearGradient id='scan' x1='0' y1='0' x2='0' y2='1'>
            <stop offset='0' stop-color='#00e5ff' stop-opacity='0'/>
            <stop offset='0.5' stop-color='#00e5ff' stop-opacity='0.18'/>
            <stop offset='1' stop-color='#00e5ff' stop-opacity='0'/>
        </linearGradient>
        <clipPath id='outer_rectangle'>
            <rect width='495' height='195' rx='4.5'/>
        </clipPath>
        <mask id='mask_out_ring_behind_fire'>
            <rect width='495' height='195' fill='white'/>
            <ellipse id='mask-ellipse' cx='247.5' cy='32' rx='13' ry='18' fill='black'/>
        </mask>
    </defs>
    <g clip-path='url(#outer_rectangle)'>
        <g style='isolation: isolate'>
            <rect stroke='#00e5ff' stroke-opacity='0.45' fill='url(#bg)' rx='4.5' x='0.5' y='0.5' width='494' height='194'/>
            <rect x='1' y='1' width='493' height='193' rx='4' fill='url(#grid)'/>
        </g>
        <g style='isolation: isolate'>
            <line x1='165' y1='28' x2='165' y2='170' vector-effect='non-scaling-stroke'
                stroke-width='1' stroke='#00e5ff' stroke-opacity='0.3' stroke-linejoin='miter'
                stroke-linecap='square' stroke-miterlimit='3'/>
            <line x1='330' y1='28' x2='330' y2='170' vector-effect='non-scaling-stroke'
                stroke-width='1' stroke='#00e5ff' stroke-opacity='0.3' stroke-linejoin='miter'
                stroke-linecap='square' stroke-miterlimit='3'/>
        </g>

        <g stroke='#00e5ff' stroke-width='1.5' fill='none' opacity='0.85'>
            <path d='M6 20V6H20'/><path d='M475 6H489V20'/>
            <path d='M6 175V189H20'/><path d='M475 189H489V175'/>
        </g>
        <rect x='1' y='-30' width='493' height='30' fill='url(#scan)'>
            <animate attributeName='y' values='-30;195' dur='5s' repeatCount='indefinite'/>
        </rect>

        <!-- Total Contributions -->
        <g style='isolation: isolate'>
            <g transform='translate(82.5, 48)'>
                <text x='0' y='32' stroke-width='0' text-anchor='middle'
                    fill='#00e5ff' stroke='none'
                    font-family='Courier New, Courier, monospace'
                    font-weight='700' font-size='28px'
                    style='opacity: 0; animation: fadein 0.5s linear forwards 0.6s'>{tc:,}</text>
            </g>
            <g transform='translate(82.5, 84)'>
                <text x='0' y='32' stroke-width='0' text-anchor='middle'
                    fill='#e6fbff' stroke='none'
                    font-family='Courier New, Courier, monospace'
                    font-weight='400' font-size='14px'
                    style='opacity: 0; animation: fadein 0.5s linear forwards 0.7s'>CONTRIBUTIONS</text>
            </g>
            <g transform='translate(82.5, 114)'>
                <text x='0' y='32' stroke-width='0' text-anchor='middle'
                    fill='#7fb8c4' stroke='none'
                    font-family='Courier New, Courier, monospace'
                    font-weight='400' font-size='12px'
                    style='opacity: 0; animation: fadein 0.5s linear forwards 0.8s'>{total_range}</text>
            </g>
        </g>

        <!-- Current Streak -->
        <g style='isolation: isolate'>
            <g transform='translate(247.5, 48)'>
                <text x='0' y='32' stroke-width='0' text-anchor='middle'
                    fill='#e6fbff' stroke='none'
                    font-family='Courier New, Courier, monospace'
                    font-weight='700' font-size='28px'
                    style='animation: currstreak 0.6s linear forwards'>{cs}</text>
            </g>
            <g transform='translate(247.5, 108)'>
                <text x='0' y='32' stroke-width='0' text-anchor='middle'
                    fill='#00e5ff' stroke='none'
                    font-family='Courier New, Courier, monospace'
                    font-weight='700' font-size='14px'
                    style='opacity: 0; animation: fadein 0.5s linear forwards 0.9s'>CURRENT STREAK</text>
            </g>
            <g transform='translate(247.5, 145)'>
                <text x='0' y='21' stroke-width='0' text-anchor='middle'
                    fill='#7fb8c4' stroke='none'
                    font-family='Courier New, Courier, monospace'
                    font-weight='400' font-size='12px'
                    style='opacity: 0; animation: fadein 0.5s linear forwards 0.9s'>{streak_range}</text>
            </g>
            <!-- Ring around number -->
            <g mask='url(#mask_out_ring_behind_fire)'>
                <circle cx='247.5' cy='71' r='40' fill='none'
                    stroke='#00e5ff' stroke-width='5'
                    style='opacity: 0; animation: fadein 0.5s linear forwards 0.4s'/>
            </g>
            <!-- Fire icon -->
            <g transform='translate(247.5, 19.5)' stroke-opacity='0'
                style='opacity: 0; animation: fadein 0.5s linear forwards 0.6s'>
                <path d='M -12 -0.5 L 15 -0.5 L 15 23.5 L -12 23.5 L -12 -0.5 Z' fill='none'/>
                <path d='M 1.5 0.67 C 1.5 0.67 2.24 3.32 2.24 5.47 C 2.24 7.53 0.89 9.2 -1.17 9.2
                    C -3.23 9.2 -4.79 7.53 -4.79 5.47 L -4.76 5.11
                    C -6.78 7.51 -8 10.62 -8 13.99 C -8 18.41 -4.42 22 0 22
                    C 4.42 22 8 18.41 8 13.99 C 8 8.6 5.41 3.79 1.5 0.67 Z
                    M -0.29 19 C -2.07 19 -3.51 17.6 -3.51 15.86
                    C -3.51 14.24 -2.46 13.1 -0.7 12.74
                    C 1.07 12.38 2.9 11.53 3.92 10.16
                    C 4.31 11.45 4.51 12.81 4.51 14.2
                    C 4.51 16.85 2.36 19 -0.29 19 Z'
                    fill='#00e5ff' stroke-opacity='0'/>
            </g>
        </g>

        <!-- Longest Streak -->
        <g style='isolation: isolate'>
            <g transform='translate(412.5, 48)'>
                <text x='0' y='32' stroke-width='0' text-anchor='middle'
                    fill='#00e5ff' stroke='none'
                    font-family='Courier New, Courier, monospace'
                    font-weight='700' font-size='28px'
                    style='opacity: 0; animation: fadein 0.5s linear forwards 1.2s'>{ls}</text>
            </g>
            <g transform='translate(412.5, 84)'>
                <text x='0' y='32' stroke-width='0' text-anchor='middle'
                    fill='#e6fbff' stroke='none'
                    font-family='Courier New, Courier, monospace'
                    font-weight='400' font-size='14px'
                    style='opacity: 0; animation: fadein 0.5s linear forwards 1.3s'>LONGEST STREAK</text>
            </g>
            <g transform='translate(412.5, 114)'>
                <text x='0' y='32' stroke-width='0' text-anchor='middle'
                    fill='#7fb8c4' stroke='none'
                    font-family='Courier New, Courier, monospace'
                    font-weight='400' font-size='12px'
                    style='opacity: 0; animation: fadein 0.5s linear forwards 1.4s'>{longest_range}</text>
            </g>
        </g>

    </g>
</svg>"""
    return svg


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