#!/bin/sh
# SketchUp Mode — GUI scenario runner (PLANO.md §8.2). Requires `source tools/sketchup_mode/dev_env.sh <AGENT>`.
#
#   tools/sketchup_mode/run_gui.sh <scenario> [out_dir]      # scenario = tests/sketchup_mode/gui/<scenario>.py
#
# Serialised between agents with /usr/bin/lockf on /tmp/su_gui.lock (macOS has no flock; the lock is
# released if the process dies). Opens the real template with --enable-event-simulate (real input is
# ignored, so the user's mouse cannot disturb the run). Result: <out_dir>/results.json; exit != 0 on failure.
# Base: doc/sketchup_mode/visual_spike/run.sh + driver.py.
set -u

die() { echo "run_gui.sh: $*" >&2; exit 2; }
[ -n "${SU_STAGE:-}" ] || die "SU_STAGE not set — run: source tools/sketchup_mode/dev_env.sh <AGENT>"
case "$SU_STAGE" in /private/tmp/su_stage_?*) ;; *) die "SU_STAGE outside /private/tmp/su_stage_*: $SU_STAGE" ;; esac
case "${BLENDER_USER_RESOURCES:-}" in /private/tmp/su_stage_?*) ;; *) die "BLENDER_USER_RESOURCES outside /private/tmp/su_stage_*" ;; esac
for v in "${BLENDER_USER_CONFIG:-}" "${BLENDER_USER_SCRIPTS:-}" "${BLENDER_USER_DATAFILES:-}" \
         "${BLENDER_USER_EXTENSIONS:-}" "${TMPDIR:-}" "${BLENDER_SYSTEM_SCRIPTS:-}"; do
    case "$v" in "$SU_STAGE"/*) ;; *) die "path not inside $SU_STAGE: '$v'" ;; esac
done
[ -f "$BLENDER_USER_CONFIG/userpref.blend" ] || die "userpref.blend not seeded — re-source dev_env.sh"
[ $# -ge 1 ] || die "usage: run_gui.sh <scenario> [out_dir]"

SCN="$1"
OUT="${2:-$SU_STAGE/out/$SCN}"
[ -f "$SU_ROOT/tests/sketchup_mode/gui/$SCN.py" ] || die "scenario not found: tests/sketchup_mode/gui/$SCN.py"

# Re-run this script under the GUI lock (one Blender GUI at a time for all agents).
if [ "${SU_GUI_LOCKED:-}" != "1" ]; then
    SU_GUI_LOCKED=1 exec /usr/bin/lockf -k -t 1800 /tmp/su_gui.lock "$0" "$@"
fi

rm -rf "$OUT"; mkdir -p "$OUT" "$TMPDIR"
TIMEOUT="${SU_GUI_TIMEOUT:-420}"     # hard kill (the harness has its own, shorter, Python watchdog)

# -p is ignored on this Mac (window opens maximised); passed anyway, nothing depends on it.
"$SU_BLENDER" --app-template SketchUp_Mode --enable-event-simulate -p 0 0 1440 900 \
    --python "$SU_ROOT/tests/sketchup_mode/gui/harness.py" -- "$SCN" "$OUT" > "$OUT/stdout.txt" 2>&1 &
BPID=$!
( sleep "$TIMEOUT"; if kill -0 "$BPID" 2>/dev/null; then echo "run_gui.sh: timeout ${TIMEOUT}s, killing Blender" >> "$OUT/stdout.txt"; kill -9 "$BPID"; fi ) &
WPID=$!
wait "$BPID"; RC=$?
kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null

if [ -f "$OUT/status.txt" ] && [ "$(cat "$OUT/status.txt")" = "PASS" ] && [ -f "$OUT/results.json" ]; then
    echo "run_gui.sh: $SCN PASSED (blender exit $RC) — $OUT/results.json"
    exit 0
fi
echo "run_gui.sh: $SCN FAILED (blender exit $RC) — $OUT" >&2
[ -f "$OUT/results.json" ] && cat "$OUT/results.json" >&2
echo "---- last lines of stdout.txt ----" >&2
tail -n 40 "$OUT/stdout.txt" >&2
exit 1
