import json
import os
import urllib.request
from datetime import datetime, timezone

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
USERNAME = os.environ.get("GITHUB_ACTOR", "SaladDann")
OUTPUT_PATH = os.path.join("data", "metrics.json")

USER_OVERVIEW_QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    starredRepositories(first: 1) {
      totalCount
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
    repositories(ownerAffiliations: OWNER, isFork: false) {
      totalCount
    }
  }
}
"""

PAGINATED_REPOS_QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    repositories(
      first: 100
      after: $cursor
      ownerAffiliations: OWNER
      isFork: false
      orderBy: {field: UPDATED_AT, direction: DESC}
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node {
              name
            }
          }
        }
      }
    }
  }
}
"""


def execute_graphql(token: str, query: str, variables: dict) -> dict:
    url = "https://api.github.com/graphql"
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "SaladDann-Profile-Telemetry",
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        if "errors" in result:
            raise RuntimeError(f"GraphQL Error: {result['errors']}")
        return result["data"]["user"]


def fetch_all_repositories(token: str, username: str) -> list[dict]:
    all_repos = []
    cursor = None

    while True:
        data = execute_graphql(
            token,
            PAGINATED_REPOS_QUERY,
            {"login": username, "cursor": cursor},
        )
        repo_conn = data["repositories"]
        all_repos.extend(repo_conn["nodes"])

        page_info = repo_conn["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

    return all_repos


def fetch_github_graphql(token: str, username: str) -> dict:
    user_data = execute_graphql(token, USER_OVERVIEW_QUERY, {"login": username})
    user_data["all_repositories"] = fetch_all_repositories(token, username)
    return user_data


def format_short_date(iso_date: str) -> str:
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    return dt.strftime("%b %d").replace(" 0", " ")


def calculate_streaks(days: list[dict]) -> dict:
    longest = 0
    longest_start = ""
    longest_end = ""

    temp_streak = 0
    temp_start = ""

    for day in days:
        count = day["contributionCount"]
        date_str = day["date"]
        if count > 0:
            if temp_streak == 0:
                temp_start = date_str
            temp_streak += 1
            if temp_streak >= longest:
                longest = temp_streak
                longest_start = temp_start
                longest_end = date_str
        else:
            temp_streak = 0

    current = 0
    current_date_label = ""
    if days:
        last_idx = len(days) - 1
        if days[last_idx]["contributionCount"] == 0 and last_idx > 0:
            last_idx -= 1

        if days[last_idx]["contributionCount"] > 0:
            current_date_label = format_short_date(days[last_idx]["date"])
            for i in range(last_idx, -1, -1):
                if days[i]["contributionCount"] > 0:
                    current += 1
                else:
                    break
        else:
            current_date_label = format_short_date(days[-1]["date"])

    longest_range = (
        f"{format_short_date(longest_start)} - {format_short_date(longest_end)}"
        if longest > 0
        else "Sin registros"
    )

    return {
        "current_streak": current,
        "current_date": current_date_label,
        "longest_streak": longest,
        "longest_range": longest_range,
    }


def calculate_top_languages(repos: list[dict], exclude: set[str] | None = None) -> list[dict]:
    if exclude is None:
        exclude = {"HTML", "CSS", "Shell", "Makefile"}

    lang_bytes: dict[str, int] = {}
    for repo in repos:
        for edge in repo.get("languages", {}).get("edges", []):
            name = edge["node"]["name"]
            if name in exclude:
                continue
            lang_bytes[name] = lang_bytes.get(name, 0) + edge["size"]

    total_bytes = sum(lang_bytes.values()) or 1
    sorted_langs = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)

    result = []
    others_bytes = 0

    for idx, (name, size) in enumerate(sorted_langs):
        pct = round((size / total_bytes) * 100, 1)
        if idx < 7 and pct >= 1.5:
            result.append({"name": name, "bytes": size, "percent": pct})
        else:
            others_bytes += size

    if others_bytes > 0:
        others_pct = round((others_bytes / total_bytes) * 100, 1)
        if others_pct > 0:
            result.append({"name": "Otros", "bytes": others_bytes, "percent": others_pct})

    return result


def build_metrics_snapshot(user_data: dict, generated_at: str | None = None) -> dict:
    contrib = user_data["contributionsCollection"]
    calendar = contrib["contributionCalendar"]
    weeks = calendar["weeks"]

    all_days = [day for week in weeks for day in week["contributionDays"]]
    streaks = calculate_streaks(all_days)

    all_repos = user_data["all_repositories"]
    top_langs = calculate_top_languages(all_repos)

    created_dt = datetime.strptime(user_data["createdAt"][:10], "%Y-%m-%d")
    joined_label = created_dt.strftime("%b %d, %Y")

    total_commits = contrib["totalCommitContributions"] + contrib["restrictedContributionsCount"]
    stars_given = user_data["starredRepositories"]["totalCount"]
    stars_received = sum(repo.get("stargazerCount", 0) for repo in all_repos)

    return {
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "username": USERNAME,
        "stats": {
            "commits_year": total_commits,
            "repos": len(all_repos),
            "prs": contrib["totalPullRequestContributions"],
            "issues": contrib["totalIssueContributions"],
            "stars_given": stars_given,
            "stars_received": stars_received,
        },
        "streak": {
            "total_contributions": calendar["totalContributions"],
            "date_range": f"{joined_label} - Present",
            **streaks,
        },
        "languages": top_langs,
        "recent_25_days": all_days[-25:],
        "calendar_weeks": weeks[-52:],
    }


def _without_timestamp(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k != "generated_at"}


def load_existing_snapshot(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def main():
    if not GITHUB_TOKEN:
        raise EnvironmentError("Falta la variable de entorno GITHUB_TOKEN.")

    raw_user = fetch_github_graphql(GITHUB_TOKEN, USERNAME)
    now_iso = datetime.now(timezone.utc).isoformat()
    snapshot = build_metrics_snapshot(raw_user, generated_at=now_iso)

    existing = load_existing_snapshot(OUTPUT_PATH)
    if existing is not None and _without_timestamp(existing) == _without_timestamp(snapshot):
        print(f"[SKIP] Sin cambios reales en métricas; se conserva {OUTPUT_PATH}")
        return

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"[OK] Métricas actualizadas en {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
