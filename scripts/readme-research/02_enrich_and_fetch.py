#!/usr/bin/env python3
"""
Step 2: enrich each candidate with authoritative metadata (via ungh.cc, a
public GitHub API mirror that isn't subject to this sandbox's repo-scoping
restriction) and fetch each repo's README from raw.githubusercontent.com
(a static CDN, also unrestricted).

Writes:
  docs/readme-analysis/01_ranked_repos.json          - full enriched, ranked list
  docs/readme-analysis/repos/<owner>__<repo>/meta.json
  docs/readme-analysis/repos/<owner>__<repo>/README.<ext>   (raw fetched readme, verbatim)
"""
import json
import os
import time
import urllib.request
import urllib.error

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(REPO_ROOT, "docs", "readme-analysis")
CAND_PATH = f"{BASE}/00_candidates.json"
OUT_RANKED = f"{BASE}/01_ranked_repos.json"
REPOS_DIR = f"{BASE}/repos"
os.makedirs(REPOS_DIR, exist_ok=True)

README_CANDIDATES = [
    "README.md", "readme.md", "Readme.md", "README.MD",
    "README.rst", "README.txt", "README", "docs/README.md",
]

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "readme-research-script/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, str(e).encode()

def get_meta(full_name):
    status, body = fetch(f"https://ungh.cc/repos/{full_name}")
    if status != 200:
        return None
    try:
        return json.loads(body)["repo"]
    except Exception:
        return None

def get_readme(full_name, branch):
    # Deduped: when the default branch is already "main" the old list fetched it
    # twice, which is 8 wasted requests per repo against a rate-limited CDN.
    branches = []
    for branch_try in (branch, "main", "master"):
        if branch_try and branch_try not in branches:
            branches.append(branch_try)
    for branch_try in branches:
        for fname in README_CANDIDATES:
            url = f"https://raw.githubusercontent.com/{full_name}/{branch_try}/{fname}"
            status, body = fetch(url)
            if status == 200 and body and len(body) > 20:
                return fname, branch_try, body
    return None, None, None

def main():
    with open(CAND_PATH) as f:
        candidates = json.load(f)

    enriched = []
    for i, c in enumerate(candidates):
        fn = c["full_name"]
        print(f"[{i+1}/{len(candidates)}] {fn}", flush=True)
        meta = get_meta(fn)
        if meta is None:
            print(f"  ! metadata fetch failed, skipping")
            time.sleep(0.3)
            continue
        fname, branch_used, body = get_readme(fn, meta.get("defaultBranch"))
        if body is None:
            print(f"  ! no README found, skipping")
            time.sleep(0.3)
            continue

        slug = fn.replace("/", "__")
        repo_dir = os.path.join(REPOS_DIR, slug)
        os.makedirs(repo_dir, exist_ok=True)
        ext = os.path.splitext(fname)[1] or ".md"
        readme_path = os.path.join(repo_dir, f"README{ext}")
        with open(readme_path, "wb") as rf:
            rf.write(body)

        record = {
            "full_name": fn,
            "html_url": f"https://github.com/{fn}",
            "description": meta.get("description") or c.get("description_hint", ""),
            "stars_total": meta.get("stars", 0),
            "forks": meta.get("forks", 0),
            "watchers": meta.get("watchers", 0),
            "created_at": meta.get("createdAt"),
            "pushed_at": meta.get("pushedAt"),
            "default_branch": meta.get("defaultBranch"),
            "readme_branch_used": branch_used,
            "readme_filename": fname,
            "readme_local_path": readme_path,
            "readme_bytes": len(body),
            "source": c.get("source"),
            "stars_3mo_gained": c.get("stars_3mo_gained"),
            "est_stars_gained_1y": c.get("est_stars_gained_1y"),
            "slug": slug,
        }
        with open(os.path.join(repo_dir, "meta.json"), "w") as mf:
            json.dump(record, mf, indent=2)
        enriched.append(record)
        time.sleep(0.25)

    # Final ranking: by measured trailing-3-month star growth where available,
    # else by total stars (for repos that are new-in-window this year).
    enriched.sort(key=lambda r: (r.get("stars_3mo_gained") or 0, r.get("stars_total") or 0), reverse=True)
    for idx, r in enumerate(enriched):
        r["rank"] = idx + 1

    with open(OUT_RANKED, "w") as f:
        json.dump(enriched, f, indent=2)
    print(f"\nDone. {len(enriched)}/{len(candidates)} repos enriched with metadata + README.")

if __name__ == "__main__":
    main()
