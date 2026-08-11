#!/usr/bin/env python3
"""
Step 3: quantitative README analysis.

For each repo's fetched README, compute a structured stats dict covering
layout (section inventory + order), sentence/paragraph length, images,
badges, centering, links, code blocks, tables, and TOC presence.

Usage:
  python3 03_analyze_readme.py <path-to-readme> [--json]
  python3 03_analyze_readme.py --batch   # process every repo under docs/readme-analysis/repos/
"""
import json
import os
import re
import statistics
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(REPO_ROOT, "docs", "readme-analysis")
REPOS_DIR = f"{BASE}/repos"

# ---------------------------------------------------------------- section map
SECTION_KEYWORDS = [
    ("toc", ["table of contents", "contents", "index"]),
    ("features", ["features", "why ", "highlights", "why use", "what is"]),
    ("demo", ["demo", "screenshot", "preview", "gallery", "in action", "showcase"]),
    ("installation", ["install", "setup", "getting started", "quick start", "quickstart", "requirements", "prerequisites"]),
    ("usage", ["usage", "how to use", "quick example", "getting started", "basic usage"]),
    ("examples", ["example"]),
    ("configuration", ["config", "options", "settings", "environment variable"]),
    ("api", ["api reference", " api", "documentation", "docs"]),
    ("architecture", ["architecture", "how it works", "design", "internals"]),
    ("contributing", ["contributing", "contribute", "development guide", "developing"]),
    ("testing", ["testing", "run tests", "tests"]),
    ("roadmap", ["roadmap", "todo", "future work", "upcoming"]),
    ("faq", ["faq", "frequently asked", "troubleshoot"]),
    ("license", ["license", "licence"]),
    ("credits", ["acknowledg", "credits", "thanks", "contributors", "inspired by"]),
    ("support", ["support", "community", "contact", "discord", "get help", "help"]),
    ("sponsors", ["sponsor", "backers", "funding"]),
    ("changelog", ["changelog", "release notes", "history", "whats new", "what's new"]),
    ("security", ["security"]),
    ("related", ["related", "see also", "alternatives", "comparison"]),
    ("performance", ["performance", "benchmark"]),
]

def classify_heading(text):
    t = text.strip().lower().lstrip("#").strip()
    t = re.sub(r"[^\w\s'-]", " ", t)
    for cat, kws in SECTION_KEYWORDS:
        for kw in kws:
            if kw in t:
                return cat
    return "other"

