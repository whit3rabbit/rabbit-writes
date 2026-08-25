#!/usr/bin/env python3
"""
A voice profile, rendered as an output style.

The renderer's whole job is to be a faithful, shorter statement of a profile.
Two failure directions and both are tested here: dropping a refusal the profile
carries, and inventing one it does not. The second is the worse of the two,
because a style is the strongest push this plugin can apply and nobody
inspects the generated file.

Stdlib only, 3.9+. Tests take no arguments.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import helpers  # noqa: E402

from rwlib import outputstyle  # noqa: E402
from rwlib import voices as voices_mod  # noqa: E402


def _profile(name):
    rules_path = os.path.join(helpers.VOICES, name + ".rules.json")
    rules = voices_mod.load(rules_path)
    md_path = os.path.join(helpers.VOICES, name + ".md")
    with open(md_path, encoding="utf-8") as fh:
        return rules, fh.read()


def test_every_forbidden_mechanic_reaches_the_style():
    """A refusal the profile carries and the style drops is a rule silently
    turned off for every session that style is active."""
    cases = [
        ("whit3rabbit", ["em dash", "semicolon", "emoji", "one-word sentence",
                         "Oxford comma"]),
        ("satoshi", ["em dash", "emoji"]),
    ]
    for name, expected in cases:
        rules, md = _profile(name)
        out = outputstyle.render(rules, md, voice_name=name).lower()
        for phrase in expected:
            assert phrase.lower() in out, "%s: %r missing from the style" % (name, phrase)


def test_a_profiles_own_sentence_cap_renders_and_not_the_standards():
    """satoshi carries 35, his measured p95. A style that printed 25 would be
    quoting the STE default as this writer's rule."""
    rules, md = _profile("satoshi")
    out = outputstyle.render(rules, md, voice_name="satoshi")
    assert "under 35 words" in out, out
    assert "under 25 words" not in out, out
    assert "under 28 words a sentence" in out, out


def test_a_mechanic_set_to_allow_says_nothing():
    """`allow` is the absence of a rule. A line about it teaches the model
    that this writer thinks about semicolons, which is the opposite of true."""
    rules = {"voice": "probe", "mechanics": {"semicolon": "allow",
                                             "em_dash": "allow"}}
    out = outputstyle.render(rules)
    assert "semicolon" not in out.lower(), out
    assert "em dash" not in out.lower(), out


def test_an_overuse_rule_is_not_rendered_as_a_ban():
    """`efficiency-overuse` carries max_allowed 2. "Never" would be a rule the
    writer did not write, and the kind of overcorrection that gets a style
    deleted."""
    rules, md = _profile("whit3rabbit")
    out = outputstyle.render(rules, md, voice_name="whit3rabbit")
    assert "at most 2 in a piece" in out, out
    assert "Never: Overused efficiency" not in out, out


def test_signature_moves_never_reach_the_style():
    """The engine caps voice-signature-underuse at P2 whatever a profile says,
    because a rule that tells an editor to add a move installs a tic. A system
    prompt is a stronger push than any finding, so it must not carry them."""
    rules, md = _profile("john")
    ids = [m.get("id") for m in rules.get("signature_moves", [])]
    assert ids, "john's profile no longer has signature moves to exclude"
    out = outputstyle.render(rules, md, voice_name="john")
    for move_id in ids:
        assert move_id not in out, "%s reached the style" % move_id
    assert "star-rating" not in out.lower(), out


def test_the_frontmatter_is_what_the_host_reads():
    rules, md = _profile("whit3rabbit")
    out = outputstyle.render(rules, md, voice_name="whit3rabbit")
    lines = out.splitlines()
    assert lines[0] == "---", out[:80]
    end = lines.index("---", 1)
    keys = [line.split(":", 1)[0] for line in lines[1:end]]
    for key in keys:
        assert key in outputstyle.FRONTMATTER_KEYS, "invented key %r" % key
    assert "keep-coding-instructions: true" in lines, lines[1:end]
    assert "force-for-plugin" not in out, out


def test_the_style_name_is_quoted_because_it_carries_a_colon():
    """`name: Rabbit: whit3rabbit` unquoted is ambiguous YAML that a parser
    reads as a nested mapping."""
    out = outputstyle.render({"voice": "dana"})
    assert 'name: "Rabbit: dana"' in out, out


def test_a_long_list_is_cut_and_says_so():
    """satoshi has 78 preferred substitutions. A system prompt is not a
    lexicon dump, and silently truncating reads as a shorter profile."""
    rules, md = _profile("satoshi")
    out = outputstyle.render(rules, md, voice_name="satoshi")
    assert "more swaps live in the profile" in out, out
    swaps = out.split("## Swaps", 1)[1].split("##", 1)[0]
    assert swaps.count("\n- ") <= outputstyle.MAX_SWAPS + 1, swaps


def test_a_profile_note_is_cut_to_one_sentence():
    """Notes are written for a maintainer reading the rules file. whit3rabbit's
    closer note ends by explaining the register matrix, which is not an
    instruction to anybody writing an email."""
    rules, md = _profile("whit3rabbit")
    out = outputstyle.render(rules, md, voice_name="whit3rabbit")
    assert "genre columns" not in out, out
    assert "Which closer depends on the rung" in out, out


def test_the_long_form_profile_stays_out():
    """Structure, warmth calibration, and the anti-overfitting guide are
    thousands of tokens on every request, and the skill loads them at the
    moment they are worth paying for."""
    rules, md = _profile("whit3rabbit")
    out = outputstyle.render(rules, md, voice_name="whit3rabbit")
    assert "feedback sandwich" not in out.lower(), out
    assert "Anti-overfitting" not in out, out
    assert len(out) < 6000, "style is %d chars, which is a system prompt" % len(out)


def test_a_rules_dict_with_nothing_in_it_still_renders():
    """The eval and half the tests build a profile from a bare dict. A
    renderer that needed a file on disk would not survive either."""
    out = outputstyle.render({"voice": "nobody"})
    assert out.startswith("---\n"), out
    assert "# Write as nobody" in out, out
    assert "## Scope" in out, out


def test_the_rendered_style_carries_no_invisible_characters():
    """The same sweep the engine sources get. A style file is prose that ships,
    and a stray U+00A0 in a system prompt is invisible in every diff.

    satoshi is in this list because he caught one. `satoshi.md`'s essentials
    section carried an em dash while `satoshi.rules.json` forbids them, and
    that section is exactly what the renderer lifts, so the generated style
    said "never use an em dash" three lines under one.
    """
    for name in ("whit3rabbit", "john", "satoshi"):
        rules, md = _profile(name)
        out = outputstyle.render(rules, md, voice_name=name)
        bad = sorted({hex(ord(c)) for c in out if ord(c) > 0x7E})
        assert not bad, "%s style carries %s" % (name, bad)
