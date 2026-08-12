#!/usr/bin/env python3
"""
The edits a machine is allowed to make.

scan.py reports and stops, and for almost everything it finds that is correct:
"this paragraph is nine sentences long" has no mechanical fix, and a tool that
guessed one would be the humanizer-shaped thing this plugin exists not to be.

A small subset is different. Stripping a zero-width space, dropping a
`utm_source=chatgpt.com`, or swapping a word for the replacement the writer's
own profile already names are edits with exactly one correct answer, and leaving
them to a language model is asking it to do a `sed` job with a chance of
paraphrasing the sentence on the way past. That subset is this module, and the
split is the same fingerprint-versus-judgment line the rest of the plugin draws.

The subset is smaller than it looks. Converting a typed `--` into an em dash was
in it for about an hour, until the property tests pointed out that verify.py
forbids adding an em dash under any circumstances and every fix therefore failed
the plugin's own gate. It is report-only now, with the reason. Rule 3 below is
what caught it.

Four rules on what gets in:

1. One correct answer, decided by data already in the repo. No inference.
2. Nothing inside a span the plugin promises not to touch. Code, inline code,
   tables, block quotes, frontmatter, quoted examples, URLs, and file paths are
   masked off, so an edit cannot land in one. A hidden character inside a fence
   is reported and left alone: the promise is worth more than the fix, and the
   report says where it is.
3. The output has to pass verify.py. --apply-safe runs it, which is what makes
   this a closed loop rather than a second thing to review.
4. Anything that depends on the register, the reader, or the sentence around it
   stays report-only, forever.

Stdlib only, 3.9+.
"""

import re

from .artifacts import (AI_PARAM_RX, HIDDEN_UNICODE, SPACE_LIKE_TOLERANCE,
                        SPACE_LIKE_UNICODE, ZERO_WIDTH, norm_url, occurrences)
from .markdown import (BLOCKQUOTE_RX, FENCE_RX, FRONTMATTER_RX, HEADING_RX,
                       INLINE_CODE_RX, PATH_RX, QUOTED_RX, TABLE_ROW_RX,
                       URL_RX, line_of)

# The two space-like characters, mapped to what they become. Separated from the
# zero-width ones because deleting a non-breaking space closes a word gap, and
# because they are only touched past the count a typesetter would use, which is
# the same threshold scan.py applies before reporting them at all.
SPACE_LIKE = {ch: " " for ch in sorted(SPACE_LIKE_UNICODE)}

DOUBLE_HYPHEN_RX = re.compile(r"\s--\s")

# Spans an edit may never land in. Every one of these is separately checked for
# verbatim preservation by verify.py, so masking them is not belt and braces: it
# is what keeps --apply-safe's own verification pass green.
#
# Split in two because the tracking-parameter rule is the one edit whose whole
# job is to rewrite a URL. It still has to respect everything else: a URL inside
# a fence is part of a command somebody is meant to paste, and rewriting it
# breaks the paste and fails verification. That was a live bug, found by the
# property tests within a hundred generated documents, on a fixture where two
# stray ``` lines paired up around a link.
#
# Headings are in the base set rather than beside URL_RX, because verify.py
# holds heading text inviolable by default and does not carve out a URL inside
# one. A substituted word in `# Leverage the API` produced a "heading changed or
# removed" violation, --apply-safe discarded the whole run including the fixes
# that were fine, and told the user to report a bug in the fixer. It was one.
QUOTED_PATTERNS = (FRONTMATTER_RX, FENCE_RX, INLINE_CODE_RX, TABLE_ROW_RX,
                   BLOCKQUOTE_RX, QUOTED_RX, HEADING_RX)
PROTECTED_PATTERNS = QUOTED_PATTERNS + (URL_RX, PATH_RX)

