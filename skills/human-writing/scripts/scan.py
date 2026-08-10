#!/usr/bin/env python3
"""
scan.py - the mechanical layer of the human-writing skill.

Finds what a regex and a counter find better than a reader does: copy-paste
fingerprints, tiered vocabulary density, and stylometric uniformity. Everything
requiring judgment lives in references/patterns.md and stays out of here.

This reports signals. It does not classify authorship, and it deliberately does
not emit a single "AI score" for the document. Detector audits report false
positive rates above 60% on non-native English writers (Liang et al., Stanford,
Patterns 2023). A number invites a verdict; a list of named findings invites a
check.

Findings come back in three bands:

    voice        this writer's own rules, from --voice-rules. A hit is a defect.
    fingerprint  evidence the text came out of a chat tool.
    craft        general writing problems, never evidence about authorship.

Usage:
    python3 scan.py draft.md
    python3 scan.py draft.md --json
    python3 scan.py draft.md --profile technical-blog
    python3 scan.py draft.md --voice-rules ../../rabbit-writes/voices/whit3rabbit.rules.json
    python3 scan.py --profile casual < input.txt
    python3 scan.py draft.md --no-exempt      # score quoted examples too

A register profile relaxes the general rules. It never relaxes a voice rule:
lowercase and loose punctuation are fine off the clock, a banned phrase is not.

Exit codes: 0 always, unless --check is passed, in which case any P0 finding
exits 1. Stdlib only; runs on Python 3.8+.
"""

import argparse
import json
import math
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
LEXICON_PATH = os.path.join(HERE, "lexicon.json")

# Registers and the categories they suppress. Mirrors the tolerance matrix in
# references/context.md. P0 fingerprints are never suppressed anywhere.
PROFILE_SKIP = {
    "linkedin": {"transition-stack", "generic-conclusion", "tier3-density",
                 "uniform-paragraphs", "em-dash-rate", "curly-quote"},
    "blog": {"curly-quote"},
    "technical-blog": {"curly-quote", "hedge-stack", "diff-anchored"},
    "investor-email": {"curly-quote"},
    "docs": {"transition-stack", "curly-quote", "uniform-paragraphs",
             "rhetorical-question", "diff-anchored", "list-label-period"},
    "casual": {"transition-stack", "generic-conclusion", "curly-quote",
               "em-dash-rate", "uniform-paragraphs", "tier3-density",
               "tier2-cluster", "confidence-calibration", "signposting"},
}

# Human reference ranges. Sources: Copyleaks stylometric work (arXiv 2503.01659),
# classical type-token-ratio literature, and the ranges published by
# brandonwise/humanizer. Directional, not diagnostic.
BANDS = {
    "burstiness": (0.45, 1.10),   # sd/mean of sentence length
    "mattr": (0.62, 0.85),        # moving-average TTR, window 100
    "ttr": (0.40, 0.75),          # raw type-token ratio, length-sensitive
    "trigram_repetition": (0.0, 0.06),
    "em_dashes_per_1k": (0.0, 6.0),
}

RELIABILITY_TIERS = [
    (600, "high"),
    (250, "medium"),
    (120, "low"),
]

FENCE_RX = re.compile(r"^```.*?^```", re.M | re.S)
INLINE_CODE_RX = re.compile(r"`[^`\n]+`")
FRONTMATTER_RX = re.compile(r"\A---\n.*?\n---\n", re.S)
TABLE_RX = re.compile(r"(?m)^\s*\|.*\|\s*$")
BLOCKQUOTE_RX = re.compile(r"(?m)^\s*>.*$")
URL_RX = re.compile(r"https?://\S+")
QUOTED_RX = re.compile(r"[\"“][^\"”\n]{4,200}[\"”]")

HIDDEN_UNICODE = {
    "​": "zero-width space",
    "‌": "zero-width non-joiner",
    "‍": "zero-width joiner",
    "⁠": "word joiner",
    "﻿": "byte-order mark",
    "­": "soft hyphen",
    " ": "non-breaking space",
    " ": "narrow no-break space",
}

