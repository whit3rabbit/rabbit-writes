#!/usr/bin/env python3
"""
Voice rules files, with inheritance.

Blending interpolates two whole profiles, which answers the question "what does
the average of these two people sound like". The commoner real need is smaller
and sharper: my voice, plus a few things this particular repo or client does
differently. `.rabbit-voice` already pins which profile a repo uses. This is the
other half, the per-repo delta:

    {
      "voice": "whit3rabbit-acme",
      "extends": "whit3rabbit",
      "banned_words": ["synergy"],
      "mechanics": {"oxford_comma": "require"}
    }

The merge rule is deliberately lopsided.

  bans      union. A child adds to what the parent forbids and cannot quietly
            drop one, because a house style that silently unbans a word is a
            house style nobody can rely on. To soften an inherited rule, give
            the child a `banned_regex` entry with the same id: entries merge by
            id and the child's wins outright, so it can lower a priority, widen
            a `max_allowed`, or point the pattern at something narrower.
  mechanics child wins, key by key. Parent keys the child does not mention
            survive, so an override file stays two lines long.
  scalars   child wins. `voice`, `default_priority`, and anything else.

Cycles are caught rather than recursed into, and a missing parent is an error
rather than a silent fall back to no rules at all: a profile that inherits from
nothing enforces nothing, and reporting a clean voice band on a document nobody
checked is the failure mode this whole file exists to avoid.

Stdlib only, 3.8+.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
VOICES_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "voices")

# Keys merged as an ordered union of scalars.
LIST_UNION_KEYS = ("banned_words", "banned_phrases")
# Keys merged by the "id" of each entry, child wins.
LIST_BY_ID_KEYS = ("banned_regex", "required_when")
# Keys merged key by key, child wins.
DICT_MERGE_KEYS = ("mechanics", "preferred_substitutions")

MAX_DEPTH = 8


class VoiceError(Exception):
    """A rules file that cannot be resolved. Never swallowed: see the module
    docstring on why an unenforced voice is worse than a missing one."""


def _union(parent, child):
    out = list(parent)
    seen = {v.lower() for v in parent if isinstance(v, str)}
    for v in child:
        key = v.lower() if isinstance(v, str) else v
        if key not in seen:
            out.append(v)
            seen.add(key)
    return out


def _by_id(parent, child):
    out = [dict(e) for e in parent]
    index = {e.get("id"): i for i, e in enumerate(out) if e.get("id")}
    for entry in child:
        eid = entry.get("id")
        if eid is not None and eid in index:
            out[index[eid]] = entry
        else:
            out.append(entry)
    return out


def merge(parent, child):
    """One level of inheritance. Order matters: parent first, then child."""
    out = dict(parent)
    for key, value in child.items():
        if key == "extends":
            continue
        if key in LIST_UNION_KEYS:
            out[key] = _union(parent.get(key, []), value)
        elif key in LIST_BY_ID_KEYS:
            out[key] = _by_id(parent.get(key, []), value)
        elif key in DICT_MERGE_KEYS:
            merged = dict(parent.get(key, {}))
            merged.update(value)
            out[key] = merged
        else:
            out[key] = value
    return out


def _resolve_parent(name, voices_dir, source):
    """A parent named by profile name, or by a path relative to the child."""
    candidates = [os.path.join(voices_dir, name + ".rules.json")]
    if os.sep in name or name.endswith(".json"):
        candidates.insert(0, os.path.join(os.path.dirname(source), name))
    for path in candidates:
        if os.path.exists(path):
            return path
    raise VoiceError(
        "%s extends %r, which resolves to none of: %s. A profile that inherits "
        "from nothing enforces nothing."
        % (os.path.basename(source), name, ", ".join(candidates)))


def load(path, voices_dir=None, _seen=None, _depth=0):
    """The fully merged rules dict for a profile.

    Reads exactly like a flat rules file to every caller, which is the point:
    scan.py does not know or care whether a voice was written in one file or
    three.
    """
    voices_dir = voices_dir or VOICES_DIR
    path = os.path.abspath(path)
    _seen = _seen or []
    if path in _seen:
        raise VoiceError("voice inheritance loops: %s"
                         % " -> ".join(os.path.basename(p)
                                       for p in _seen + [path]))
    if _depth > MAX_DEPTH:
        raise VoiceError("voice inheritance deeper than %d files" % MAX_DEPTH)

    try:
        with open(path, encoding="utf-8") as fh:
            rules = json.load(fh)
    except (OSError, ValueError) as exc:
        raise VoiceError("could not read voice rules: %s" % exc)
    if not isinstance(rules, dict):
        raise VoiceError("%s is not a rules object" % os.path.basename(path))

    parent_name = rules.get("extends")
    if not parent_name:
        return rules
    parent_path = _resolve_parent(parent_name, voices_dir, path)
    parent = load(parent_path, voices_dir, _seen + [path], _depth + 1)
    return merge(parent, rules)


def lineage(path, voices_dir=None):
    """[profile name] from this file up to the root, for reporting.

    A report that says "voice: acme" when acme inherits most of its rules from
    somebody else is telling half the truth about what just got enforced.
    """
    voices_dir = voices_dir or VOICES_DIR
    out, seen, current = [], set(), os.path.abspath(path)
    while current and current not in seen and len(out) <= MAX_DEPTH:
        seen.add(current)
        try:
            with open(current, encoding="utf-8") as fh:
                rules = json.load(fh)
        except (OSError, ValueError):
            break
        out.append(rules.get("voice")
                   or os.path.basename(current).replace(".rules.json", ""))
        parent = rules.get("extends")
        if not parent:
            break
        try:
            current = _resolve_parent(parent, voices_dir, current)
        except VoiceError:
            break
    return out
