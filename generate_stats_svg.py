import os
import json
import math
import urllib.request
from datetime import datetime, timezone

USERNAME = os.environ.get("GITHUB_USERNAME", "KodEx-SA")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT_PATH = os.environ.get("STATS_OUTPUT_PATH", "github-stats.svg")


def fetch(url, token):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "github-stats-svg-generator")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def graphql(query, token):
    data = json.dumps({"query": query}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=data)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "github-stats-svg-generator")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get_stats(username, token):
    query = f"""
    {{
      user(login: "{username}") {{
        name
        repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {{
          totalCount
          nodes {{
            stargazerCount
            forkCount
            primaryLanguage {{ name }}
          }}
        }}
        contributionsCollection {{
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          totalRepositoryContributions
          contributionCalendar {{
            totalContributions
          }}
        }}
        followers {{ totalCount }}
        following {{ totalCount }}
      }}
    }}
    """
    result = graphql(query, token)
    user = result["data"]["user"]

    repos = user["repositories"]["nodes"]
    total_stars = sum(r["stargazerCount"] for r in repos)
    total_forks = sum(r["forkCount"] for r in repos)

    lang_counts = {}
    for r in repos:
        if r.get("primaryLanguage"):
            lang = r["primaryLanguage"]["name"]
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
    top_lang = max(lang_counts, key=lang_counts.get) if lang_counts else "N/A"

    cc = user["contributionsCollection"]
    return {
        "total_repos": user["repositories"]["totalCount"],
        "total_stars": total_stars,
        "total_forks": total_forks,
        "total_commits": cc["totalCommitContributions"],
        "total_prs": cc["totalPullRequestContributions"],
        "total_issues": cc["totalIssueContributions"],
        "total_contributions": cc["contributionCalendar"]["totalContributions"],
        "followers": user["followers"]["totalCount"],
        "top_lang": top_lang,
    }


def fmt(n):
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def build_svg(stats):
    W, H = 480, 200

    items = [
        ("⭐", "Stars Earned",    fmt(stats["total_stars"])),
        ("🔀", "Total Commits",   fmt(stats["total_commits"])),
        ("🔃", "Pull Requests",   fmt(stats["total_prs"])),
        ("🐛", "Issues",          fmt(stats["total_issues"])),
        ("📦", "Repositories",    fmt(stats["total_repos"])),
        ("🏆", "Contributions",   fmt(stats["total_contributions"])),
    ]

    col_w = W // 3
    row_h = (H - 70) // 2

    lines = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="GitHub Stats for {USERNAME}">'
    )
    lines.append(f'<title>GitHub Stats — {USERNAME}</title>')

    # Background
    lines.append(
        f'<rect width="{W}" height="{H}" rx="12" fill="#0d1117" stroke="#21262d" stroke-width="1"/>'
    )

    # Title row
    lines.append(
        f'<text x="20" y="26" font-family="monospace" font-size="11" '
        f'fill="#34eb5c" letter-spacing="2" opacity="0.85">GITHUB STATS — {USERNAME.upper()}</text>'
    )
    lines.append(
        f'<line x1="20" y1="33" x2="{W-20}" y2="33" stroke="#21262d" stroke-width="0.8"/>'
    )

    # Top lang pill
    lines.append(
        f'<rect x="{W - 110}" y="12" width="95" height="18" rx="9" fill="#161b22" stroke="#21262d" stroke-width="1"/>'
    )
    lines.append(
        f'<text x="{W - 63}" y="25" text-anchor="middle" font-family="monospace" '
        f'font-size="10" fill="#34eb5c">✦ {stats["top_lang"]}</text>'
    )

    # Stat cells
    for i, (icon, label, value) in enumerate(items):
        col = i % 3
        row = i // 3
        x = col * col_w + col_w // 2
        y = 44 + row * row_h + row_h // 2

        # Cell background
        cell_x = col * col_w + 8
        cell_y = 40 + row * row_h
        lines.append(
            f'<rect x="{cell_x}" y="{cell_y}" width="{col_w - 16}" height="{row_h - 8}" '
            f'rx="8" fill="#0d1117" stroke="#21262d" stroke-width="0.5"/>'
        )

        # Icon
        lines.append(
            f'<text x="{x}" y="{y - 8}" text-anchor="middle" font-size="18">{icon}</text>'
        )
        # Value
        lines.append(
            f'<text x="{x}" y="{y + 14}" text-anchor="middle" font-family="monospace" '
            f'font-size="20" font-weight="bold" fill="#34eb5c">{value}</text>'
        )
        # Label
        lines.append(
            f'<text x="{x}" y="{y + 28}" text-anchor="middle" font-family="monospace" '
            f'font-size="9" fill="#8b949e">{label.upper()}</text>'
        )

    # Footer
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines.append(
        f'<text x="{W - 20}" y="{H - 8}" text-anchor="end" font-family="monospace" '
        f'font-size="9" fill="#484f58">updated {now} UTC</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


def main():
    print(f"Fetching GitHub stats for: {USERNAME}")
    stats = get_stats(USERNAME, TOKEN)
    print(json.dumps(stats, indent=2))
    svg = build_svg(stats)
    with open(OUTPUT_PATH, "w") as f:
        f.write(svg)
    print(f"SVG written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