ABBREV_RX = re.compile(
    r"\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|etc|vs|approx|dept|est|vol|Inc|Ltd|Fig|No)\.",
    re.I,
)


# --------------------------------------------------------------------------
# text preparation
# --------------------------------------------------------------------------

def blank(match):
    """Replace a span with same-length whitespace so offsets stay stable."""
    return re.sub(r"\S", " ", match.group(0))


def apply_exemptions(text):
    """Blank out the spans this skill promises never to rewrite, so a document
    that quotes AI patterns in order to warn about them does not score as one.
    Same escape hatch stated in SKILL.md, made executable."""
    out = FRONTMATTER_RX.sub(blank, text)
    out = FENCE_RX.sub(blank, out)
    out = INLINE_CODE_RX.sub(blank, out)
    out = TABLE_RX.sub(blank, out)
    out = BLOCKQUOTE_RX.sub(blank, out)
    out = QUOTED_RX.sub(blank, out)
    return out


def strip_for_stats(text):
    """Remove code and markup noise before measuring prose statistics.

    Tables are dropped as well as code: a comparison table legitimately repeats
    the same cell values, and counting those repeats as trigram repetition or
    the cell separators as prose rhythm would measure the markup, not the
    writing."""
    out = FRONTMATTER_RX.sub("", text)
    out = FENCE_RX.sub("", out)
    out = INLINE_CODE_RX.sub("", out)
    out = TABLE_RX.sub("", out)
    out = URL_RX.sub("", out)
    out = re.sub(r"(?m)^#{1,6}\s+", "", out)
    out = re.sub(r"[*_`>]", "", out)
    return out


def split_sentences(text):
    protected = ABBREV_RX.sub(lambda m: m.group(0).replace(".", "․"), text)
    protected = re.sub(r"\b([A-Z])\.", r"\1․", protected)
    protected = re.sub(r"(?m)^\s*(\d+)\.", r"\1․", protected)
    parts = re.split(r"(?<=[.!?])[\s\n]+", protected)
    return [p.replace("․", ".").strip() for p in parts if p.strip()]


def tokenize(text):
    return re.findall(r"[A-Za-z][A-Za-z'\-]*", text.lower())


def syllables(word):
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    groups = re.findall(r"[aeiouy]+", word)
    n = len(groups)
    if word.endswith("e") and n > 1 and not word.endswith(("le", "ee", "ye")):
        n -= 1
    return max(n, 1)


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------

def moving_ttr(words, window=100):
    if len(words) < window:
        return None
    ratios = []
    for i in range(len(words) - window + 1):
        chunk = words[i:i + window]
        ratios.append(len(set(chunk)) / window)
    return sum(ratios) / len(ratios)


