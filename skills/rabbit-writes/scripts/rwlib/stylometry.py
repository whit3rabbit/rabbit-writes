#!/usr/bin/env python3
"""
A voice as a measurable target: the fingerprint, and the distance to it.

Everything the voice band enforces today is a refusal: a banned word, a
punctuation rule, a paragraph cap. A document can clear all of them and sound
like nobody, which SKILL.md admits in prose and nothing measures. This module
is the measurement. It answers "how far is this document from how this person
writes" with a number whose calibrated range comes from the person's own
samples, so "in the voice" stops being a feeling and becomes a band.

The measure is Burrows' Delta, the standard authorship-attribution distance:
the document's function-word rates, z-scored against the author's baseline,
averaged. Function words carry the signal on purpose. Content words are about
the topic, and a voice has to survive a change of topic. "also" versus
"additionally", the contraction rate, and how often a sentence opens with
"but" are the connective tissue where a generic register creeps back in, and
they are exactly what no ban list reaches.

Two departures from textbook Delta, both forced by the data this runs on:

  A fixed marker list, not the corpus top-N. Delta classically takes the most
  frequent words of a large reference corpus. Three writing samples do not
  have a stable top-N: one essay about markets puts "market" in it. The list
  below is fixed, versioned, and English-only, like every other calibration
  in this engine.

  A floored standard deviation. Three samples give a noisy sd, and a marker
  the author uses at an identical rate in every sample gives sd 0, at which
  point any deviation divides to infinity. Each marker's sd is floored at a
  fraction of its mean and at an absolute minimum, so a marker the author
  never uses can still register a deviation without one "moreover" scoring as
  an infinite departure. The floors are stated as constants, not buried.

What a distance is, and is not. It is a signal about register, reported at P2
and never enforced: a writer is allowed to sound unlike themselves on purpose,
and a number that blocked a commit over it would be the humanizer-shaped
failure this plugin exists to avoid. It is also not an authorship verdict, for
every reason references/false-positives.md gives. The finding it feeds says
"further from the profile than any of the samples are from each other", quotes
the markers responsible, and stops there.

The per-marker contributors are the half that makes it actionable. A bare
distance tells a rewrite loop nothing. "additionally at 3.1 sd over the
profile, so at 2.4 sd under" tells it which words to trade.

**Callers pass prose with the markup already stripped.** `scan.strip_for_stats`
is that function, and both call sites in this plugin run it first. A fingerprint
built over raw markdown and compared against stripped prose would be measuring
two different things, and the difference would read as a register change: a
code fence has no function words in it at all.

Stdlib only, 3.9+.
"""

import json
import math
import os
import re
from collections import Counter

try:
    from .voices import strip_rules_suffix
except ImportError:                     # run as a script: no package, but
    from voices import strip_rules_suffix   # rwlib/ is on sys.path

SCHEMA_VERSION = 1

# The file that sits beside a profile's rules. scan.py looks for it there and
# runs without one, which is the only sane default: a fingerprint costs the
# writer three samples to make, and a profile that has none is still a profile.
FINGERPRINT_SUFFIX = ".fingerprint.json"

# Below this many words a document's marker rates are sampling noise, the same
# reasoning as scan.py's reliability tiers. Reported, never silently ignored.
RELIABLE_WORDS = 250

# The sd floors. RELATIVE_SD_FLOOR is the fraction of a marker's own mean rate
# its sd may not fall under: three samples that happen to agree exactly do not
# license infinite confidence. ABSOLUTE_SD_FLOOR (per 1,000 words) is the floor
# for markers the author never uses at all, chosen so that one occurrence of an
# unused marker in a 1,000-word document scores about 2 sd: notable, finite.
RELATIVE_SD_FLOOR = 0.25
ABSOLUTE_SD_FLOOR = 0.5

# Per-marker z is capped before averaging. A voice is a broad property and the
# distance has to measure breadth. Uncapped, one paragraph that leans on a
# marker the author never uses ("should" nine times in a policy list) scores z
# in the thirties and single-handedly outweighs a hundred markers that sit
# exactly on the profile. Capped, that spike counts as one strong deviation
# among many possible ones, and only a document deviating across many markers
# reads as a different register. The cap is generous enough that a real
# departure still registers at full weight on each marker it touches.
Z_CAP = 4.0

