#!/bin/bash
# Build the MBot server image (Track B) inside a privileged arm64 Linux container.
# Started by image/build.sh. Never run this on a robot.
#
# The container sees the MBOT-Dev folder at /work (repository in /work/mbot-dev, images in
# /work/images). The original base image is only read. All work happens on a copy in
# /work/images/work/build.img.
#
# Usage: build-image.sh [--resume] [--steps "00 10 20 30 35 40 50 60"] [--reports-from NAME]
#   --resume        reuse the existing working image and run the steps again (steps are idempotent)
#   --steps         run only these steps (sanitize, shrink and compress always run)
#   --reports-from  start from the reports of an earlier output NAME (for steps not rerun)

set -euo pipefail

TOP=/work
REPO="$TOP/mbot-dev"
IMAGES="$TOP/images"
WORK="$IMAGES/work"
BUILD_DIR="$REPO/image/build"
IMG="$WORK/build.img"
ROOT=/mnt/mbot-root
SCRATCH=/var/tmp/mbot-build
SOLUTION_HASHES=/var/tmp/mbot-solution-only.sha256

# shellcheck source=../manifests/versions.lock
. "$REPO/image/manifests/versions.lock"
# shellcheck source=build.conf
. "$BUILD_DIR/build.conf"

resume=0
steps="00 10 20 30 35 40 50 60"
reports_from=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --resume) resume=1; shift ;;
        --steps) steps="${2:?}"; shift 2 ;;
        --reports-from) reports_from="${2:?}"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done

log() { printf '[%s build-image] %s\n' "$(date '+%H:%M:%S')" "$*"; }
die() { log "ERROR: $*"; exit 1; }

[[ "$(uname -m)" == "aarch64" ]] || die "this build needs an arm64 Linux environment"
[[ -d "$REPO/image/build" && -d "$IMAGES" ]] || die "expected /work/mbot-dev and /work/images"

BUILD_DATE="$(date +%Y%m%d)"
OUT_NAME="${OUTPUT_NAME:-mbot-server-24.04.3-${BUILD_DATE}-${RELEASE_LABEL}}"
REPORTS_OUT="$IMAGES/${OUT_NAME}.reports"

