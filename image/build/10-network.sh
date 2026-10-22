#!/bin/bash
# Step 10: networking and remote access (D-09, NET-002, NET-006, OS-005).
# NetworkManager as the netplan renderer, hotspot dependencies, US regulatory domain,
# SSH with password login, cloud-init limited to first-boot tasks, HDMI console kept.
# Safe to run more than once.
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
require_image_chroot

mapfile -t pkgs < <(manifest_packages "$MANIFESTS/apt-packages.txt" 10)
apt_install "${pkgs[@]}"

log "netplan: NetworkManager renderer"
install_file "$SYSTEM_DIR/network/01-mbot-network-manager.yaml" /etc/netplan/01-mbot-network-manager.yaml 0600
rm -f /etc/netplan/50-cloud-init.yaml
install_file "$SYSTEM_DIR/network/10-globally-managed-devices.conf" \
    /etc/NetworkManager/conf.d/10-globally-managed-devices.conf 0644

log "systemd-networkd off (NetworkManager manages the interfaces)"
systemctl disable systemd-networkd.service systemd-networkd.socket \
    systemd-networkd-wait-online.service 2>/dev/null || true
systemctl enable NetworkManager.service NetworkManager-wait-online.service

log "Wi-Fi regulatory domain US (kernel command line)"
cmdline=/boot/firmware/cmdline.txt
if ! grep -q 'cfg80211.ieee80211_regdom=' "$cmdline"; then
    sed -i '1 s/$/ cfg80211.ieee80211_regdom=US/' "$cmdline"
fi
log "cmdline.txt: $(cat "$cmdline")"

log "SSH: password login, host key fallback"
install_file "$SYSTEM_DIR/ssh/40-mbot.conf" /etc/ssh/sshd_config.d/40-mbot.conf 0644
install_file "$SYSTEM_DIR/systemd/mbot-ssh-hostkeys.service" /etc/systemd/system/mbot-ssh-hostkeys.service 0644
systemctl enable mbot-ssh-hostkeys.service
if ! systemctl is-enabled --quiet ssh.socket && ! systemctl is-enabled --quiet ssh.service; then
    systemctl enable ssh.service
fi
log "ssh.socket: $(systemctl is-enabled ssh.socket 2>&1 || true), ssh.service: $(systemctl is-enabled ssh.service 2>&1 || true)"

log "cloud-init: first boot only (grow partition, new SSH host keys), no default user, no network config"
install_file "$SYSTEM_DIR/cloud-init/90-mbot.cfg" /etc/cloud/cloud.cfg.d/90-mbot.cfg 0644
install_file "$SYSTEM_DIR/cloud-init/user-data" /boot/firmware/user-data 0644

log "HDMI text console: $(systemctl is-enabled getty@tty1.service 2>&1 || true) (console=tty1 in cmdline.txt)"
grep -q 'console=tty1' "$cmdline" || die "console=tty1 missing from cmdline.txt"

# mwireless-setup is installed by step 35 (needs mbot-start-network from step 30).

log "done"
