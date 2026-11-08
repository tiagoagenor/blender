# SketchUp Mode — isolated development environment (PLANO.md §9.0). SOURCE this file, do not execute it:
#
#   source tools/sketchup_mode/dev_env.sh <AGENT>      # e.g. A, B, ... G (run from inside your worktree)
#
# Everything Blender reads or writes goes to /private/tmp/su_stage_<AGENT>; the real
# ~/Library/Application Support/Blender is never touched. Works in sh, bash and zsh.
# Derived from doc/sketchup_mode/visual_spike/run.sh (BLENDER_USER_CONFIG alone does NOT redirect
# DATAFILES/EXTENSIONS, so every user path is set explicitly, plus BLENDER_USER_RESOURCES).

if [ -z "$1" ]; then
    echo "usage: source tools/sketchup_mode/dev_env.sh <AGENT>   (A..G)" >&2
    return 2 2>/dev/null || exit 2
fi
case "$1" in
    *[!A-Za-z0-9_]*) echo "dev_env.sh: invalid agent name '$1'" >&2; return 2 2>/dev/null || exit 2 ;;
esac

SU_AGENT="$1"
SU_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$SU_ROOT" ] || [ ! -d "$SU_ROOT/scripts/startup/bl_app_templates_system/SketchUp_Mode" ]; then
    echo "dev_env.sh: run from inside a sketchup-mode worktree (SketchUp_Mode template not found)" >&2
    return 2 2>/dev/null || exit 2
fi
SU_STAGE="/private/tmp/su_stage_$SU_AGENT"
SU_BLENDER="${SU_BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
SU_TEMPLATE_DIR="$SU_ROOT/scripts/startup/bl_app_templates_system/SketchUp_Mode"

BLENDER_SYSTEM_SCRIPTS="$SU_STAGE/sys"
BLENDER_USER_RESOURCES="$SU_STAGE/user"
BLENDER_USER_CONFIG="$SU_STAGE/user/config"
BLENDER_USER_SCRIPTS="$SU_STAGE/user/scripts"
BLENDER_USER_DATAFILES="$SU_STAGE/user/datafiles"
BLENDER_USER_EXTENSIONS="$SU_STAGE/user/extensions"
TMPDIR="$SU_STAGE/tmp"
export SU_AGENT SU_ROOT SU_STAGE SU_BLENDER SU_TEMPLATE_DIR TMPDIR \
       BLENDER_SYSTEM_SCRIPTS BLENDER_USER_RESOURCES BLENDER_USER_CONFIG BLENDER_USER_SCRIPTS \
       BLENDER_USER_DATAFILES BLENDER_USER_EXTENSIONS

mkdir -p "$BLENDER_SYSTEM_SCRIPTS/startup/bl_app_templates_system" "$BLENDER_USER_CONFIG" \
         "$BLENDER_USER_SCRIPTS" "$BLENDER_USER_DATAFILES" "$BLENDER_USER_EXTENSIONS" "$TMPDIR" "$SU_STAGE/out"

# The template is served from the worktree through a symlink (always points at THIS worktree).
ln -sfn "$SU_TEMPLATE_DIR" "$BLENDER_SYSTEM_SCRIPTS/startup/bl_app_templates_system/SketchUp_Mode"

# Seed userpref.blend once (splash/Quick Setup off: otherwise it swallows simulated events;
# auto-save of preferences off so runs are reproducible).
if [ ! -f "$BLENDER_USER_CONFIG/userpref.blend" ]; then
    "$SU_BLENDER" --background --factory-startup --python-exit-code 1 --python-expr \
"import bpy
p = bpy.context.preferences
p.view.show_splash = False
p.use_preferences_save = False
bpy.ops.wm.save_userpref()
" > "$SU_STAGE/seed_userpref.log" 2>&1
    if [ ! -f "$BLENDER_USER_CONFIG/userpref.blend" ]; then
        echo "dev_env.sh: failed to seed $BLENDER_USER_CONFIG/userpref.blend (see $SU_STAGE/seed_userpref.log)" >&2
        return 1 2>/dev/null || exit 1
    fi
fi

echo "SketchUp Mode dev env: agent=$SU_AGENT stage=$SU_STAGE root=$SU_ROOT"
