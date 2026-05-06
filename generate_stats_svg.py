import os
import json
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
          contributionCalendar {{ totalContributions }}
        }}
        followers {{ totalCount }}
      }}
    }}
    """
    result = graphql(query, token)
    user = result["data"]["user"]
    repos = user["repositories"]["nodes"]
    total_stars = sum(r["stargazerCount"] for r in repos)

    lang_counts = {}
    for r in repos:
        if r.get("primaryLanguage"):
            lang = r["primaryLanguage"]["name"]
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
    top_lang = max(lang_counts, key=lang_counts.get) if lang_counts else "N/A"

    cc = user["contributionsCollection"]
    return {
        "total_repos":         user["repositories"]["totalCount"],
        "total_stars":         total_stars,
        "total_commits":       cc["totalCommitContributions"],
        "total_prs":           cc["totalPullRequestContributions"],
        "total_issues":        cc["totalIssueContributions"],
        "total_contributions": cc["contributionCalendar"]["totalContributions"],
        "followers":           user["followers"]["totalCount"],
        "top_lang":            top_lang,
    }


def fmt(n):
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def build_svg(stats):
    W, H = 495, 195

    items = [
        ("Stars",         fmt(stats["total_stars"]),         "#e3b341"),
        ("Commits",       fmt(stats["total_commits"]),        "#34eb5c"),
        ("Pull Requests", fmt(stats["total_prs"]),            "#58a6ff"),
        ("Issues",        fmt(stats["total_issues"]),         "#f78166"),
        ("Repos",         fmt(stats["total_repos"]),          "#bc8cff"),
        ("Contributions", fmt(stats["total_contributions"]),  "#34eb5c"),
    ]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="GitHub Stats for {USERNAME}">'
    )
    lines.append(f'<title>GitHub Stats — {USERNAME}</title>')

    # Card background
    lines.append(f'<rect width="{W}" height="{H}" rx="12" fill="#0d1117" stroke="#30363d" stroke-width="1"/>')

    # Header bar
    lines.append(f'<rect width="{W}" height="42" rx="12" fill="#161b22"/>')
    lines.append(f'<rect y="30" width="{W}" height="12" fill="#161b22"/>')
    lines.append(f'<line x1="0" y1="42" x2="{W}" y2="42" stroke="#30363d" stroke-width="0.8"/>')

    # Title
    lines.append(
        f'<text x="18" y="27" font-family="monospace" font-size="12" '
        f'font-weight="bold" fill="#34eb5c" letter-spacing="1">GitHub Stats</text>'
    )

    # Top lang pill
    lines.append(f'<rect x="{W-116}" y="13" width="100" height="18" rx="9" fill="#1f2937" stroke="#30363d" stroke-width="0.8"/>')
    lines.append(
        f'<circle cx="{W-108}" cy="22" r="4" fill="#34eb5c"/>'
    )
    lines.append(
        f'<text x="{W-100}" y="26" font-family="monospace" font-size="10" fill="#c9d1d9">'
        f'{stats["top_lang"]}</text>'
    )

    # 2x3 stat grid
    cols = 3
    cell_w = W // cols
    cell_h = (H - 42) // 2
    pad_top = 42

    for i, (label, value, color) in enumerate(items):
        col = i % cols
        row = i // cols
        cx = col * cell_w + cell_w // 2
        cy = pad_top + row * cell_h + cell_h // 2

        # subtle cell dividers
        if col > 0:
            lx = col * cell_w
            lines.append(
                f'<line x1="{lx}" y1="{pad_top + 12}" x2="{lx}" y2="{H - 12}" '
                f'stroke="#21262d" stroke-width="0.8"/>'
            )
        if row == 1 and col == 0:
            lines.append(
                f'<line x1="12" y1="{pad_top + cell_h}" x2="{W - 12}" y2="{pad_top + cell_h}" '
                f'stroke="#21262d" stroke-width="0.8"/>'
            )

        # Value — large and colored
        lines.append(
            f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-family="monospace" '
            f'font-size="22" font-weight="bold" fill="{color}">{value}</text>'
        )
        # Label — small muted
        lines.append(
            f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" font-family="monospace" '
            f'font-size="9" fill="#6e7681" letter-spacing="0.5">{label.upper()}</text>'
        )

    # Footer date
    lines.append(
        f'<text x="{W - 14}" y="{H - 7}" text-anchor="end" font-family="monospace" '
        f'font-size="8" fill="#484f58">updated {now}</text>'
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