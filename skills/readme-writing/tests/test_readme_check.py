#!/usr/bin/env python3
"""
Calibration tests for readme_check.py. A README that follows the measured
convention comes back quiet; one that violates it comes back loud; and the
checks that cost the most in false positives (bare URLs, buried pitches) are
pinned against real corpus files rather than only against fixtures.

Run: python3 tests/test_readme_check.py   (from the skill root)
"""

import glob
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "scripts", "readme_check.py")
SAMPLES = os.path.join(ROOT, "tests", "samples")
PLUGIN_ROOT = os.path.dirname(os.path.dirname(ROOT))
CORPUS = os.path.join(PLUGIN_ROOT, "docs", "readme-analysis", "repos")

failures = []


def check(name, condition, detail=""):
    if condition:
        print("  pass  %s" % name)
    else:
        print("  FAIL  %s  %s" % (name, detail))
        failures.append(name)


# The corpus under docs/readme-analysis/repos is a snapshot committed with the
# study, so the band below is a regression guard rather than a live measurement.
# Refetching it invalidates the band, which is why the count is asserted first.
EXPECTED_CORPUS_READMES = 100


def run(path, *extra):
    out = subprocess.run([sys.executable, CHECK, path, "--json", *extra],
                         capture_output=True, text=True)
    if out.returncode not in (0, 1):
        raise SystemExit("readme_check failed on %s:\n%s" % (path, out.stderr))
    return json.loads(out.stdout)


def run_code(path, *extra):
    """Exit code as well as findings, for the documented --check contract."""
    out = subprocess.run([sys.executable, CHECK, path, "--json", *extra],
                         capture_output=True, text=True)
    return json.loads(out.stdout), out.returncode


def ids(result, priority=None):
    return [f["id"] for f in result["findings"]
            if priority is None or f["priority"] == priority]