def compute_stats(raw_text):
    prose = strip_for_stats(raw_text)
    words = tokenize(prose)
    sentences = split_sentences(prose)
    paragraphs = [p for p in re.split(r"\n\s*\n", prose) if p.strip()]

    stats = {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
    }
    if not words or not sentences:
        return stats

    lengths = [len(tokenize(s)) for s in sentences]
    lengths = [n for n in lengths if n > 0]
    mean = sum(lengths) / len(lengths) if lengths else 0.0
    if len(lengths) > 1:
        var = sum((n - mean) ** 2 for n in lengths) / (len(lengths) - 1)
        sd = math.sqrt(var)
    else:
        sd = 0.0

    stats["avg_sentence_words"] = round(mean, 1)
    stats["sentence_sd"] = round(sd, 1)
    stats["burstiness"] = round(sd / mean, 3) if mean else 0.0
    stats["longest_sentence"] = max(lengths) if lengths else 0
    stats["shortest_sentence"] = min(lengths) if lengths else 0

    stats["ttr"] = round(len(set(words)) / len(words), 3)
    mattr = moving_ttr(words)
    stats["mattr"] = round(mattr, 3) if mattr is not None else None

    trigrams = [tuple(words[i:i + 3]) for i in range(len(words) - 2)]
    if trigrams:
        counts = Counter(trigrams)
        repeated = sum(c - 1 for c in counts.values() if c > 1)
        stats["trigram_repetition"] = round(repeated / len(trigrams), 4)
    else:
        stats["trigram_repetition"] = 0.0

    em = prose.count("—") + prose.count("–")
    stats["em_dashes"] = em
    stats["em_dashes_per_1k"] = round(em / len(words) * 1000, 2)

    if paragraphs:
        plens = [len(split_sentences(p)) for p in paragraphs]
        pmean = sum(plens) / len(plens)
        if len(plens) > 1:
            psd = math.sqrt(sum((n - pmean) ** 2 for n in plens) / (len(plens) - 1))
        else:
            psd = 0.0
        stats["avg_paragraph_sentences"] = round(pmean, 1)
        stats["paragraph_sd"] = round(psd, 2)

    syl = sum(syllables(w) for w in words)
    stats["flesch_kincaid_grade"] = round(
        0.39 * (len(words) / len(sentences)) + 11.8 * (syl / len(words)) - 15.59, 1
    )
    return stats


def reliability(word_count):
    for threshold, label in RELIABILITY_TIERS:
        if word_count >= threshold:
            return label
    return "insufficient"


# --------------------------------------------------------------------------
# findings
# --------------------------------------------------------------------------

def line_of(text, index):
    return text.count("\n", 0, index) + 1


def excerpt(text, start, end, pad=34):
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)
    frag = text[lo:hi].replace("\n", " ")
    return re.sub(r"\s+", " ", frag).strip()


def word_regex(entries):
    escaped = sorted((re.escape(e) for e in entries), key=len, reverse=True)
    return re.compile(r"(?i)(?<![\w-])(" + "|".join(escaped) + r")(?![\w-])")


def phrase_regex(entries):
    escaped = sorted((re.escape(e).replace(r"\ ", r"\s+") for e in entries),
                     key=len, reverse=True)
    return re.compile(r"(?i)\b(" + "|".join(escaped) + r")\b")


def find(text, rx, pattern_id, label, band, priority, findings):
    for m in rx.finditer(text):
        if not m.group(0).strip():
            continue
        findings.append({
            "id": pattern_id,
            "label": label,
            "band": band,
            "priority": priority,
            "line": line_of(text, m.start()),
            "match": m.group(0).strip()[:80],
            "excerpt": excerpt(text, m.start(), m.end()),
        })


EMOJI_RX = re.compile(
    "[" "\U0001F300-\U0001FAFF" "☀-➿" "\U0001F900-\U0001F9FF"
    "⬀-⯿" "️" "]")
ONE_WORD_SENTENCE_RX = re.compile(r"(?m)(?:^|(?<=[.!?]\s))([A-Z][a-z']{1,14})\.(?=\s|$)")
US_DATE_RX = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},?\s+\d{4}\b")
DMY_DATE_RX = re.compile(
    r"\b\d{1,2}\s+(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4}\b")
ISO_DATE_RX = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


LIST_ITEM_RX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
LIST_DASH_RX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\)|`[^`]+`)\s*[—–]\s")


def in_list_typography(text, index):
    """True when this dash separates a bolded lead term in a list item
    (`- **Term** — description`). That is typography, not a prose splice, and
    the general em-dash rule already carves it out. A voice ban should agree.

    Checked against the raw text rather than the exemption-blanked copy, so a
    list item leading with an inline-code term still reads as a list item.
    Blanking preserves length, so the offsets line up."""
    start = text.rfind("\n", 0, index) + 1
    return bool(LIST_DASH_RX.match(text[start:index + 2]))


def is_prose_block(block):
    """A markdown list, table, heading, or fence is not a paragraph. Counting
    its items as sentences turns a 12-item list into a 'paragraph of 12
    sentences', which is noise rather than a finding."""
    lines = [ln for ln in block.strip().split("\n") if ln.strip()]
    if not lines:
        return False
    first = lines[0].lstrip()
    if first.startswith(("#", ">", "|", "```", "    ")):
        return False
    listish = sum(1 for ln in lines if LIST_ITEM_RX.match(ln))
    return listish * 2 < len(lines)


