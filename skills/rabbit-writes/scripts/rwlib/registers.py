#!/usr/bin/env python3
"""
The tolerance matrix, read from registers.json.

One fact, one home. The matrix used to be stated three times: as prose in
references/context.md, as PROFILE_SKIP and PROFILE_RELAX in scan.py, and as a
test that parsed the markdown table to check the first two agreed. That test was
clever and it was a workaround. It broke on table formatting rather than on a
real disagreement, and it could not see a cell that claimed a tolerance nobody
had implemented, which is how `curly-quote` sat in every skip set unable to fire
in any register.

Now scan.py derives its tables from this module, and the markdown table is
rendered from the same data:

    python3 scripts/rwlib/registers.py            # print the table
    python3 scripts/rwlib/registers.py --write    # write it into context.md
    python3 scripts/rwlib/registers.py --check    # exit 1 if the doc has drifted

validate.py runs --check, so editing the table by hand fails the build with the
diff rather than shipping a document that describes a different engine.

Stdlib only, 3.9+.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
REGISTERS_PATH = os.path.join(SCRIPTS, "registers.json")
CONTEXT_MD = os.path.join(os.path.dirname(SCRIPTS), "references", "context.md")

MATRIX_HEADING = "## Tolerance matrix"
# Where the rendered block stops. The prose under the table explains the modes
# and is written by hand, so the renderer has to know where its own output ends.
MATRIX_END_MARKER = "**Extra strict** means"

MODES = ("strict", "skip", "relaxed", "partial", "extra-strict", "p0-only")

_CACHE = {}


def load(path=REGISTERS_PATH):
    if path not in _CACHE:
        with open(path, encoding="utf-8") as fh:
            _CACHE[path] = json.load(fh)
    return _CACHE[path]


def registers(path=REGISTERS_PATH):
    """The registers --profile accepts, in matrix order.

    Declared, never inferred from the skip table. Inferred, a register whose
    skip set emptied out disappeared from the CLI without a word, and with it
    from the coverage the tests get by iterating the register list. A register
    with nothing to skip and nothing to relax is a legitimate register.
    """
    return tuple(load(path)["registers"])


def default_register(path=REGISTERS_PATH):
    return load(path)["default_register"]


def version(path=REGISTERS_PATH):
    return load(path).get("version")


def _cells(path):
    for rule in load(path)["rules"]:
        for register, cell in rule["cells"].items():
            yield rule, register, cell


def skip_table(path=REGISTERS_PATH):
    """{register: {finding id}} for every cell that suppresses a rule outright.

    `p0-only` lands here with `skip`, because every id it names is P1 or P2 and
    a P0 fingerprint is never suppressed in any register.
    """
    out = {r: set() for r in registers(path)}
    for rule, register, cell in _cells(path):
        if rule["id"] and cell["mode"] in ("skip", "p0-only"):
            out[register].add(rule["id"])
    return {r: ids for r, ids in out.items() if ids}


def relax_table(path=REGISTERS_PATH):
    """{register: {finding id: allowance}} for cells that report past a count.

    A relaxed cell with no allowance is a documentation row for a rule with no
    mechanical form, and it is dropped here rather than defaulting to zero: an
    allowance of zero is indistinguishable from strict and would claim an
    implementation that does not exist.
    """
    out = {r: {} for r in registers(path)}
    for rule, register, cell in _cells(path):
        if rule["id"] and cell["mode"] == "relaxed" and "allowance" in cell:
            out[register][rule["id"]] = cell["allowance"]
    return {r: ids for r, ids in out.items() if ids}


def vocab_exempt_registers(path=REGISTERS_PATH):
    """Registers where the vocabulary tiers drop the technical words.

    This is what a `partial` cell means, and it is why those registers take no
    hit allowance on the vocabulary rows: an allowance would let a second
    `delve` through, and the named exemption list does not.
    """
    return {register for rule, register, cell in _cells(path)
            if cell["mode"] == "partial"}


def unimplemented_rules(path=REGISTERS_PATH):
    """Labels of rules with no pattern, applied by reading rather than by regex."""
    return [r["label"] for r in load(path)["rules"] if not r["id"]]


def priorities(lexicon_path=None):
    """{finding id: worst priority it can be raised at}.

    Catalogue patterns carry their own, the engine's own findings are listed in
    lexicon.SYNTHETIC_PRIORITIES, and the two id spaces do not overlap.

    The argument names the *lexicon*, unlike every other `path` in this module.
    Spelled out, because it read as the registers path and would have loaded
    registers.json as a catalogue: no `patterns` key, no error, and every
    catalogue priority silently missing from the answer.
    """
    from . import lexicon
    out = dict(lexicon.SYNTHETIC_PRIORITIES)
    for pattern in lexicon.load(lexicon_path or lexicon.LEXICON_PATH).get("patterns", []):
        if pattern.get("id") and pattern.get("priority"):
            out[pattern["id"]] = pattern["priority"]
    return out


def problems(known_ids, path=REGISTERS_PATH, id_priorities=None):
    """Everything wrong with the matrix, as messages. Run by validate.py.

    `known_ids` is every finding id the engine can raise. A cell naming an id
    outside it is a silent no-op: the register quietly stops honouring a
    tolerance it claims in the docs, and the only symptom is a finding somebody
    eventually learns to ignore.

    `id_priorities` defaults to reading the lexicon, and exists as an argument
    so a test can hand in a matrix that does not match the shipped catalogue.
    """
    data = load(path)
    if id_priorities is None:
        id_priorities = priorities()
    known_registers = set(data["registers"])
    out = []
    if data["default_register"] not in known_registers:
        out.append("default_register %r is not in registers"
                   % data["default_register"])
    seen_labels = set()
    for rule in data["rules"]:
        label = rule["label"]
        if label in seen_labels:
            out.append("duplicate rule label %r" % label)
        seen_labels.add(label)
        if rule["id"] and rule["id"] not in known_ids:
            out.append("rule %r names id %r, which is not a lexicon pattern id "
                       "or a built-in finding id" % (label, rule["id"]))
        for register, cell in rule["cells"].items():
            where = "%s x %s" % (register, label)
            if register not in known_registers:
                out.append("%s is not a register in %r"
                           % (where, data["registers"]))
            mode = cell.get("mode")
            if mode not in MODES:
                out.append("%s has unknown mode %r" % (where, mode))
                continue
            if mode == "strict":
                out.append("%s says strict, which is the default. Delete the "
                           "cell rather than restating it" % where)
            if mode == "relaxed" and "allowance" in cell and not rule["id"]:
                out.append("%s carries an allowance but the rule has no id, so "
                           "nothing can honour it" % where)
            if mode == "relaxed" and "allowance" not in cell and rule["id"]:
                out.append("%s says relaxed and the rule has an id, but no "
                           "allowance implements it" % where)
            if mode == "partial" and rule["id"] not in data["vocabulary_rules"]:
                out.append("%s says partial, which only means something for a "
                           "vocabulary rule (%s)"
                           % (where, ", ".join(data["vocabulary_rules"])))
            # skip_table folds p0-only in with skip, on the stated grounds that
            # every id it names is P1 or P2. Nothing used to check that, so a
            # p0-only cell on a P0 id would have read in the docs as "the P0s
            # still fire here" and behaved as a full suppression of a
            # credibility killer.
            if mode == "p0-only" and id_priorities.get(rule["id"]) == "P0":
                out.append("%s says p0-only, but %r is itself a P0. That cell "
                           "suppresses the finding outright, which is the "
                           "opposite of what it says" % (where, rule["id"]))
    relaxed = relax_table(path)
    for register, ids in skip_table(path).items():
        overlap = sorted(ids & set(relaxed.get(register, {})))
        if overlap:
            out.append("register %r both skips and relaxes %s; skip wins, so "
                       "the allowance never applies" % (register, ", ".join(overlap)))
    return out


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def _cell_text(cell):
    mode = cell["mode"]
    if mode == "strict":
        return "strict"
    if mode == "skip":
        return "skip"
    if mode == "p0-only":
        return "P0 only"
    if mode == "extra-strict":
        return "**extra strict**"
    if mode == "partial":
        return "**partial**, see below"
    note = cell.get("note")
    return "relaxed (%s)" % note if note else "relaxed"


def render_table(path=REGISTERS_PATH):
    """The markdown table, exactly as it appears in references/context.md."""
    regs = registers(path)
    lines = ["| Rule | %s |" % " | ".join(regs),
             "|---|%s" % ("---|" * len(regs))]
    for rule in load(path)["rules"]:
        cells = [_cell_text(rule["cells"].get(r, {"mode": "strict"}))
                 for r in regs]
        lines.append("| %s | %s |" % (rule["label"], " | ".join(cells)))
    return "\n".join(lines)


def _split_doc(text):
    """(before, table_block, after) around the rendered table in context.md."""
    head, sep, rest = text.partition(MATRIX_HEADING)
    if not sep:
        raise ValueError("%s has no %r section" % (CONTEXT_MD, MATRIX_HEADING))
    body, end_sep, tail = rest.partition(MATRIX_END_MARKER)
    if not end_sep:
        raise ValueError("%s: no %r line to stop at" % (CONTEXT_MD, MATRIX_END_MARKER))
    table_lines = [ln for ln in body.splitlines() if ln.startswith("|")]
    if not table_lines:
        raise ValueError("%s: no table under %r" % (CONTEXT_MD, MATRIX_HEADING))
    return head + sep, body, end_sep + tail, "\n".join(table_lines)


def doc_table(doc_path=CONTEXT_MD):
    with open(doc_path, encoding="utf-8") as fh:
        return _split_doc(fh.read())[3]


def write_doc(doc_path=CONTEXT_MD, path=REGISTERS_PATH):
    with open(doc_path, encoding="utf-8") as fh:
        text = fh.read()
    head, body, tail, current = _split_doc(text)
    new = render_table(path)
    if current == new:
        return False
    with open(doc_path, "w", encoding="utf-8") as fh:
        fh.write(head + body.replace(current, new) + tail)
    return True


def main(argv):
    if "--write" in argv:
        changed = write_doc()
        print("context.md updated" if changed else "context.md already current")
        return 0
    if "--check" in argv:
        if doc_table() == render_table():
            print("tolerance matrix in context.md matches registers.json")
            return 0
        print("references/context.md's tolerance matrix has drifted from "
              "registers.json. Run: python3 %s --write"
              % os.path.relpath(__file__), file=sys.stderr)
        return 1
    print(render_table())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
