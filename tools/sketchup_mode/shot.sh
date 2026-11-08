#!/bin/sh
# SketchUp Mode — screenshot of the mode (PLANO.md §8.3). Requires `source tools/sketchup_mode/dev_env.sh <AGENT>`.
#
#   tools/sketchup_mode/shot.sh <scenario|none> <out.png>
#
# Runs tests/sketchup_mode/gui/scn_shot.py under run_gui.sh (GUI lock, isolation, maximised window):
# optionally the scenario <scenario> first (its own screenshots/asserts are kept in the run folder),
# then a full-window screenshot (3024×1708 on this Mac) copied to <out.png>, plus a light copy
# <out>_small.png (sips -Z 1600) for the phone.
set -u
die() { echo "shot.sh: $*" >&2; exit 2; }
[ $# -eq 2 ] || die "usage: shot.sh <scenario|none> <out.png>"
[ -n "${SU_STAGE:-}" ] || die "SU_STAGE not set — run: source tools/sketchup_mode/dev_env.sh <AGENT>"
HERE="$(cd "$(dirname "$0")" && pwd)"
RUN="$SU_STAGE/out/shot"
SU_SHOT_SCENARIO="$1" SU_SHOT_OUT="$RUN/shot.png" "$HERE/run_gui.sh" scn_shot "$RUN"
RC=$?
[ -f "$RUN/shot.png" ] || die "no screenshot produced (see $RUN)"
mkdir -p "$(dirname "$2")"
cp "$RUN/shot.png" "$2"
case "$2" in *.png) SMALL="${2%.png}_small.png" ;; *) SMALL="$2_small.png" ;; esac
sips -Z 1600 "$2" --out "$SMALL" >/dev/null 2>&1 || true
echo "shot.sh: $2 ($SMALL) — scenario exit $RC"
exit $RC