# The marker list, fixed and versioned. Function words, discourse connectors,
# hedges, and the common contractions, because a contraction is one token to
# this tokenizer and the contraction rate is one of the strongest register
# signals a person has. Content words stay out: the fingerprint has to survive
# a change of subject. Editing this list changes every stored fingerprint's
# meaning, which is what SCHEMA_VERSION is for.
MARKER_WORDS = (
    # articles, core prepositions, conjunctions
    "the", "a", "an", "of", "to", "in", "on", "at", "by", "for", "with",
    "from", "into", "over", "under", "about", "between", "through", "during",
    "against", "without", "within", "across", "after", "before", "and", "or",
    "but", "nor", "if", "then", "than", "when", "while", "where", "because",
    "since", "although", "though", "unless", "until", "whereas",
    # pronouns and determiners
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us",
    "them", "my", "your", "his", "its", "our", "their", "this", "that",
    "these", "those", "which", "who", "whom", "whose", "what", "any", "some",
    "all", "no", "none", "each", "every", "both", "either", "neither", "such",
    "same", "own", "other", "another",
    # copulas, auxiliaries, modals
    "is", "are", "was", "were", "be", "been", "being", "am", "do", "does",
    "did", "have", "has", "had", "will", "would", "can", "could", "should",
    "shall", "may", "might", "must",
    # quantity and degree
    "more", "most", "less", "least", "few", "many", "much", "very", "quite",
    "rather", "too", "enough", "only", "even", "still", "yet", "just",
    # discourse connectors, the additionally-versus-also axis
    "so", "also", "however", "additionally", "moreover", "furthermore",
    "therefore", "thus", "hence", "instead", "otherwise", "meanwhile",
    "indeed", "anyway", "besides",
    # hedges and stance adverbs
    "really", "actually", "honestly", "probably", "possibly", "perhaps",
    "maybe", "certainly", "clearly", "obviously", "arguably", "roughly",
    "basically", "essentially", "mostly", "usually", "often", "sometimes",
    "never", "always", "again", "now", "here", "there", "not",
    # contractions, one token each to WORD_RX
    "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't",
    "can't", "won't", "wouldn't", "couldn't", "shouldn't", "it's", "that's",
    "there's", "what's", "i'm", "i've", "i'd", "i'll", "you're", "you've",
    "we're", "we've", "they're", "let's",
)

MARKER_SET = frozenset(MARKER_WORDS)

# Written as an escape and never as a literal, the same rule the invisible
# character tables follow: anything that normalizes the source turns a literal
# curly apostrophe into a straight one, and the line still looks correct while
# the substitution it performs has become a no-op.
CURLY_APOSTROPHE = "\u2019"

# Lowercase on the way in, apostrophes kept, so "Don't" and "don't" are one
# marker and a contraction is one token. Curly apostrophes are normalized
# first: half the samples anybody pastes come out of an editor that curls
# them, and a fingerprint that reads the curled "don't" as two tokens is
# measuring the editor rather than the writer.
WORD_RX = re.compile(r"[a-z][a-z'\-]*")


def _straight(text):
    return text.lower().replace(CURLY_APOSTROPHE, "'")


def _tokens(text):
    return WORD_RX.findall(_straight(text))


def rates(text):
    """({marker: occurrences per 1,000 words}, word_count) for one document.

    Every marker appears in the dict, at 0.0 when absent, because a missing
    key and a rate of zero are the same fact and downstream arithmetic should
    not have to know two spellings of it.
    """
    tokens = _tokens(text)
    n = len(tokens)
    if n == 0:
        return {m: 0.0 for m in MARKER_WORDS}, 0
    counts = Counter(t for t in tokens if t in MARKER_SET)
    return {m: 1000.0 * counts[m] / n for m in MARKER_WORDS}, n


def _mean_sd(vectors):
    """Per-marker mean and sample sd across sample vectors."""
    n = len(vectors)
    mean = {m: sum(v[m] for v in vectors) / n for m in MARKER_WORDS}
    if n < 2:
        sd = {m: 0.0 for m in MARKER_WORDS}
    else:
        sd = {m: math.sqrt(sum((v[m] - mean[m]) ** 2 for v in vectors)
                           / (n - 1))
              for m in MARKER_WORDS}
    return mean, sd


def _floored(mean, sd):
    return {m: max(sd[m], RELATIVE_SD_FLOOR * mean[m], ABSOLUTE_SD_FLOOR)
            for m in MARKER_WORDS}


