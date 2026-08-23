#!/usr/bin/env python3
"""
publish_clawhub.py - Rebuild each clawhub skill folder and hand it to the CLI.

Publishing is a human act with a logged-in account, so this wrapper never
runs in CI (it exits 1 there) and runs nothing until the bundles have passed
the packaging gate. It rebuilds fresh through package_skills.build_skill_folder,
then invokes `clawhub skill publish <path> --version <version>` per skill.

Only the two flags every source agrees on are passed by default. --slug,
--name, and --changelog appear in third-party guides but not in the official
docs/cli.md of the openclaw/clawhub repository (checked 2026-08), so the
wrapper prints the suggested slug and the changelog text for the human
instead, and --extra forwards anything else verbatim. The full argv prints
before each run, which is where a flag drift shows up at --dry-run time.

  python3 scripts/publish_clawhub.py --dry-run

Exit code: 0 on success, 1 on failure. Stdlib only.
"""

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load_package_skills():
    """The packager, loaded by path so the wrapper runs from anywhere."""
    path = os.path.join(HERE, "package_skills.py")
    spec = importlib.util.spec_from_file_location("rw_publish_packaging", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def plugin_manifest():
    with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
        return json.load(fh)


def default_changelog():
    """The top Unreleased paragraph of CHANGELOG.md, unwrapped to one line."""
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"^## Unreleased\s*\n\s*\n(.+?)\n\s*\n", text, re.S | re.M)
    if not m:
        return "See CHANGELOG.md in the plugin repository."
    return " ".join(m.group(1).split())


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Rebuild the clawhub skill folders and publish each one.")
    parser.add_argument("--skill", action="append", default=[],
                        help="Publish only this skill. Repeatable. Default: all five.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Forward --dry-run to the CLI, which resolves the "
                             "publish without uploading.")
    parser.add_argument("--json", action="store_true",
                        help="Forward --json to the CLI for machine-readable output.")
    parser.add_argument("--changelog",
                        help="Changelog text for the run note. Default: the top "
                             "Unreleased paragraph of CHANGELOG.md.")
    parser.add_argument("--slug-prefix", default="",
                        help="Prefix for the suggested slug, printed for the human.")
    parser.add_argument("--clawhub-bin", default="clawhub",
                        help="Path to the clawhub CLI. Default: clawhub on PATH.")
    parser.add_argument("--extra", action="append", default=[],
                        help="Extra flag(s) forwarded verbatim to "
                             "`clawhub skill publish`. Repeatable.")
    args = parser.parse_args(argv)

    if os.environ.get("CI"):
        print("publish_clawhub.py never runs in CI. Publishing is a human act "
              "with a logged-in account, and the clawhub binary and login do "
              "not exist there.", file=sys.stderr)
        return 1

    try:
        pkg = load_package_skills()
    except Exception as exc:
        print("ERROR: could not load package_skills.py: %s" % exc, file=sys.stderr)
        return 1

    skills = args.skill or list(pkg.SKILL_NAMES)
    unknown = [s for s in skills if s not in pkg.SKILL_NAMES]
    if unknown:
        parser.error("unknown skill(s) %s; choose from %s"
                     % (", ".join(unknown), ", ".join(pkg.SKILL_NAMES)))

    version = plugin_manifest()["version"]
    changelog = args.changelog or default_changelog()

    print("ClawHub scans every upload (a hash check plus a code review) and "
          "cross-checks declared metadata against the code. These bundles "
          "quote attack patterns as detection documentation, so a warning "
          "label is possible even though the bundles only detect and report. "
          "SECURITY.md at each bundle root is the appeal evidence, and daily "
          "rescans can change a skill's status after publishing.\n")

    ok = True
    for skill in skills:
        if not pkg.build_skill_folder(skill):
            ok = False
            continue
        folder = os.path.join(pkg.DIST_DIR, pkg.CLAWHUB_DIR, skill)
        run_argv = [args.clawhub_bin, "skill", "publish", folder,
                    "--version", version]
        if args.dry_run:
            run_argv.append("--dry-run")
        if args.json:
            run_argv.append("--json")
        run_argv.extend(args.extra)
        print("Suggested slug: %s%s" % (args.slug_prefix, skill))
        print("Changelog for %s:\n  %s" % (version, changelog))
        print("Running: %s\n" % " ".join(run_argv))
        try:
            proc = subprocess.run(run_argv)
        except FileNotFoundError:
            print("ERROR: %s not found. Install it with `npm i -g clawhub` "
                  "and log in with `clawhub login`." % args.clawhub_bin,
                  file=sys.stderr)
            return 1
        if proc.returncode != 0:
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
