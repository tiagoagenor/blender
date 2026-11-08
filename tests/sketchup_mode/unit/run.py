# SPDX-License-Identifier: GPL-2.0-or-later
"""Headless unit-test runner (owner: A). PLANO.md §8.1. Started by tools/sketchup_mode/run_unit.sh:

    Blender --background --factory-startup --python tests/sketchup_mode/unit/run.py -- --pattern <substr>

Puts the template folder on sys.path (so the package is plain `su`), registers it (draw/* is not
imported in background), runs every tests/sketchup_mode/unit/test_*.py whose file name contains the
pattern, unregisters, and exits 0 only if all tests pass and register/unregister raised no perf.error.
Zero matching tests is a pass.
"""

import argparse
import importlib
import os
import sys
import unittest

import bpy

sys.dont_write_bytecode = True      # no __pycache__ in the worktree

HERE =os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TEMPLATE = os.path.join(ROOT, "scripts", "startup", "bl_app_templates_system", "SketchUp_Mode")
STAGE_PREFIX = "/private/tmp/su_stage_"


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="run.py")
    ap.add_argument("--pattern", default="")
    return ap.parse_args(argv)


def _check_isolation():
    paths = {k: bpy.utils.resource_path('USER') if k == "USER" else bpy.utils.user_resource(k)
             for k in ("USER", "CONFIG", "SCRIPTS", "DATAFILES", "EXTENSIONS")}
    paths["tempdir"] = bpy.app.tempdir
    bad = {k: v for k, v in paths.items() if not os.path.realpath(v).startswith(STAGE_PREFIX)}
    return bad


def main():
    args = _args()
    bad = _check_isolation()
    if bad:
        print("run.py: NOT ISOLATED (source tools/sketchup_mode/dev_env.sh <AGENT>):", bad)
        return 2
    sys.path.insert(0, TEMPLATE)
    sys.path.insert(0, HERE)
    import su
    from su import perf

    su.register()
    reg_errors = perf.messages()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    load_errors = []
    files = sorted(f for f in os.listdir(HERE)
                   if f.startswith("test_") and f.endswith(".py") and args.pattern in f)
    for f in files:
        try:
            mod = importlib.import_module(f[:-3])
        except Exception as ex:
            load_errors.append("{:s}: {!r}".format(f, ex))
            continue
        suite.addTests(loader.loadTestsFromModule(mod))

    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)

    n_before = perf.errors()
    su.unregister()
    unreg_errors = perf.messages()[n_before:]

    ok = result.wasSuccessful() and not reg_errors and not unreg_errors and not load_errors
    print("=" * 70)
    print("SU UNIT: pattern={!r} files={:d} tests={:d} failures={:d} errors={:d} "
          "register_errors={:d} unregister_errors={:d} load_errors={:d} -> {:s}".format(
              args.pattern, len(files), result.testsRun, len(result.failures), len(result.errors),
              len(reg_errors), len(unreg_errors), len(load_errors), "OK" if ok else "FAILED"))
    for m in reg_errors + unreg_errors + load_errors:
        print("  ", m)
    return 0 if ok else 1


sys.exit(main())
