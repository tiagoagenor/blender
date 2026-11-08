#!/bin/zsh
# Abre o Blender no "SketchUp Mode" com o código desta pasta.
# Usa uma configuração separada em /private/tmp/su_stage_USUARIO,
# então o seu Blender normal não é alterado.
# Uso: dois cliques neste arquivo no Finder, ou rode no Terminal.

cd "$(dirname "$0")/../.." || exit 1
source tools/sketchup_mode/dev_env.sh USUARIO >/dev/null || exit 1
exec "$SU_BLENDER" --app-template SketchUp_Mode "$@"
