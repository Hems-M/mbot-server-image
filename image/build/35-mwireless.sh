#!/bin/bash
# Step 35: MWireless setup tool (D-09, NET-001 partial).
# Installs system/network/mwireless/mwireless-setup as /usr/local/bin/mwireless-setup.
# Does not run it and creates no Wi-Fi profile. Checks that it runs, that the CA it
# trusts is present, and that the names it expects from the MBot system layer exist.
# Needs step 30 (mbot-start-network). Safe to run more than once.
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
require_image_chroot

src="$SYSTEM_DIR/network/mwireless/mwireless-setup"
dest=/usr/local/bin/mwireless-setup
expected_version="1.2.0"

log "install $dest (root, 0755)"
install -D -o root -g root -m 0755 "$src" "$dest"

report="$MBOT_REPORTS/mwireless-setup.txt"
{
    echo "# mwireless-setup checks inside the image"
    echo "sha256: $(sha256sum "$dest" | cut -d' ' -f1)"
} > "$report"

log "check: --version"
version_out="$("$dest" --version)"
echo "--version: $version_out" >> "$report"
[[ "$version_out" == "mwireless-setup $expected_version" ]] || die "unexpected version output: $version_out"

log "check: --help"
help_out="$("$dest" --help)" || die "--help failed"
grep -q 'Usage' <<< "$help_out" || die "--help output has no Usage section"
echo "--help: OK ($(wc -l <<< "$help_out") lines)" >> "$report"

log "check: pinned USERTrust root CA present and matching the script's fingerprint"
ca_file=/etc/ssl/certs/USERTrust_RSA_Certification_Authority.pem
[[ -r "$ca_file" ]] || die "$ca_file missing (ca-certificates)"
pinned="$(sed -n 's/^MW_ROOT_CA_SHA256="\([^"]*\)".*/\1/p' "$dest" | tr 'a-f' 'A-F')"
actual="$(openssl x509 -in "$ca_file" -noout -fingerprint -sha256 | sed 's/^.*=//' | tr 'a-f' 'A-F')"
[[ -n "$pinned" && "$pinned" == "$actual" ]] || die "CA fingerprint mismatch: script $pinned, file $actual"
echo "CA: $ca_file fingerprint matches the pinned value" >> "$report"

log "check: interface contract with the MBot system layer"
fallback_con="$(sed -n 's/^MW_FALLBACK_CON="\([^"]*\)".*/\1/p' "$dest")"
fallback_service="$(sed -n 's/^MW_FALLBACK_SERVICE="\([^"]*\)".*/\1/p' "$dest")"
[[ "$fallback_con" == "mbot_wifi_ap" ]] || die "script expects hotspot '$fallback_con', not mbot_wifi_ap"
grep -q "con-name $fallback_con" /usr/local/etc/mbot_start_networking.sh \
    || die "mbot_start_networking.sh does not create '$fallback_con'"
[[ "$fallback_service" == "mbot-start-network.service" ]] || die "script expects unit '$fallback_service'"
[[ -f "/etc/systemd/system/$fallback_service" ]] || die "$fallback_service not installed (run step 30 first)"
systemctl is-enabled --quiet "$fallback_service" || die "$fallback_service not enabled"
echo "contract: hotspot $fallback_con created by mbot_start_networking.sh; $fallback_service installed and enabled" >> "$report"

log "check: programs the script calls"
for cmd in nmcli openssl flock systemd-run timedatectl journalctl; do
    command -v "$cmd" >/dev/null || die "required program missing: $cmd"
done
for cmd in curl rfkill ss ping; do
    if command -v "$cmd" >/dev/null; then
        echo "optional program present: $cmd" >> "$report"
    else
        log "WARNING: optional program missing: $cmd"
        echo "optional program missing: $cmd" >> "$report"
    fi
done
nm_version="$(dpkg-query -W -f '${Version}' network-manager)"
echo "network-manager: $nm_version (the script needs 1.42 or newer to skip certificate date checks)" >> "$report"

echo "not installed: mwireless.conf, cert refresh timer, boot drop-in, login banner (see system/network/mwireless/README.md)" >> "$report"
log "report written: $report"
log "done"
