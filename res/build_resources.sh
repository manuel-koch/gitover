#!/bin/bash
set -e
BASE_DIR=$(dirname ${0})

RESOURCE_IN=${BASE_DIR}/resources.qrc
RESOURCE_OUT=${BASE_DIR}/../gitover/ui/resources.py

echo "Building Resources ( $(which pyrcc5) : $(pyrcc5 -version 2>&1 | cut -d' ' -f2) )..."
echo "from ${RESOURCE_IN}"
echo "to   ${RESOURCE_OUT}"
[ -s "$RESOURCE_OUT" ] && rm "$RESOURCE_OUT"
pyrcc5 -o "$RESOURCE_OUT" "$RESOURCE_IN" && echo Done

echo  >> "$RESOURCE_OUT"
echo  >> "$RESOURCE_OUT"
HEAD_COMMIT=$(git rev-parse --short=8 HEAD)
LATEST_VERSION=$(git tag | grep -e "^v" | sort | tail -1 | cut -b2-)
HEAD_VERSION=$(git tag --points-at HEAD | grep -e "^v" | sort | tail -1 | cut -b2-)
VERSION_POSTFIX=""
[[ "$LATEST_VERSION" != "$HEAD_VERSION" ]] && VERSION_POSTFIX="-$HEAD_COMMIT"
BUILD_TIME=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
echo "gitover_commit_sha = '$HEAD_COMMIT'" >> "$RESOURCE_OUT"
echo "gitover_version = '${LATEST_VERSION}${VERSION_POSTFIX}'" >> "$RESOURCE_OUT"
echo "gitover_build_time = '${BUILD_TIME}'" >> "$RESOURCE_OUT"
echo "Using version info ${LATEST_VERSION}${VERSION_POSTFIX}"

ICON_IN=${BASE_DIR}/icon.png
ICON_OUT=${BASE_DIR}/icon.icns
echo "Building Iconset..."
echo "from ${ICON_IN}"
echo "to   ${ICON_OUT}"
sips -s format icns "$ICON_IN" --out "$ICON_OUT"
