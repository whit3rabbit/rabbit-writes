#!/usr/bin/env python3
"""
SARIF 2.1.0 output, so findings land on the diff instead of in a CI log.

An audit tool wants to live inline on the pull request, next to the line it is
talking about. GitHub's `codeql-action/upload-sarif` puts it there, and the
finding shape in rwlib.findings maps onto SARIF without inventing anything:

    id        -> ruleId
    priority  -> level          P0 error, P1 warning, P2 note
    line      -> region.startLine
    label     -> message.text, with the excerpt as the second line
    band      -> a rule property, and a tag, so a reviewer can filter on it

Levels are a judgement call worth stating: P0 maps to `error` because a P0 is
what makes a reader bounce or a credential leak into a document, and GitHub
surfaces errors as blocking annotations. P1 and P2 are advisory and must not
be, or people turn the whole thing off.

Nothing here decides anything. It reformats a list of findings that some other
module already produced, which is why it is safe for it to know nothing about
prose.

Stdlib only, 3.8+.
"""

from . import findings as findings_mod

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"

LEVEL_BY_PRIORITY = {"P0": "error", "P1": "warning", "P2": "note"}

BAND_DESCRIPTIONS = {
    "structure": "The shape of the document, measured against a corpus of 100 "
                 "trending repositories.",
    "voice": "This writer's own rules, from their voice profile. A hit is a "
             "defect, not a suggestion.",
    "fingerprint": "Evidence about how the text was produced. Never evidence "
                   "about who wrote it.",
    "craft": "A general writing problem. Says nothing about authorship.",
}


def _message(f):
    """Label first, then the excerpt or the matched span, on its own line.

    Two lines rather than one: GitHub truncates a long annotation in the diff
    view but keeps the first line intact, so the part that names the problem has
    to come first.
    """
    tail = f.get("excerpt") or f.get("match") or ""
    return "%s\n%s" % (f["label"], tail) if tail else f["label"]


def build(findings, uri, tool_name, tool_version=None, information_uri=None,
          extra_properties=None):
    """A SARIF log for one file's findings.

    `uri` must be relative to the repository root. GitHub silently drops results
    whose artifact location it cannot resolve to a file in the checkout, and
    "silently" is the operative word: the upload succeeds and nothing appears.
    """
    rules, rule_index = [], {}
    for f in findings:
        if f["id"] in rule_index:
            continue
        rule_index[f["id"]] = len(rules)
        rules.append({
            "id": f["id"],
            "name": f["id"],
            "shortDescription": {"text": f["label"]},
            "fullDescription": {"text": BAND_DESCRIPTIONS.get(f["band"], "")},
            "defaultConfiguration": {
                "level": LEVEL_BY_PRIORITY.get(f["priority"], "note")},
            "properties": {"band": f["band"], "priority": f["priority"],
                           "tags": [f["band"]]},
        })

    results = []
    for f in findings:
        results.append({
            "ruleId": f["id"],
            "ruleIndex": rule_index[f["id"]],
            "level": LEVEL_BY_PRIORITY.get(f["priority"], "note"),
            "message": {"text": _message(f)},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": uri},
                    # No endLine and no columns. The engine reports the line a
                    # match starts on and nothing narrower, and a region that
                    # claims a column it did not measure would put the squiggle
                    # under the wrong word.
                    "region": {"startLine": max(1, int(f["line"]))},
                },
            }],
            "properties": {"band": f["band"], "priority": f["priority"]},
        })

    driver = {"name": tool_name, "rules": rules,
              "properties": {"findingSchemaVersion": findings_mod.SCHEMA_VERSION}}
    if tool_version:
        driver["version"] = str(tool_version)
    if information_uri:
        driver["informationUri"] = information_uri
    if extra_properties:
        driver["properties"].update(extra_properties)

    return {"$schema": SARIF_SCHEMA, "version": SARIF_VERSION,
            "runs": [{"tool": {"driver": driver}, "results": results}]}
