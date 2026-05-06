import os
import json
import math
import urllib.request
from datetime import datetime, timezone

USERNAME = os.environ.get("GITHUB_USERNAME", "KodEx-SA")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT_PATH = os.environ.get("STATS_OUTPUT_PATH", "github-stats.svg")


def graphql(query, token):
    data = json.dumps({"query": query}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=data)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "github-stats-svg-generator")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get_stats(username, token):
    year = datetime.now(timezone.utc).year
    query = f"""
    {{
      user(login: "{username}") {{
        name
        repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {{
          totalCount
          nodes {{
            stargazerCount
            primaryLanguage {{ name }}
          }}
        }}
        contributionsCollection {{
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          totalRepositoryContributions
          contributionCalendar {{ totalContributions }}
        }}
        repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {{
          totalCount
        }}
      }}
    }}
    """
    result = graphql(query, token)
    user = result["data"]["user"]
    repos = user["repositories"]["nodes"]
    total_stars = sum(r["stargazerCount"] for r in repos)
    cc = user["contributionsCollection"]
    name = user.get("name") or username
    return {
        "name":            name,
        "year":            year,
        "total_stars":     total_stars,
        "total_commits":   cc["totalCommitContributions"],
        "total_prs":       cc["totalPullRequestContributions"],
        "total_issues":    cc["totalIssueContributions"],
        "contrib_to":      user["repositoriesContributedTo"]["totalCount"],
        "total_repos":     user["repositories"]["totalCount"],
    }


def compute_rank(stats):
    """
    Compute rank letter (S, A+, A, A-, B+, B, C, ?) and percentile
    based on a weighted score similar to github-readme-stats.
    """
    THRESHOLDS = {
        "S":  1,
        "A+": 12.5,
        "A":  25,
        "A-": 37.5,
        "B+": 50,
        "B":  62.5,
        "C":  75,
    }

    # Weights (same as github-readme-stats open source formula)
    WEIGHTS = {
        "commits":  6.5,
        "prs":      3,
        "issues":   1,
        "stars":    0.5,
        "contrib":  1.65,
    }

    # Median reference values (GitHub community medians)
    MEDIANS = {
        "commits":  250,
        "prs":      50,
        "issues":   25,
        "stars":    50,
        "contrib":  10,
    }

    def exp_cdf(x, lam):
        return 1 - math.exp(-lam * x)

    def log_normal_cdf(x, sigma, mu):
        if x <= 0:
            return 0
        return 0.5 * (1 + math.erf((math.log(x) - mu) / (math.sqrt(2) * sigma)))

    score = (
        WEIGHTS["commits"]  * exp_cdf(stats["total_commits"],   1 / MEDIANS["commits"]) +
        WEIGHTS["prs"]      * exp_cdf(stats["total_prs"],       1 / MEDIANS["prs"]) +
        WEIGHTS["issues"]   * exp_cdf(stats["total_issues"],    1 / MEDIANS["issues"]) +
        WEIGHTS["stars"]    * log_normal_cdf(stats["total_stars"], 1, math.log(MEDIANS["stars"])) +
        WEIGHTS["contrib"]  * log_normal_cdf(stats["contrib_to"], 1, math.log(MEDIANS["contrib"]))
    )

    total_weight = sum(WEIGHTS.values())
    percentile = 100 - (score / total_weight) * 100

    rank = "?"
    for letter, threshold in THRESHOLDS.items():
        if percentile <= threshold:
            rank = letter
            break
    if rank == "?":
        rank = "C"

    return rank, percentile