def _delta(mean, floored_sd, doc_rates):
    """Burrows' Delta of one document against a baseline, with the receipts.

    Returns (distance, contributors). Contributors are every marker at 1.5 sd
    or more, worst first, each carrying the direction and both rates, because
    the number alone tells a rewrite loop nothing: "additionally at +3.1 sd,
    so at -2.4 sd" tells it which words to trade.

    The cap applies to the distance and not to the receipt. Averaging needs the
    cap so one spiky marker cannot impersonate a register change. The
    contributor list is there to say what happened, and "18 per 1,000 words
    against a profile of zero" is the size of the fact. Capping the report
    would also tie every large deviation at the cap, and a top-N slice of ties
    orders by accident of iteration.
    """
    raw = {m: (doc_rates[m] - mean[m]) / floored_sd[m] for m in MARKER_WORDS}
    distance = sum(min(abs(z), Z_CAP) for z in raw.values()) / len(MARKER_WORDS)
    contributors = [
        {"marker": m, "z": round(raw[m], 2),
         "doc_per_1k": round(doc_rates[m], 2),
         "profile_per_1k": round(mean[m], 2)}
        for m in sorted(raw, key=lambda k: -abs(raw[k]))
        if abs(raw[m]) >= 1.5
    ]
    return distance, contributors


# --------------------------------------------------------------------------
# exemplars
# --------------------------------------------------------------------------
#
# A profile describes and an exemplar demonstrates, and demonstration
# conditions a model harder than adjectives do. These live inside the
# fingerprint file rather than in a `voices/<name>/samples/` directory, so a
# profile stays three files that travel together and there is one path to
# resolve rather than two. The cost is that a fingerprint carrying exemplars
# has the writer's own prose in it, which is why writing them is opt-in and
# why measure_voice.py says so out loud before it writes one.

EXEMPLAR_MIN_WORDS = 25
EXEMPLAR_MAX_WORDS = 220
EXEMPLAR_MAX = 40


def paragraphs(text, min_words=EXEMPLAR_MIN_WORDS, max_words=EXEMPLAR_MAX_WORDS):
    """Prose paragraphs worth keeping as demonstrations.

    Bounded at both ends. Under the floor a paragraph demonstrates nothing, and
    over the ceiling it costs more context than it teaches. Lines that are
    bullets, headings or fences are dropped: an exemplar is there to show how
    this person writes a paragraph.
    """
    out = []
    for block in re.split(r"\n\s*\n", text):
        body = block.strip()
        if not body:
            continue
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        if any(re.match(r"^(?:[-*+>#]|\d+[.)]\s|```|\|)", ln) for ln in lines):
            continue
        n = len(_tokens(body))
        if min_words <= n <= max_words:
            out.append(" ".join(lines))
    return out


def nearest_exemplars(paragraph, sample_paragraphs, k=3):
    """The writer's own paragraphs most like the one being rewritten.

    For conditioning a conversion. Similarity is length plus marker profile,
    which is crude and is enough: the point is to hand the model a paragraph of
    theirs in the same register and rough shape, not to find a semantic twin.
    Content similarity would be the wrong axis anyway, since the exemplar is
    there for its voice and not for its subject.
    """
    target_rates, target_n = rates(paragraph)
    scored = []
    for i, sp in enumerate(sample_paragraphs):
        r, n = rates(sp)
        if n < 20:
            continue
        marker_gap = sum(abs(r[m] - target_rates[m])
                         for m in MARKER_WORDS) / len(MARKER_WORDS)
        length_gap = abs(n - target_n) / max(target_n, 1)
        # The index breaks ties, so two equally close paragraphs come back in
        # the order the samples were given rather than by whichever sorts first
        # as a string.
        scored.append((marker_gap + length_gap, i, sp))
    scored.sort(key=lambda row: (row[0], row[1]))
    return [sp for _, _, sp in scored[:k]]


# --------------------------------------------------------------------------
# distributions
# --------------------------------------------------------------------------
#
# The aggregate numbers a voice profile already carries are means: average
# sentence length, average paragraph size, one contraction rate. A mean hides
# the thing a reader actually recognizes. Two writers with the same 18-word
# average write nothing alike if one opens half her sentences with "But" and
# the other never does. These are the distributions behind the means, and they
# are rewrite targets rather than thresholds: nothing enforces them.

# Grouped so the report can say which axis moved rather than listing 30 words.
CONNECTOR_GROUPS = {
    "additive": ("also", "and", "besides", "additionally", "moreover",
                 "furthermore", "plus"),
    "adversative": ("but", "however", "though", "although", "yet", "still",
                    "whereas", "instead"),
    "causal": ("so", "because", "since", "therefore", "thus", "hence",
               "consequently", "accordingly"),
    "sequential": ("then", "next", "first", "finally", "meanwhile", "later",
                   "after", "before"),
}

