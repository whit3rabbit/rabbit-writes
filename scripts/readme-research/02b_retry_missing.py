#!/usr/bin/env python3
"""Retry the handful of candidates that failed transiently in step 2, and merge them in."""
import json, os, time, urllib.request, urllib.error

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(REPO_ROOT, "docs", "readme-analysis")
CAND_PATH = f"{BASE}/00_candidates.json"
OUT_RANKED = f"{BASE}/01_ranked_repos.json"
REPOS_DIR = f"{BASE}/repos"

README_CANDIDATES = ["README.md", "readme.md", "Readme.md", "README.MD", "README.rst", "README.txt", "README", "docs/README.md"]

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
    for attempt in range(4):
        status, body = fetch(f"https://ungh.cc/repos/{full_name}")
        if status == 200:
            return json.loads(body)["repo"]
        time.sleep(2)
    return None

def get_readme(full_name, branch):
    # Deduped for the same reason as step 02: a default branch of "main" made
    # the old list fetch the same 8 URLs twice.
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

with open(CAND_PATH) as f:
    candidates = {c["full_name"]: c for c in json.load(f)}
with open(OUT_RANKED) as f:
    ranked = json.load(f)
have = set(r["full_name"] for r in ranked)
missing = [fn for fn in candidates if fn not in have]
print("retrying:", missing)

for fn in missing:
    c = candidates[fn]
    meta = get_meta(fn)
    if not meta:
        print(f"  still failing: {fn}")
        continue
    fname, branch_used, body = get_readme(fn, meta.get("defaultBranch"))
    if not body:
        print(f"  no readme: {fn}")
        continue
    slug = fn.replace("/", "__")
    repo_dir = os.path.join(REPOS_DIR, slug)
    os.makedirs(repo_dir, exist_ok=True)
    ext = os.path.splitext(fname)[1] or ".md"
    readme_path = os.path.join(repo_dir, f"README{ext}")
    with open(readme_path, "wb") as rf:
        rf.write(body)
    record = {
        "full_name": fn, "html_url": f"https://github.com/{fn}",
        "description": meta.get("description") or c.get("description_hint", ""),
        "stars_total": meta.get("stars", 0), "forks": meta.get("forks", 0),
        "watchers": meta.get("watchers", 0), "created_at": meta.get("createdAt"),
        "pushed_at": meta.get("pushedAt"), "default_branch": meta.get("defaultBranch"),
        "readme_branch_used": branch_used, "readme_filename": fname,
        "readme_local_path": readme_path, "readme_bytes": len(body),
        "source": c.get("source"), "stars_3mo_gained": c.get("stars_3mo_gained"),
        "est_stars_gained_1y": c.get("est_stars_gained_1y"), "slug": slug,
    }
    with open(os.path.join(repo_dir, "meta.json"), "w") as mf:
        json.dump(record, mf, indent=2)
    ranked.append(record)
    print(f"  recovered: {fn}")

ranked.sort(key=lambda r: (r.get("stars_3mo_gained") or 0, r.get("stars_total") or 0), reverse=True)
for idx, r in enumerate(ranked):
    r["rank"] = idx + 1
with open(OUT_RANKED, "w") as f:
    json.dump(ranked, f, indent=2)
print(f"Final count: {len(ranked)}")