def voice_finding(rules_id, label, priority, line, match, excerpt_text):
    return {
        "id": rules_id,
        "label": label,
        "band": "voice",
        "priority": priority,
        "line": line,
        "match": match,
        "excerpt": excerpt_text,
    }


def apply_voice_rules(scored, raw_text, rules, stats, findings):
    """Enforce one writer's own rules. These sit above the register profile:
    a register can relax a general rule, never a voice rule."""
    default = rules.get("default_priority", "P0")
    mech = rules.get("mechanics", {})
    subs = rules.get("preferred_substitutions", {})

    def fix_hint(term):
        key = term.lower().strip()
        return "use %s" % subs[key] if key in subs else "cut it or say the specific thing"

    # Punctuation and formatting mechanics.
    if mech.get("em_dash") == "forbid":
        for m in re.finditer(r"[—–]", scored):
            if in_list_typography(raw_text, m.start()):
                continue
            findings.append(voice_finding(
                "voice-em-dash", "Em dash (voice forbids)", default,
                line_of(scored, m.start()), m.group(0),
                excerpt(scored, m.start(), m.end())))
    elif mech.get("em_dash") == "limit":
        cap = float(mech.get("max_em_dashes_per_1000w", 2))
        rate = stats.get("em_dashes_per_1k", 0)
        if rate > cap:
            findings.append(voice_finding(
                "voice-em-dash-rate", "Em-dash rate %.1f/1k over voice cap %.1f"
                % (rate, cap), default, 1, "%d dashes" % stats.get("em_dashes", 0),
                "This writer uses em dashes, but not this many."))

    if mech.get("semicolon") == "forbid":
        for m in re.finditer(r";", scored):
            findings.append(voice_finding(
                "voice-semicolon", "Semicolon (voice forbids)", default,
                line_of(scored, m.start()), ";",
                excerpt(scored, m.start(), m.end())))

    if mech.get("emoji") == "forbid":
        for m in EMOJI_RX.finditer(scored):
            findings.append(voice_finding(
                "voice-emoji", "Emoji (voice forbids)", default,
                line_of(scored, m.start()), m.group(0),
                excerpt(scored, m.start(), m.end())))

    if mech.get("curly_quotes") == "forbid":
        for m in re.finditer(r"[“”‘’]", scored):
            findings.append(voice_finding(
                "voice-curly-quote", "Curly quote (voice forbids)", "P2",
                line_of(scored, m.start()), m.group(0),
                excerpt(scored, m.start(), m.end())))

    if mech.get("one_word_sentence") == "forbid":
        for m in ONE_WORD_SENTENCE_RX.finditer(scored):
            findings.append(voice_finding(
                "voice-one-word-sentence",
                "One-word sentence for emphasis (voice forbids)", default,
                line_of(scored, m.start()), m.group(0),
                "Reads harsh. Fold it into the sentence that follows."))

    fmt = mech.get("date_format", "any")
    if fmt == "dmy":
        for m in US_DATE_RX.finditer(scored):
            findings.append(voice_finding(
                "voice-date-format", "US date format (voice wants day-month-year)",
                default, line_of(scored, m.start()), m.group(0),
                "Write it as 12 September 2025."))
    elif fmt == "mdy":
        for m in DMY_DATE_RX.finditer(scored):
            findings.append(voice_finding(
                "voice-date-format", "Day-month-year (voice wants month-day-year)",
                default, line_of(scored, m.start()), m.group(0), ""))
    elif fmt == "iso":
        for m in list(US_DATE_RX.finditer(scored)) + list(DMY_DATE_RX.finditer(scored)):
            findings.append(voice_finding(
                "voice-date-format", "Spelled date (voice wants ISO)", default,
                line_of(scored, m.start()), m.group(0), "Write it as 2025-09-12."))

    cap = mech.get("max_paragraph_sentences")
    if cap:
        offset = 0
        for para in re.split(r"(\n\s*\n)", scored):
            body = para.strip()
            if body and is_prose_block(body):
                n = len(split_sentences(body))
                if n > int(cap):
                    findings.append(voice_finding(
                        "voice-paragraph-length",
                        "Paragraph of %d sentences (voice cap %s)" % (n, cap),
                        default, line_of(scored, offset), "%d sentences" % n,
                        "Break it. Dense blocks read as machine output."))
            offset += len(para)

    cap = mech.get("max_avg_sentence_words")
    if cap and stats.get("avg_sentence_words", 0) > float(cap):
        findings.append(voice_finding(
            "voice-sentence-length",
            "Average sentence %.1f words (voice cap %s)"
            % (stats["avg_sentence_words"], cap), default, 1,
            "avg sentence length", "This writer writes shorter than this."))

    # Word and phrase bans.
    if rules.get("banned_words"):
        for m in word_regex(rules["banned_words"]).finditer(scored):
            findings.append(voice_finding(
                "voice-banned-word", "Banned word", default,
                line_of(scored, m.start()), m.group(0),
                fix_hint(m.group(0))))

    if rules.get("banned_phrases"):
        for m in phrase_regex(rules["banned_phrases"]).finditer(scored):
            findings.append(voice_finding(
                "voice-banned-phrase", "Banned phrase", default,
                line_of(scored, m.start()), m.group(0),
                fix_hint(m.group(0))))

    # Custom regexes, including overuse rules that allow N hits before flagging.
    for entry in rules.get("banned_regex", []):
        try:
            rx = re.compile(entry["rx"])
        except (re.error, KeyError) as exc:
            print("voice-rules: bad entry %s (%s)" % (entry.get("id"), exc),
                  file=sys.stderr)
            continue
        hits = [m for m in rx.finditer(scored) if m.group(0).strip()]
        allowed = int(entry.get("max_allowed", 0))
        if len(hits) <= allowed:
            continue
        note = entry.get("note", "")
        for m in hits[allowed:]:
            label = entry.get("label", entry["id"])
            if allowed:
                label = "%s (%d uses, cap %d)" % (label, len(hits), allowed)
            findings.append(voice_finding(
                entry["id"], label, entry.get("priority", default),
                line_of(scored, m.start()), m.group(0).strip()[:60],
                note or excerpt(scored, m.start(), m.end())))

    # Presence checks. Advisory by design: a fragment has no sign-off.
    # `when_rx` gates the check so it only runs on text of the right shape.
    # Without a gate, "missing closer" fires on every document that is not a
    # letter, which is most of them.
    for entry in rules.get("required_when", []):
        registers = entry.get("applies_to_registers")
        if registers and stats.get("_profile") not in registers:
            continue
        gate = entry.get("when_rx")
        if gate and not re.search(gate, scored):
            continue
        found = any(re.search(rx, scored) for rx in entry.get("any_of_rx", []))
        if not found:
            findings.append(voice_finding(
                entry["id"], entry.get("label", entry["id"]),
                entry.get("priority", "P2"), 1, "not found",
                entry.get("note", "")))