HEDGES = ("probably", "possibly", "perhaps", "maybe", "roughly", "about",
          "around", "somewhat", "fairly", "pretty", "mostly", "usually",
          "often", "sometimes", "seems", "seem", "suggests", "suggest",
          "tends", "tend", "arguably", "i think", "i suspect", "i'd guess",
          "as far as i know", "in my experience")

INTENSIFIERS = ("very", "really", "actually", "honestly", "clearly",
                "obviously", "certainly", "definitely", "absolutely",
                "completely", "entirely", "totally", "hugely", "massively")

CONTRACTION_RX = re.compile(
    "(?i)\\b[a-z]+['%s](?:t|s|re|ve|ll|d|m)\\b" % CURLY_APOSTROPHE)


def _rate(count, words):
    return round(1000.0 * count / words, 2) if words else 0.0


def distributions(text, top=8, split_sentences=None):
    """The shapes a mean hides, for one document.

    `split_sentences` is `rwlib.sentences.split_sentences` when the caller has
    it. It is a parameter rather than an import because this module is the one
    place a voice gets measured and it should stay usable on a bare string, and
    because the sentence splitter is the engine's and its behaviour is pinned by
    the engine's own tests. Without it, sentences are split on terminal
    punctuation and the openers are a little rougher.
    """
    if split_sentences is None:
        def split_sentences(body):
            return [s for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]

    tokens = _tokens(text)
    words = len(tokens)
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    sentences = [s.strip() for s in split_sentences(text) if s.strip()]

    def first_word(body):
        found = WORD_RX.search(_straight(body))
        return found.group(0) if found else ""

    sentence_openers = Counter(w for w in (first_word(s) for s in sentences) if w)
    paragraph_openers = Counter(w for w in (first_word(b) for b in blocks) if w)

    counts = Counter(tokens)
    connectors = {
        group: {"per_1k": _rate(sum(counts[w] for w in members), words),
                "used": sorted(w for w in members if counts[w])}
        for group, members in CONNECTOR_GROUPS.items()
    }

    lowered = _straight(text)
    contractions = Counter(_straight(m.group(0))
                           for m in CONTRACTION_RX.finditer(text))

    def phrase_count(entries):
        out = Counter()
        for entry in entries:
            if " " in entry:
                n = len(re.findall(r"\b%s\b" % re.escape(entry), lowered))
            else:
                n = counts[entry]
            if n:
                out[entry] = n
        return out

    hedges = phrase_count(HEDGES)
    intensifiers = phrase_count(INTENSIFIERS)

    # The last sentence of the document, verbatim. Nothing counts it. It is
    # here because "how do they sign off" is the question a voice profile most
    # often gets wrong, and no rate answers it: a person reads three of these
    # and knows. Whitespace collapsed, because a sentence that wrapped across
    # three source lines is one sentence and a report prints it on one row.
    closer = " ".join(sentences[-1].split()) if sentences else ""

    return {
        "words": words,
        "sentence_openers": [{"word": w, "n": n,
                              "share": round(n / len(sentences), 3)}
                             for w, n in sentence_openers.most_common(top)]
                            if sentences else [],
        "paragraph_openers": [{"word": w, "n": n} for w, n
                              in paragraph_openers.most_common(top)],
        "connectors": connectors,
        "contractions": {
            "per_1k": _rate(sum(contractions.values()), words),
            "inventory": [{"form": f, "n": n}
                          for f, n in contractions.most_common(top)],
        },
        "hedges": {"per_1k": _rate(sum(hedges.values()), words),
                   "used": [{"term": t, "n": n} for t, n in hedges.most_common(top)]},
        "intensifiers": {"per_1k": _rate(sum(intensifiers.values()), words),
                         "used": [{"term": t, "n": n}
                                  for t, n in intensifiers.most_common(top)]},
        "closer": closer[:200],
    }


# --------------------------------------------------------------------------
# the fingerprint
# --------------------------------------------------------------------------

