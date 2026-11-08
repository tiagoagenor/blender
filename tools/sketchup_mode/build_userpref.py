# SPDX-License-Identifier: GPL-2.0-or-later
"""Build the template's userpref.blend and studio light (owner: D). PLANO.md §4.7.

Run by build_all.sh in --background --factory-startup with BLENDER_USER_CONFIG pointing at a scratch
folder inside the agent stage:

    Blender --background --factory-startup --python build_userpref.py -- <template dir>

With an app template Blender takes from the TEMPLATE's userpref.blend only: themes, UI fonts/styles,
add-ons, keymaps/keyconfig, gizmo and app flags (corner split, region toggles, edge resize), splash
and save-prompt flags, ui_scale (BKE_blender_userdef_app_template_data_swap). So: Blender_Light +
SketchUp overrides (su.theme.apply_theme), splash off, no navigation gizmo, no corner split / region
toggles, edge resize ON. Also (re)writes studiolights/sketchup.sl.
"""

import os
import shutil
import sys

import bpy

sys.dont_write_bytecode = True


def main():
    tpl = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
    sys.path.insert(0, tpl)
    from su import theme                    # plain `su` package (like the unit runner)

    prefs = bpy.context.preferences
    theme.apply_theme(bpy.context)
    theme.apply_template_prefs(bpy.context)
    prefs.use_preferences_save = False
    theme.write_studio_light(os.path.join(tpl, "studiolights", theme.STUDIO_LIGHT_NAME))
    bpy.ops.wm.save_userpref()
    src = os.path.join(bpy.utils.user_resource('CONFIG'), "userpref.blend")
    if not os.path.isfile(src):
        raise SystemExit("build_userpref: save_userpref wrote nothing at " + src)
    shutil.copyfile(src, os.path.join(tpl, "userpref.blend"))
    print("build_userpref: ok", os.path.join(tpl, "userpref.blend"))


main()
