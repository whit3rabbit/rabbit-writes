#!/usr/bin/env python3
"""
What counts as an "installation" section, decided once.

The corpus study classifies headings to measure where each section sits, and
readme_check.py classifies them again to compare one README against those
measurements. Two copies meant a README could be compared against thresholds
derived from a different definition of the same word, and the copies did
diverge: "getting started" was listed under both installation and usage, and
" api" could not match a heading that is just "API", so the commonest API
heading there is counted as "other" and the study undercounted api sections.

Stdlib only, 3.9+.
"""

import re

# Order matters. The first category with a matching keyword wins, so the more
# specific rows sit above the ones that would swallow them.
SECTION_KEYWORDS = [
    ("toc", ["table of contents", "contents", "index"]),
    ("features", ["features", "why ", "highlights", "why use", "what is"]),
    ("demo", ["demo", "screenshot", "preview", "gallery", "in action", "showcase"]),
    ("installation", ["install", "setup", "getting started", "quick start",
                      "quickstart", "requirements", "prerequisites"]),
    # "getting started" belongs to installation, which is tested first, so a
    # copy of it here could never win a heading anyway.
    ("usage", ["usage", "how to use", "quick example", "basic usage"]),
    ("examples", ["example"]),
    ("configuration", ["config", "options", "settings", "environment variable"]),
    # " api " and " apis " are whole-word matches and the spaces are
    # load-bearing: see classify_heading, which pads the heading before the
    # test. A bare "api" here would swallow "apiary" and "rapid". The plural is
    # spelled out rather than inferred so "Required APIs" keeps the
    # classification it has always had.
    ("api", ["api reference", " api ", " apis ", "documentation", "docs"]),
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

SECTION_NAMES = tuple(cat for cat, _ in SECTION_KEYWORDS)

# Sections that exist for people already sold on the project. A quickstart
# appearing after one of these is the ordering inversion worth flagging.
LATE_SECTIONS = frozenset({"contributing", "changelog", "credits", "faq",
                           "testing", "roadmap", "license"})


def classify_heading(text):
    t = re.sub(r"[^\w\s'-]", " ", text.strip().lower().lstrip("#").strip())
    # Padded, so a keyword can ask for a whole word by writing its own spaces
    # (" api ") while a keyword that wants a prefix keeps working unchanged
    # ("install" still catches "Installation"). Without the padding the only way
    # to write a word-boundary keyword was a leading space, and a leading space
    # has nothing to sit against at the start of the string.
    t = " %s " % t
    for cat, kws in SECTION_KEYWORDS:
        if any(kw in t for kw in kws):
            return cat
    return "other"
