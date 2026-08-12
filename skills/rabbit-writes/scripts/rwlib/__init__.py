"""
rwlib - the shared engine behind rabbit-writes, readme-writing, and the corpus
research scripts.

Stdlib only, and importable by path, because these scripts run from a plugin
directory that is not on anybody's PYTHONPATH. Every consumer bootstraps the
same way:

    HERE = os.path.dirname(os.path.abspath(__file__))
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from rwlib import markdown as md

Modules:

    markdown    spans: fences, links, images, tables, quotes, dashes, badges.
                Every blanking helper preserves length so offsets survive.
    sentences   English sentence and word segmentation.
    lexicon     the pattern catalogue, its version, and the two regex builders.
    sections    what counts as an "installation" heading, for README work.
    registers   the tolerance matrix, read from registers.json.
    corpus      the README corpus figures, and the drift check against them.
    findings    the finding schema and its version.
    injection   the safety band: concealed text, and text aimed at an agent.
                Surfaces and quarantines. Nothing here is ever fixable.
    voices      voice rules files, including `extends` inheritance.
    language    the English-only scope check. Warns, never fails.
    sarif       findings as SARIF 2.1.0, for PR annotations.
    fixes       the mechanically safe subset of edits, for scan.py --apply-safe.

Nothing here decides what good writing is. That lives in the reference files,
where a person can argue with it.
"""

__all__ = ["markdown", "sentences", "lexicon", "sections", "registers",
           "corpus", "findings", "voices", "language", "sarif", "fixes",
           "injection"]
