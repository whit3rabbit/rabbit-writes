#!/usr/bin/env python3
"""
build_satoshi_thesaurus.py - Extract and calibrate a measured thesaurus,
most common words, and preferred word/phrase substitutions for Satoshi Nakamoto.

Reads clean Satoshi samples from scratch/clean_satoshi_samples/*.md and
compares against standard overreach/hype/corporate/AI vocabulary. Emits
recommended `preferred_substitutions` for voices/satoshi.rules.json and
vocabulary guidance for voices/satoshi.md.
"""

import os
import re
import json
import glob
from collections import Counter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(REPO_ROOT, "scratch", "clean_satoshi_samples")

def load_corpus(samples_dir=SAMPLES_DIR):
    files = glob.glob(os.path.join(samples_dir, "*.md"))
    corpus = {}
    for f in sorted(files):
        with open(f, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
            if text.strip():
                corpus[os.path.basename(f)] = text
    return corpus

def analyze_vocabulary(corpus):
    full_text = "\n\n".join(corpus.values())
    words = re.findall(r"\b[a-zA-Z0-9_\'-]+\b", full_text)
    words_lower = [w.lower() for w in words]
    counts = Counter(words_lower)
    total_words = len(words_lower)
    return counts, total_words, full_text

# Candidate word and phrase pairings: (overreach / buzzword / AI word, satoshi preferred alternative)
CANDIDATE_SUBSTITUTIONS = {
    # Measured thesaurus pairs (plain words Satoshi actually used vs inflated synonyms)
    "utilize": "use",
    "utilizes": "uses",
    "utilized": "used",
    "utilizing": "using",
    "demonstrate": "show",
    "demonstrates": "shows",
    "demonstrating": "showing",
    "illustrate": "show",
    "illustrates": "shows",
    "commence": "start",
    "commences": "starts",
    "commenced": "started",
    "individuals": "people",
    "inquire": "ask",
    "inquires": "asks",
    "inquired": "asked",
    "suboptimal": "bad",
    "inadequate": "bad",
    "genuinely": "really",
    "furthermore": "also",
    "moreover": "also",
    "additionally": "also",
    
    # Modern crypto & marketing hype -> Precise technical equivalents
    "revolutionary": "new",
    "groundbreaking": "new",
    "game-changer": "major improvement",
    "game-changing": "major improvement",
    "disrupt": "replace",
    "disrupting": "replacing",
    "disrupts": "replaces",
    "unhackable": "computationally secure",
    "synergy": "cooperation",
    "synergies": "cooperation",
    "paradigm": "model",
    "paradigms": "models",
    "paradigm shift": "new approach",
    
    # Corporate & AI fluff phrases -> Direct plain alternatives
    "in order to": "to",
    "deep dive": "analysis",
    "deep-dive": "analysis",
    "delve": "examine",
    "delves": "examines",
    "delved": "examined",
    "delving": "examining",
    "delve into": "examine",
    "reach out to": "contact",
    "circle back": "follow up",
    "touch base": "check in",
    "move the needle": "make progress",
    "low-hanging fruit": "simple cases",
    "at its core": "basically",
    "the future looks bright": "there is potential",
    "harness the power of": "use",
    "unlock the potential": "allow",
    "unlocking the potential": "allowing",
    "spearhead": "lead",
    "spearheading": "leading",
    "seamless": "clean",
    "seamlessly": "cleanly",
    "robust": "reliable",
    "robustness": "reliability",
    "ecosystem": "network",
    "ecosystems": "networks",
    "cutting-edge": "modern",
    "state-of-the-art": "current",
    "comprehensive": "complete",
    "pivotal": "important",
    "crucial": "important",
    "foster": "support",
    "fostering": "supporting",
    "elevate": "improve",
    "streamline": "simplify",
    "empower": "enable",
    "empowers": "enables",
    "bolster": "strengthen",
    "facilitate": "help",
    "facilitates": "helps",
    "leverage": "use",
    "leveraging": "using",
    "landscape": "field"
}

def build_thesaurus():
    corpus = load_corpus()
    counts, total_words, text = analyze_vocabulary(corpus)
    
    print(f"Loaded {len(corpus)} Satoshi samples ({total_words:,} total words).")
    print("\n--- Satoshi's High-Frequency Anchor Words ---")
    anchors = ["use", "used", "using", "show", "start", "want", "people", "also", "need", "problem",
               "network", "nodes", "block", "blocks", "transaction", "transactions", "proof-of-work",
               "chain", "cpu", "hash", "money", "coins", "attack", "honest", "verify", "signatures"]
    for a in anchors:
        print(f"  {a:16s}: {counts[a]:4d} occurrences")
        
    print("\n--- Validating Candidate Substitutions against Corpus ---")
    # The first version of this loop computed both counts and read neither,
    # so every candidate shipped as "verified". Now the counts decide: a
    # replacement Satoshi never reached for is not his word, and it lands in
    # the unsupported list instead of the output. A multi-word replacement is
    # counted as a phrase, since the word counter cannot see it at all.
    lower_text = text.lower()

    def occurrences(term):
        if " " in term:
            return len(re.findall(r"(?<!\w)%s(?!\w)"
                                  % re.escape(term.lower()), lower_text))
        return counts.get(term.lower(), 0)

    verified_subs = {}
    unsupported = []
    for overreach, replacement in CANDIDATE_SUBSTITUTIONS.items():
        # Evidence for the replacement: the head word of a multi-word
        # phrase counts too ("major improvement" is supported by "major").
        rep_count = max(occurrences(replacement),
                        occurrences(replacement.split()[0]))
        over_count = occurrences(overreach)
        if rep_count == 0:
            unsupported.append((overreach, replacement))
            continue
        if over_count > 2:
            # Satoshi used the "overreach" word himself. Substituting it
            # away rewrites his own vocabulary, so say so out loud.
            print(f"  NOTE {overreach!r} appears {over_count}x in the "
                  f"corpus; review before shipping this pair")
        verified_subs[overreach] = replacement

    if unsupported:
        print(f"\n{len(unsupported)} candidate(s) dropped, replacement "
              "never appears in the corpus:")
        for overreach, replacement in unsupported:
            print(f"  {overreach!r} -> {replacement!r}")

    print(f"\nGenerated {len(verified_subs)} corpus-supported substitutions.")
    return verified_subs

if __name__ == "__main__":
    subs = build_thesaurus()
    print("\nJSON output for voices/satoshi.rules.json:")
    print(json.dumps({"preferred_substitutions": subs}, indent=2))
