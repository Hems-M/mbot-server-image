#!/bin/bash
# Shared helpers for the image build steps (00-*.sh to 50-*.sh).
# Sourced by each step. The steps run as root inside the chroot of the image being built.
# build-image.sh mounts the repository read-only at /tmp/mbot-dev and a scratch
# directory at /tmp/mbot-build before running a step.

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
# Retry downloads during the build; one DNS failure stopped an rc2 build in step 00.
APT_RETRY=(-o Acquire::Retries=5)
export LANG=C.UTF-8

MBOT_REPO="${MBOT_REPO:-/tmp/mbot-dev}"
MBOT_BUILD_TMP="${MBOT_BUILD_TMP:-/tmp/mbot-build}"
MBOT_REPORTS="$MBOT_BUILD_TMP/reports"
MANIFESTS="$MBOT_REPO/image/manifests"
# SYSTEM_DIR and UPSTREAM are used by the steps that source this file.
# shellcheck disable=SC2034
SYSTEM_DIR="$MBOT_REPO/system"
# shellcheck disable=SC2034
UPSTREAM="$MBOT_REPO/upstream"
STAMPS=/opt/mbot/stamps
STEP_NAME="$(basename "$0" .sh)"

# shellcheck source=../manifests/versions.lock
. "$MANIFESTS/versions.lock"
# Values that build-image.sh passes in (user name, default password, submodule commits).
# shellcheck source=/dev/null
[[ -r "$MBOT_BUILD_TMP/build.env" ]] && . "$MBOT_BUILD_TMP/build.env"

mkdir -p "$MBOT_REPORTS" "$STAMPS"

log() { printf '[%s %s] %s\n' "$(date '+%H:%M:%S')" "$STEP_NAME" "$*"; }
die() { log "ERROR: $*"; exit 1; }

# Refuse to run anywhere except inside the image chroot.
require_image_chroot() {
    [[ "$(id -u)" -eq 0 ]] || die "must run as root"
    [[ "$(uname -m)" == "aarch64" ]] || die "must run on arm64"
    grep -q 'VERSION_CODENAME=noble' /etc/os-release || die "not Ubuntu 24.04 (noble)"
    [[ -d /boot/firmware ]] || die "/boot/firmware missing: not the Raspberry Pi image"
    [[ -d "$MBOT_REPO/image/build" ]] || die "repository not mounted at $MBOT_REPO"
}

# Print the packages for one step from a manifest file.
# Lines look like "<package> <step> # reason". Comments and blank lines are ignored.
manifest_packages() {
    local file="$1" step="${2:-}"
    sed 's/#.*//' "$file" | awk -v s="$step" 'NF { if (s == "" || $2 == s) print $1 }'
}

apt_install() {
    [[ $# -gt 0 ]] || return 0
    log "apt-get install: $*"
    apt-get "${APT_RETRY[@]}" install -y "$@"
}

# install_file <source> <destination> <mode>
install_file() {
    log "install $3 $2"
    install -D -m "$3" "$1" "$2"
}

# Append a line to a file unless it is already there.
ensure_line() {
    local file="$1" line="$2"
    touch "$file"
    grep -qxF -- "$line" "$file" || { log "add to $file: $line"; printf '%s\n' "$line" >> "$file"; }
}

# Stamps record which pinned commit a source build in the image came from,
# so running a step again skips work that is already done.
stamp_matches() { [[ -f "$STAMPS/$1" && "$(cat "$STAMPS/$1")" == "$2" ]]; }
stamp_write() { printf '%s\n' "$2" > "$STAMPS/$1"; }

# git_pinned <url> <tag-or-empty> <commit> <dir>
# Clone exactly one commit. With a tag, the tag must point to the commit.
git_pinned() {
    local url="$1" tag="$2" commit="$3" dir="$4"
    rm -rf "$dir"
    if [[ -n "$tag" ]]; then
        log "git clone $url at tag $tag"
        git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$tag" "$url" "$dir"
    else
        log "git fetch $url at commit $commit"
        git init --quiet "$dir"
        git -C "$dir" fetch --quiet --depth 1 "$url" "$commit"
        git -C "$dir" -c advice.detachedHead=false checkout --quiet FETCH_HEAD
    fi
    local head
    head="$(git -C "$dir" rev-parse HEAD)"
    [[ "$head" == "$commit" ]] || die "$url: expected commit $commit, got $head"
}

# Run a command with the ROS environment loaded. ROS setup scripts use unset variables.
with_ros() {
    (
        set +u
        # shellcheck source=/dev/null
        . "/opt/ros/$ROS_DISTRO/setup.bash"
        set -u
        "$@"
    )
}
