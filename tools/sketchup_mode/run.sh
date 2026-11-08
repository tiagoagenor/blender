#!/bin/sh
# SketchUp Mode — open the mode by hand, isolated (PLANO.md §9.0). Requires `source tools/sketchup_mode/dev_env.sh <AGENT>`.
#
#   tools/sketchup_mode/run.sh [extra Blender args...]
#
# Real input (no --enable-event-simulate). Everything Blender writes stays in $SU_STAGE
# (base: doc/sketchup_mode/visual_spike/run.sh). Not under the GUI lock: do not run it while a GUI
# scenario of another agent is running if you need a quiet screen.
set -u
die() { echo "run.sh: $*" >&2; exit 2; }
[ -n "${SU_STAGE:-}" ] || die "SU_STAGE not set — run: source tools/sketchup_mode/dev_env.sh <AGENT>"
case "$SU_STAGE" in /private/tmp/su_stage_?*) ;; *) die "SU_STAGE outside /private/tmp/su_stage_*: $SU_STAGE" ;; esac
case "${BLENDER_USER_RESOURCES:-}" in /private/tmp/su_stage_?*) ;; *) die "BLENDER_USER_RESOURCES outside /private/tmp/su_stage_*" ;; esac
[ -f "$BLENDER_USER_CONFIG/userpref.blend" ] || die "userpref.blend not seeded — re-source dev_env.sh"
mkdir -p "$TMPDIR"
exec "$SU_BLENDER" --app-template SketchUp_Mode "$@"