def fingerprint(sample_texts, voice=None, exemplars=False):
    """The stored fingerprint for a set of the writer's samples.

    Carries the calibration with it: each sample's leave-one-out distance to
    a fingerprint built from the others. That self-distance band is what makes
    a later measurement readable. A raw Delta means nothing on its own, and
    "0.9, where this writer's own samples sit between 0.5 and 0.8 of each
    other" is a claim a person can act on. With two samples the band is one
    number and thin, and the fingerprint says so instead of hiding it.

    `exemplars=True` embeds the writer's own paragraphs, for conditioning a
    conversion. Opt-in, because it copies their prose into a file that then
    travels with the plugin.
    """
    if len(sample_texts) < 2:
        raise ValueError("a fingerprint needs at least 2 samples: "
                         "one sample has no self-distance to calibrate against")
    vectors, words = [], []
    for text in sample_texts:
        v, n = rates(text)
        vectors.append(v)
        words.append(n)

    mean, sd = _mean_sd(vectors)

    # Leave-one-out mean, full-set sd. The mean has to exclude the held-out
    # sample or every self-distance is biased low by the sample's own presence
    # in its baseline. The sd deliberately does not: over the two or three
    # samples that remain it is noise, and a marker where the held-out sample
    # happens to be the spread collapses to a tiny sd and an inflated z. The
    # full-set sd is the one distance() will use later, so the band and the
    # measurement it calibrates are computed with the same yardstick.
    floors = _floored(mean, sd)
    self_distances = []
    for i in range(len(vectors)):
        rest = vectors[:i] + vectors[i + 1:]
        rest_mean, _ = _mean_sd(rest)
        d, _ = _delta(rest_mean, floors, vectors[i])
        self_distances.append(round(d, 3))

    thin = [n for n in words if n < RELIABLE_WORDS]
    out = {
        "schema_version": SCHEMA_VERSION,
        "voice": voice,
        "n_samples": len(sample_texts),
        "sample_words": words,
        "thin_samples": len(thin),
        "markers": {m: {"mean": round(mean[m], 3), "sd": round(sd[m], 3)}
                    for m in MARKER_WORDS},
        "self_distance": {
            "per_sample": self_distances,
            "mean": round(sum(self_distances) / len(self_distances), 3),
            "max": round(max(self_distances), 3),
        },
    }
    if exemplars:
        picked = []
        for text in sample_texts:
            picked.extend(paragraphs(text))
        out["exemplars"] = picked[:EXEMPLAR_MAX]
    return out


def distance(fp, text):
    """One document against a stored fingerprint.

    Returns a dict rather than a float, because the float is the least useful
    part: the verdict compares it to the writer's own band, the contributors
    say what moved it, and the reliability says whether to believe any of it.

    verdict values:
        in_range      at or under the max self-distance: indistinguishable
                      from another sample by this measure
        near          under 1.5x the band: drifting, read the contributors
        out_of_range  past that: this does not sound like the profile's owner
    """
    if fp.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("fingerprint schema %r, this module reads %d: "
                         "regenerate it with measure_voice.py"
                         % (fp.get("schema_version"), SCHEMA_VERSION))
    doc_rates, n = rates(text)
    try:
        mean = {m: fp["markers"][m]["mean"] for m in MARKER_WORDS}
        sd = {m: fp["markers"][m]["sd"] for m in MARKER_WORDS}
    except (KeyError, TypeError) as exc:
        raise ValueError("fingerprint is missing marker %s. It was written by a "
                         "different marker list: regenerate it with "
                         "measure_voice.py" % exc)
    d, contributors = _delta(mean, _floored(mean, sd), doc_rates)

    band_max = fp["self_distance"]["max"]
    if d <= band_max:
        verdict = "in_range"
    elif d <= 1.5 * band_max:
        verdict = "near"
    else:
        verdict = "out_of_range"

    return {
        "voice": fp.get("voice"),
        "delta": round(d, 3),
        "band": dict(fp["self_distance"]),
        "verdict": verdict,
        "words": n,
        "reliable": n >= RELIABLE_WORDS,
        "contributors": contributors[:10],
    }


def path_for(rules_path):
    """The fingerprint that belongs to a voice's rules file, if it exists.

    Beside the rules rather than named separately, so whichever profile
    `rwlib.voices.resolve` picked is the one measured against. A profile
    resolved by `.rabbit-voice` and a fingerprint found by some other rule
    would be the two-checkers-disagreeing bug resolve() was written to end.
    """
    if not rules_path:
        return None
    candidate = strip_rules_suffix(rules_path) + FINGERPRINT_SUFFIX
    return candidate if os.path.exists(candidate) else None


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(fp, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(fp, fh, indent=2, sort_keys=False)
        fh.write("\n")
