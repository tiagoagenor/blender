#!/bin/sh
# usage: ./run.sh shots/raw_name.png   — isolated config, never touches ~/Library/Application Support/Blender
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/$1"
rm -rf "$HERE/raw/cfg" "$HERE/raw/uscripts" "$HERE/raw/udata" "$HERE/raw/uext"; mkdir -p "$HERE/raw/cfg" "$HERE/raw/uscripts" "$HERE/raw/udata" "$HERE/raw/uext"
BLENDER_SYSTEM_SCRIPTS="$HERE/tpl" BLENDER_USER_CONFIG="$HERE/raw/cfg" BLENDER_USER_SCRIPTS="$HERE/raw/uscripts" \
  BLENDER_USER_DATAFILES="$HERE/raw/udata" BLENDER_USER_EXTENSIONS="$HERE/raw/uext" \
  /Applications/Blender.app/Contents/MacOS/Blender --app-template SketchUpSpike --enable-event-simulate \
  --python "$HERE/driver.py" -- "$OUT" > "$HERE/raw/stdout.txt" 2>&1