def scan(raw_text, profile="blog", exempt=True, voice_rules=None):
    lex = json.load(open(LEXICON_PATH, encoding="utf-8"))
    scored = apply_exemptions(raw_text) if exempt else raw_text
    skip = PROFILE_SKIP.get(profile, set())
    findings = []
    stats = compute_stats(raw_text)
    stats["_profile"] = profile

    # 1. Hidden unicode. Checked on the raw text; exemptions do not apply,
    #    because a zero-width space inside a code fence is still a paste artifact.
    for ch, name in HIDDEN_UNICODE.items():
        n = raw_text.count(ch)
        if n:
            findings.append({
                "id": "hidden-unicode",
                "label": "Hidden unicode: %s" % name,
                "band": "fingerprint",
                "priority": "P0",
                "line": line_of(raw_text, raw_text.index(ch)),
                "match": "U+%04X x%d" % (ord(ch), n),
                "excerpt": "%d occurrence(s) of %s" % (n, name),
            })

    # 2. Catalog regexes.
    for p in lex["patterns"]:
        if p["id"] in skip:
            continue
        try:
            rx = re.compile(p["rx"])
        except re.error as exc:
            print("lexicon: bad regex %s (%s)" % (p["id"], exc), file=sys.stderr)
            continue
        find(scored, rx, p["id"], p["label"], p["band"], p["priority"], findings)

    # 3. Vocabulary, tiered. Tier 1 always flags. Clarity edits are reported in
    #    their own band and never counted toward the AI-vocabulary signal, so a
    #    wordiness fix can never look like authorship evidence.
    technical = profile == "technical-blog"
    exempt_words = set(w.lower() for w in lex["technical_exempt"]) if technical else set()

    t1 = [w for w in lex["tier1"] if w.lower() not in exempt_words]
    find(scored, word_regex(t1), "tier1", "Tier-1 vocabulary",
         "fingerprint", "P1", findings)
    find(scored, phrase_regex(lex["tier1_phrases"]), "tier1", "Tier-1 phrase",
         "fingerprint", "P1", findings)

    find(scored, word_regex(lex["clarity"]), "clarity", "Wordiness",
         "craft", "P1", findings)
    find(scored, phrase_regex(lex["clarity_phrases"]), "clarity", "Wordiness",
         "craft", "P1", findings)

    # Tier 2 fires only when two or more land in the same paragraph.
    if "tier2-cluster" not in skip:
        t2 = [w for w in lex["tier2"] if w.lower() not in exempt_words]
        t2rx = word_regex(t2)
        offset = 0
        for para in re.split(r"(\n\s*\n)", scored):
            hits = [m for m in t2rx.finditer(para)]
            if len(hits) >= 2:
                findings.append({
                    "id": "tier2-cluster",
                    "label": "Tier-2 cluster (%d in one paragraph)" % len(hits),
                    "band": "craft",
                    "priority": "P1",
                    "line": line_of(scored, offset),
                    "match": ", ".join(sorted({h.group(0).lower() for h in hits})),
                    "excerpt": excerpt(para, hits[0].start(), hits[-1].end()),
                })
            offset += len(para)

    # Tier 3 fires only at density.
    wc = stats.get("word_count", 0)
    if "tier3-density" not in skip and wc >= 120:
        t3 = [w for w in lex["tier3"] if w.lower() not in exempt_words]
        hits = list(word_regex(t3).finditer(scored))
        density = len(hits) / wc
        if density >= 0.02:
            findings.append({
                "id": "tier3-density",
                "label": "Tier-3 saturation (%.1f%% of words)" % (density * 100),
                "band": "craft",
                "priority": "P2",
                "line": line_of(scored, hits[0].start()) if hits else 1,
                "match": ", ".join(sorted({h.group(0).lower() for h in hits})[:12]),
                "excerpt": "Replace some with specifics: numbers, comparisons, examples.",
            })

    # 4. Stylometric flags.
    if wc >= 120:
        b = stats.get("burstiness", 0)
        if "uniformity" not in skip and b < BANDS["burstiness"][0]:
            findings.append({
                "id": "uniformity",
                "label": "Low burstiness (%.2f, human range %.2f-%.2f)"
                         % (b, *BANDS["burstiness"]),
                "band": "craft",
                "priority": "P1",
                "line": 1,
                "match": "sd/mean of sentence length",
                "excerpt": "Sentence lengths are too even. Mix 3-8 word sentences "
                           "with 20+ word ones. Vary the sentences, not the punctuation.",
            })
        m = stats.get("mattr")
        if m is not None and m < BANDS["mattr"][0]:
            findings.append({
                "id": "low-diversity",
                "label": "Low vocabulary diversity (MATTR %.2f, human range %.2f-%.2f)"
                         % (m, *BANDS["mattr"]),
                "band": "craft",
                "priority": "P2",
                "line": 1,
                "match": "moving-average type-token ratio",
                "excerpt": "Broaden the what, not the thesaurus: name specific things, "
                           "cite specific cases, replace a reused abstract noun with the instance.",
            })
        tr = stats.get("trigram_repetition", 0)
        if tr > BANDS["trigram_repetition"][1]:
            findings.append({
                "id": "trigram-repetition",
                "label": "Repeated 3-word phrases (%.1f%%)" % (tr * 100),
                "band": "craft",
                "priority": "P2",
                "line": 1,
                "match": "trigram repetition",
                "excerpt": "The draft reuses the same phrasings. Rewrite the repeats or cut them.",
            })
        psd = stats.get("paragraph_sd")
        if ("uniform-paragraphs" not in skip and psd is not None
                and psd < 0.75 and stats.get("paragraph_count", 0) >= 5):
            findings.append({
                "id": "uniform-paragraphs",
                "label": "Uniform paragraph length (sd %.2f sentences)" % psd,
                "band": "craft",
                "priority": "P2",
                "line": 1,
                "match": "paragraph length",
                "excerpt": "Every paragraph is about the same size. Some should be one sentence.",
            })

    if "em-dash-rate" not in skip:
        rate = stats.get("em_dashes_per_1k", 0)
        if rate > BANDS["em_dashes_per_1k"][1] and stats.get("em_dashes", 0) > 1:
            findings.append({
                "id": "em-dash-rate",
                "label": "Em-dash rate %.1f per 1,000 words" % rate,
                "band": "craft",
                "priority": "P1",
                "line": 1,
                "match": "%d em/en dashes" % stats.get("em_dashes", 0),
                "excerpt": "Guidance, not a ban. A user's writing sample overrides this. "
                           "Never add one during a rewrite.",
            })

    # Voice rules run last and are never suppressed by the register profile.
    if voice_rules:
        apply_voice_rules(scored, raw_text, voice_rules, stats, findings)

    stats.pop("_profile", None)
    band_order = {"voice": 0, "fingerprint": 1, "craft": 2}
    findings.sort(key=lambda f: ({"P0": 0, "P1": 1, "P2": 2}[f["priority"]],
                                 band_order.get(f["band"], 3), f["line"]))
    return findings, stats


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------

