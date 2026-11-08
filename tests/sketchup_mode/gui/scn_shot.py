# SPDX-License-Identifier: GPL-2.0-or-later
"""Screenshot scenario for tools/sketchup_mode/shot.sh (owner: A).
Env: SU_SHOT_SCENARIO (= another scenario name, "none" or "<scn>:<variant>" — the variant is exported as
SU_SHOT_VARIANT for that scenario), SU_SHOT_OUT (png path)."""

import importlib.util
import os


def run(h):
    name = os.environ.get("SU_SHOT_SCENARIO", "none")
    out = os.environ.get("SU_SHOT_OUT", os.path.join(h.out_dir, "shot.png"))
    if name and name != "none":
        scn, _, variant = name.partition(":")
        os.environ["SU_SHOT_VARIANT"] = variant
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), scn + ".py")
        spec = importlib.util.spec_from_file_location("su_shot_" + scn, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        yield from mod.run(h)
    h.park_mouse()
    yield 0.6
    h.screenshot(out)
    yield 0.4
    h.check("screenshot written", os.path.isfile(out), out)
