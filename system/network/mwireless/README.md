# mwireless-setup

Connects an MBot to U-M MWireless (WPA2-Enterprise, PEAP/MSCHAPv2) from a terminal, so no desktop is needed. Students run `sudo mwireless-setup` over SSH. See `mwireless-setup --help`.

- **Version:** 1.2.0
- **Source:** 1.1.0 copied from `MBOT-Dev-Files/mwireless-setup/mwireless-setup` on 2026-10-14 (SHA256 `e6442873...4af60c`). 1.2.0 (2026-10-16, on Hemanth's request): University of Michigan maize and blue theme for the screen output (banner, four step headers, prompts, heads-up box, `--status` dashboard), the same palette as the ROBuntu tools. Connection, certificate and clock logic unchanged
- **SHA256 (1.2.0):** `cc69586157f35793dbf5d8ebac8b2b1a7d8c45a0bf334761a9fc56c2ee01ebbc`
- **Installed by:** `image/build/35-mwireless.sh` to `/usr/local/bin/mwireless-setup` (root, 0755). The build does not run it and creates no Wi-Fi profile.
- **Status:** not tested on a robot or against real MWireless.

## Interface contract

The script expects these names from the MBot system layer (review finding MW4). `35-mwireless.sh` checks both at build time.

| Name | Used for |
|------|----------|
| `mbot_wifi_ap` | NetworkManager hotspot profile created by `mbot_start_networking.sh` |
| `mbot-start-network.service` | Restarted to bring the hotspot back after a failed attempt |

## Not included yet

These parts of the full package are missing (review finding MW1) and are not in the image. They are needed for NET-001.

| Part | Effect while missing |
|------|----------------------|
| `mwireless.conf` | None for normal use: the script has the same defaults built in. Site overrides are not possible |
| `systemd/` units: `mwireless-cert-refresh.service` and `.timer` | No weekly certificate refresh. The script still refreshes certificates after each successful connection |
| `systemd/mwireless-boot.service` | No zero-touch setup from `mbot_config.txt` (off by default in the package anyway) |
| `systemd/mbot-start-network.service.d/10-wait-mwireless.conf` | At boot, `mbot-start-network` does not wait for MWireless. On campus the hotspot may start before MWireless connects |
| `motd/90-mwireless` | No MWireless status in the SSH login banner. Use `sudo mwireless-setup --status` |
| `tools/customize-image.sh` | Track A (OS-007) cannot be built |
| `install.sh` extras | No pre-built CA bundle (built on first run) and no `/etc/mwireless/build-epoch` clock floor |

`install.sh`, `README.md` and `wifi.sh` from the original folder are not copied. `wifi.sh` is not supported (review finding MW2).

## Known style issues

The script uses em dashes in comments and the theme symbols ✔ ▲ ◆ in output, which `docs/style-guide.md` does not allow in docs. The output symbols are deliberate (same as the ROBuntu tools); the em dashes in comments are left for NET-001.
