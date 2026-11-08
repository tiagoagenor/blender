#!/bin/sh
# SketchUp Mode — headless unit tests (PLANO.md §8.1). Requires `source tools/sketchup_mode/dev_env.sh <AGENT>`.
#
#   tools/sketchup_mode/run_unit.sh [pattern]     # pattern = substring of the test file name, e.g. test_a_
#
# No lock: may run in parallel with other agents. Exit code 0 = all tests passed (0 tests is a pass).
set -u

die() { echo "run_unit.sh: $*" >&2; exit 2; }
[ -n "${SU_STAGE:-}" ] || die "SU_STAGE not set — run: source tools/sketchup_mode/dev_env.sh <AGENT>"
case "$SU_STAGE" in /private/tmp/su_stage_?*) ;; *) die "SU_STAGE outside /private/tmp/su_stage_*: $SU_STAGE" ;; esac
case "${BLENDER_USER_RESOURCES:-}" in /private/tmp/su_stage_?*) ;; *) die "BLENDER_USER_RESOURCES outside /private/tmp/su_stage_*" ;; esac
for v in "${BLENDER_USER_CONFIG:-}" "${BLENDER_USER_SCRIPTS:-}" "${BLENDER_USER_DATAFILES:-}" \
         "${BLENDER_USER_EXTENSIONS:-}" "${TMPDIR:-}"; do
    case "$v" in "$SU_STAGE"/*) ;; *) die "user path not inside $SU_STAGE: '$v'" ;; esac
done

PATTERN="${1:-}"
mkdir -p "$TMPDIR"
exec "$SU_BLENDER" --background --factory-startup --python-exit-code 1 \
    --python "$SU_ROOT/tests/sketchup_mode/unit/run.py" -- --pattern "$PATTERN"
