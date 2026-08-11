#!/usr/bin/env python3
"""
Step 1: build the candidate population of currently-popular repos and rank
them by an estimated "stars gained in the past 12 months" metric.

GitHub's REST/Search API has no native "stars gained in window X" sort, so we
combine two public signals:

  List A - OSS Insight's public "Fastest Growing Repositories" collection for
           the `past_3_months` window (the finest-grained trailing window
           their public API exposes; no `past_1_year` option exists). We
           annualize by treating the 3-month star count as one quarter of a
           rough year-estimate (x4). This is a coarse extrapolation, not a
           measurement, and is labeled as such in the output.

  List B - GitHub Search API: repos created in the last 365 days, sorted by
           total stars. For a repo that didn't exist a year ago, current
           total stars IS (almost exactly) the stars gained in the past
           year, so this is an exact figure rather than an estimate.

We merge A + B, dedupe by full_name, fetch authoritative metadata for each
from the REST API, and rank by the best available "stars gained in past
year" figure (exact for List B, estimated for List A-only repos).

Note: List B requires unrestricted access to api.github.com's Search API.
In a network-sandboxed environment (e.g. one scoped to a single repo) that
call will fail and List B simply comes back empty -- the pipeline still
works fine on List A alone, which is what produced the shipped dataset in
docs/readme-analysis/.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

TOKEN = os.environ.get("GITHUB_TOKEN")
# The one host the token is for. gh_request is called against api.ossinsight.io
# as well, and a bearer header attached by default sends the user's GitHub
# credential to a third party that never asked for it and cannot use it.
# Compared exactly, not by suffix: "api.github.com.example.net" is somebody
# else's domain.
TOKEN_HOSTS = {"api.github.com"}
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(REPO_ROOT, "docs", "readme-analysis")
os.makedirs(OUT_DIR, exist_ok=True)

def sends_token(url):
    return urllib.parse.urlsplit(url).hostname in TOKEN_HOSTS


def gh_request(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url)
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "readme-research-script")
    if TOKEN and sends_token(url):
        req.add_header("Authorization", f"Bearer {TOKEN}")
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            body = e.read()
            if e.code in (403, 429):
                # rate limited - back off
                wait = int(e.headers.get("Retry-After", 5)) if e.headers else 5
                print(f"  rate limited on {url}, sleeping {wait}s (attempt {attempt+1})", file=sys.stderr)
                time.sleep(wait + 1)
                continue
            return e.code, body
        except Exception as e:
            print(f"  error {e} on {url}, retrying", file=sys.stderr)
            time.sleep(2)
    return None, b""

def fetch_ossinsight_growth():
    url = "https://api.ossinsight.io/v1/trends/repos/?period=past_3_months"
    status, body = gh_request(url)
    if status != 200:
        print(f"OSS Insight fetch failed: {status}", file=sys.stderr)
        return []
    d = json.loads(body)
    rows = d["data"]["rows"]
    out = []
    for r in rows:
        try:
            stars_3mo = int(r["stars"])
        except (ValueError, TypeError):
            stars_3mo = 0
        out.append({
            "full_name": r["repo_name"],
            "source": "ossinsight_past_3_months",
            "stars_3mo_gained": stars_3mo,
            "est_stars_gained_1y": stars_3mo * 4,  # coarse annualization, labeled as estimate
            "description_hint": r.get("description", ""),
        })
    return out

def fetch_new_repos_by_stars():
    one_year_ago = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    out = []
    for page in (1, 2):  # 2 pages x 100 = 200 candidates
        url = (
            "https://api.github.com/search/repositories"
            f"?q=created:>{one_year_ago}&sort=stars&order=desc&per_page=100&page={page}"
        )
        status, body = gh_request(url)
        if status != 200:
            print(f"Search page {page} failed: {status} {body[:200]}", file=sys.stderr)
            break
        d = json.loads(body)
        items = d.get("items", [])
        if not items:
            break
        for it in items:
            out.append({
                "full_name": it["full_name"],
                "source": "github_search_created_past_year",
                "stars_total_at_fetch": it["stargazers_count"],
                # for a repo created within the window, total stars approx == stars gained in window
                "est_stars_gained_1y": it["stargazers_count"],
                "description_hint": it.get("description") or "",
            })
        time.sleep(1)  # respect search rate limit (30/min)
    return out

def main():
    print("Fetching OSS Insight past-3-months growth collection...")
    list_a = fetch_ossinsight_growth()
    print(f"  -> {len(list_a)} repos")

    print("Fetching GitHub Search: repos created in the past year, sorted by stars...")
    list_b = fetch_new_repos_by_stars()
    print(f"  -> {len(list_b)} repos")

    merged = {}
    for r in list_a + list_b:
        fn = r["full_name"]
        if fn not in merged:
            merged[fn] = r
        else:
            # prefer the exact (List B) estimate over the extrapolated one, keep both signals
            existing = merged[fn]
            new_est = r.get("est_stars_gained_1y", 0)
            if r["source"] == "github_search_created_past_year":
                existing["est_stars_gained_1y"] = new_est
                existing["stars_total_at_fetch"] = r.get("stars_total_at_fetch")
                existing["source"] = existing["source"] + "+github_search_created_past_year"
            else:
                existing["source"] = existing["source"] + "+ossinsight_past_3_months"
                existing["stars_3mo_gained"] = r.get("stars_3mo_gained")

    candidates = sorted(merged.values(), key=lambda r: r.get("est_stars_gained_1y", 0), reverse=True)
    print(f"Merged unique candidates: {len(candidates)}")

    with open(os.path.join(OUT_DIR, "00_candidates.json"), "w") as f:
        json.dump(candidates, f, indent=2)
    print(f"Wrote {len(candidates)} candidates to 00_candidates.json")

if __name__ == "__main__":
    main()