# A preferred substitution is only mechanical when the replacement is a word or
# two, not an instruction. whit3rabbit's own profile maps `leverage` to `use`,
# which is a swap, and `at the end of the day` to `cut it`, which is a note to
# the writer. Applying the second one literally would put the words "cut it"
# into the sentence.
SUBSTITUTION_RX = re.compile(r"\A[A-Za-z][A-Za-z'-]*(?: [A-Za-z'-]+){0,2}\Z")
INSTRUCTION_OPENERS = ("cut", "delete", "remove", "drop", "name", "say",
                       "write", "rephrase", "reword", "specify", "state")


def is_mechanical_substitution(value):
    """True when a preferred_substitutions value is a replacement, not advice."""
    if not isinstance(value, str) or not SUBSTITUTION_RX.match(value.strip()):
        return False
    return value.strip().split()[0].lower() not in INSTRUCTION_OPENERS


def span_mask(text, patterns=PROTECTED_PATTERNS):
    """A bytearray marking every character covered by one of `patterns`."""
    mask = bytearray(len(text))
    for rx in patterns:
        for m in rx.finditer(text):
            mask[m.start():m.end()] = b"\x01" * (m.end() - m.start())
    return mask


def protected_mask(text):
    """Every character no edit may touch."""
    return span_mask(text, PROTECTED_PATTERNS)


def _free(mask, start, end):
    return not any(mask[start:end])


def _match_case(source, replacement):
    """Keep a capital where the original had one. Nothing cleverer: ALL CAPS and
    Title Case Across Words are judgement calls about emphasis."""
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _record(fid, text, start, end, before, after, note=""):
    return {"id": fid, "line": line_of(text, start), "start": start, "end": end,
            "before": before, "after": after, "note": note}


