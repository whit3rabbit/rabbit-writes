#!/usr/bin/env python3
"""
analyze_transcript_tells.py - Mine local Claude/Codex/LLM transcripts on this machine
to identify high-frequency LLM words, n-grams, and habitual filler phrases.

Outputs a ranked catalogue of candidate LLM tells for use in thesaurus expansion,
preferred substitutions, and voice de-slopping rules.
"""

import os
import glob
import json
import re
from collections import Counter


# Common stop words to exclude from single-word tell detection (keep them for n-grams)
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "as", "is", "was", "are", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "shall", "should", "may", "might", "must",
    "can", "could", "it", "its", "it's", "this", "that", "these", "those", "i", "you", "he",
    "she", "we", "they", "me", "him", "her", "us", "them", "my", "your", "his", "their",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "s", "t", "just", "don't", "now",
    "then", "if", "there", "here", "up", "out", "about", "into", "over", "after"
}

def clean_text(raw):
    """Strip code blocks, XML tags, tool tags, and normalize whitespace."""
    # Strip markdown code blocks
    text = re.sub(r"```[\s\S]*?```", " ", raw)
    # Strip inline code
    text = re.sub(r"`[^`]*`", " ", text)
    # Strip XML/HTML tags and tool markup
    text = re.sub(r"<[^>]+>", " ", text)
    # Strip URLs
    text = re.sub(r"https?://\S+", " ", text)
    # Strip file paths
    text = re.sub(r"(/[a-zA-Z0-9_.-]+)+", " ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_claude_prose():
    pattern = os.path.expanduser("~/.claude/projects/**/*.jsonl")
    files = glob.glob(pattern, recursive=True)
    print(f"Ingesting {len(files)} Claude transcript files...")
    
    prose_blocks = []
    total_files_parsed = 0
    
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if '"assistant"' in line:
                        try:
                            d = json.loads(line)
                            if d.get("type") == "assistant":
                                msg = d.get("message", {})
                                content = msg.get("content", [])
                                if isinstance(content, list):
                                    for c in content:
                                        if isinstance(c, dict) and c.get("type") == "text":
                                            t = clean_text(c.get("text", ""))
                                            if len(t.split()) >= 4:
                                                prose_blocks.append(t)
                        except Exception:
                            pass
            total_files_parsed += 1
        except Exception:
            pass
            
    print(f"Extracted {len(prose_blocks):,} assistant prose blocks from {total_files_parsed} files.")
    return prose_blocks

def find_ngrams(tokens, n):
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]

def analyze_tells(prose_blocks):
    full_text = " ".join(prose_blocks).lower()
    words = re.findall(r"\b[a-z'-]+\b", full_text)
    total_words = len(words)
    print(f"Total analyzed words in assistant prose: {total_words:,}")
    
    # 1. Single word frequencies (excluding basic stop words)
    content_word_counts = Counter(w for w in words if w not in STOP_WORDS and len(w) > 2)
    
    # 2. 2-grams, 3-grams, and 4-grams
    bigrams = Counter(find_ngrams(words, 2))
    trigrams = Counter(find_ngrams(words, 3))
    quadgrams = Counter(find_ngrams(words, 4))
    
    return {
        "total_words": total_words,
        "content_words": content_word_counts,
        "bigrams": bigrams,
        "trigrams": trigrams,
        "quadgrams": quadgrams
    }

if __name__ == "__main__":
    blocks = extract_claude_prose()
    results = analyze_tells(blocks)
    
    print("\n" + "="*80)
    print("TOP 50 MOST FREQUENT CONTENT WORDS IN ASSISTANT TURNS")
    print("="*80)
    for w, c in results["content_words"].most_common(50):
        print(f"  {w:20s}: {c:6d}")
        
    print("\n" + "="*80)
    print("TOP 40 MOST FREQUENT 2-GRAM PHRASES")
    print("="*80)
    for p, c in results["bigrams"].most_common(40):
        print(f"  {p:30s}: {c:6d}")
        
    print("\n" + "="*80)
    print("TOP 40 MOST FREQUENT 3-GRAM PHRASES")
    print("="*80)
    for p, c in results["trigrams"].most_common(40):
        print(f"  {p:40s}: {c:6d}")
        
    print("\n" + "="*80)
    print("TOP 30 MOST FREQUENT 4-GRAM PHRASES")
    print("="*80)
    for p, c in results["quadgrams"].most_common(30):
        print(f"  {p:50s}: {c:6d}")
