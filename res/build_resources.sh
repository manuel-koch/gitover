#!/bin/bash
set -e
BASE_DIR=$(dirname ${0})

IN=${BASE_DIR}/resources.qrc
OUT=${BASE_DIR}/../gitover/ui/resources.py
echo "Building Resources..."
echo "from ${IN}"
echo "to   ${OUT}"
[ -s "$OUT" ] && rm "$OUT"
pyrcc5 -o "$OUT" "$IN" && echo Done

IN=${BASE_DIR}/icon.png
OUT=${BASE_DIR}/icon.icns
echo "Building Iconset..."
echo "from ${IN}"
echo "to   ${OUT}"
sips -s format icns "$IN" --out "$OUT"
