#!/bin/bash
# Step 90: sanitize the image root before release (REL-002, risks R-C3, R-C4).
# Runs on the build host against a mounted image root, not inside the chroot, so it
# can check the image without the build mounts. Removes machine identity, SSH host keys,
# histories, caches, ROS logs (the rosdep cache stays), logs, Wi-Fi profiles except the
# hotspot, credentials and the test
# sudoers file. Then fails if any 802.1X profile, credential file or solution code remains.
# Safe to run more than once.
#
# Usage: 90-sanitize.sh --root DIR [--solution-hashes FILE] [--config-template FILE]
#   --solution-hashes  sha256 list of files that exist only in the solution repository
#   --config-template  the upstream mbot_config.txt; the image copy must be identical

set -euo pipefail

root=""
solution_hashes=""
config_template=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --root) root="${2:?}"; shift 2 ;;
        --solution-hashes) solution_hashes="${2:?}"; shift 2 ;;
        --config-template) config_template="${2:?}"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done

log() { printf '[%s 90-sanitize] %s\n' "$(date '+%H:%M:%S')" "$*"; }
fail=0
problem() { log "FAIL: $*"; fail=1; }

[[ -n "$root" && -d "$root/etc" && -d "$root/usr" ]] || { echo "Not an image root: ${root:-<none>}" >&2; exit 2; }
[[ "$root" != "/" ]] || { echo "Refusing to sanitize the build host (/)" >&2; exit 2; }
R="$root"

# Build mounts must be gone before checking, or the scan would see the repository.
extra_mounts="$(awk -v r="$R/" 'index($2, r) == 1 && $2 != r "boot/firmware" {print $2}' /proc/mounts)"
if [[ -n "$extra_mounts" ]]; then
    echo "Build mounts still present under $R. Unmount them first:" >&2
    echo "$extra_mounts" >&2
    exit 2
fi

log "remove the test sudoers file if present"
rm -f "$R/etc/sudoers.d/90-mbot-dev-test"

log "machine identity: empty /etc/machine-id, no SSH host keys (recreated on first boot)"
: > "$R/etc/machine-id"
rm -f "$R"/etc/ssh/ssh_host_*
[[ -L "$R/var/lib/dbus/machine-id" ]] || rm -f "$R/var/lib/dbus/machine-id"

log "Wi-Fi profiles: keep only the MBot hotspot (mbot_wifi_ap)"
nm_dir="$R/etc/NetworkManager/system-connections"
if [[ -d "$nm_dir" ]]; then
    find "$nm_dir" -type f -print0 | while IFS= read -r -d '' f; do
        if ! grep -qx 'id=mbot_wifi_ap' "$f"; then
            log "remove NetworkManager profile $(basename "$f")"
            rm -f "$f"
        fi
    done
fi
rm -f "$R"/etc/wpa_supplicant/*.conf

log "credentials, histories, caches"
for home in "$R/root" "$R"/home/*; do
    [[ -d "$home" ]] || continue
    rm -rf "$home/.git-credentials" "$home/.config/gh" "$home/.netrc" "$home/.docker" \
        "$home/.bash_history" "$home/.python_history" "$home/.lesshst" "$home/.viminfo" \
        "$home/.wget-hsts" "$home/.cache" "$home/.ros/log" "$home/.ssh/known_hosts"
done
rm -rf "$R"/tmp/* "$R"/var/tmp/*
rm -f "$R"/var/cache/apt/archives/*.deb "$R"/var/cache/apt/*.bin
find "$R/var/lib/apt/lists" -maxdepth 1 -type f ! -name lock -delete
rm -rf "$R/var/lib/mwireless"
# The login message would otherwise show the build container's IP, load and user count.
rm -f "$R/var/lib/landscape/landscape-sysinfo.cache"

log "logs and cloud-init state (first boot runs cloud-init again)"
find "$R/var/log" -type f -delete
rm -rf "$R"/var/log/journal/*
rm -rf "$R"/var/lib/cloud/*
rm -f "$R/usr/sbin/policy-rc.d"

# ------------------------------------------------------------------ checks
log "check: no 802.1X or Wi-Fi password profiles"
if [[ -d "$nm_dir" ]] && grep -rlE '^\[802-1x\]|^eap=|^identity=' "$nm_dir" 2>/dev/null; then
    problem "802.1X profile present in $nm_dir"
fi
if grep -rlsE '^\s*(psk|password)=' "$R/etc/wpa_supplicant" 2>/dev/null; then
    problem "wpa_supplicant configuration with a password present"
fi

log "check: no credential files"
while IFS= read -r f; do
    problem "credential file present: ${f#"$R"}"
done < <(find "$R/root" "$R/home" "$R/etc" \( -name '.git-credentials' -o -name '.netrc' \
    -o -path '*/.config/gh/hosts.yml' -o -name '90-mbot-dev-test' -o -name 'id_rsa' \
    -o -name 'id_ed25519' -o -name 'id_ecdsa' \) 2>/dev/null)

log "check: machine-id empty, no SSH host keys"
[[ ! -s "$R/etc/machine-id" ]] || problem "/etc/machine-id is not empty"
compgen -G "$R/etc/ssh/ssh_host_*" >/dev/null && problem "SSH host keys present"

if [[ -n "$config_template" ]]; then
    log "check: /boot/firmware/mbot_config.txt is the upstream template (no real Wi-Fi details)"
    if [[ -f "$R/boot/firmware/mbot_config.txt" ]] && ! cmp -s "$config_template" "$R/boot/firmware/mbot_config.txt"; then
        problem "mbot_config.txt differs from the upstream template"
    fi
fi

log "check: no solution code"
while IFS= read -r d; do
    problem "solution directory present: ${d#"$R"}"
done < <(find "$R/home" "$R/root" "$R/opt" "$R/srv" "$R/usr/local" -type d -name 'mbot_ros_labs*' 2>/dev/null)
if [[ -n "$solution_hashes" && -s "$solution_hashes" ]]; then
    found="$(find "$R/home" "$R/root" "$R/opt" "$R/srv" "$R/usr/local" -type f \
        \( -name '*.cpp' -o -name '*.hpp' -o -name '*.h' -o -name '*.c' -o -name '*.py' \) \
        -print0 2>/dev/null | xargs -0 -r sha256sum | awk '{print $1}' | sort -u \
        | comm -12 - <(awk '{print $1}' "$solution_hashes" | sort -u) | wc -l)"
    log "solution-only file hashes found in image: $found (checked $(wc -l < "$solution_hashes") hashes)"
    [[ "$found" -eq 0 ]] || problem "$found files with solution-only content found"
else
    log "WARNING: no solution hash list given; only the directory name check ran"
fi

if [[ "$fail" -ne 0 ]]; then
    log "SANITIZE FAILED"
    exit 1
fi
log "sanitize OK"
