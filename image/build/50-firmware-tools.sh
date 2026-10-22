#!/bin/bash
# Step 50: Pico firmware toolchain (OS-006).
# ARM GCC and newlib from Ubuntu, pico-sdk at a pinned tag in /opt/pico-sdk,
# picotool 2.2.0 built from source. Then a test build of the pinned mbot_firmware_ros in
# a scratch directory (it is not kept in the image). Safe to run more than once.
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
require_image_chroot

mapfile -t pkgs < <(manifest_packages "$MANIFESTS/apt-packages.txt" 50)
apt_install "${pkgs[@]}"

jobs="$(nproc)"

# ---------------------------------------------------------------- pico-sdk
if stamp_matches pico-sdk "$PICO_SDK_COMMIT" && [[ -f /opt/pico-sdk/pico_sdk_init.cmake ]]; then
    log "pico-sdk already installed ($PICO_SDK_TAG)"
else
    rm -rf /opt/pico-sdk
    git_pinned "$PICO_SDK_REPO" "$PICO_SDK_TAG" "$PICO_SDK_COMMIT" /opt/pico-sdk
    log "pico-sdk submodules (commits pinned by the tag)"
    git -C /opt/pico-sdk submodule update --init --depth 1 --recursive
    git -C /opt/pico-sdk submodule status --recursive > "$MBOT_REPORTS/pico-sdk-submodules.txt"
    stamp_write pico-sdk "$PICO_SDK_COMMIT"
fi

# ---------------------------------------------------------------- picotool
if stamp_matches picotool "$PICOTOOL_COMMIT" && [[ -x /usr/local/bin/picotool ]]; then
    log "picotool already installed ($PICOTOOL_TAG)"
else
    src="$MBOT_BUILD_TMP/picotool"
    git_pinned "$PICOTOOL_REPO" "$PICOTOOL_TAG" "$PICOTOOL_COMMIT" "$src"
    cmake -S "$src" -B "$src/build" -DPICO_SDK_PATH=/opt/pico-sdk -DCMAKE_BUILD_TYPE=Release
    make -C "$src/build" -j "$jobs"
    make -C "$src/build" install
    rm -rf "$src"
    stamp_write picotool "$PICOTOOL_COMMIT"
fi
log "picotool check: $(picotool version 2>&1 | head -1)"

# ---------------------------------------------------------------- firmware test build
log "test build of upstream mbot_firmware_ros (${MBOT_FIRMWARE_ROS_COMMIT:-unknown}), not kept"
fw="$MBOT_BUILD_TMP/firmware-test"
rm -rf "$fw"
cp -a "$UPSTREAM/mbot_firmware_ros" "$fw"
rm -rf "$fw/build"
(
    export PICO_SDK_PATH=/opt/pico-sdk PICO_TOOLCHAIN_PATH=/usr/bin/
    cmake -S "$fw" -B "$fw/build"
    make -C "$fw/build" -j "$jobs"
)
{
    echo "# Test build of mbot_firmware_ros ${MBOT_FIRMWARE_ROS_COMMIT:-unknown} with pico-sdk $PICO_SDK_TAG"
    (cd "$fw/build" && sha256sum ./*.uf2)
} > "$MBOT_REPORTS/firmware-test-build.txt"
uf2_count="$(find "$fw/build" -maxdepth 1 -name '*.uf2' | wc -l)"
[[ "$uf2_count" -gt 0 ]] || die "firmware test build produced no .uf2 files"
log "firmware test build OK: $uf2_count .uf2 files"
rm -rf "$fw"

log "done"
