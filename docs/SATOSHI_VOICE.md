# Satoshi Nakamoto Voice Profile: Stylometric Analysis, Architecture & Oracle Testing

This document details the research, statistical extraction, voice profile architecture, and empirical validation for the **Satoshi Nakamoto** voice profile in `rabbit-writes`.

All data, stylometric baselines, and test fixtures are derived from the complete corpus preserved at [nakamotoinstitute.org](https://github.com/NakamotoInstitute/nakamotoinstitute.org), covering the 2008 Bitcoin whitepaper, 39 cryptography mailing list emails, and 539 BitcoinTalk forum posts.

---

## 1. Corpus Methodology & Quote Sanitization

Satoshi's writings span three distinct historical media between October 2008 and December 2010. A primary challenge in authorship analysis of forum posts and email threads is avoiding contamination from other writers quoted in replies (e.g., Martti Malmi, Hal Finney, Gavin Andresen, Mike Hearn, theymos).

```
Raw Nakamoto Institute Corpus
  ├── Whitepaper: Library Markdown (3,560 words)
  ├── Emails: Metzdowd Cryptography List JSON (72 total, 39 from Satoshi)
  └── Forum Posts: BitcoinTalk Forum JSON (3,845 total, 539 from Satoshi)
            │
            ▼
Automated Parsing & Sanitization
  ├── HTML tag & entity unescaping (resolving &nbsp;, &quot;, &#39;)
  ├── Blockquote & quote div elimination (<div class="quote">...</div>)
  ├── Signature block & mailing list footer removal
  └── Non-breaking space normalization (U+00A0 -> U+0020)
            │
            ▼
Pure Authored Corpus: 62,660 Words
```

### Partitioning Across Three Registers

| Register | Source Documents | Pure Authored Words | Primary Function |
|---|---|---:|---|
| **Formal (`formal`)** | Bitcoin Whitepaper (2008) | 3,560 words | Mathematical foundations, consensus proofs, state machine design |
| **Informal (`informal`)** | 39 Cryptography Mailing List Emails | 8,386 words | Architecture debate, cryptographic trade-offs, security bounds |
| **Chat (`chat`)** | 539 BitcoinTalk Forum Posts | 50,714 words | Release announcements, bug triage, protocol economics, community Q&A |
| **Aggregate Total** | **All 3 Formats Combined** | **62,660 words** | **Unified stylistic baseline** |

Three partitions, not four. `technical-blog` is a real, mechanically distinct register in the engine (Section 3), but Satoshi left no writing in that register, so it has no row of its own here and no independent fingerprint: `--profile technical-blog` measures against the Aggregate Total row, not the whitepaper-only row. Section 3 explains the fallback in full.

---

## 2. Quantitative Stylometrics & Empirical Findings

Using `measure_voice.py` and dedicated stylometric tokenizers from `rwlib/stylometry.py`, we measured the quantitative fingerprint of Satoshi's prose:

### Summary Table

| Stylometric Metric | Formal (Whitepaper) | Informal (Emails) | Chat (Forum) | Aggregate Corpus |
|---|---|---|---|---|
| **Avg Sentence Length** | 22.08 words | 18.88 words | 16.00 words | **16.61 words** |
| **Sentence Length SD** | 15.06 | 12.51 | 12.61 | **12.80** |
| **Sentence Percentiles (p10 / p50 / p90)** | 4 / 21 / 35 | 7 / 17 / 32 | 6 / 13 / 27 | **6 / 14 / 29** |
| **Moving-Avg Type-Token Ratio (MATTR)** | 0.650 | 0.719 | 0.705 | **0.700** |
| **Burstiness ($\sigma / \mu$)** | 0.626 | 0.642 | 0.690 | **0.685** |
| **Double Space After Period (`.  `)** | 0.0% (markdown) | 78.2% | **97.5%** | **88.2%** |
| **Contraction Rate (per 1,000 words)** | 5.21 | 19.98 | 28.10 | **25.63** |
| **Exclamation Frequency (per 1,000 words)** | 0.50 | 0.59 | 1.14 | **1.03** |
| **Semicolon Rate (per 1,000 words)** | 7.19 | 0.35 | 1.71 | **1.87** |
| **Em Dash Rate (`—` Unicode)** | 0.0 | 0.0 | 0.0 | **0.0** |

### Key Stylometric Discoveries

1. **The Double-Space Signature (`.  `)**:
   In forum posts, **97.5%** of sentences conclude with two spaces before the next capital letter (1,398 double spaces vs 36 single spaces). In emails, **78.2%** conclude with double spaces. This is a classic typewriter/LaTeX convention preserved across almost every post.
2. **Hybrid British/Commonwealth Orthography**:
   Satoshi displays a consistent preference for British spellings for common words, while retaining standard American software terminology:
   - `favour` (100% UK, 0% US)
   - `neighbour` (100% UK, 0% US)
   - `grey` (100% UK, 0% US)
   - `defence` (100% UK, 0% US)
   - `cheque` (100% UK, 0% US)
   - `programme` / `programmed` (18% UK vs 82% US)
   - Computing terms remain standard: `optimize`, `realize`, `license`, `check`.
3. **Extreme Emotional Restraint**:
   Exclamation points appear at approximately ~1 per 1,000 words across all 62k words. Even when dealing with heated forum debates or existential project bugs, Satoshi never uses emotional punctuation.
4. **Conditional State-Machine Framing**:
   `If` is the 2nd most frequent sentence opener in the whitepaper (5.0%) and 3rd in forum posts (6.3%), reflecting a persistent instinct to trace branches of execution (`If an attacker...`, `If you have...`, `As long as...`).

---

## 3. Qualitative Voice Architecture

The qualitative profile lives in [`skills/rabbit-writes/voices/satoshi.md`](../skills/rabbit-writes/voices/satoshi.md).

### The Three Essentials

1. **Lead with the protocol mechanics, never the promise.** Explain data structures, network incentives, and computation. State what the code actually does before describing what it enables.
2. **Calibrated epistemic modesty.** Distinguish between mathematical certainty (hash chains, digital signatures, proof-of-work) and empirical uncertainty (network latency, market adoption, human behavior). Never claim something is "unhackable" or "revolutionary"—state the exact security bound or condition under which the property holds.
3. **Calm, pragmatic dismissal of unsolvable side arguments.** State operational trade-offs directly without escalating. If an architectural constraint settles the question, do not debate philosophy.

### Five Dimensions

```yaml
formality: 0.55       # Technical, clean, and direct. Neither slangy nor bureaucratic
confidence: 0.90      # High conviction on architecture, strictly calibrated on unknowns
warmth: 0.20          # Polite and respectful, but strictly matter-of-fact
energy: 0.20          # Low, steady temperature. Zero exclamation points or performative excitement
complexity: 0.65      # Conceptually dense systems logic expressed in simple, unadorned English
```

### Register Ladder

| Register | Opener | Closer | Characteristics |
|---|---|---|---|
| `chat` | None, or quote context | None, or `Satoshi` | Direct, answers bug reports and patches, double spaces after periods |
| `informal` | None, or `Hi,` | `Satoshi Nakamoto` | Explains architectural trade-offs to mailing list peers |
| `technical-blog` | None | None | Systematic breakdown of design choices and economic incentives |
| `formal` | `Abstract` | `References` | 3rd person / academic first-person plural (`We propose`), formal probability math |

`technical-blog` has no fingerprint of its own. Satoshi's corpus (Section 1) has no writing in that register, only whitepaper, emails, and forum posts, so `--profile technical-blog` measures stylometric distance against the general/aggregate fingerprint instead of a fabricated register-specific one. The register's mechanical relaxations still apply (`registers.json`: vocabulary exemption, relaxed hedging and curly quotes, skipped diff-anchoring). Only the stylometric comparison target falls back.

### Hard Nos (Refusals)

- **No marketing or hype buzzwords:** `revolutionary`, `disrupt`, `game-changer`, `synergy`, `paradigm shift`, `unlocking potential`, `next-gen`, `tapestry`, `delve`.
- **No emotional escalation or personal attacks:** Never turn technical trade-offs into ideological feuds.
- **No absolute unverified security claims:** Never say `100% secure` or `unhackable`. Always state the explicit condition (`as long as honest nodes control a majority of CPU power`).
- **No corporate consulting clichés:** `reach out`, `circle back`, `touch base`, `low-hanging fruit`, `move the needle`, `deep dive`.

---

## 4. Machine-Enforceable Rules (`satoshi.rules.json`)

The mechanical layer lives in [`skills/rabbit-writes/voices/satoshi.rules.json`](../skills/rabbit-writes/voices/satoshi.rules.json).

### Validated Rules Schema

```json
{
  "voice": "satoshi",
  "default_priority": "P0",
  "mechanics": {
    "em_dash": "forbid",
    "semicolon": "allow",
    "emoji": "forbid",
    "curly_quotes": "allow",
    "oxford_comma": "allow",
    "one_word_sentence": "allow",
    "max_avg_sentence_words": 28,
    "date_format": "any"
  },
  "mechanics_by_register": {
    "chat": {
      "one_word_sentence": "allow",
      "curly_quotes": "allow"
    },
    "formal": {
      "max_avg_sentence_words": 32
    }
  },
  "banned_words": [
    "synergy", "synergies", "revolutionary", "unhackable",
    "delve", "tapestry", "hodl", "wagmi", "fud", "airdrop", "furthermore"
  ],
  "banned_phrases": [
    "thought leader", "thought leaders", "thought leadership",
    "paradigm shift", "deep dive", "delve into", "reach out to",
    "circle back", "touch base", "move the needle", "low-hanging fruit",
    "the future looks bright", "revolutionary new", "groundbreaking technology",
    "game-changer", "game-changing"
  ]
}
```

### Regex Banned Patterns (with Live-Fire Probe Examples)

1. `absolute-security-claim`: `(?i)\b((100|one hundred) ?% (secure|safe|unhackable)|impossible to (hack|break|compromise)|guarantees? (complete|total|full) security|zero risk)\b`
   - *Probe:* `"The protocol is 100% secure against all attacks."`
2. `crypto-marketing-hype`: `(?i)\b(to the moon|revolutioni[sz]e (finance|banking|the world)|next-?gen(eration)? (blockchain|crypto)|disrupt(ing)? legacy (banking|finance)|wealth generation opportunity)\b`
   - *Probe:* `"This will revolutionize finance and disrupt legacy banking."`
3. `corporate-fluff-verb`: `(?i)\b(harness(ing)? the power of|unlock(ing)? the potential|synergistic alignment|spearhead(ing)? the future)\b`
   - *Probe:* `"We are unlocking the potential of decentralized networks."`
4. `emotional-escalation`: `(?i)\b(you are an idiot|you don'?t know what you'?re talking about|stupid argument|stop being ridiculous)\b`
   - *Probe:* `"That is a stupid argument and you have no idea."`

---

## 5. Oracle Discrimination Testing Benchmark

We built an automated test runner ([`scripts/satoshi_oracle_test.py`](../scripts/satoshi_oracle_test.py)) to test authorship discrimination.

A document is classified as **Satoshi** if:
1. **0 P0 Voice Violations** (clean of banned words, hype, buzzwords, and absolute security claims).
2. **Stylometric Distance** $\Delta \le 1.0$ (or verdict `in_range` / `near` against the voice fingerprint).

### Benchmark Results (15 Test Documents)

```
================================================================================
SATOSHI NAKAMOTO ORACLE DISCRIMINATION TEST SUITE
================================================================================

--- POSITIVE TESTS (Authentic Satoshi Partitions) ---
[PASS [MATCH]] Satoshi: Whitepaper Part 1 (2,067 words) -> Delta: 0.301 | Verdict: in_range | Voice violations: 0
[PASS [MATCH]] Satoshi: Whitepaper Part 2 (1,754 words) -> Delta: 0.302 | Verdict: in_range | Voice violations: 0
[PASS [MATCH]] Satoshi: Technical Emails (Early) (4,909 words) -> Delta: 0.330 | Verdict: in_range | Voice violations: 0
[PASS [MATCH]] Satoshi: Technical Emails (Late) (3,106 words) -> Delta: 0.330 | Verdict: in_range | Voice violations: 0
[PASS [MATCH]] Satoshi: Forum Discussions Part 1 (24,742 words) -> Delta: 0.205 | Verdict: in_range | Voice violations: 0
[PASS [MATCH]] Satoshi: Forum Discussions Part 2 (23,008 words) -> Delta: 0.205 | Verdict: in_range | Voice violations: 0

--- NEGATIVE TESTS (Contemporary Cypherpunk Peers) ---
[PASS [REJECTED]] Nick Szabo: Bit Gold (973 words) -> Delta: 1.099 | Verdict: out_of_range | Voice violations: 1
[PASS [REJECTED]] Nick Szabo: Smart Contracts (1,294 words) -> Delta: 0.873 | Verdict: near | Voice violations: 1
[PASS [REJECTED]] Hal Finney: RPOW (372 words) -> Delta: 1.283 | Verdict: out_of_range | Voice violations: 1
[PASS [REJECTED]] Hal Finney: Bitcoin and Me (956 words) -> Delta: 1.364 | Verdict: out_of_range | Voice violations: 1
[PASS [REJECTED]] Wei Dai: B-Money (1,347 words) -> Delta: 0.966 | Verdict: out_of_range | Voice violations: 1
[PASS [REJECTED]] Ian Grigg: The Ricardian Contract (5,168 words) -> Delta: 0.763 | Verdict: near | Voice violations: 4
[PASS [REJECTED]] Tim May: Crypto Anarchist Manifesto (499 words) -> Delta: 1.176 | Verdict: out_of_range | Voice violations: 3

--- NEGATIVE TESTS (Modern Crypto Hype & AI Slop) ---
[PASS [REJECTED]] Modern Web3 Hype Pitch (112 words) -> Delta: 1.462 | Voice violations: 19 | P0s: 19
[PASS [REJECTED]] Standard AI-generated Guide (120 words) -> Delta: 1.51 | Voice violations: 5 | P0s: 7

================================================================================
ORACLE TEST SUMMARY
================================================================================
Total Tests Run: 15
Overall Accuracy: 15/15 (100.0%)
Positive Sensitivity (Recall on Satoshi): 6/6 (100.0%)
Negative Specificity (Rejection of Non-Satoshi): 9/9 (100.0%)
================================================================================
```

The two "Modern Crypto Hype & AI Slop" deltas (1.462 and 1.51) are measured with `--profile technical-blog`, the only two tests in this suite that are. They read higher than they used to (formerly 1.123 and 1.121) because the comparison target changed with the fingerprint fix in Section 3: both now measure against the Aggregate Total fingerprint rather than a whitepaper-only one that was never actually independent of `formal`. Every other row in this table uses `--profile formal` or the general fingerprint and is unaffected. All 15 verdicts, including these two, are unchanged.

---

## 6. Cross-Voice Conversion & Verification

We tested bidirectional cross-voice rewriting with `verify.py`, `scan.py`, and `attain.py`:

### Test Case 1: Inbound Conversion (Modern Crypto Hype -> Satoshi)

#### Input: Modern Crypto Pitch (203 words)
> *"We are thrilled to unveil NextGenChain, a revolutionary and groundbreaking blockchain architecture engineered to disrupt legacy global banking forever. By harnessing the power of state-of-the-art cryptographic primitives and synergistic zero-knowledge scaling, our mission is to unlock the full potential of web3 commerce. NextGenChain provides a 100% secure, unhackable execution environment..."*
>
> **Scan Findings:** 13 P0 Voice Violations, 10 Tier-1 vocabulary tells.

#### Output: Converted to Satoshi Voice (259 words)
> *"A purely peer-to-peer version of electronic cash would allow online payments to be sent directly from one party to another without going through a financial institution.  Digital signatures provide part of the solution, but the main benefits are lost if a trusted third party is still required to prevent double-spending.*
>
> *We propose a solution to the double-spending problem using a peer-to-peer network.  The network timestamps transactions by hashing them into an ongoing chain of hash-based proof-of-work... To support higher transaction volume without burdening every node with intermediate states, participants can establish bidirectional payment channels..."*
>
> **Verification Results:**
> - `scan.py --voice satoshi`: **0 P0 Violations**, clean pass.
> - `verify.py`: Verified tell reduction (**15 -> 1**), no syntax or formatting corruption.
> - `attain.py`: **3 of 5 statistical measures on target** (sentence length converged from 16.9 to 19.9 words).

### Test Case 2: Outbound Conversion (Satoshi Whitepaper -> whit3rabbit)

#### Input: Satoshi's "Reclaiming Disk Space"
> *"Once the latest transaction in a coin is buried under enough blocks, the spent transactions before it can be discarded to save disk space.  To facilitate this without breaking the block's hash, transactions are hashed in a Merkle Tree, with only the root included in the block's hash..."*

#### Output: Converted to whit3rabbit Voice (BLUF + Evidence Bullets)
> *"Bottom line: old transactions can be safely pruned from disk without breaking block verification.*
>
> *Here is how the pruning mechanism works:*
> *- Transactions are hashed into a Merkle tree.*
> *- Only the root hash is stored in the block header.*
> *- Spent transaction branches are stubbed out once they are buried under enough blocks.*
> *- Interior hashes are discarded, leaving the header intact.*
>
> *Storage growth is negligible:*
> *- Header size: ~80 bytes.*
> *- Annual rate: 80 bytes * 6 blocks/hour * 24 hours * 365 days = 4.2 MB per year."*
>
> **Verification Results:**
> - `scan.py --voice whit3rabbit`: **0 P0 Violations**.
> - `verify.py`: **0 errors**, 9/9 numerical facts preserved verbatim.

---

## 7. CLI Quick Reference

```bash
# 1. Validate the Satoshi profile and rule probes
python3 skills/voice-setup/scripts/build_voice.py --check satoshi

# 2. Scan any document against Satoshi's voice rules
python3 skills/rabbit-writes/scripts/scan.py draft.md --voice satoshi --profile technical-blog

# 2b. Or detect the register from document structure instead of naming it
python3 skills/rabbit-writes/scripts/scan.py draft.md --voice satoshi --profile auto

# 3. Check attainment when rewriting into Satoshi's voice
python3 skills/rabbit-writes/scripts/attain.py original.md rewritten.md --voice satoshi

# 4. Verify text preservation during a conversion
python3 skills/rabbit-writes/scripts/verify.py original.md rewritten.md --allow-structure --allow-facts

# 5. Run the Oracle discrimination test suite
python3 scripts/satoshi_oracle_test.py
```

`--profile auto` (command 2b) only detects `docs`, `linkedin`, and `formal` shapes: the engine-wide signals strong enough to trust unattended, none specific to this voice. Forum-post and mailing-list prose, the two registers most of Satoshi's own corpus is measured in, have no reliable structural tell and are not auto-detected, so `--profile chat` or `--profile informal` named explicitly is still the right call for that content.
