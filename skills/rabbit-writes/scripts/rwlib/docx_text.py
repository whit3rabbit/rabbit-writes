#!/usr/bin/env python3
"""
Word documents: the visible text, and the runs a reader was never meant to see.

A .docx is a zip with the document in word/document.xml, and unlike HTML the
hiding is declared right on the run: `w:vanish` is Word's own hidden-text
checkbox, `w:webHidden` its web twin, `w:color w:val="FFFFFF"` is white-on-the
-page, and a `w:sz` of a few half-points is a glyph nobody can read. That makes
detection cheaper and more honest than the CSS case, because there is no
renderer to second-guess: the file says the run is hidden.

The judgement about what a hidden run means belongs to rwlib/injection.py's
band and is deliberately reused rather than restated: a hidden run carrying a
directive is injection-hidden-directive at P0, a hidden run carrying prose is
injection-hidden-text at P1 past the same eight-word floor, and this module
only supplies the docx spellings of concealment. The finding's `line` is the
paragraph number, which is the nearest thing a .docx has.

Out of scope, on purpose: styles.xml (a hidden *style* applied by reference),
themed or near-background colors, text boxes layered behind images, and the
OLE-era .doc format. Each needs either a style resolver or a renderer, and the
module says so here rather than silently half-covering them.

Stdlib only, 3.9+.
"""

import zipfile
from xml.etree import ElementTree

from .findings import make
from .injection import (BAND, DIRECTIVE_RX, HIDDEN_DIRECTIVE_ID,
                        HIDDEN_TEXT_ID, MIN_HIDDEN_WORDS, REVIEW, _flat)
from .lexicon import synthetic_priority as SYNTH

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# The whites CONCEAL_WHITE_ELEMENT_RX accepts, uppercased the way Word writes
# them. Word has no inline background on a run by default, so the CSS module's
# declared-background guard has no docx equivalent to carry over.
WHITE_VALS = frozenset({"FFFFFF", "FEFEFE", "FDFDFD"})

# w:sz counts half-points. 4 is a two-point glyph, which is decoration at best.
TINY_HALF_POINTS = 4


class DocxError(Exception):
    """The file could not be read as a Word document. Callers exit 2 on this,
    the way scan.py does for an unreadable --voice-rules path: the alternative
    was a clean report on a document nobody checked."""


def is_docx(path):
    """Cheap routing test: the extension, or a zip that holds a Word body.

    .docm is accepted alongside .docx: it is the macro-enabled twin and carries
    the identical word/document.xml, which is where the hidden-run tricks live
    in the wild. --apply-safe still refuses it the way it refuses .docx, because
    neither is a text file the fixer can write back."""
    if path.lower().endswith((".docx", ".docm")):
        return True
    try:
        with open(path, "rb") as fh:
            if fh.read(4) != b"PK\x03\x04":
                return False
        with zipfile.ZipFile(path) as zf:
            return "word/document.xml" in zf.namelist()
    except (OSError, zipfile.BadZipFile):
        return False


def _toggled(rpr, tag):
    # w:vanish is a toggle property: present means on, unless w:val says off.
    el = rpr.find(W + tag)
    return (el is not None
            and el.get(W + "val", "true").lower() not in ("false", "0", "none"))


def _hidden_kind(rpr):
    if rpr is None:
        return None
    if _toggled(rpr, "vanish") or _toggled(rpr, "webHidden"):
        return "vanished run"
    color = rpr.find(W + "color")
    if color is not None and color.get(W + "val", "").upper() in WHITE_VALS:
        return "white font run"
    sz = rpr.find(W + "sz")
    if sz is not None:
        try:
            if float(sz.get(W + "val", "")) <= TINY_HALF_POINTS:
                return "tiny font run"
        except ValueError:
            pass
    return None


def _judge(kind, text, paragraph):
    """One hidden stretch of text, judged the way injection.scan judges a
    concealed span. Restated here rather than routed through injection.scan
    because that function reads markdown, and wrapping docx runs in fake markup
    to reuse it would make the line numbers lie."""
    hit = DIRECTIVE_RX.search(text)
    if hit:
        return make(
            HIDDEN_DIRECTIVE_ID, "Instruction hidden in %s" % kind,
            BAND, SYNTH(HIDDEN_DIRECTIVE_ID), paragraph,
            match=_flat(text, 80),
            excerpt="Concealed text addressing an agent, in docx paragraph "
                    "%d: %s. %s" % (paragraph, _flat(hit.group(0), 60), REVIEW))
    if len(text.split()) < MIN_HIDDEN_WORDS:
        return None
    return make(
        HIDDEN_TEXT_ID, "Hidden text with no visible purpose",
        BAND, SYNTH(HIDDEN_TEXT_ID), paragraph,
        match=_flat(text, 80),
        excerpt="A %s in docx paragraph %d: a reader never sees it, and it "
                "carries prose. Not an attack on its own. Worth one look at "
                "why it is here." % (kind, paragraph))


def extract(path):
    """(visible_text, findings) for one .docx.

    The visible text comes back paragraph per line, ready for the ordinary
    prose scan; the findings cover every run the file itself declares hidden.
    Adjacent hidden runs of one kind are judged as one stretch, because Word
    splits runs mid-sentence on any formatting hiccup and a directive should
    not escape by being split across two of them.
    """
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise DocxError("%s is not a readable .docx: %s" % (path, exc))
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise DocxError("%s: word/document.xml did not parse: %s" % (path, exc))

    visible, findings = [], []
    for paragraph, para in enumerate(root.iter(W + "p"), start=1):
        parts = []          # (kind or None, text), in document order
        for run in para.iter(W + "r"):
            text = "".join(t.text or "" for t in run.iter(W + "t"))
            if not text:
                continue
            parts.append((_hidden_kind(run.find(W + "rPr")), text))

        visible.append("".join(t for kind, t in parts if kind is None))

        stretch_kind, stretch = None, []
        for kind, text in parts + [(None, "")]:
            if kind is not None and kind == stretch_kind:
                stretch.append(text)
                continue
            if stretch_kind is not None:
                finding = _judge(stretch_kind, "".join(stretch), paragraph)
                if finding:
                    findings.append(finding)
            stretch_kind, stretch = kind, [text]

    text = "\n\n".join(p for p in visible if p.strip())
    return (text + "\n" if text else ""), findings
