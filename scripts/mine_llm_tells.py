#!/usr/bin/env python3
"""
mine_llm_tells.py - Comprehensive mining of local Claude transcripts and LLM outputs
to generate candidate words and phrases for thesaurus expansion and voice rules.
"""

import os
import glob
import json
import re
from collections import Counter


# Characteristic LLM markers and inflated vocabulary categories
CATEGORIES = {
    "Conversational Meta-Tells / Scaffolding": [
        "let me check",
        "now let me",
        "i'll start by",
        "let me verify",
        "let me confirm",
        "say the word",
        "now let's check",
        "now let's examine",
        "let me take a look",
        "as mentioned earlier",
        "in summary",
        "to summarize",
        "in conclusion",
        "it's worth noting",
        "it is important to note",
        "it is worth noting that"
    ],
    "Overreach & Inflated Verbs": [
        "utilize",
        "delve",
        "commence",
        "facilitate",
        "streamline",
        "foster",
        "elevate",
        "bolster",
        "spearhead",
        "leverage",
        "reimagine",
        "galvanize",
        "elucidate",
        "juxtapose",
        "augment"
    ],
    "Corporate & Marketing Buzzwords": [
        "synergy",
        "synergies",
        "paradigm shift",
        "game-changer",
        "game-changing",
        "deep dive",
        "circle back",
        "touch base",
        "move the needle",
        "low-hanging fruit",
        "unlocking the potential",
        "harness the power of",
        "seamless integration"
    ],
    "Stock Rhetorical Fillers": [
        "in order to",
        "at its core",
        "rich tapestry",
        "in the realm of",
        "evolving landscape",
        "crucial role",
        "pivotal moment",
        "testament to",
        "indelible mark"
    ]
}

def scan_transcripts_for_candidates():
    pattern = os.path.expanduser("~/.claude/projects/**/*.jsonl")
    files = glob.glob(pattern, recursive=True)
    
    found_counts = Counter()
    total_messages = 0
    
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if '"type":"assistant"' in line:
                        try:
                            d = json.loads(line)
                            msg = d.get("message", {})
                            content = msg.get("content", [])
                            if isinstance(content, list):
                                for c in content:
                                    if isinstance(c, dict) and c.get("type") == "text":
                                        text = c.get("text", "").lower()
                                        total_messages += 1
                                        for cat, items in CATEGORIES.items():
                                            for item in items:
                                                if re.search(r"\b" + re.escape(item) + r"\b", text):
                                                    found_counts[item] += 1
                        except Exception:
                            pass
        except Exception:
            pass
            
    print(f"Scanned {total_messages:,} assistant messages across {len(files)} transcript files.\n")
    print("="*80)
    print("FREQUENCY OF IDENTIFIED LLM TELLS IN CLAUDE TRANSCRIPTS")
    print("="*80)
    
    for cat, items in CATEGORIES.items():
        print(f"\n--- {cat} ---")
        for item in items:
            print(f"  {item:35s}: {found_counts[item]:5d} occurrences")

if __name__ == "__main__":
    scan_transcripts_for_candidates()