def plan(text, voice_rules=None):
    """(edits, skipped) without touching anything.

    `edits` are non-overlapping (start, end, replacement, record) tuples in
    document order. `skipped` are findings this module could have fixed if they
    were not sitting inside a protected span, each carrying the reason.
    """
    mask = protected_mask(text)
    # The same mask without the URL and path spans, for the one rule whose job
    # is to edit a URL. It still may not reach into a fence or a table.
    quoted = span_mask(text, QUOTED_PATTERNS)
    edits, skipped = [], []

    # 1. Invisible characters. `occurrences` rather than a scan of its own: it
    #    is the same function scan.py counts with, and it is what keeps the
    #    fixer from deleting the joiner in the middle of an emoji.
    for ch, name in ZERO_WIDTH.items():
        for start in occurrences(text, ch):
            end = start + len(ch)
            if _free(mask, start, end):
                edits.append((start, end, "",
                              _record("hidden-unicode", text, start, end,
                                      "U+%04X" % ord(ch), "", "deleted %s" % name)))
            else:
                skipped.append(_record(
                    "hidden-unicode", text, start, end,
                    "U+%04X" % ord(ch), "",
                    "%s sits inside a span this skill promises not to touch. "
                    "Remove it by hand." % name))

    # 2. Space-like characters, past the count a typesetter would use.
    #
    #    The threshold counts every occurrence, masked ones included, because
    #    that is what scan.py reports on. Thresholding on the editable ones
    #    instead meant a document with 4 non-breaking spaces, 2 of them in a
    #    fence, got a P2 from the scan and then nothing at all from --apply-safe:
    #    no edit, and no line saying why. The masked ones now get a skip record,
    #    the way the zero-width branch above has always done.
    for ch, replacement in SPACE_LIKE.items():
        at = occurrences(text, ch)
        if len(at) <= SPACE_LIKE_TOLERANCE:
            continue
        for start in at:
            end = start + len(ch)
            if _free(mask, start, end):
                edits.append((start, end, replacement,
                              _record("hidden-unicode", text, start, end,
                                      "U+%04X" % ord(ch), "space",
                                      "%d of them, past the %d a typesetter would use"
                                      % (len(at), SPACE_LIKE_TOLERANCE))))
            else:
                skipped.append(_record(
                    "hidden-unicode", text, start, end,
                    "U+%04X" % ord(ch), "space",
                    "one of %d %s, but this one sits inside a span this skill "
                    "promises not to touch. Replace it by hand."
                    % (len(at), HIDDEN_UNICODE[ch])))

    # 3. AI tracking parameters. URLs are masked against every other rule here,
    #    so this is the one edit allowed to land inside one, and it is still not
    #    allowed inside a fence, a table, or a quoted example.
    for m in URL_RX.finditer(text):
        cleaned = norm_url(m.group(0))
        if cleaned == m.group(0):
            continue
        if _free(quoted, m.start(), m.end()):
            edits.append((m.start(), m.end(), cleaned,
                          _record("ai-utm", text, m.start(), m.end(),
                                  m.group(0), cleaned,
                                  "dropped an AI tool's tracking parameter")))
        else:
            skipped.append(_record(
                "ai-utm", text, m.start(), m.end(), m.group(0), cleaned,
                "the tracking parameter is inside a span this skill promises "
                "not to edit: a fence, inline code, a table row, a block quote, "
                "a heading, or a quoted example. Drop it by hand if the line is "
                "not meant to be copied exactly as written."))

    # 4. A typed em dash, reported and never fixed.
    #
    #    This one started life as a fix, on the reasoning that ` -- ` is somebody
    #    typing an em dash and the typographic answer is to give them one. The
    #    property tests killed it in about four seconds: verify.py's promise is
    #    that a rewrite never adds an em dash, full stop, so every document with
    #    a `--` in it produced output that failed the plugin's own gate. Under a
    #    voice that forbids em dashes it was worse still, turning a P2 craft note
    #    into a P0 voice defect.
    #
    #    So there is no mechanical answer here. A comma, a colon, or two
    #    sentences all work and choosing between them is reading, which is the
    #    line this module does not cross.
    for m in DOUBLE_HYPHEN_RX.finditer(text):
        if not _free(mask, m.start(), m.end()):
            continue
        skipped.append(_record(
            "double-hyphen-dash", text, m.start(), m.end(), m.group(0), "",
            "a typed em dash. No mechanical fix: this plugin never adds an em "
            "dash, so it needs a comma, a colon, or two sentences."))

    # 5. The writer's own preferred substitutions, where they are substitutions.
    subs = (voice_rules or {}).get("preferred_substitutions", {})
    for term, replacement in sorted(subs.items(), key=lambda kv: -len(kv[0])):
        if not is_mechanical_substitution(replacement):
            continue
        rx = re.compile(r"(?i)(?<![\w-])%s(?![\w-])"
                        % re.escape(term).replace(r"\ ", r"\s+"))
        for m in rx.finditer(text):
            if not _free(mask, m.start(), m.end()):
                continue
            new = _match_case(m.group(0), replacement.strip())
            edits.append((m.start(), m.end(), new,
                          _record("voice-substitution", text, m.start(), m.end(),
                                  m.group(0), new,
                                  "this voice's own preferred substitution")))

    edits.sort(key=lambda e: e[0])
    deduped, last_end = [], -1
    for edit in edits:
        # Two rules can land on the same span (a substituted term that also
        # contains a soft hyphen). First one wins, and the second is dropped
        # rather than applied to a string that no longer exists.
        if edit[0] < last_end:
            continue
        deduped.append(edit)
        last_end = edit[1]
    skipped.sort(key=lambda r: r["line"])
    return deduped, skipped


def apply(text, voice_rules=None):
    """(fixed_text, applied_records, skipped_records)."""
    edits, skipped = plan(text, voice_rules)
    out, cursor = [], 0
    for start, end, replacement, _ in edits:
        out.append(text[cursor:start])
        out.append(replacement)
        cursor = end
    out.append(text[cursor:])
    return "".join(out), [e[3] for e in edits], skipped
