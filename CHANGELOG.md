# Changelog

## 2026-10-22

First release. Built from the development release candidates rc0 to rc7, plus the latest `mbot_firmware_ros` (`2aeb657`).

- Ubuntu Server 24.04.3 and ROS 2 Jazzy without a desktop, with the same home folder, workspace, Pico SDK and tools as the ROB550 desktop image.
- Camera: Raspberry Pi libcamera and rpicam-apps for the Pi 5; `camera_ros` from the student workspace works.
- OLED: IP address in large digits, Wi-Fi name, battery voltage, health page, MBot animation, a shutdown animation, and warnings only for problems that last.
- `mbot --help`, `mbot health` (with `--live`), `mbot report`, `mbot-viz`, and a command manual in the home folder.
- `mwireless-setup` 1.2.0: MWireless from the terminal, in Maize and Blue.
- Firmware flashing without the white/green wire: `mbot-upload-firmware` asks the Pico over USB, or for the buttons. The boot script no longer drives the Pico pins. Firmware patch for USB flashing in `system/firmware/`.
- Pi 5 fan check in `mbot health`.
- ROB550 website pages for the server image in `website/`, with `serve.sh` to open them locally.