MOUNTS=()
LOOPS=()
cleanup() {
    local i
    for (( i=${#MOUNTS[@]}-1; i>=0; i-- )); do
        umount "${MOUNTS[$i]}" 2>/dev/null || umount -l "${MOUNTS[$i]}" 2>/dev/null || true
    done
    MOUNTS=()
    for i in "${LOOPS[@]}"; do losetup -d "$i" 2>/dev/null || true; done
    LOOPS=()
}
trap cleanup EXIT

track_mount() { mount "$@"; MOUNTS+=("${*: -1}"); }
bind_ro() { mkdir -p "$2"; track_mount --bind "$1" "$2"; mount -o remount,bind,ro "$2"; }
unmount_from() {
    # Unmount every tracked mount added after index $1.
    local keep="$1" i
    for (( i=${#MOUNTS[@]}-1; i>=keep; i-- )); do
        umount "${MOUNTS[$i]}" 2>/dev/null || umount -l "${MOUNTS[$i]}"
        unset 'MOUNTS[i]'
    done
    MOUNTS=("${MOUNTS[@]}")
}

# Print "start size" in 512-byte sectors for partition $1 of the working image.
part_geometry() {
    sfdisk -d "$IMG" | grep -E "^${IMG}$1 :" | sed -E 's/.*start= *([0-9]+), size= *([0-9]+).*/\1 \2/'
}
# Attach partition $1 as a loop device and store its name in the variable named $2.
# (Not used in $( ), so the device is also recorded in LOOPS for cleanup.)
loop_part() {
    local start size dev
    read -r start size < <(part_geometry "$1")
    dev="$(losetup -f --show -o $((start * 512)) --sizelimit $((size * 512)) "$IMG")"
    LOOPS+=("$dev")
    printf -v "$2" '%s' "$dev"
}
fsck_ok() { local rc=0; e2fsck -fy "$1" || rc=$?; [[ $rc -le 1 ]] || die "e2fsck $1 failed ($rc)"; }

log "host tools"
apt-get update -qq
apt-get install -y -qq fdisk e2fsprogs xz-utils git zerofree ca-certificates >/dev/null
git config --global --add safe.directory '*'

# ------------------------------------------------------------------ base image
log "verify base image checksum"
base="$IMAGES/$BASE_IMAGE_FILE"
[[ -f "$base" ]] || die "base image not found: $base"
echo "$BASE_IMAGE_SHA256  $base" | sha256sum -c - || die "base image checksum mismatch"
grep -q "^$BASE_IMAGE_SHA256 [ *]$BASE_IMAGE_FILE\$" "$IMAGES/SHA256SUMS" \
    || die "checksum in versions.lock does not match $IMAGES/SHA256SUMS"

mkdir -p "$WORK"
if [[ $resume -eq 0 || ! -f "$IMG" ]]; then
    log "decompress a fresh working copy: $IMG"
    rm -f "$IMG" "$IMG.part"
    xz -dc -T0 "$base" > "$IMG.part"
    mv "$IMG.part" "$IMG"
else
    log "resume: reuse $IMG"
fi

log "grow working image to ${BUILD_IMAGE_SIZE_GIB} GiB"
target=$((BUILD_IMAGE_SIZE_GIB * 1024 * 1024 * 1024))
if [[ "$(stat -c %s "$IMG")" -lt $target ]]; then
    truncate -s "$target" "$IMG"
fi
echo ', +' | sfdisk --no-reread --no-tell-kernel -q -N 2 "$IMG"
sfdisk -d "$IMG"

LROOT=""; LBOOT=""
loop_part 2 LROOT
loop_part 1 LBOOT
fsck_ok "$LROOT"
resize2fs "$LROOT"

# ------------------------------------------------------------------ chroot
log "mount image root and boot partition"
mkdir -p "$ROOT"
track_mount "$LROOT" "$ROOT"
# The image has no /boot/firmware directory; systemd creates the mount point at boot.
mkdir -p "$ROOT/boot/firmware"
track_mount "$LBOOT" "$ROOT/boot/firmware"
base_mounts=${#MOUNTS[@]}

track_mount -t proc proc "$ROOT/proc"
track_mount -t sysfs sys "$ROOT/sys"
track_mount --bind /dev "$ROOT/dev"
track_mount --bind /dev/pts "$ROOT/dev/pts"
track_mount -t tmpfs tmpfs "$ROOT/run"
mkdir -p "$ROOT/run/systemd/resolve"
cp /etc/resolv.conf "$ROOT/run/systemd/resolve/stub-resolv.conf"
cp /etc/resolv.conf "$ROOT/run/systemd/resolve/resolv.conf"

rm -rf "$SCRATCH"
mkdir -p "$SCRATCH/reports" "$ROOT/tmp/mbot-build"
if [[ -n "$reports_from" ]]; then
    [[ -d "$IMAGES/$reports_from.reports" ]] || die "no reports for $reports_from"
    log "start from the reports of $reports_from (steps not rerun keep those reports)"
    cp -a "$IMAGES/$reports_from.reports/." "$SCRATCH/reports/"
    echo "$reports_from" > "$SCRATCH/reports/reports-carried-over-from.txt"
fi
track_mount --bind "$SCRATCH" "$ROOT/tmp/mbot-build"

# Only the parts of the repository the steps need. The solution submodule is never mounted.
for d in image system upstream/mbot_sys_utils upstream/mbot_ros2_ws upstream/mbot_firmware_ros \
         upstream/mbot_ros_labs upstream/mbot_servo_lib; do
    bind_ro "$REPO/$d" "$ROOT/tmp/mbot-dev/$d"
done
if [[ -d "$TOP/MBOT-Dev-Files/mwireless-setup" ]]; then
    bind_ro "$TOP/MBOT-Dev-Files/mwireless-setup" "$ROOT/tmp/mwireless-setup"
fi

log "policy-rc.d: no service starts during the build"
printf '#!/bin/sh\nexit 101\n' > "$ROOT/usr/sbin/policy-rc.d"
chmod 0755 "$ROOT/usr/sbin/policy-rc.d"

log "build environment for the steps"
sub_commit() { git -C "$REPO/upstream/$1" rev-parse HEAD; }
{
    printf 'MBOT_USER=%q\n' "$MBOT_USER"
    printf 'MBOT_DEFAULT_PASSWORD=%q\n' "$MBOT_DEFAULT_PASSWORD"
    printf 'MBOT_ROS2_WS_COMMIT=%q\n' "$(sub_commit mbot_ros2_ws)"
    printf 'MBOT_FIRMWARE_ROS_COMMIT=%q\n' "$(sub_commit mbot_firmware_ros)"
    printf 'MBOT_SYS_UTILS_COMMIT=%q\n' "$(sub_commit mbot_sys_utils)"
} > "$SCRATCH/build.env"
chmod 0600 "$SCRATCH/build.env"

for s in $steps; do
    script="$(find "$BUILD_DIR" -maxdepth 1 -name "${s}-*.sh" ! -name '90-*' | head -1)"
    [[ -n "$script" ]] || die "no build step $s"
    log "===== step $(basename "$script") ====="
    t0=$(date +%s)
    chroot "$ROOT" /usr/bin/env -i HOME=/root TERM=dumb LANG=C.UTF-8 \
        PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
        FK_MACHINE="$FK_MACHINE" MBOT_REPO=/tmp/mbot-dev MBOT_BUILD_TMP=/tmp/mbot-build \
        bash "/tmp/mbot-dev/image/build/$(basename "$script")"
    log "===== step $(basename "$script") finished in $(( $(date +%s) - t0 )) s ====="
done

log "image release: /etc/mbot/image-release (shown on the OLED and at login)"
mkdir -p "$ROOT/etc/mbot"
printf '%s %s\n%s\n' "$RELEASE_LABEL" "$(date +%Y-%m-%d)" "$OUT_NAME" > "$ROOT/etc/mbot/image-release"
chmod 0644 "$ROOT/etc/mbot/image-release"

log "finalize: release the build-time kernel hold, clean apt, collect facts"
held="$(chroot "$ROOT" apt-mark showhold)"
if [[ -n "$held" ]]; then
    # shellcheck disable=SC2086
    chroot "$ROOT" apt-mark unhold $held
fi
chroot "$ROOT" apt-get clean
R="$SCRATCH/reports"
# shellcheck disable=SC2016  # dpkg-query format string, not shell expansion
chroot "$ROOT" dpkg-query -W -f '${Package}\t${Version}\t${Architecture}\n' | sort > "$R/dpkg-list.tsv"
grep -E '^ros-' "$R/dpkg-list.tsv" > "$R/ros-packages-installed.tsv" || true
ls "$ROOT/lib/modules" > "$R/kernel.txt"
chroot "$ROOT" systemctl get-default > "$R/default-target.txt"
chroot "$ROOT" systemctl list-unit-files --state=enabled --no-pager --no-legend > "$R/enabled-units.txt"
du -sh "$ROOT/opt/ros" "$ROOT/opt/mbot" "$ROOT/opt/pico-sdk" "$ROOT/usr/local" "$ROOT/usr" > "$R/disk-usage.txt" 2>&1 || true
df -h "$ROOT" >> "$R/disk-usage.txt"
cp "$ROOT/boot/firmware/config.txt" "$R/config.txt"
cp "$ROOT/boot/firmware/cmdline.txt" "$R/cmdline.txt"
# Package comparison with the current course image (list taken from that image, see
# results/course-image-2026-01-15/README.md).
course="$REPO/results/course-image-2026-01-15/dpkg-packages.txt"
if [[ -f "$course" ]]; then
    comm -23 <(sort -u "$course") <(cut -f1 "$R/dpkg-list.tsv" | sort -u) > "$R/only-in-course-image.txt"
    comm -13 <(sort -u "$course") <(cut -f1 "$R/dpkg-list.tsv" | sort -u) > "$R/only-in-server-image.txt"
    log "compared with the course image: $(wc -l < "$R/only-in-course-image.txt") packages only there, $(wc -l < "$R/only-in-server-image.txt") only here"
fi

log "check: server image definition (D-03)"
grep -qx 'multi-user.target' "$R/default-target.txt" || die "default target is not multi-user.target"
desktop_re='^(gdm3|lightdm|sddm|ubuntu-desktop.*|gnome-shell|xfce4-session|nomachine|tigervnc.*|x11vnc|xrdp)\b'
if cut -f1 "$R/dpkg-list.tsv" | grep -E "$desktop_re"; then
    die "display manager, desktop session, VNC or NoMachine installed"
fi
cut -f1 "$R/dpkg-list.tsv" | grep -E '^xserver-xorg-core$' > "$R/xserver.txt" || echo "xserver-xorg-core not installed" > "$R/xserver.txt"

log "unmount build mounts"
unmount_from "$base_mounts"
rm -f "$ROOT/usr/sbin/policy-rc.d"
rm -rf "$ROOT/tmp/mbot-dev" "$ROOT/tmp/mbot-build" "$ROOT/tmp/mwireless-setup"

log "solution-only file hashes for the leak check"
: > "$SOLUTION_HASHES"
sol="$REPO/upstream/mbot_ros_labs_solution"
if [[ -n "$(ls -A "$sol" 2>/dev/null)" ]]; then
    src_files() { find "$@" -type f \( -name '*.cpp' -o -name '*.hpp' -o -name '*.h' -o -name '*.c' -o -name '*.py' \) \
        -not -path '*/.git/*' -size +0 -print0 | xargs -0 -r sha256sum | awk '{print $1}' | sort -u; }
    comm -23 <(src_files "$sol") <(src_files "$REPO/upstream/mbot_ros_labs" "$REPO/upstream/mbot_ros2_ws") > "$SOLUTION_HASHES"
    log "$(wc -l < "$SOLUTION_HASHES") solution-only source file hashes"
else
    log "WARNING: solution submodule not checked out; content check limited to directory names"
fi

log "===== step 90-sanitize.sh ====="
bash "$BUILD_DIR/90-sanitize.sh" --root "$ROOT" --solution-hashes "$SOLUTION_HASHES" \
    --config-template "$REPO/upstream/mbot_sys_utils/ros2_mbot_sys_utils/mbot_config.txt"

log "copy reports to $REPORTS_OUT"
rm -rf "$REPORTS_OUT"
cp -a "$R" "$REPORTS_OUT"

unmount_from 0
sync

# ------------------------------------------------------------------ shrink
log "shrink root file system (first boot grows it again)"
fsck_ok "$LROOT"
resize2fs -M "$LROOT"
bsize="$(dumpe2fs -h "$LROOT" 2>/dev/null | awk -F: '/^Block size/ {gsub(/ /,"",$2); print $2}')"
blocks="$(dumpe2fs -h "$LROOT" 2>/dev/null | awk -F: '/^Block count/ {gsub(/ /,"",$2); print $2}')"
margin=$(( 1024 * 1024 * 1024 / bsize ))
resize2fs "$LROOT" $(( blocks + margin ))
blocks="$(dumpe2fs -h "$LROOT" 2>/dev/null | awk -F: '/^Block count/ {gsub(/ /,"",$2); print $2}')"
fsck_ok "$LROOT"
log "zero free blocks for better compression"
zerofree "$LROOT"
for l in "${LOOPS[@]}"; do losetup -d "$l"; done
LOOPS=()

read -r p2_start _ < <(part_geometry 2)
p2_sectors=$(( (blocks * bsize / 512 + 2047) / 2048 * 2048 ))
echo "start=$p2_start, size=$p2_sectors, type=83" | sfdisk --no-reread --no-tell-kernel -q -N 2 "$IMG"
truncate -s $(( (p2_start + p2_sectors) * 512 )) "$IMG"
LROOT=""; LBOOT=""
loop_part 2 LROOT
fsck_ok "$LROOT"
losetup -d "$LROOT"
LOOPS=()
log "image size after shrink: $(( $(stat -c %s "$IMG") / 1024 / 1024 )) MiB"
sfdisk -d "$IMG"

# ------------------------------------------------------------------ outputs
manifest="$IMAGES/${OUT_NAME}.manifest.txt"
log "write manifest $manifest"
{
    echo "# MBot server image manifest"
    echo "image: ${OUT_NAME}.img.xz"
    echo "status: ${RELEASE_LABEL} ${BUILD_DATE}, not fully tested on hardware (see the README)"
    echo "built: $(date -u '+%Y-%m-%dT%H:%M:%SZ') in an arm64 Linux container ($(uname -r))"
    echo "repository: branch $(git -C "$REPO" rev-parse --abbrev-ref HEAD), commit $(git -C "$REPO" rev-parse HEAD)"
    echo "uncommitted changes in repository: $(git -C "$REPO" status --porcelain | wc -l) paths"
    echo "steps run in this build: $steps"
    [[ -n "$reports_from" ]] && echo "built on top of: $reports_from (its working image; reports of steps not rerun carried over)"
    echo "kernel: $(cat "$REPORTS_OUT/kernel.txt")"
    echo "default target: $(cat "$REPORTS_OUT/default-target.txt")"
    echo
    echo "## Base image and pinned versions (image/manifests/versions.lock)"
    grep -E '^[A-Z0-9_]+=' "$REPO/image/manifests/versions.lock"
    echo
    echo "## Submodule commits"
    git -C "$REPO" submodule status
    echo
    echo "## Source builds"
    cat "$REPORTS_OUT/micro-ros-agent-superbuild.txt" 2>/dev/null || true
    cat "$REPORTS_OUT/libcamera-subprojects.txt" 2>/dev/null || true
    echo
    echo "## ROS packages"
    cat "$REPORTS_OUT/ros-packages-installed.tsv"
    echo
    echo "## All Debian packages ($(wc -l < "$REPORTS_OUT/dpkg-list.tsv"))"
    cat "$REPORTS_OUT/dpkg-list.tsv"
} > "$manifest"

log "compress (xz) ${OUT_NAME}.img.xz"
xz -T0 -6 -c "$IMG" > "$IMAGES/${OUT_NAME}.img.xz.part"
mv "$IMAGES/${OUT_NAME}.img.xz.part" "$IMAGES/${OUT_NAME}.img.xz"
(cd "$IMAGES" && sha256sum "${OUT_NAME}.img.xz" > "${OUT_NAME}.img.xz.sha256")
{
    echo
    echo "## Output"
    echo "uncompressed size: $(stat -c %s "$IMG") bytes"
    echo "sha256: $(cut -d' ' -f1 "$IMAGES/${OUT_NAME}.img.xz.sha256")  ${OUT_NAME}.img.xz"
} >> "$manifest"

log "copy small reports into the repository (results/image-build/${OUT_NAME})"
res="$REPO/results/image-build/${OUT_NAME}"
rm -rf "$res"
mkdir -p "$res"
cp "$manifest" "$res/manifest.txt"
for f in ros-gui-deps.txt installed-gui-packages.txt rosdep-check.txt enabled-units.txt \
         disk-usage.txt config.txt cmdline.txt firmware-test-build.txt pico-sdk-submodules.txt \
         mwireless-setup.txt xserver.txt micro-ros-agent-superbuild.txt libcamera-subprojects.txt \
         oled-tests.txt oled-smoke-test.txt camera-ros-test-build.txt camera-ros-env-check.txt home.txt mbot-health.txt only-in-course-image.txt \
         only-in-server-image.txt; do
    [[ -f "$REPORTS_OUT/$f" ]] && cp "$REPORTS_OUT/$f" "$res/"
done

log "DONE: $IMAGES/${OUT_NAME}.img.xz"
cat "$IMAGES/${OUT_NAME}.img.xz.sha256"
