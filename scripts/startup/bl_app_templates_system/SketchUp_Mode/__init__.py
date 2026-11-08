# SPDX-License-Identifier: GPL-2.0-or-later
# SketchUp Mode — App Template entry point (owner: A). Everything lives in the `su` package;
# this file only forwards register/unregister. Inside `su` always use RELATIVE imports
# (the package is `bl_app_templates_system.SketchUp_Mode.su` here and plain `su` in unit tests).

import os
import sys

if os.environ.get("SU_STAGE"):
    # Dev environment (tools/sketchup_mode/dev_env.sh): keep __pycache__ out of the worktree.
    sys.dont_write_bytecode = True

from . import su


def register():
    su.register()


def unregister():
    su.unregister()
