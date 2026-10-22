#!/bin/bash
# Build the MBot server image on a developer machine with Docker (arm64 engine).
# Tested only on macOS with Colima (aarch64 VM). Runs build/build-image.sh in a
# privileged ubuntu:24.04 container, which needs loop devices.
#
# Layout expected next to the repository:
#   ../images/<base image>.img.xz and ../images/SHA256SUMS   (inputs, never modified)
#   ../images/work/                                         (working copy, created)
#
# Usage: image/build.sh [--resume] [--steps "00 10 20 30 35 40 50 60"] [--reports-from NAME]

set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo="$(dirname "$here")"
top="$(dirname "$repo")"
images="$top/images"

# shellcheck source=manifests/versions.lock
. "$here/manifests/versions.lock"

log() { printf '[%s build.sh] %s\n' "$(date '+%H:%M:%S')" "$*"; }
die() { log "ERROR: $*"; exit 1; }

command -v docker >/dev/null || die "docker not found"
arch="$(docker info --format '{{.Architecture}}' 2>/dev/null)" || die "Docker engine not running"
[[ "$arch" == "aarch64" || "$arch" == "arm64" ]] || die "Docker engine is $arch, need arm64"

free_gb="$(df -k "$images" | awk 'NR == 2 {print int($4 / 1024 / 1024)}')"
log "free disk space at $images: ${free_gb} GB"
[[ "$free_gb" -ge 40 ]] || die "less than 40 GB free"

log "verify base image checksum"
if command -v sha256sum >/dev/null; then
    sum="$(sha256sum "$images/$BASE_IMAGE_FILE" | cut -d' ' -f1)"
else
    sum="$(shasum -a 256 "$images/$BASE_IMAGE_FILE" | cut -d' ' -f1)"
fi
[[ "$sum" == "$BASE_IMAGE_SHA256" ]] || die "checksum mismatch: $sum"
grep -q "^$sum [ *]$BASE_IMAGE_FILE\$" "$images/SHA256SUMS" || die "checksum not in $images/SHA256SUMS"
log "checksum OK: $sum"

mkdir -p "$images/work"
logfile="$images/work/build-$(date '+%Y%m%d-%H%M%S').log"
log "log file: $logfile"

set +e
docker run --rm --privileged --name mbot-image-build \
    -v "$top:/work" -v "$repo:/work/mbot-dev" ubuntu:24.04 \
    bash /work/mbot-dev/image/build/build-image.sh "$@" 2>&1 | tee "$logfile"
rc=${PIPESTATUS[0]}
set -e
log "build finished with exit code $rc"
exit "$rc"