def band_note(value, key):
    if value is None:
        return ""
    lo, hi = BANDS[key]
    if value < lo:
        return "  below human range (%.2f-%.2f)" % (lo, hi)
    if value > hi:
        return "  above human range (%.2f-%.2f)" % (lo, hi)
    return "  in human range"


BAND_HEADERS = {
    "voice": "  voice (this writer's own rules)",
    "fingerprint": "  fingerprints (evidence about production)",
    "craft": "  craft (bad writing regardless of author)",
}


def report(findings, stats, profile, exempt, voice_name=None):
    out = []
    wc = stats.get("word_count", 0)
    rel = reliability(wc)
    out.append("human-writing scan")
    out.append("register: %s   voice: %s   words: %d   reliability: %s%s"
               % (profile, voice_name or "none", wc, rel,
                  "   (quoted examples exempt)" if exempt else "   (nothing exempt)"))
    if rel in ("low", "insufficient"):
        out.append("Short sample. Treat every number below as directional; "
                   "re-run on 250+ words before making any call that matters.")
    out.append("")

    if not findings:
        out.append("No mechanical findings. The judgment layer still applies: "
                   "run references/patterns.md and references/checklist.md.")
    else:
        for pri in ("P0", "P1", "P2"):
            group = [f for f in findings if f["priority"] == pri]
            if not group:
                continue
            titles = {"P0": "P0  credibility killers",
                      "P1": "P1  obvious machine smell",
                      "P2": "P2  polish"}
            out.append(titles[pri])
            for band in ("voice", "fingerprint", "craft"):
                sub = [f for f in group if f["band"] == band]
                if not sub:
                    continue
                out.append(BAND_HEADERS[band])
                seen = Counter(f["id"] for f in sub)
                shown = Counter()
                for f in sub:
                    shown[f["id"]] += 1
                    if shown[f["id"]] > 4:
                        continue
                    out.append("    L%-4d %-32s %s" % (f["line"], f["label"], f["match"]))
                for pid, n in seen.items():
                    if n > 4:
                        out.append("    ... and %d more %s" % (n - 4, pid))
            out.append("")

    out.append("stylometrics")
    rows = [
        ("words", wc, None),
        ("sentences", stats.get("sentence_count"), None),
        ("avg sentence words", stats.get("avg_sentence_words"), None),
        ("sentence length sd", stats.get("sentence_sd"), None),
        ("burstiness (sd/mean)", stats.get("burstiness"), "burstiness"),
        ("MATTR-100", stats.get("mattr"), "mattr"),
        ("type-token ratio", stats.get("ttr"), "ttr"),
        ("trigram repetition", stats.get("trigram_repetition"), "trigram_repetition"),
        ("em dashes / 1k words", stats.get("em_dashes_per_1k"), "em_dashes_per_1k"),
        ("avg paragraph sentences", stats.get("avg_paragraph_sentences"), None),
        ("paragraph length sd", stats.get("paragraph_sd"), None),
        ("Flesch-Kincaid grade", stats.get("flesch_kincaid_grade"), None),
    ]
    for name, value, key in rows:
        if value is None:
            continue
        note = band_note(value, key) if key else ""
        out.append("  %-26s %-8s%s" % (name, value, note))
    out.append("")
    out.append("Flesch-Kincaid is a diagnostic, never a target. Readability formulas "
               "are poor proxies for comprehension and reward gaming.")
    out.append("These are signals, not proof. Never use this output to decide who "
               "wrote something.")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="file to scan; omit to read stdin")
    ap.add_argument("--profile", default="blog", choices=sorted(PROFILE_SKIP),
                    help="register profile (default: blog)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--no-exempt", action="store_true",
                    help="also score quoted examples, code, tables, and block quotes")
    ap.add_argument("--voice-rules", metavar="PATH",
                    help="a voice's <name>.rules.json; its findings land in the "
                         "'voice' band and are never relaxed by --profile")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any P0 finding is present")
    args = ap.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()

    voice_rules, voice_name = None, None
    if args.voice_rules:
        try:
            with open(args.voice_rules, encoding="utf-8") as fh:
                voice_rules = json.load(fh)
        except (OSError, ValueError) as exc:
            print("scan: could not read voice rules: %s" % exc, file=sys.stderr)
            return 2
        voice_name = voice_rules.get("voice", os.path.basename(args.voice_rules))

    exempt = not args.no_exempt
    findings, stats = scan(text, args.profile, exempt, voice_rules)

    if args.json:
        print(json.dumps({
            "profile": args.profile,
            "voice": voice_name,
            "exempt_applied": exempt,
            "reliability": reliability(stats.get("word_count", 0)),
            "stats": stats,
            "human_ranges": BANDS,
            "counts": {
                "P0": sum(1 for f in findings if f["priority"] == "P0"),
                "P1": sum(1 for f in findings if f["priority"] == "P1"),
                "P2": sum(1 for f in findings if f["priority"] == "P2"),
                "voice": sum(1 for f in findings if f["band"] == "voice"),
                "fingerprint": sum(1 for f in findings if f["band"] == "fingerprint"),
                "craft": sum(1 for f in findings if f["band"] == "craft"),
            },
            "findings": findings,
        }, indent=2))
    else:
        print(report(findings, stats, args.profile, exempt, voice_name))

    if args.check and any(f["priority"] == "P0" for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
