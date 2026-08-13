#!/usr/bin/env python3
"""
Run the engine tests without pytest.

    python3 tests/run.py                 # everything
    python3 tests/run.py -k register     # only tests whose name matches
    python3 tests/run.py test_voice.py   # only this file

pytest runs the same files and is the better experience: use it if it is
installed. This exists because every script in this plugin runs on a checkout
with nothing installed, and a test suite that needs a package manager is a test
suite that stops being run on the machine where a bug shows up.

The suite used to be one 930-line function with a `test_all()` shim so pytest
would collect something. Splitting it bought failure isolation, `-k`, and a
place for a contributor to add a test without reading the whole file to find
where it goes. It cost the shared setup, which helpers.py memoizes back.
"""

import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def discover(selected_files):
    names = sorted(f for f in os.listdir(HERE)
                   if f.startswith("test_") and f.endswith(".py"))
    if selected_files:
        wanted = {os.path.basename(f) for f in selected_files}
        names = [n for n in names if n in wanted]
    return names


def main(argv):
    keyword = None
    if "-k" in argv:
        index = argv.index("-k")
        if index + 1 >= len(argv):
            print("-k needs a following keyword", file=sys.stderr)
            return 2
        keyword = argv[index + 1]
        argv = argv[:index] + argv[index + 2:]

    files = discover(argv)
    if not files:
        print("no test files matched %r" % argv, file=sys.stderr)
        return 2

    passed, failed, errors, ran = 0, [], [], 0
    for filename in files:
        module_name = filename[:-3]
        print(module_name)
        try:
            module = __import__(module_name)
        except Exception:
            print("  ERROR  could not import %s" % filename)
            traceback.print_exc()
            errors.append(filename)
            continue
        tests = sorted(name for name in dir(module) if name.startswith("test_"))
        for name in tests:
            if keyword and keyword not in name and keyword not in module_name:
                continue
            fn = getattr(module, name)
            if not callable(fn):
                continue
            # A test that declares parameters wants pytest fixtures, which this
            # runner does not provide. Reported rather than skipped silently:
            # the convention in this suite is no-argument tests calling the
            # memoized helpers, and a fixture-shaped test would vanish here.
            if fn.__code__.co_argcount:
                print("  SKIP   %s takes arguments, so only pytest can run it"
                      % name)
                errors.append("%s::%s" % (filename, name))
                continue
            ran += 1
            try:
                fn()
            except AssertionError as exc:
                print("  FAIL   %s" % name)
                for line in str(exc).splitlines()[:6]:
                    print("         %s" % line)
                failed.append("%s::%s" % (module_name, name))
            except Exception:
                print("  ERROR  %s" % name)
                traceback.print_exc()
                errors.append("%s::%s" % (module_name, name))
            else:
                print("  pass   %s" % name)
                passed += 1

    print()
    print("%d passed, %d failed, %d errored" % (passed, len(failed), len(errors)))
    for name in failed + errors:
        print("  %s" % name)
    if keyword is not None and ran == 0:
        print("no tests matched keyword %r" % keyword, file=sys.stderr)
        return 2
    return 1 if (failed or errors) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
