#!/bin/bash
# Step 00: base system (OS-002, D-16).
# apt sources and policy, security updates, locale, time zone, hostname, user mbot,
# basic tools. Safe to run more than once.
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
require_image_chroot

log "apt sources: add noble-updates (the Raspberry Pi image lists only noble and noble-security)"
sources=/etc/apt/sources.list.d/ubuntu.sources
if ! grep -q 'noble-updates' "$sources"; then
    sed -i 's/^Suites: noble$/Suites: noble noble-updates/' "$sources"
fi
grep -q 'noble-updates' "$sources" || die "could not add noble-updates to $sources"

log "apt policy: block Ubuntu libcamera, security-only unattended upgrades"
install_file "$SYSTEM_DIR/apt/mbot-block-ubuntu-libcamera" /etc/apt/preferences.d/mbot-block-ubuntu-libcamera 0644
install_file "$SYSTEM_DIR/apt/52mbot-unattended-upgrades" /etc/apt/apt.conf.d/52mbot-unattended-upgrades 0644

# Keep the kernel and boot firmware of the pinned base image during the build.
# build-image.sh removes the hold at the end (the kernel is not held in the image yet).
mapfile -t kernel_pkgs < <(dpkg-query -W -f '${db:Status-Abbrev} ${Package}\n' 'linux-*raspi*' 'linux-firmware-raspi' 2>/dev/null \
    | awk '$1 == "ii" {print $2}' || true)
if [[ ${#kernel_pkgs[@]} -gt 0 ]]; then
    log "hold during build: ${kernel_pkgs[*]}"
    apt-mark hold "${kernel_pkgs[@]}" >/dev/null
fi

log "apt-get update and upgrade"
apt-get "${APT_RETRY[@]}" update
apt-get "${APT_RETRY[@]}" -y upgrade

mapfile -t pkgs < <(manifest_packages "$MANIFESTS/apt-packages.txt" 00)
apt_install "${pkgs[@]}"

# Server image definition (D-03). Ubuntu Server images default to graphical.target.
log "default boot target: multi-user.target"
systemctl set-default multi-user.target

log "locale en_US.UTF-8"
ensure_line /etc/locale.gen 'en_US.UTF-8 UTF-8'
locale-gen en_US.UTF-8
update-locale LANG=en_US.UTF-8

log "time zone America/Detroit"
ln -sfn /usr/share/zoneinfo/America/Detroit /etc/localtime
printf 'America/Detroit\n' > /etc/timezone

# mbot-start-network replaces this name with mbot_hostname from mbot_config.txt at boot.
log "default hostname mbot-0000 (matches the mbot_config.txt template)"
printf 'mbot-0000\n' > /etc/hostname
if grep -q '^127\.0\.1\.1' /etc/hosts; then
    sed -i 's/^127\.0\.1\.1.*/127.0.1.1\tmbot-0000/' /etc/hosts
else
    printf '127.0.1.1\tmbot-0000\n' >> /etc/hosts
fi

log "user ${MBOT_USER}"
[[ -n "${MBOT_DEFAULT_PASSWORD:-}" ]] || die "MBOT_DEFAULT_PASSWORD not set (image/build/build.conf)"
if ! id "$MBOT_USER" >/dev/null 2>&1; then
    useradd --create-home --shell /bin/bash --comment "MBot" "$MBOT_USER"
fi
# dialout: Pico USB serial, GPIO (/dev/gpiochip*) and I2C on this image's udev rules.
# video: camera. sudo: administration. adm: read logs. No separate gpio or i2c group is needed.
for g in sudo adm dialout video plugdev netdev render input; do
    if getent group "$g" >/dev/null; then
        usermod -aG "$g" "$MBOT_USER"
    fi
done
printf '%s:%s\n' "$MBOT_USER" "$MBOT_DEFAULT_PASSWORD" | chpasswd
log "groups of ${MBOT_USER}: $(id -nG "$MBOT_USER")"

log "done"
