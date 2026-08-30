#!/usr/bin/env python3
"""Generate the compact GitHub profile snapshot from the account's repositories."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://api.github.com"
TOKEN = os.environ["PROFILE_STATS_TOKEN"]
OUTPUT = Path(__file__).parent.parent / "assets" / "snapshot-live.svg"


def api_get(path: str, params: dict[str, str | int]) -> object:
    url = f"{API_URL}{path}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def get_owned_repositories() -> list[dict[str, object]]:
    repositories: list[dict[str, object]] = []
    page = 1

    while True:
        result = api_get(
            "/user/repos",
            {
                "affiliation": "owner",
                "per_page": 100,
                "page": page,
                "sort": "updated",
            },
        )
        if not isinstance(result, list):
            raise RuntimeError("GitHub returned an invalid repository response.")

        repositories.extend(result)
        if len(result) < 100:
            return repositories
        page += 1


def count_commits(repository: str, author: str, since: str) -> int:
    total = 0
    page = 1

    while True:
        result = api_get(
            f"/repos/{repository}/commits",
            {
                "author": author,
                "since": since,
                "per_page": 100,
                "page": page,
            },
        )
        if not isinstance(result, list):
            raise RuntimeError(f"GitHub returned an invalid commit response for {repository}.")

        total += len(result)
        if len(result) < 100:
            return total
        page += 1


def render_svg(years_on_github: int, commits_last_year: int, project_count: int) -> str:
    return f"""<svg width="1280" height="150" viewBox="0 0 1280 150" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title description">
  <title id="title">Profile snapshot</title>
  <desc id="description">{years_on_github}+ years on GitHub, {commits_last_year} commits in the last 365 days, and {project_count}+ projects built.</desc>
  <defs>
    <linearGradient id="background" x1="0" y1="0" x2="1280" y2="150" gradientUnits="userSpaceOnUse">
      <stop stop-color="#111827"/>
      <stop offset=".5" stop-color="#1E1B4B"/>
      <stop offset="1" stop-color="#083344"/>
    </linearGradient>
    <linearGradient id="divider" x1="125" y1="75" x2="1155" y2="75" gradientUnits="userSpaceOnUse">
      <stop stop-color="#22D3EE" stop-opacity="0"/>
      <stop offset=".5" stop-color="#A78BFA" stop-opacity=".7"/>
      <stop offset="1" stop-color="#22D3EE" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="1280" height="150" rx="16" fill="url(#background)"/>
  <path d="M426 31V119M854 31V119" stroke="url(#divider)" stroke-width="1.5"/>
  <g font-family="Arial, Helvetica, sans-serif" text-anchor="middle">
    <text x="214" y="62" fill="#A5F3FC" font-size="13" font-weight="700" letter-spacing="2">ON GITHUB</text>
    <text x="214" y="105" fill="white" font-family="monospace" font-size="36" font-weight="700">{years_on_github:02d}+ YEARS</text>
    <text x="640" y="62" fill="#DDD6FE" font-size="13" font-weight="700" letter-spacing="2">LAST 365 DAYS</text>
    <text x="640" y="105" fill="white" font-family="monospace" font-size="36" font-weight="700">{commits_last_year} COMMITS</text>
    <text x="1066" y="62" fill="#A5F3FC" font-size="13" font-weight="700" letter-spacing="2">IN THE LAB</text>
    <text x="1066" y="105" fill="white" font-family="monospace" font-size="36" font-weight="700">{project_count:02d}+ PROJECTS</text>
  </g>
</svg>
"""


def main() -> None:
    user = api_get("/user", {})
    if not isinstance(user, dict):
        raise RuntimeError("GitHub returned an invalid user response.")

    login = user.get("login")
    created_at = user.get("created_at")
    if not isinstance(login, str) or not isinstance(created_at, str):
        raise RuntimeError("GitHub user response is missing identity data.")

    now = datetime.now(UTC)
    joined_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    years_on_github = now.year - joined_at.year - (
        (now.month, now.day) < (joined_at.month, joined_at.day)
    )
    since = (now - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")

    repositories = [
        repository
        for repository in get_owned_repositories()
        if not repository.get("fork") and not repository.get("archived")
    ]
    commit_total = sum(
        count_commits(str(repository["full_name"]), login, since)
        for repository in repositories
    )

    OUTPUT.write_text(
        render_svg(years_on_github, commit_total, len(repositories)),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
