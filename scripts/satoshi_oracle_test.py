#!/usr/bin/env python3
"""
satoshi_oracle_test.py - Oracle testing and authorship discrimination suite
for the Satoshi Nakamoto voice profile in rabbit-writes.

Evaluates the precision, recall, and discriminative power of:
1. voices/satoshi.md
2. voices/satoshi.rules.json
3. voices/satoshi.fingerprint.json (and register variants)

Tests against:
- Positive Class: Authentic Satoshi Nakamoto writings (Whitepaper, Mailing List Emails, Forum Posts)
- Negative Class:
    a) Contemporary Cypherpunks (Nick Szabo, Hal Finney, Wei Dai, Ian Grigg, Tim May)
    b) Modern Cryptocurrency Marketing / Hype text (Token sale pitches, web3 press releases)
    c) Generic AI-generated crypto text (Standard LLM style)
"""

import os, sys, json, re

# Add rabbit-writes scripts to sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import scan
from rwlib import stylometry, voices

POSITIVE_SAMPLES = [
    ("Satoshi: Whitepaper Part 1", "scratch/clean_satoshi_samples/whitepaper_part1.md", "formal"),
    ("Satoshi: Whitepaper Part 2", "scratch/clean_satoshi_samples/whitepaper_part2.md", "formal"),
    ("Satoshi: Technical Emails (Early)", "scratch/clean_satoshi_samples/emails_1.md", "informal"),
    ("Satoshi: Technical Emails (Late)", "scratch/clean_satoshi_samples/emails_2.md", "informal"),
    ("Satoshi: Forum Discussions Part 1", "scratch/clean_satoshi_samples/satoshi_forum_1.md", "chat"),
    ("Satoshi: Forum Discussions Part 2", "scratch/clean_satoshi_samples/satoshi_forum_2.md", "chat"),
]

NEGATIVE_PEERS = [
    ("Nick Szabo: Bit Gold", "scratch/nakamotoinstitute/server/content/library/bit-gold.en.md", "formal"),
    ("Nick Szabo: Smart Contracts", "scratch/nakamotoinstitute/server/content/library/smart-contracts.en.md", "formal"),
    ("Hal Finney: RPOW", "scratch/nakamotoinstitute/server/content/library/rpow.en.md", "formal"),
    ("Hal Finney: Bitcoin and Me", "scratch/nakamotoinstitute/server/content/library/bitcoin-and-me.en.md", "informal"),
    ("Wei Dai: B-Money", "scratch/nakamotoinstitute/server/content/library/b-money.en.md", "formal"),
    ("Ian Grigg: The Ricardian Contract", "scratch/nakamotoinstitute/server/content/library/the-ricardian-contract.en.md", "formal"),
    ("Tim May: Crypto Anarchist Manifesto", "scratch/nakamotoinstitute/server/content/library/crypto-anarchist-manifesto.en.md", "formal"),
]

# Create synthetic modern hype & AI text for testing
MODERN_HYPE_TEXT = """# QuantumLedger: The Revolutionary Next-Generation Blockchain Ecosystem

QuantumLedger is a revolutionary, game-changing paradigm shift in decentralized finance. By harnessing the power of cutting-edge zero-knowledge state channels, we unlock unprecedented scalability to seamlessly empower global commerce.

Our state-of-the-art blockchain is 100% secure, unhackable, and designed to disrupt legacy banking forever. Unlike antiquated legacy networks, QuantumLedger fosters a thriving ecosystem where thought leaders and innovators embark on a transformative journey toward financial freedom.

With our upcoming massive airdrop, we are paving the way to the moon. Don't let FUD stop you from joining this groundbreaking revolution. Let's delve into the deep dive of our synergistic tokenomics and examine how we will move the needle across the entire web3 space! HODL and WAGMI!
"""

AI_LLM_TEXT = """# Understanding Proof of Work in Distributed Systems

In this comprehensive guide, we will delve into the intricate tapestry of consensus mechanisms that underpin modern distributed ledgers. Proof of Work stands as a testament to human ingenuity, playing a pivotal role in ensuring Byzantine fault tolerance without requiring a centralized authority.

At its core, the algorithm requires participating nodes to solve a computationally intensive puzzle. Studies show that maintaining network synchronization in an ever-evolving digital landscape requires robust security guarantees. Furthermore, it is important to note that miners expend considerable energy in order to ascertain transaction validity.

In conclusion, navigating the complex dynamics of decentralized protocols presents unique challenges. However, the future looks bright as innovative architectures continue to elevate performance and foster broader adoption across diverse industries.
"""