def main():
    good = run(os.path.join(SAMPLES, "good-readme.md"), "--no-voice")
    bad = run(os.path.join(SAMPLES, "bad-readme.md"), "--no-voice")

    print("calibration")
    check("good sample raises no P0", good["counts"]["P0"] == 0,
          "got %s" % ids(good, "P0"))
    check("good sample raises no P1", good["counts"]["P1"] == 0,
          "got %s" % ids(good, "P1"))
    check("bad sample raises P0", bad["counts"]["P0"] >= 1, "got %s" % ids(bad, "P0"))
    check("bad sample separated by 5x", sum(bad["counts"][k] for k in ("P0", "P1", "P2"))
          > 5 * sum(good["counts"][k] for k in ("P0", "P1", "P2")),
          "%s vs %s" % (bad["counts"], good["counts"]))

    print("structure")
    check("buried pitch found", "pitch-buried" in ids(bad))
    check("sponsor block above pitch found", "promo-before-pitch" in ids(bad))
    check("install after community sections found", "install-late" in ids(bad))
    check("license not last found", "license-not-last" in ids(bad))
    check("restated license terms found", "license-long" in ids(bad))
    check("badge wall found", "badge-wall" in ids(bad))
    check("TOC on a short README found", "toc-unneeded" in ids(bad))
    check("uncaveated claim found", "uncaveated-claim" in ids(bad))
    check("caveated claim not flagged", "uncaveated-claim" not in ids(good))
    # Vacuous if the good sample has no claim at all, which is how this check
    # passed for a while.
    check("the good sample actually contains a headline claim",
          good["stats"]["headline_claims"] >= 1,
          "got %s" % good["stats"]["headline_claims"])
    check("HTML header not read as a buried pitch", "pitch-buried" not in ids(good))

    print("line numbers")
    # Fences, headings, and tables get blanked rather than stripped, so a
    # finding's line still points at the file. Deleting them shifts every line
    # below, which is worse than no line number at all.
    sample_lines = open(os.path.join(SAMPLES, "good-readme.md"),
                        encoding="utf-8").read().split("\n")
    expected = next(i + 1 for i, l in enumerate(sample_lines)
                    if l.startswith("Bug reports and patches"))
    para = [f for f in good["findings"] if f["id"] == "long-paragraph"]
    check("long paragraph reported at its real line",
          len(para) == 1 and para[0]["line"] == expected,
          "expected L%d, got %s" % (expected, [f["line"] for f in para]))

    print("links")
    check("link syntax inside backticks not counted",
          "reference-links" not in ids(good), ids(good))
    check("bare URL found", "bare-url" in ids(bad))
    check("vague link text found", "vague-link-text" in ids(bad))
    check("HTML href not counted as bare", good["stats"]["bare_urls"] == 0,
          "got %d" % good["stats"]["bare_urls"])
    check("HTML badges counted", good["stats"]["badge_count"] == 2,
          "got %d" % good["stats"]["badge_count"])

    # Searching for the link text finds the first occurrence every time, so
    # three "here" links used to send the writer to the same line three times.
    vague_lines = sorted(f["line"] for f in bad["findings"]
                         if f["id"] == "vague-link-text")
    check("repeated vague link text reports distinct lines",
          len(vague_lines) >= 3 and len(set(vague_lines)) == len(vague_lines),
          str(vague_lines))
    bad_src = open(os.path.join(SAMPLES, "bad-readme.md"), encoding="utf-8").read().split("\n")
    check("each reported line really holds that link",
          all("[here]" in bad_src[n - 1] for n in vague_lines),
          str([(n, bad_src[n - 1][:40]) for n in vague_lines]))

    print("claims are caveated near the claim, not anywhere")
    scoped = tempfile.mkdtemp()
    try:
        far = os.path.join(scoped, "README.md")
        with open(far, "w", encoding="utf-8") as fh:
            fh.write("# Tool\n\nTool does one thing well and does it fast.\n\n"
                     "## Install\n\n```bash\npip install tool\n```\n\n"
                     "## Benchmarks\n\nIt is 40% faster than the alternative.\n\n"
                     "## FAQ\n\nWhy is it slow for me? Results vary.\n\n"
                     "## License\n\nMIT.\n")
        far_result = run(far, "--no-voice")
        check("a caveat in a distant section does not launder the claim",
              "uncaveated-claim" in ids(far_result), str(ids(far_result)))

        near = os.path.join(scoped, "NEAR.md")
        with open(near, "w", encoding="utf-8") as fh:
            fh.write("# Tool\n\nTool does one thing well and does it fast.\n\n"
                     "## Install\n\n```bash\npip install tool\n```\n\n"
                     "## Benchmarks\n\nIt is 40% faster than the alternative. "
                     "That is measured on one machine and results vary with disk.\n\n"
                     "## License\n\nMIT.\n")
        near_result = run(near, "--no-voice")
        check("a caveat in the claim's own section still counts",
              "uncaveated-claim" not in ids(near_result), str(ids(near_result)))
    finally:
        shutil.rmtree(scoped, ignore_errors=True)

    print("--check exit code")
    result, code = run_code(os.path.join(SAMPLES, "good-readme.md"), "--no-voice", "--check")
    check("--check exits 0 with no P0", code == 0 and result["counts"]["P0"] == 0,
          "code %d, %s" % (code, result["counts"]))
    result, code = run_code(os.path.join(SAMPLES, "bad-readme.md"), "--no-voice", "--check")
    check("--check exits 1 on a P0", code == 1 and result["counts"]["P0"] >= 1,
          "code %d, %s" % (code, result["counts"]))
    _, code = run_code(os.path.join(SAMPLES, "bad-readme.md"), "--no-voice")
    check("without --check a P0 still exits 0", code == 0, "code %d" % code)

    print("voice")
    sample = os.path.join(SAMPLES, "voiced-readme.md")
    resolved = run(sample)
    check("active voice resolved without being named", resolved["voice"] is not None,
          "notes: %s" % resolved["notes"])
    check("profile markdown pointed at, not just the rules file",
          any(".md" in n for n in resolved["notes"]), resolved["notes"])

    # Enforcement runs against a fixture profile, not against whichever voice the
    # plugin ships or has active. Swapping either must not move these results.
    rules = os.path.join(SAMPLES, "test-voice.rules.json")
    voiced = run(sample, "--voice-rules", rules)
    voice_hits = [f["id"] for f in voiced["findings"] if f["band"] == "voice"]
    check("em dash caught in a README", "voice-em-dash" in voice_hits, voice_hits)
    check("semicolon caught in a README", "voice-semicolon" in voice_hits, voice_hits)
    check("banned word caught", "voice-banned-word" in voice_hits, voice_hits)
    check("banned phrase caught", "voice-banned-phrase" in voice_hits, voice_hits)
    check("correspondence closer not demanded of a README",
          "missing-closer" not in voice_hits, voice_hits)
    quiet = run(sample, "--no-voice")
    check("--no-voice suppresses the voice band",
          not [f for f in quiet["findings"] if f["band"] == "voice"])
    check("voice findings do not change structure findings",
          set(ids(voiced)) >= set(ids(quiet)))

    print("voice resolution")
    # Run against a throwaway voices/ so these assert the mechanism, not whichever
    # profile this checkout happens to ship or have active.
    spec = importlib.util.spec_from_file_location("rc_resolve", CHECK)
    rc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rc)
    tmp = tempfile.mkdtemp()
    real_voices = rc.VOICES_DIR
    try:
        rc.VOICES_DIR = tmp
        readme = os.path.join(tmp, "README.md")
        open(readme, "w").close()
        for who in ("ada", "grace"):
            with open(os.path.join(tmp, who + ".rules.json"), "w") as fh:
                json.dump({"voice": who}, fh)
            open(os.path.join(tmp, who + ".md"), "w").close()

        with open(os.path.join(tmp, "ACTIVE"), "w") as fh:
            fh.write("grace\n")
        rules, name, note = rc.resolve_voice(readme)
        check("ACTIVE decides which voice, whoever it is",
              name == "grace" and rules.endswith("grace.rules.json") and note is None,
              "%s %s %s" % (name, rules, note))

        os.remove(os.path.join(tmp, "ACTIVE"))
        rules, name, note = rc.resolve_voice(readme)
        check("no ACTIVE with several profiles asks instead of guessing",
              rules is None and "Name one" in (note or ""), note)

        os.remove(os.path.join(tmp, "ada.rules.json"))
        rules, name, note = rc.resolve_voice(readme)
        check("no ACTIVE with one profile falls back and says so",
              name == "grace" and rules is not None and "falling back" in (note or ""), note)

        with open(os.path.join(tmp, ".rabbit-voice"), "w") as fh:
            fh.write("grace\n")
        with open(os.path.join(tmp, "ACTIVE"), "w") as fh:
            fh.write("nobody\n")
        rules, name, note = rc.resolve_voice(readme)
        check("a repo pin outranks ACTIVE", name == "grace" and "pinned" in (note or ""), note)
    finally:
        rc.VOICES_DIR = real_voices
        shutil.rmtree(tmp, ignore_errors=True)

    if os.path.isdir(CORPUS):
        print("corpus regression")
        readmes = []
        for slug in sorted(os.listdir(CORPUS)):
            hits = sorted(glob.glob(os.path.join(CORPUS, slug, "README.*")))
            preferred = [h for h in hits if h.lower().endswith(".md")]
            if preferred or hits:
                readmes.append((slug, (preferred or hits)[0]))
        p0 = [slug for slug, path in readmes if run(path, "--no-voice")["counts"]["P0"]]

        # The band is calibrated against the snapshot committed with the study,
        # so it only means anything on that snapshot. Refetching the corpus
        # changes the denominator and the repos in it, and a band that keeps
        # asserting through a refetch is asserting about a different population.
        pinned = len(readmes) == EXPECTED_CORPUS_READMES
        if pinned:
            # 6 of 100 in the study sample. A jump means a check got noisier,
            # which matters more than the exact number: a linter nobody trusts
            # is a linter nobody runs.
            check("P0 rate stays in the worst decile of the corpus",
                  2 <= len(p0) <= 12, "%d repos: %s" % (len(p0), p0))
        else:
            print("  note  corpus is %d READMEs, not the %d snapshot the band was "
                  "calibrated on. P0 rate %d, reported and not asserted."
                  % (len(readmes), EXPECTED_CORPUS_READMES, len(p0)))
        slugs = {slug for slug, _ in readmes}
        # Named fixtures, asserted whether or not the snapshot moved: these two
        # are in the study by name and their verdicts are the calibration.
        if "github__spec-kit" in slugs:
            check("spec-kit stays clean of P0", "github__spec-kit" not in p0)
        if "affaan-m__ECC" in slugs:
            check("ECC still flagged", "affaan-m__ECC" in p0)
    else:
        print("corpus regression: skipped, docs/readme-analysis/repos not present")

    print()
    if failures:
        print("%d failure(s): %s" % (len(failures), ", ".join(failures)))
        return 1
    print("all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
