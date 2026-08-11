#!/usr/bin/env python3
"""Step 4: aggregate corpus-wide findings across all analyzed READMEs."""
import glob
import json
import os
import re
import statistics
from collections import Counter, defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(REPO_ROOT, "docs", "readme-analysis")

with open(f"{BASE}/02_all_stats.json") as f:
    all_data = json.load(f)

N = len(all_data)
recs = list(all_data.values())

def pct(cond_fn):
    return round(100 * sum(1 for r in recs if cond_fn(r)) / N, 1)

def mean_of(fn):
    vals = [fn(r) for r in recs]
    vals = [v for v in vals if v is not None]
    return round(statistics.mean(vals), 2) if vals else 0

def median_of(fn):
    vals = [fn(r) for r in recs]
    vals = [v for v in vals if v is not None]
    return round(statistics.median(vals), 2) if vals else 0

summary = {"n_repos": N}

# --- presence rates
summary["pct_has_badges_in_header"] = pct(lambda r: r["stats"]["badges_in_header_block"] > 0)
summary["pct_has_any_badge"] = pct(lambda r: r["stats"]["badge_count"] > 0)
summary["pct_uses_centering"] = pct(lambda r: r["stats"]["uses_centering"])
summary["pct_has_toc"] = pct(lambda r: r["stats"]["has_toc_section"])
summary["pct_has_installation_section"] = pct(lambda r: r["stats"]["has_installation_section"])
summary["pct_has_usage_or_examples"] = pct(lambda r: r["stats"]["has_usage_or_examples_section"])
summary["pct_has_contributing_section"] = pct(lambda r: r["stats"]["has_contributing_section"])
summary["pct_has_license_section_or_badge"] = pct(lambda r: r["stats"]["has_license_section_or_badge"])
summary["pct_has_demo_media"] = pct(lambda r: r["stats"]["has_demo_section_or_media"])
summary["pct_has_screenshot_or_logo_image"] = pct(lambda r: r["stats"]["screenshot_or_logo_image_count"] > 0)
summary["pct_has_gif"] = pct(lambda r: r["stats"]["gif_count"] > 0)
summary["pct_has_video_embed"] = pct(lambda r: r["stats"]["has_video_embed"])
summary["pct_has_code_blocks"] = pct(lambda r: r["stats"]["code_block_count"] > 0)
summary["pct_has_table"] = pct(lambda r: r["stats"]["table_present"])
summary["pct_uses_reference_style_links"] = pct(lambda r: r["stats"]["uses_reference_style_links"])
summary["pct_has_h1"] = pct(lambda r: r["stats"]["has_h1"])
summary["pct_has_bare_urls"] = pct(lambda r: r["stats"]["bare_url_count"] > 0)

# --- averages
summary["avg_readme_word_count"] = mean_of(lambda r: r["stats"]["total_prose_words"])
summary["median_readme_word_count"] = median_of(lambda r: r["stats"]["total_prose_words"])
summary["avg_heading_count"] = mean_of(lambda r: r["stats"]["heading_count"])
summary["median_heading_count"] = median_of(lambda r: r["stats"]["heading_count"])
summary["avg_sentence_words"] = mean_of(lambda r: r["stats"]["avg_sentence_words"] if r["stats"]["sentence_count"] >= 5 else None)
summary["median_sentence_words_repo_level"] = median_of(lambda r: r["stats"]["median_sentence_words"] if r["stats"]["sentence_count"] >= 5 else None)
summary["avg_paragraph_words"] = mean_of(lambda r: r["stats"]["avg_paragraph_words"] if r["stats"]["paragraph_count"] >= 3 else None)
summary["avg_short_sentence_pct"] = mean_of(lambda r: r["stats"]["short_sentence_pct"] if r["stats"]["sentence_count"] >= 5 else None)
summary["avg_medium_sentence_pct"] = mean_of(lambda r: r["stats"]["medium_sentence_pct"] if r["stats"]["sentence_count"] >= 5 else None)
summary["avg_long_sentence_pct"] = mean_of(lambda r: r["stats"]["long_sentence_pct"] if r["stats"]["sentence_count"] >= 5 else None)
summary["avg_badge_count"] = mean_of(lambda r: r["stats"]["badge_count"])
summary["median_badge_count"] = median_of(lambda r: r["stats"]["badge_count"])
summary["avg_image_count"] = mean_of(lambda r: r["stats"]["image_count_total"])
summary["avg_code_block_count"] = mean_of(lambda r: r["stats"]["code_block_count"])
summary["avg_preamble_word_count"] = mean_of(lambda r: r["stats"]["preamble_word_count"])
summary["avg_total_markdown_links"] = mean_of(lambda r: r["stats"]["total_markdown_links"])
summary["avg_bare_url_count"] = mean_of(lambda r: r["stats"]["bare_url_count"])
summary["avg_link_text_words"] = mean_of(lambda r: r["stats"]["avg_link_text_words"] if r["stats"]["inline_link_count"] >= 3 else None)

