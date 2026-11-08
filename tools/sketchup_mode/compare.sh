#!/bin/sh
# SketchUp Mode — side-by-side print (PLANO.md §8.3). Requires `source tools/sketchup_mode/dev_env.sh <AGENT>`.
#
#   tools/sketchup_mode/compare.sh <ours.png> <sketchup_ref.png> <out.png>
#
# sips --resampleHeight 900 on both → compose.py (Blender headless: ref | ours with labels
# "SketchUp 2027" / "SketchUp Mode") → sips -Z 1600 (light for the phone).
set -u
die() { echo "compare.sh: $*" >&2; exit 2; }
[ $# -eq 3 ] || die "usage: compare.sh <ours.png> <ref.png> <out.png>"
[ -n "${SU_STAGE:-}" ] || die "SU_STAGE not set — run: source tools/sketchup_mode/dev_env.sh <AGENT>"
case "${BLENDER_USER_RESOURCES:-}" in /private/tmp/su_stage_?*) ;; *) die "BLENDER_USER_RESOURCES outside /private/tmp/su_stage_*" ;; esac
HERE="$(cd "$(dirname "$0")" && pwd)"
W="$SU_STAGE/tmp/compare"; mkdir -p "$W" "$(dirname "$3")"
sips -s format png --resampleHeight 900 "$2" --out "$W/ref.png" >/dev/null || die "sips failed on $2"
sips -s format png --resampleHeight 900 "$1" --out "$W/ours.png" >/dev/null || die "sips failed on $1"
"$SU_BLENDER" --background --factory-startup --python-exit-code 1 --python "$HERE/compose.py" -- \
    "$W/ref.png" "$W/ours.png" "$W/full.png" "SketchUp 2027" "SketchUp Mode" > "$W/compose.log" 2>&1 \
    || { tail -20 "$W/compose.log" >&2; die "compose.py failed"; }
sips -Z 1600 "$W/full.png" --out "$3" >/dev/null || die "sips -Z failed"
echo "compare.sh: $3"