CODE_FENCE_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
REF_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\[([^\]]*)\]")
REF_DEF_RE = re.compile(r"^\s*\[([^\]]+)\]:\s*(\S+)", re.MULTILINE)
# A URL only counts as bare when nothing already wraps it. The first pass of this
# study matched inside HTML href/src attributes and inside inline code, which put
# 2,009 attribute URLs in the "bare" bucket and inflated the rate by an order of
# magnitude. strip_wrapped_urls below is the fix.
BARE_URL_RE = re.compile(r"https?://[^\s)>\]\"']+")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
HTML_ATTR_URL_RE = re.compile(r"(?:src|href)\s*=\s*[\"'][^\"']*[\"']", re.IGNORECASE)
HTML_IMG_RE = re.compile(r"<img[^>]+src\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
HTML_LINK_RE = re.compile(r"<a[^>]+href\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
AUTOLINK_RE = re.compile(r"<https?://[^>]+>")
HTML_CENTER_RE = re.compile(r"<(p|div|h[1-6])\s+align=[\"']center[\"']", re.IGNORECASE)
TABLE_ROW_RE = re.compile(r"^\|.+\|\s*$", re.MULTILINE)
TABLE_SEP_RE = re.compile(r"^\|?[\s:|-]+\|[\s:|-]+\|?\s*$", re.MULTILINE)
BADGE_HOST_HINTS = ["shields.io", "badge.fury.io", "img.shields", "badgen.net", "travis-ci",
                     "circleci.com/gh", "codecov.io", "coveralls.io", "github.com/.*/workflows/.*badge",
                     "actions/workflows", "sonarcloud.io", "snyk.io", "discord.com/api/guilds",
                     "opencollective.com", "npmjs.com/package", "pypi.org/project", "crates.io/v",
                     "gitpod.io/button", "deepwiki.com/badge", "img.badgesize.io", "visitor-badge"]

def strip_code_blocks(text):
    return CODE_FENCE_RE.sub("", text)

def strip_wrapped_urls(text):
    """Blank every URL that is already inside a markdown link, an HTML attribute,
    an autolink, a reference definition, or inline code. What survives is bare."""
    out = IMAGE_RE.sub(" ", text)
    out = LINK_RE.sub(" ", out)
    out = HTML_ATTR_URL_RE.sub(" ", out)
    out = AUTOLINK_RE.sub(" ", out)
    out = REF_DEF_RE.sub(" ", out)
    out = INLINE_CODE_RE.sub(" ", out)
    return out

def is_badge_url(url):
    lu = url.lower()
    return any(h in lu for h in BADGE_HOST_HINTS)

def sentence_split(text):
    # Very light sentence splitter: split on . ! ? followed by whitespace+capital or newline,
    # while trying not to split on common abbreviations / decimal numbers / version strings.
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    # protect decimals and versions like v1.2.3, e.g., i.e.
    protected = re.sub(r"(\d)\.(\d)", r"\1<DOT>\2", text)
    protected = re.sub(r"\b(e\.g|i\.e|etc|vs|Mr|Mrs|Dr|Inc|Ltd)\.", r"\1<DOT>", protected)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'`(*_])", protected)
    sentences = [p.replace("<DOT>", ".").strip() for p in parts if p.strip()]
    return sentences

def word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", text))

def analyze_readme(text, full_name=""):
    stats = {}
    raw_lines = text.splitlines()
    stats["total_lines"] = len(raw_lines)
    stats["non_blank_lines"] = len([l for l in raw_lines if l.strip()])
    stats["total_chars"] = len(text)

    # ---- headings / section inventory & order
    headings = []
    for m in HEADING_RE.finditer(text):
        level = len(m.group(1))
        heading_text = m.group(2).strip()
        headings.append({"level": level, "text": heading_text, "category": classify_heading(heading_text), "pos": m.start()})
    stats["heading_count"] = len(headings)
    stats["heading_levels_used"] = sorted(set(h["level"] for h in headings))
    stats["section_order"] = [h["category"] for h in headings if h["level"] <= 3]
    stats["section_order_detail"] = [{"level": h["level"], "text": h["text"], "category": h["category"]} for h in headings]
    stats["has_h1"] = any(h["level"] == 1 for h in headings)

    # ---- section word counts (between consecutive top-level-ish headings)
    section_words = {}
    if headings:
        sorted_h = sorted(headings, key=lambda h: h["pos"])
        for i, h in enumerate(sorted_h):
            start = h["pos"]
            end = sorted_h[i + 1]["pos"] if i + 1 < len(sorted_h) else len(text)
            body = text[start:end]
            body = HEADING_RE.sub("", body, count=1)
            body_nocod = strip_code_blocks(body)
            wc = word_count(body_nocod)
            cat = h["category"]
            section_words.setdefault(cat, []).append(wc)
    stats["section_word_counts"] = {k: v for k, v in section_words.items()}

    # ---- preamble (before first heading): tagline/description length
    if headings:
        preamble = text[:headings[0]["pos"]]
    else:
        preamble = text
    preamble_nocode = strip_code_blocks(preamble)
    stats["preamble_word_count"] = word_count(preamble_nocode)
    stats["preamble_has_centered_block"] = bool(HTML_CENTER_RE.search(preamble))

    # ---- centering
    center_matches = HTML_CENTER_RE.findall(text)
    stats["centered_block_count"] = len(center_matches)
    stats["uses_centering"] = len(center_matches) > 0

    # ---- images
    body_for_media = text  # include everywhere, badges usually near top but can be anywhere
    images = IMAGE_RE.findall(body_for_media)
    # 76% of this corpus centers its header, and a centered header uses raw HTML.
    # Counting markdown images only missed most of the badges in the sample.
    all_image_urls = [u for _, u in images] + HTML_IMG_RE.findall(body_for_media)
    badge_imgs = [u for u in all_image_urls if is_badge_url(u)]
    non_badge_imgs = [u for u in all_image_urls if not is_badge_url(u)]
    gif_imgs = [u for u in non_badge_imgs if u.lower().endswith(".gif")]
    stats["image_count_total"] = len(all_image_urls)
    stats["badge_count"] = len(badge_imgs)
    stats["screenshot_or_logo_image_count"] = len(non_badge_imgs)
    stats["gif_count"] = len(gif_imgs)
    stats["has_video_embed"] = bool(re.search(r"<video|youtube\.com/watch|youtu\.be/|loom\.com/share|asciinema\.org", text, re.IGNORECASE))
    # badges specifically within first 20 non-blank lines (typical badge-row placement)
    head_text = "\n".join(raw_lines[:20])
    head_urls = [u for _, u in IMAGE_RE.findall(head_text)] + HTML_IMG_RE.findall(head_text)
    stats["badges_in_header_block"] = len([u for u in head_urls if is_badge_url(u)])

    # ---- links
    text_no_code = strip_code_blocks(text)
    inline_links = LINK_RE.findall(text_no_code)
    ref_links = REF_LINK_RE.findall(text_no_code)
    ref_defs = REF_DEF_RE.findall(text_no_code)
    bare_urls = BARE_URL_RE.findall(strip_wrapped_urls(text_no_code))
    stats["html_link_count"] = len(HTML_LINK_RE.findall(text_no_code))
    stats["inline_link_count"] = len(inline_links)
    stats["reference_style_link_count"] = len(ref_links)
    stats["reference_definitions_count"] = len(ref_defs)
    stats["bare_url_count"] = len(bare_urls)
    total_md_links = len(inline_links) + len(ref_links)
    stats["total_markdown_links"] = total_md_links
    stats["uses_reference_style_links"] = len(ref_links) > 0
    link_text_word_counts = [word_count(t) for t, _ in inline_links if t.strip()]
    stats["avg_link_text_words"] = round(statistics.mean(link_text_word_counts), 2) if link_text_word_counts else 0
    anchor_links = [u for _, u in inline_links if u.startswith("#")]
    stats["internal_anchor_link_count"] = len(anchor_links)
    stats["has_toc_like_anchor_list"] = len(anchor_links) >= 3

    # ---- code blocks
    code_blocks = CODE_FENCE_RE.findall(text)
    stats["code_block_count"] = len(code_blocks)
    langs = [lang.lower() for lang, _ in code_blocks if lang.strip()]
    stats["code_block_languages"] = sorted(set(langs))
    if code_blocks:
        cb_lines = [len(body.splitlines()) for _, body in code_blocks]
        stats["avg_code_block_lines"] = round(statistics.mean(cb_lines), 2)
    else:
        stats["avg_code_block_lines"] = 0

    # ---- tables
    stats["table_row_count"] = len(TABLE_ROW_RE.findall(text_no_code))
    stats["table_present"] = bool(TABLE_SEP_RE.search(text_no_code))

    # ---- sentence / paragraph stats (prose only: strip code, tables, headings)
    prose = text_no_code
    prose = HEADING_RE.sub("", prose)
    prose = re.sub(r"^\|.*\|\s*$", "", prose, flags=re.MULTILINE)  # drop table rows
    prose = IMAGE_RE.sub("", prose)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", prose) if p.strip() and not p.strip().startswith(("- ", "* ", "1.", ">"))]
    para_word_counts = [word_count(p) for p in paragraphs]
    stats["paragraph_count"] = len(paragraphs)
    stats["avg_paragraph_words"] = round(statistics.mean(para_word_counts), 2) if para_word_counts else 0
    stats["median_paragraph_words"] = round(statistics.median(para_word_counts), 2) if para_word_counts else 0

    all_sentences = []
    for p in paragraphs:
        all_sentences.extend(sentence_split(p))
    sent_word_counts = [word_count(s) for s in all_sentences if word_count(s) > 0]
    stats["sentence_count"] = len(sent_word_counts)
    if sent_word_counts:
        stats["avg_sentence_words"] = round(statistics.mean(sent_word_counts), 2)
        stats["median_sentence_words"] = round(statistics.median(sent_word_counts), 2)
        stats["stdev_sentence_words"] = round(statistics.pstdev(sent_word_counts), 2) if len(sent_word_counts) > 1 else 0
        stats["short_sentence_pct"] = round(100 * len([w for w in sent_word_counts if w < 10]) / len(sent_word_counts), 1)
        stats["medium_sentence_pct"] = round(100 * len([w for w in sent_word_counts if 10 <= w <= 20]) / len(sent_word_counts), 1)
        stats["long_sentence_pct"] = round(100 * len([w for w in sent_word_counts if w > 20]) / len(sent_word_counts), 1)
    else:
        stats["avg_sentence_words"] = stats["median_sentence_words"] = stats["stdev_sentence_words"] = 0
        stats["short_sentence_pct"] = stats["medium_sentence_pct"] = stats["long_sentence_pct"] = 0

    stats["total_prose_words"] = word_count(prose)

    # ---- misc flags
    stats["has_license_section_or_badge"] = ("license" in stats["section_order"]) or any("license" in u.lower() or "licence" in u.lower() for u in badge_imgs)
    stats["has_contributing_section"] = "contributing" in stats["section_order"]
    stats["has_toc_section"] = "toc" in stats["section_order"] or stats["has_toc_like_anchor_list"]
    stats["has_installation_section"] = "installation" in stats["section_order"]
    stats["has_usage_or_examples_section"] = ("usage" in stats["section_order"]) or ("examples" in stats["section_order"])
    stats["has_demo_section_or_media"] = ("demo" in stats["section_order"]) or stats["screenshot_or_logo_image_count"] > 0 or stats["has_video_embed"]

    return stats

def main():
    if "--batch" in sys.argv:
        results = {}
        repo_dirs = sorted(os.listdir(REPOS_DIR))
        for slug in repo_dirs:
            repo_dir = os.path.join(REPOS_DIR, slug)
            meta_path = os.path.join(repo_dir, "meta.json")
            if not os.path.isfile(meta_path):
                continue
            with open(meta_path) as f:
                meta = json.load(f)
            # meta.json records the absolute path from the machine that fetched
            # the corpus. The copy that ships in this repo sits beside meta.json,
            # so prefer that and fall back to the recorded path.
            readme_path = os.path.join(repo_dir, "README.md")
            if not os.path.isfile(readme_path):
                readme_path = meta["readme_local_path"]
            try:
                with open(readme_path, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except Exception as e:
                print(f"skip {slug}: {e}")
                continue
            stats = analyze_readme(text, meta["full_name"])
            out = {"meta": meta, "stats": stats}
            with open(os.path.join(repo_dir, "stats.json"), "w") as f:
                json.dump(out, f, indent=2)
            results[meta["full_name"]] = out
            print(f"analyzed {meta['full_name']}: {stats['heading_count']} headings, {stats['sentence_count']} sentences, {stats['image_count_total']} images")
        with open(f"{BASE}/02_all_stats.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nBatch complete: {len(results)} repos analyzed.")
    else:
        path = sys.argv[1]
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        stats = analyze_readme(text)
        print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    main()