# --- link style ratio (reference vs inline, corpus-wide totals not per-repo average, more robust)
total_inline = sum(r["stats"]["inline_link_count"] for r in recs)
total_ref = sum(r["stats"]["reference_style_link_count"] for r in recs)
total_bare = sum(r["stats"]["bare_url_count"] for r in recs)
tot_links_all = total_inline + total_ref + total_bare
summary["link_style_corpus_totals"] = {
    "inline_markdown_links": total_inline,
    "reference_style_links": total_ref,
    "bare_urls": total_bare,
    "pct_inline": round(100 * total_inline / tot_links_all, 1) if tot_links_all else 0,
    "pct_reference_style": round(100 * total_ref / tot_links_all, 1) if tot_links_all else 0,
    "pct_bare_url": round(100 * total_bare / tot_links_all, 1) if tot_links_all else 0,
}

# --- badge type breakdown (via URL keyword sniffing across corpus)
badge_keywords = {
    "build/CI": ["actions/workflows", "travis-ci", "circleci", "badge.svg"],
    "license": ["license"],
    "version/release": ["npmjs.com/package", "pypi.org/project", "crates.io", "badge/version", "release"],
    "coverage": ["codecov", "coveralls"],
    "code_quality": ["sonarcloud", "snyk", "codefactor"],
    "chat/community": ["discord.com/api/guilds", "discord"],
    "docs": ["deepwiki", "readthedocs"],
    "stars/social": ["github/stars", "visitor-badge"],
    "sponsor": ["opencollective", "github/sponsors"],
}
badge_type_counts = Counter()
# Must stay identical to 03_analyze_readme.py's IMAGE_RE. Without the optional
# title clause, `![alt](url "title")` does not match at all and the image drops
# out of this count while step 03 still sees it, so the two steps disagree about
# the same corpus.
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_IMG_RE = re.compile(r"<img[^>]+src\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
for full_name, r in all_data.items():
    meta = r["meta"]
    # Prefer the copy that ships in this repo. readme_local_path is absolute and
    # points at the machine that fetched the corpus. Silently failing here is how
    # this counter shipped empty. Globbed rather than hardcoded to README.md,
    # because step 02 saves README.rst and README.txt under their real names.
    repo_dir = os.path.join(BASE, "repos", full_name.replace("/", "__"))
    hits = sorted(glob.glob(os.path.join(repo_dir, "README.*")))
    local = ([h for h in hits if h.lower().endswith(".md")] or hits or [""])[0]
    path = local if local and os.path.isfile(local) else meta.get("readme_local_path", "")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        print("badge typing: could not read %s" % full_name)
        continue
    urls = [u for _, u in IMAGE_RE.findall(text)] + HTML_IMG_RE.findall(text)
    for url in urls:
        lu = url.lower()
        matched = False
        for cat, kws in badge_keywords.items():
            if any(k in lu for k in kws):
                badge_type_counts[cat] += 1
                matched = True
                break
summary["badge_type_counts_corpus"] = dict(badge_type_counts.most_common())

# --- most common canonical section-order sequence: drop every "other" heading,
#     then collapse runs of the same category, then keep the first n
def canon_seq(r, n=6):
    seq = r["stats"]["section_order"]
    seq = [s for s in seq if s != "other"]
    out = []
    for s in seq:
        if not out or out[-1] != s:
            out.append(s)
    return tuple(out[:n])

seq_counter = Counter(canon_seq(r) for r in recs)
summary["top_section_sequences"] = [{"sequence": list(seq), "count": count} for seq, count in seq_counter.most_common(15)]

# --- category presence rate (any occurrence anywhere) - which sections show up most
cat_presence = Counter()
for r in recs:
    cats_present = set(r["stats"]["section_order"])
    for c in cats_present:
        cat_presence[c] += 1
summary["section_category_presence_pct"] = {k: round(100 * v / N, 1) for k, v in sorted(cat_presence.items(), key=lambda x: -x[1])}

# --- section word-count medians (across repos that have that section)
section_word_stats = defaultdict(list)
for r in recs:
    for cat, wcs in r["stats"]["section_word_counts"].items():
        section_word_stats[cat].append(sum(wcs))
summary["section_median_word_count"] = {
    cat: {"median_words": round(statistics.median(v), 1), "n_repos": len(v)}
    for cat, v in sorted(section_word_stats.items(), key=lambda x: -len(x[1]))
    if cat != "other"
}

# --- correlation-ish: readme length vs stars (rough deciles)
by_length = sorted(recs, key=lambda r: r["stats"]["total_prose_words"])
summary["readme_word_count_percentiles"] = {
    "p10": by_length[int(N * 0.10)]["stats"]["total_prose_words"],
    "p25": by_length[int(N * 0.25)]["stats"]["total_prose_words"],
    "p50": by_length[int(N * 0.50)]["stats"]["total_prose_words"],
    "p75": by_length[int(N * 0.75)]["stats"]["total_prose_words"],
    "p90": by_length[int(N * 0.90)]["stats"]["total_prose_words"],
}

# --- average relative position of each section category (0=start, 1=end)
pos_by_cat = defaultdict(list)
for r in recs:
    seq = [s for s in r["stats"]["section_order"] if s != "other"]
    n = len(seq)
    if n == 0:
        continue
    for i, cat in enumerate(seq):
        pos_by_cat[cat].append(i / max(n - 1, 1))
position_result = {
    cat: {"avg_relative_position": round(statistics.mean(v), 2), "n_occurrences": len(v)}
    for cat, v in pos_by_cat.items()
}
summary["section_avg_relative_position"] = dict(sorted(position_result.items(), key=lambda x: x[1]["avg_relative_position"]))

with open(f"{BASE}/03_aggregate_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print(json.dumps(summary, indent=2))