def fmt(n):
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def build_svg(stats):
    rank, percentile = compute_rank(stats)
    year = stats["year"]
    name = stats["name"]

    # Rank circle animation: dasharray=250, offset goes from 251.3 (empty) to filled
    circumference = 2 * math.pi * 40  # ~251.327
    # filled portion = (100 - percentile) / 100
    filled = max(0.0, min(1.0, (100 - percentile) / 100))
    dash_offset = circumference * (1 - filled)

    rows = [
        # (icon_path, label, value, data_testid, delay_ms)
        (
            "M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25zm0 2.445L6.615 5.5a.75.75 0 01-.564.41l-3.097.45 2.24 2.184a.75.75 0 01.216.664l-.528 3.084 2.769-1.456a.75.75 0 01.698 0l2.77 1.456-.53-3.084a.75.75 0 01.216-.664l2.24-2.183-3.096-.45a.75.75 0 01-.564-.41L8 2.694v.001z",
            "Total Stars Earned:", fmt(stats["total_stars"]), "stars", 450
        ),
        (
            "M1.643 3.143L.427 1.927A.25.25 0 000 2.104V5.75c0 .138.112.25.25.25h3.646a.25.25 0 00.177-.427L2.715 4.215a6.5 6.5 0 11-1.18 4.458.75.75 0 10-1.493.154 8.001 8.001 0 101.6-5.684zM7.75 4a.75.75 0 01.75.75v2.992l2.028.812a.75.75 0 01-.557 1.392l-2.5-1A.75.75 0 017 8.25v-3.5A.75.75 0 017.75 4z",
            f"Total Commits ({year}):", fmt(stats["total_commits"]), "commits", 600
        ),
        (
            "M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z",
            "Total PRs:", fmt(stats["total_prs"]), "prs", 750
        ),
        (
            "M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm9 3a1 1 0 11-2 0 1 1 0 012 0zm-.25-6.25a.75.75 0 00-1.5 0v3.5a.75.75 0 001.5 0v-3.5z",
            "Total Issues:", fmt(stats["total_issues"]), "issues", 900
        ),
        (
            "M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z",
            "Contributed to (last year):", fmt(stats["contrib_to"]), "contribs", 1050
        ),
    ]

    out = []
    out.append(f'''<svg
  width="467"
  height="195"
  viewBox="0 0 467 195"
  fill="none"
  xmlns="http://www.w3.org/2000/svg"
  role="img"
  aria-labelledby="descId"
>
  <title id="titleId">{name}'s GitHub Stats, Rank: {rank}</title>
  <desc id="descId">Total Stars Earned: {stats["total_stars"]}, Total Commits in {year}: {stats["total_commits"]}, Total PRs: {stats["total_prs"]}, Total Issues: {stats["total_issues"]}, Contributed to (last year): {stats["contrib_to"]}</desc>
  <style>
    .header {{
      font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif;
      fill: #34eb5c;
      animation: fadeInAnimation 0.8s ease-in-out forwards;
    }}
    @supports(-moz-appearance: auto) {{
      .header {{ font-size: 15.5px; }}
    }}
    .stat {{
      font: 600 14px 'Segoe UI', Ubuntu, "Helvetica Neue", Sans-Serif;
      fill: #13e065;
    }}
    @supports(-moz-appearance: auto) {{
      .stat {{ font-size: 12px; }}
    }}
    .stagger {{
      opacity: 0;
      animation: fadeInAnimation 0.3s ease-in-out forwards;
    }}
    .rank-text {{
      font: 800 24px 'Segoe UI', Ubuntu, Sans-Serif;
      fill: #13e065;
      animation: scaleInAnimation 0.3s ease-in-out forwards;
    }}
    .bold {{ font-weight: 700 }}
    .icon {{
      fill: #13e065;
      display: block;
    }}
    .rank-circle-rim {{
      stroke: #34eb5c;
      fill: none;
      stroke-width: 6;
      opacity: 0.2;
    }}
    .rank-circle {{
      stroke: #34eb5c;
      stroke-dasharray: 250;
      fill: none;
      stroke-width: 6;
      stroke-linecap: round;
      opacity: 0.8;
      transform-origin: -10px 8px;
      transform: rotate(-90deg);
      animation: rankAnimation 1s forwards ease-in-out;
    }}
    @keyframes rankAnimation {{
      from {{ stroke-dashoffset: {circumference:.5f}; }}
      to   {{ stroke-dashoffset: {dash_offset:.5f}; }}
    }}
    @keyframes scaleInAnimation {{
      from {{ transform: translate(-5px, 5px) scale(0); }}
      to   {{ transform: translate(-5px, 5px) scale(1); }}
    }}
    @keyframes fadeInAnimation {{
      from {{ opacity: 0; }}
      to   {{ opacity: 1; }}
    }}
  </style>

  <rect
    x="0.5" y="0.5" rx="4.5"
    height="99%" stroke="#e4e2e2"
    width="466" fill="#0d1117" stroke-opacity="1"
  />

  <g data-testid="card-title" transform="translate(25, 35)">
    <text x="0" y="0" class="header" data-testid="header">{name}'s GitHub Stats</text>
  </g>

  <g data-testid="main-card-body" transform="translate(0, 55)">

    <g data-testid="rank-circle" transform="translate(390.5, 47.5)">
      <circle class="rank-circle-rim" cx="-10" cy="8" r="40"/>
      <circle class="rank-circle" cx="-10" cy="8" r="40"/>
      <g class="rank-text">
        <text x="-5" y="3"
          alignment-baseline="central"
          dominant-baseline="central"
          text-anchor="middle"
          data-testid="level-rank-icon">{rank}</text>
      </g>
    </g>

    <svg x="0" y="0">''')

    for i, (icon_path, label, value, testid, delay) in enumerate(rows):
        out.append(f'''
      <g transform="translate(0, {i * 25})">
        <g class="stagger" style="animation-delay: {delay}ms" transform="translate(25, 0)">
          <svg data-testid="icon" class="icon" viewBox="0 0 16 16" version="1.1" width="16" height="16">
            <path fill-rule="evenodd" d="{icon_path}"/>
          </svg>
          <text class="stat bold" x="25" y="12.5">{label}</text>
          <text class="stat bold" x="219.01" y="12.5" data-testid="{testid}">{value}</text>
        </g>
      </g>''')

    out.append('''
    </svg>
  </g>
</svg>''')

    return "\n".join(out)


def main():
    print(f"Fetching GitHub stats for: {USERNAME}")
    stats = get_stats(USERNAME, TOKEN)
    rank, pct = compute_rank(stats)
    print(f"  Rank: {rank} (percentile: {pct:.1f})")
    print(json.dumps(stats, indent=2))
    svg = build_svg(stats)
    with open(OUTPUT_PATH, "w") as f:
        f.write(svg)
    print(f"SVG written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()