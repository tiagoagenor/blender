#!/bin/sh
# SketchUp Mode — build the generated template assets (owner: D). PLANO.md §4.7.
# Requires `source tools/sketchup_mode/dev_env.sh <AGENT>`.
#
#   tools/sketchup_mode/build_all.sh [icons|userpref|startup|all]     (default: all)
#
# 1. icons      python3 build_icons.py: recoloured .dat (+ _dim) and original PNG icons (Pillow)
# 2. userpref   Blender --background: template userpref.blend (theme, splash off…) + studiolights/sketchup.sl
#               (BLENDER_USER_CONFIG = scratch folder in the stage: the agent's seeded prefs stay untouched)
# 3. startup    Blender GUI under /usr/bin/lockf /tmp/su_gui.lock: the shell start-up steps, region widths by
#               simulated drags, factory data removed → template startup.blend + $SU_STAGE/out/build_startup.png
# The outputs are committed; never edit them by hand.
set -u

die() { echo "build_all.sh: $*" >&2; exit 2; }
[ -n "${SU_STAGE:-}" ] || die "SU_STAGE not set — run: source tools/sketchup_mode/dev_env.sh <AGENT>"
case "$SU_STAGE" in /private/tmp/su_stage_?*) ;; *) die "SU_STAGE outside /private/tmp/su_stage_*: $SU_STAGE" ;; esac
case "${BLENDER_USER_RESOURCES:-}" in /private/tmp/su_stage_?*) ;; *) die "BLENDER_USER_RESOURCES outside /private/tmp/su_stage_*" ;; esac
for v in "${BLENDER_USER_CONFIG:-}" "${BLENDER_USER_SCRIPTS:-}" "${BLENDER_USER_DATAFILES:-}" \
         "${BLENDER_USER_EXTENSIONS:-}" "${TMPDIR:-}"; do
    case "$v" in "$SU_STAGE"/*) ;; *) die "user path not inside $SU_STAGE: '$v'" ;; esac
done

WHAT="${1:-all}"
HERE="$SU_ROOT/tools/sketchup_mode"
TPL="$SU_TEMPLATE_DIR"
OUT="$SU_STAGE/out/build"
mkdir -p "$OUT" "$TMPDIR"
DATAFILES_ICONS="$(dirname "$SU_BLENDER")/../Resources/$("$SU_BLENDER" --version 2>/dev/null | head -1 | sed -E 's/^Blender ([0-9]+\.[0-9]+).*/\1/')/datafiles/icons"

if [ "$WHAT" = "icons" ] || [ "$WHAT" = "all" ]; then
    [ -d "$DATAFILES_ICONS" ] || die "Blender icons not found: $DATAFILES_ICONS"
    PYTHONDONTWRITEBYTECODE=1 python3 "$HERE/build_icons.py" "$DATAFILES_ICONS" "$TPL/icons" || die "icons failed"
fi

if [ "$WHAT" = "userpref" ] || [ "$WHAT" = "all" ]; then
    CFG="$SU_STAGE/build_cfg"
    rm -rf "$CFG"; mkdir -p "$CFG"
    BLENDER_USER_CONFIG="$CFG" "$SU_BLENDER" --background --factory-startup --python-exit-code 1 \
        --python "$HERE/build_userpref.py" -- "$TPL" > "$OUT/userpref.log" 2>&1 || { tail -20 "$OUT/userpref.log"; die "userpref failed"; }
    grep "build_userpref" "$OUT/userpref.log"
fi

if [ "$WHAT" = "startup" ] || [ "$WHAT" = "all" ]; then
    if [ "${SU_GUI_LOCKED:-}" != "1" ]; then
        SU_GUI_LOCKED=1 exec /usr/bin/lockf -k -t 1800 /tmp/su_gui.lock "$0" startup
    fi
    rm -f "$TPL/startup.blend" "$OUT/build_startup_log.txt"
    "$SU_BLENDER" --app-template SketchUp_Mode --enable-event-simulate -p 0 0 1440 900 \
        --python "$HERE/build_startup.py" -- "$TPL" "$OUT/build_startup.png" > "$OUT/startup.log" 2>&1
    [ -f "$TPL/startup.blend" ] || { cat "$OUT/build_startup_log.txt" 2>/dev/null; tail -30 "$OUT/startup.log"; die "startup.blend not written"; }
    cat "$OUT/build_startup_log.txt"
    echo "build_all.sh: startup.blend ok — screenshot $OUT/build_startup.png"
fi
