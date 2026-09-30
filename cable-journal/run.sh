#!/usr/bin/env bash
# Cable journal, group scheme and floor areas from a DWG floor plan.
# Usage: ./run.sh plan.dwg [out_dir]
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 plan.dwg [out_dir]" >&2
  exit 2
fi
HERE="$(cd "$(dirname "$0")" && pwd)"
DWG="$(realpath "$1")"
OUT="$(realpath -m "${2:-$HERE/out}")"
PY="${PYTHON:-python3}"

cd "$HERE"
mkdir -p build "$OUT"
[ -d node_modules/@mlightcad/libredwg-web ] || npm install --silent

node dwg2json.mjs "$DWG" build/db.json
"$PY" trace.py
"$PY" build_xlsx.py "$OUT/Кабельный журнал.xlsx"
"$PY" scheme.py "$OUT/Схема групп.pdf"
"$PY" build_areas_xlsx.py "$OUT/Площади помещений.xlsx"
"$PY" areas_plan.py "$OUT/Площади помещений.pdf"

# Store computed formula values in the workbooks (Excel recalculates on open anyway).
if command -v soffice >/dev/null 2>&1; then
  for f in "$OUT/Кабельный журнал.xlsx" "$OUT/Площади помещений.xlsx"; do
    tmp="$(mktemp -d)"
    if SAL_USE_VCLPLUGIN=svp soffice --headless --norestore "-env:UserInstallation=file://$tmp/profile" \
         --convert-to 'xlsx:Calc MS Excel 2007 XML' --outdir "$tmp" "$f" >/dev/null 2>&1 \
       && [ -s "$tmp/$(basename "$f")" ]; then
      mv "$tmp/$(basename "$f")" "$f"
    else
      echo "LibreOffice could not recalculate $f; values will appear when opened in Excel" >&2
    fi
    rm -rf "$tmp"
  done
fi
echo "Готово: $OUT"