def evaluate_sample(label, text, register, is_positive=True):
    rules_path = os.path.join(voices.VOICES_DIR, "satoshi.rules.json")
    voice_rules = voices.load(rules_path)
    
    fingerprint_path = stylometry.path_for(rules_path, register)
    voice_fingerprint = stylometry.load(fingerprint_path) if fingerprint_path else None
    
    report, stats = scan.scan(text, profile=register, voice_rules=voice_rules,
                              voice_fingerprint=voice_fingerprint)
    
    p0_count = sum(1 for f in report if f["priority"] == "P0")
    p1_count = sum(1 for f in report if f["priority"] == "P1")
    voice_findings = [f for f in report if f.get("band") == "voice"]
    
    # Stylometric distance
    v_dist = stats.get("voice_distance")
    delta = v_dist["delta"] if v_dist else 999.0
    verdict = v_dist["verdict"] if v_dist else "no_fingerprint"
    
    # Classification logic:
    # A text is classified as "Satoshi" if:
    # 1. 0 P0 voice violations (no banned words, hype, buzzwords)
    # 2. voice distance delta <= 1.5 * band max (or in_range / near)
    is_classified_satoshi = (len(voice_findings) == 0 and (verdict in ["in_range", "near"] or delta <= 1.0))
    
    correct = (is_classified_satoshi == is_positive)
    
    return {
        "label": label,
        "is_positive": is_positive,
        "classified_satoshi": is_classified_satoshi,
        "correct": correct,
        "p0_total": p0_count,
        "voice_violations": len(voice_findings),
        "voice_findings_detail": [f["label"] for f in voice_findings],
        "delta": round(delta, 3) if delta < 900 else None,
        "verdict": verdict,
        "words": stats.get("word_count", 0)
    }

def run_oracle_suite():
    print("=" * 80)
    print("SATOSHI NAKAMOTO ORACLE DISCRIMINATION TEST SUITE")
    print("=" * 80)
    
    results = []
    
    # 1. Positive Tests
    print("\n--- POSITIVE TESTS (Authentic Satoshi) ---")
    for label, path, reg in POSITIVE_SAMPLES:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            res = evaluate_sample(label, text, reg, is_positive=True)
            results.append(res)
            status = "PASS [MATCH]" if res["correct"] else "FAIL [MISCLASSIFIED]"
            print(f"[{status}] {label} ({res['words']} words)")
            print(f"       Delta: {res['delta']} | Verdict: {res['verdict']} | Voice violations: {res['voice_violations']}")
        else:
            print(f"Skipping {label} (file not found: {path})")
            
    # 2. Negative Tests (Cypherpunk Peers)
    print("\n--- NEGATIVE TESTS: CONTEMPORARY CYPHERPUNKS ---")
    for label, path, reg in NEGATIVE_PEERS:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            # Strip frontmatter
            text = re.sub(r'^---[\s\S]*?---\s*', '', text)
            res = evaluate_sample(label, text, reg, is_positive=False)
            results.append(res)
            status = "PASS [REJECTED]" if res["correct"] else "FAIL [FALSE POSITIVE]"
            print(f"[{status}] {label} ({res['words']} words)")
            print(f"       Delta: {res['delta']} | Verdict: {res['verdict']} | Voice violations: {res['voice_violations']}")
        else:
            print(f"Skipping {label} (file not found: {path})")
            
    # 3. Negative Tests (Modern Crypto Hype & AI Slop)
    print("\n--- NEGATIVE TESTS: MODERN CRYPTO HYPE & AI SLOP ---")
    res_hype = evaluate_sample("Modern Web3 Hype Pitch", MODERN_HYPE_TEXT, "technical-blog", is_positive=False)
    results.append(res_hype)
    status = "PASS [REJECTED]" if res_hype["correct"] else "FAIL [FALSE POSITIVE]"
    print(f"[{status}] Modern Web3 Hype Pitch ({res_hype['words']} words)")
    print(f"       Delta: {res_hype['delta']} | Voice violations: {res_hype['voice_violations']} | P0s: {res_hype['p0_total']}")
    print(f"       Violations detail: {res_hype['voice_findings_detail']}")
    
    res_ai = evaluate_sample("Standard AI-generated Explanation", AI_LLM_TEXT, "technical-blog", is_positive=False)
    results.append(res_ai)
    status = "PASS [REJECTED]" if res_ai["correct"] else "FAIL [FALSE POSITIVE]"
    print(f"[{status}] Standard AI-generated Explanation ({res_ai['words']} words)")
    print(f"       Delta: {res_ai['delta']} | Voice violations: {res_ai['voice_violations']} | P0s: {res_ai['p0_total']}")
    print(f"       Violations detail: {res_ai['voice_findings_detail']}")
    
    # Summary Statistics
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    pos_total = sum(1 for r in results if r["is_positive"])
    pos_correct = sum(1 for r in results if r["is_positive"] and r["correct"])
    neg_total = sum(1 for r in results if not r["is_positive"])
    neg_correct = sum(1 for r in results if not r["is_positive"] and r["correct"])
    
    print("\n" + "=" * 80)
    print("ORACLE TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests Run: {total}")
    print(f"Overall Accuracy: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"Positive Sensitivity (Recall on Satoshi): {pos_correct}/{pos_total} ({pos_correct/pos_total*100:.1f}%)")
    print(f"Negative Specificity (Rejection of Non-Satoshi): {neg_correct}/{neg_total} ({neg_correct/neg_total*100:.1f}%)")
    print("=" * 80)

if __name__ == "__main__":
    run_oracle_suite()
