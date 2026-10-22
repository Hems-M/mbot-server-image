# Build notes: MBot server image

These notes were written while the image was developed (release candidates rc0 to rc7), in a working repository with a different layout: `docs/course-site/` there is `website/` here, `reference/course-docs` is `website/rob550-docs`. Task and decision numbers (D-, P-, OLED-, REL-) refer to that work. The release 2026-10-22 is rc7 plus the latest `mbot_firmware_ros`.


- **Status:** rc6 (section 0d): rc5 plus flashing without the Pi GPIO pins (P-38), `mbot health --live`, and course-site fixes for Foxglove and camera calibration. rc5 (section 0c, built 2026-10-16) was used on a robot by Hemanth. rc6 and rc7 (section 0e) were built on 2026-10-21 and are **not tested on a robot**. Every decision below is PROVISIONAL until the ADRs (ARCH-001) are approved and the image passes the first-boot test plan at the end of this file.
- **Track:** B (clean Ubuntu Server 24.04 build from scripts).
- **Author:** Hemanth (with Claude), autonomous build session.
- **Branch:** `local/image-build`.

## 0e. rc7: voltage only, fan check, mbot report

Hemanth (2026-10-21): remove the battery percentage and keep the voltage; check the Pi 5 fan in `mbot health` and not on the OLED; add `mbot report`.

| Item | Change |
|------|--------|
| Battery | Voltage only on the OLED (main status line, health page, MBot page), in `mbot health` and `--live`. The words "low", "motor power off" and "no jumper" come from the alert thresholds (`battery_state` in `alerts.py`). P-37 and the `battery_full_v` / `battery_empty_v` settings removed |
| Fan (P-39) | `fan.py`: the `pwmfan` hwmon device (`pwm1`, `fan1_input`). Warning "Fan not spinning" when the Pi drives the fan and it reports 0 rpm in every reading (2 readings in `mbot health`, 3 in `--live`). Not in `current_problems`, so the OLED never shows it |
| `mbot report` | `system/tools/mbot-report`: health, system, hardware, network, ROS, logs of this boot and the previous one, in `~/mbot-report-<host>-<time>.tar.gz`. Passwords removed from `mbot_config.txt` and their values blanked in every file |

## 0d. rc6: flashing without GPIO, live health view

Course staff (2026-10-21): the white/green cable between the Pi and the control board shorts the Pi's GPIO pins when BOOTSEL or RST is pressed, which damages the GPIO controller and makes the Pi 5 overheat. Students should unplug it and flash with the buttons. Hemanth asked to put a USB-based fix (prepared in `Claude/2-safe-flashing/`) in the next image, for a live `mbot health`, and for a clear answer on the Foxglove layout and on the camera calibrator window that did not open.

| Item | Cause or decision | Change |
|------|-------------------|--------|
| GPIO 4 and 17 driven by the Pi | Upstream `mbot-upload-firmware` and `mbot_start_networking.sh` (every boot) set both pins as outputs with `gpioset`. With libgpiod 1.6.3 (the image's `gpiod`), `gpioset` leaves the line an output after it exits | P-38: our `system/firmware/mbot-upload-firmware` replaces the upstream script; the installed copy of `mbot_start_networking.sh` is patched (`system/firmware/mbot_start_networking-release-gpio.patch`) to set both pins to inputs with no pull. The build fails if either still contains `gpioset` |
| Flashing without buttons | Upstream firmware does not reboot into BOOTSEL on a 1200 baud request: with `tinyusb_device` linked directly, pico-sdk 2.2.0 compiles out its handler (`PICO_STDIO_USB_ENABLE_RESET_VIA_BAUD_RATE` 0) | `mbot-upload-firmware` asks over `/dev/mbot_debug` at 1200 baud; firmware with the change in `comms/src/dual_cdc.c` (patch in `Claude/2-safe-flashing/`, for the course firmware repository) reboots into BOOTSEL. Otherwise it prints the button steps and waits 30 s in a terminal. Checked: the patched firmware builds with pico-sdk 2.2.0 and links `reset_usb_boot` in `mbot_classic_ros` and `mbot_calibrate_classic`; the script passes 11 cases with stand-ins and never calls GPIO tools |
| `mbot health --live` | Requested | `system/oled/mbot_oled/live.py`: battery, system, robot, network and problems every second, with an event log (Pico in or out, LiDAR or camera started or stopped, new IP, problems raised and resolved) |
| Foxglove layout | One way only, the course way | Course site and manual: no layout import. Turn on `/scan` and `/robot_description` in the 3D panel, set the Pose topic to `/goal_pose`. The layout file stays in `/opt/mbot/share/foxglove/` (unused) |
| Camera calibrator window did not open | `cameracalibrator` opens its window only after the first image; the image has `X11Forwarding yes` and `xauth` (checked in the rc5 image) | Checkpoint 4: keep the camera node running, XQuartz needs a log out and in, SSH from the laptop's own terminal, check `echo $DISPLAY`, a test window |

## 0c. rc5: OLED animation, IP on every screen, course Foxglove steps

Feedback from Hemanth on rc4 (2026-10-16): no LiDAR in Foxglove (bringup was not running, and `mbot-viz` was started three times at once), network line without the band, an MBot animation back, a shutdown animation, the IP on every screen, colours for warnings and errors.

| Item | Change |
|------|--------|
| OLED 2.1.0 | SSID only; health page with the IP and uptime in the status line; MBot page (drive in, LiDAR scan that draws the walls, drive off); shutdown animation ending on a sleeping MBot; errors flash, warnings stay steady (the SSD1306 has one colour) |
| `mbot-viz` | Lock per port: a second start says the bridge is already running; warns when the LiDAR is not running |
| Course site | Foxglove started with the course command (`ros2 launch foxglove_bridge foxglove_bridge_launch.xml`) plus bringup; checkpoint 1 back to the course text |

## 0b. rc4: OLED redesign, health report, Foxglove layout, UM theme

Feedback from Hemanth on rc3 (2026-10-16): camera feed works in Foxglove but the LiDAR does not show; the OLED looked improvised (tick marks, page rotation) and should report real problems only, plus battery, percentage, heat, RAM and disk; `mbot --help` should be organized and include commands that help students read the code; a health command should list everything the robot knows; `mwireless-setup` should use the maize and blue theme of the ROBuntu tools; the course site should be more organized, with clear checkpoint steps and the student work unchanged.

| Item | Cause or decision | Change |
|------|-------------------|--------|
| LiDAR not shown in Foxglove | Not an image fault. `/scan` was published (bringup log: 10 Hz, frame `lidar_link`, which is in the TF tree), but the Default layout of Foxglove's 3D panel does not subscribe to `/scan` or `/robot_description` (Topics list in the screenshot: `/tf` 125 Hz, `/scan` no rate). The second bringup in the log failed with `SL_RESULT_OPERATION_TIMEOUT` because the first one held the LiDAR. Foxglove's publish tool also defaulted to `/move_base_simple/goal` (bridge log), which the MBot code does not read | MBot Foxglove layout `system/foxglove/mbot-layout.json` (3D with robot, scan, map, paths, particles and poses on; Image; battery Plot; publish tool to `/goal_pose` and `/initialpose`), in the image at `/opt/mbot/share/foxglove/` and on the course site. `mbot-viz` prints how to get it. Foxglove Guide page on the course site |
| OLED 2.0 | Redesign | One main screen (robot name with signal, IP in large digits, network, `READY` with battery percentage and voltage), an animated health page (battery gauge, temperature, CPU, RAM, disk), alert cards only for persistent problems (P-36), short notices, a liveness pixel. Text rendered antialiased and cut to 1 bit for even spacing. No tick marks, no driving animation |
| Battery percentage | Estimate only | 3-cell Li-ion curve between 9.0 V and 12.6 V, settable with `battery_empty_v` and `battery_full_v` in `mbot_config.txt` (P-37). Displayed values use the 30 s median |
| `mbot health` (`mbot-status`) | Requested | Network (IP, Wi-Fi, signal, gateway, internet, clock, MAC), robot (Pico, agent, firmware data, battery, odometry, LiDAR, camera, Foxglove), system (CPU, load, temperature, memory, disk, under-voltage and throttling now and since boot, uptime), services, image, problems with what to do. Same rules as the OLED. Exit code 0, 1 (warnings) or 2 (errors) |
| `mbot` and `mbot --help` | Requested | `mbot help`, `mbot health`, `mbot viz`, `mbot wifi`, `mbot version`. `mbot-help` by topic (start, network, firmware, ros, code, build, sensors, viz, data, fix), with a "code" topic for reading the code (message fields, executables, launch arguments, package prefix, TF tree, finding TODOs). UM theme shared in `/opt/mbot/lib/mbot-theme.sh` |
| `mwireless-setup` 1.2.0 | Requested | UM theme for the output only (banner, steps 1/4 to 4/4, prompts, heads-up box, `--status` dashboard). Logic unchanged |
| Course site | Requested | Setup page reorganized (Foxglove setup before the tests that use it, "Check your mbot" step); new Foxglove Guide; every checkpoint uses `mbot-viz` with one link to the guide. Tasks unchanged |

## 0a. rc3: fixes from the rc2 robot test

Hemanth flashed rc2 on a robot on 2026-10-15. Boot, SSH, home folder, MWireless, firmware build and flash, `mbot_ws` build and LiDAR worked. Results and causes: `results/validation/rc2/mbot-0000/2026-10-15.md`.

| Problem on the robot | Cause | Fix in rc3 |
|----------------------|-------|------------|
| `rpicam-hello` and `rpicam-still`: "symbol lookup error ... ipa_rpi_pisp.so ... GetDebin" | `ros-jazzy-camera-ros` and `ros-jazzy-libcamera` (pulled by `apriltag_ros` 3.4.0) put libpisp 1.5.0 into `/opt/ros/jazzy/lib`, which is in `LD_LIBRARY_PATH` of every ROS shell. The Pi IPA module needs the libpisp 1.2.0 it was built with. The rc2 check ran `ldd` without the ROS environment | Placeholder package instead of the two ROS packages; build checks the camera stack with the ROS environment (P-30) |
| `rosdep install`: "rosdep installation has not been initialized" | No rosdep cache for `mbot` (the sanitizer deleted `~/.ros`) | Cache built as `mbot` in step 60, kept by the sanitizer (only `~/.ros/log` is removed) |
| Login message showed the build container's IP and time | `landscape-sysinfo.cache` from the build | Sanitizer removes it |
| "Failed to connect to changelogs.ubuntu.com" at login on campus | release-upgrade check | `Prompt=never` in `/etc/update-manager/release-upgrades` |
| `colcon` warning that `camera_ros` overrides `/opt/ros/jazzy` | as the camera problem | gone |
| Foxglove: "package 'mbot_interfaces' not found" | bridge started by hand in a shell without `mbot_ws` sourced | Documented (manual, course site): `mbot-viz`, or source first |
| `SecureW2_JoinNow.run`: "license has expired" | SecureW2 license | Documented; `mwireless-setup` is the way |

The course website with the new instructions is in `docs/course-site/` (DOC-003).

## 0. rc2: what changed and why

Feedback on rc1 from Hemanth (2026-10-14): no animation on the OLED and not enough useful information on it; the home folder was empty; a command manual for after the first boot was missing; everything on the current course image must also be on the server image.

To answer "everything that was there before" with facts instead of guesses, the current course image `2026-01-15-mbot-ros2-base-ubuntu24.img` (in `MBOT-Files/` on Hemanth's Mac) was attached read-only and compared with rc1. The facts are in `results/course-image-2026-01-15/`.

| Change | Where | Why |
|--------|-------|-----|
| New OLED service. Boot animation (the MBot is put together part by part), "Ready!" screen, network page (hostname that scrolls when long, Wi-Fi bars, SSID and band or hotspot name, Pico, agent and firmware status, uptime, Foxglove indicator), health page (battery with wiring diagnosis, CPU, temperature, RAM, disk, power supply), system page (image release, MAC address), alert page, driving MBot animation. The IP is always in the bottom strip | `system/oled/`, `system/systemd/mbot-oled.service`, step 30 | rc1 still ran the upstream 3-page script. Design from review section 11.3 (D-17). Previews in `results/oled-preview/` |
| `i2c-dev` loaded at boot | `system/modules-load/mbot.conf` | Neither image loads it explicitly [CODE]. Harmless if the driver is built into the kernel |
| Home folder like the course image: Desktop, Documents, Downloads, Music, Pictures, Public, Templates, Videos, `SecureW2_JoinNow.run`, `pico-sdk` (link to `/opt/pico-sdk`), `microros_ws/install` (link to `/opt/mbot/microros`), the MBot `.bashrc` lines, `MBOT_COMMANDS.md` | step 60 (new), `system/home/` | Course image home listing (`home-mbot.txt`). Links instead of copies keep the system parts root-owned (D-05), and the course paths still work |
| Command manual: first boot to everyday use, troubleshooting, differences from the desktop image. `mbot-help` shows or searches it; the SSH login message points to it | `system/home/MBOT_COMMANDS.md`, `system/tools/mbot-help`, `system/motd/99-mbot` | Requested |
| Login message: MBot summary (name, IP, image release, agent, OLED, Pico). Ubuntu help-text and news lines turned off | step 60 | Shorter login screen; `motd-news` no longer fetches news |
| `/etc/mbot/image-release` | `build-image.sh` | The OLED and the login message show which image a robot runs |
| Packages of the course image that are not GUI or desktop: `avahi-daemon`, `libnss-mdns`, `gdb`, `zip`, `jq`, `rsync`, `bison`, `flex`, `autoconf`, `automake`, `autotools-dev`, `libtool`, `libusb-dev`, `libgsl-dev`, `libatlas-base-dev`, GL and GLUT headers, `python3-dev`, `python3-scipy`, `python3-opencv`, `gpg`, `apt-transport-https` | `apt-packages.txt` (tag `[OLD]`) | Upstream `install_mbot_dependencies.sh` and the course image package list |
| All non-GUI members of `navigation2` and `image_pipeline` (Nav2 planners, controllers, smoothers, `nav2_simple_commander`, docking; `depth_image_proc`, `image_rotate`, `image_publisher`, `stereo_image_proc`), `vision_msgs` | `ros-packages.txt` | The course image installs both metapackages. Left out on purpose: `rviz2`, `rqt*`, `nav2_rviz_plugins`, `image_view`, `nav2_bringup` (pulls Gazebo; no MBot launch file uses it [CODE]) |
| `clang-format` and three `ament_cmake` lint tools | manifests | `rosdep` keys of the `camera_ros` tests (G-13) |
| Camera stack pinned to the course image versions: libcamera `v0.5.1+rpt20250722`, rpicam-apps `v1.8.1`, libav encoder on | `versions.lock`, step 40 | The student `camera_ros` does not compile against the libcamera 0.6 of rc0 and rc1 (P-21). Found by the new test build |
| ROS libcamera hidden from student builds; test build of the student `camera_ros` | step 40 | P-30, a problem found while comparing rc1 with the course image |
| Package comparison with the course image in every build | `build-image.sh` | `only-in-course-image.txt` and `only-in-server-image.txt` in the reports |

What the course image has that rc2 still does not have, on purpose: the GNOME desktop, NoMachine, snap applications (Firefox, Thunderbird, Snap Store), printing (CUPS), Bluetooth audio, `rviz2`, `rqt`, Gazebo libraries pulled in by `nav2_bringup`, and the libraries only those need. The full list is `only-in-course-image.txt` in the build reports.

## 1. What was built

### rc7 (current)

| Item | Value |
|------|-------|
| Output | `../images/mbot-server-24.04.3-20261021-rc7.img.xz` (2,446,423,056 bytes), `.img.xz.sha256`, `.manifest.txt`, `.reports/` |
| SHA256 | `146ebe73fce316e3c917c706a0183e21880a8a77e4c3b49e26b74d2820d5a7ef` |
| Build | Clean build of all steps, 2026-10-21, log `../images/work/logs/build-rc7.log` |
| Checks passed in the build | OLED unit tests (67) and smoke test (exits 600 ms after SIGTERM); `mbot health` as `mbot` with the new Fan row (`mbot-health.txt`, "not found" in the build container); `mbot-report` installed; the rc6 GPIO checks |

### rc6

| Item | Value |
|------|-------|
| Output | `../images/mbot-server-24.04.3-20261021-rc6.img.xz` (2,441,010,992 bytes), `.img.xz.sha256`, `.manifest.txt`, `.reports/` |
| SHA256 | `6cf2c2b73869045a2d74d909113a39b19902dfc498195e8a93bacb005246b5ea` |
| Build | Clean build of all steps, 2026-10-21, log `../images/work/logs/build-rc6.log` |
| Checks passed in the build | P-38 patch applied and no `gpioset` left in `mbot_start_networking.sh`; our `mbot-upload-firmware` installed with no GPIO calls (both also checked in the finished image); OLED unit tests (62) and smoke test (exits 800 ms after SIGTERM); the rc5 checks |

### rc5

| Item | Value |
|------|-------|
| Output | `../images/mbot-server-24.04.3-20261016-rc5.img.xz` (2,444,601,880 bytes), `.img.xz.sha256`, `.manifest.txt`, `.reports/` |
| SHA256 | `d1223350a55a5f393fb40a9314eca574009f53fdac37038170f5b466c6b46138` |
| Build | Clean build of all steps, 2026-10-16, log `../images/work/logs/build-rc5.log` |
| Checks passed in the build | OLED 2.1.0 unit tests (56) and service smoke test (exits 600 ms after SIGTERM), plus the rc4 checks |

### rc4

| Item | Value |
|------|-------|
| Output | `../images/mbot-server-24.04.3-20261016-rc4.img.xz` (2,452,627,600 bytes), `.img.xz.sha256`, `.manifest.txt`, `.reports/` |
| SHA256 | `c4304bed75e6e394873dd8a17db5b18583a29a65baf24c103a774635c775e336` |
| Build | Clean build of all steps, 2026-10-16, console log `../images/work/rc4-build-console.log`. Step times: 20: 129 s, 30: 53 s, 40: 67 s, 50: 134 s, 60: 7 s |
| Checks passed in the build | OLED 2.0 unit tests (49) and service smoke test (subscribes to `/battery_adc`, keeps running without an OLED, exits 600 ms after SIGTERM); `mbot --help`, `mbot help code` and `mbot health` run as `mbot` (`mbot-health.txt`); Foxglove layout is valid JSON; `mwireless-setup` 1.2.0 checks; camera stack with the ROS environment loads only `/usr/local` libraries; sanitizer |

### rc3

| Item | Value |
|------|-------|
| Output | `../images/mbot-server-24.04.3-20261015-rc3.img.xz` (2,449,619,492 bytes; 11,726 MiB uncompressed), `.img.xz.sha256`, `.manifest.txt`, `.reports/` |
| SHA256 | `4a409fa5007ba836952283e6c7ea826285c5d993109831443ffc53fcdd122ee0` |
| Build | Clean build of all steps, 2026-10-15, log `../images/work/build-*.log` of that day (console copy `../images/work/rc3-build-console.log`). Step times: 00: 174 s, 10: 8 s, 20: 131 s, 30: 49 s, 40: 57 s, 50: 132 s, 60: 4 s; shrink and compression about 6 min |
| Packages | 2011 Debian packages. Compared with the course image: 1116 only there, 137 only here. `ros-jazzy-camera-ros` and `ros-jazzy-libcamera` not installed; `mbot-camera-ros-placeholder` installed |
| Checks passed in the build | Camera stack with the ROS environment loads libcamera 0.5 and libpisp only from `/usr/local` (`camera-ros-env-check.txt`); student `camera_ros` builds and links the same (`camera-ros-test-build.txt`); OLED tests and smoke test; home and login shell; sanitizer. Read from the finished image: `~/.ros/rosdep` present, no landscape cache, `Prompt=never`, `/etc/mbot/image-release` = `rc3 2026-10-15` |

### rc2

| Item | Value |
|------|-------|
| Output | `../images/mbot-server-24.04.3-20261015-rc2.img.xz` (2,453,242,508 bytes; 11,739 MiB uncompressed), `.img.xz.sha256`, `.manifest.txt`, `.reports/` |
| SHA256 | `7877c008c70f726695ac7131503dffb006d743df6690127e2a88e9dc4871341f` |
| Build | Clean build of all steps (00 to 60), 2026-10-15, log `../images/work/build-20261015-002201.log`. Step times: 00: 171 s, 10: 5 s, 20: 124 s, 30: 46 s, 35: 0 s, 40: 64 s, 50: 120 s, 60: 2 s; shrink and compression about 6 min |
| Packages | 2015 Debian packages, of which 302 are ROS. Compared with the course image: 1115 packages only on the course image (desktop, GUI, NoMachine, snap, printing; list in the reports), 140 only on rc2 |
| Disk use in the image | 9.1 GB used. `/usr` 7.9 GB, `/opt/ros` 428 MB, `/opt/pico-sdk` 403 MB, `/usr/local` 16 MB, `/opt/mbot` 12 MB |
| Camera | libcamera 0.5.1 (`v0.5.1+rpt20250722`), rpicam-apps `v1.8.1` with the libav encoder |
| Build attempts | 1: no free loop device (left attached by our own read-only inspections of the course image; detached). 2: DNS failure during apt downloads in step 00 (apt retries added). 3: student `camera_ros` did not compile against libcamera 0.6 (P-21; camera stack pinned to the course image versions). 4: build passed, but the OLED smoke test log showed an abort at shutdown (`terminate called without an active exception`) and a `~/.ros` dependency; output `mbot-server-24.04.3-20261014-rc2.img.xz` is superseded, do not use it. 5: this build |

### rc1 and rc0

| Item | Value |
|------|-------|
| Output (current) | `../images/mbot-server-24.04.3-20261014-rc1.img.xz` (2,318,410,044 bytes; 11,864,637,440 bytes uncompressed), `.img.xz.sha256`, `.manifest.txt`, `.reports/` |
| SHA256 rc1 | `676a7968a7373f51e60608bb4c817ba9a3a6a8da4af496aebe7b7a6dd09066c2` |
| Previous | rc0, SHA256 `91426c5a408bf3966d60a2b62acabba9659019a94b207f2d39931f06c4d89a5c`. rc1 = rc0 plus `mwireless-setup` (step 35) |
| Base | `ubuntu-24.04.3-preinstalled-server-arm64+raspi.img.xz`, SHA256 `9bb1799c...6e33ed72`, verified against `../images/SHA256SUMS` |
| Kernel | `6.8.0-1031-raspi` (the base image kernel, kept during the build) |
| ROS | ROS 2 Jazzy, `ros-jazzy-ros-base` plus `image/manifests/ros-packages.txt` |
| Build host | macOS (Apple silicon), Colima VM profile `mbot-build` (arm64, 8 CPU, 12 GB), privileged `ubuntu:24.04` container |
| Build method | Copy of the base image grown to 16 GiB, partitions attached as loop devices, steps run in a chroot with `proc`, `sys`, `dev`, a temporary `/run` with the container's DNS settings, and a `policy-rc.d` that blocks service starts. Afterwards: sanitize, shrink the root file system to its minimum plus 1 GiB, zero free blocks, `xz -6` |
| How to rebuild | `image/build.sh` (needs Docker with an arm64 engine). `image/build.sh --resume --steps "40 50"` reruns selected steps on the existing working image |

Files added for this build:

| Path | Purpose |
|------|---------|
| `image/build.sh` | Host launcher: checks Docker arch, free disk, base checksum; runs the container; writes a log in `../images/work/` |
| `image/build/build-image.sh` | Container driver: working copy, grow, mounts, steps, finalize, sanitize, shrink, compress, manifest |
| `image/build/lib.sh` | Helpers for the steps (manifest parsing, pinned git checkout, stamps for idempotent source builds) |
| `image/build/00-base.sh` | apt sources and policy, security updates, locale, time zone, hostname, user `mbot`, tools |
| `image/build/10-network.sh` | NetworkManager, hotspot dependencies, regulatory domain, SSH, cloud-init |
| `image/build/20-ros.sh` | Pinned ROS apt source, ROS packages, `/etc/mbot/ros.env`, rosdep, GUI and rosdep reports |
| `image/build/30-mbot-system.sh` | micro-ROS agent, `mbot_interfaces` underlay, MBot scripts, udev rules, units, `config.txt` |
| `image/build/35-mwireless.sh` | Installs `mwireless-setup` 1.1.0 and checks version, help, pinned CA and the hotspot/unit names it expects |
| `image/build/40-camera.sh` | libcamera and rpicam-apps from pinned tags |
| `image/build/50-firmware-tools.sh` | ARM toolchain, pico-sdk, picotool, firmware test build |
| `image/build/90-sanitize.sh` | Removes identity, secrets, logs; fails on 802.1X profiles, credentials, solution code |
| `image/build/build.conf` | Release label, user name and the course default password, `FK_MACHINE` |
| `image/manifests/*` | `apt-packages.txt`, `ros-packages.txt` (one reason per package), `versions.lock` (every pin and checksum) |
| `system/network/mwireless/` | `mwireless-setup` 1.1.0 (copied unchanged) and a README listing the parts not included yet |
| `system/*` | Our system layer: `ros.env`, profile script, `mbot-ros-exec`, `mbot-viz`, units, netplan, NetworkManager, cloud-init, apt, SSH, tmpfiles |
| `results/image-build/<image>/` | Small reports copied from the build (manifest, GUI dependencies, rosdep check, units, disk use) |

### Build result

| Item | Value |
|------|-------|
| Packages | 1883 Debian packages, of which 269 are `ros-jazzy-*` |
| Disk use in the image | 8.6 GB used. `/usr` 7.4 GB, `/opt/pico-sdk` 403 MB, `/opt/ros` 376 MB, `/usr/local` 17 MB, `/opt/mbot` 12 MB |
| Partitions | Boot 512 MiB (FAT); root file system 10.5 GiB (minimum plus 1 GiB), grown to the card size on first boot |
| Step times (first full run, 8 CPU) | 00: 108 s, 10: 7 s, 20: 166 s, 30: 37 s, 40: 41 s, 50: 131 s; compression about 5 min |
| Idempotency | All steps were run a second time on the same image (`--resume`): 00 took 8 s, 10 to 50 took 0 to 15 s, every source build was skipped by its stamp, and the result passed the same checks |
| Build attempts | Run 1: driver bug (`/boot/firmware` mount point missing in the image, loop devices not tracked). Run 2: rpicam-apps libav build error (P-29). Run 3: full build, stopped by our D-03 check because Ubuntu Server defaults to `graphical.target`. Run 4 (`--resume` with the fix): success. Each failure had a different cause and fix |
| Build log | `../images/work/build-20261014-153609.log` (rc0, run 4), `build-20261014-152704.log` (run 3, full first-time step output), `build-20261014-155431.log` (rc1) |
| rc1 build | Made on top of the rc0 working image (`build.img`), as requested: `image/build.sh --resume --steps "35" --reports-from mbot-server-24.04.3-20261014-rc0`. The image was grown again, step 35 ran (1 s), then finalize, sanitize, shrink and compress. Reports of steps not rerun are carried over from rc0 and marked in `reports-carried-over-from.txt`. Same partition sizes and package count as rc0 |
| Working files | `../images/work/build.img` (final image, uncompressed) and `../images/work/base.img` (decompressed base copy). Both can be deleted |

## 2. Contents of the image

| Area | What is in the image | Where it is set |
|------|----------------------|-----------------|
| User | `mbot`, groups `sudo adm dialout video plugdev netdev render input`, password = the current course default | `00-base.sh`, `build.conf` |
| Locale, time | `en_US.UTF-8`, `America/Detroit` | `00-base.sh` |
| Hostname | `mbot-0000` until `mbot-start-network` applies `mbot_hostname` from `mbot_config.txt` | `00-base.sh` |
| apt | `noble`, `noble-updates`, `noble-security`; ROS apt source 1.3.0; Ubuntu libcamera blocked; unattended-upgrades security only | `00-base.sh`, `system/apt/` |
| Network | NetworkManager renders netplan (`eth0` DHCP, Wi-Fi by NetworkManager), `systemd-networkd` disabled, `dnsmasq-base`, `wpasupplicant`, `wireless-regdb`, `cfg80211.ieee80211_regdom=US` | `10-network.sh`, `system/network/` |
| MWireless | `/usr/local/bin/mwireless-setup` 1.1.0 (root, 0755). Not run during the build; no Wi-Fi profile in the image. Students run `sudo mwireless-setup` over SSH. Without the timer, drop-in and banner (G-01) | `35-mwireless.sh` |
| SSH | `openssh-server`, password login on, host keys created on first boot | `10-network.sh`, `system/ssh/`, `system/systemd/mbot-ssh-hostkeys.service` |
| First boot | cloud-init kept: grows the root partition, new SSH host keys. No `ubuntu` user, no network config from cloud-init, hostname left to MBot | `system/cloud-init/` |
| Console | `console=tty1` and `getty@tty1` unchanged (HDMI text console for recovery) | base image |
| ROS | Jazzy ros-base and the listed packages. No desktop, no `rviz2`/`rqt` packages listed by us, no `image_pipeline` metapackage | `20-ros.sh` |
| ROS environment | `/etc/mbot/ros.env` (`ROS_DISTRO=jazzy`, `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`, `ROS_DOMAIN_ID=0`), read by services with `EnvironmentFile=` and by shells through `/etc/profile.d/90-mbot.sh` and `/etc/bash.bashrc` | `system/env/`, `system/profile/` |
| micro-ROS agent | `/opt/mbot/microros` (micro-ROS-Agent `7c93232`, Micro XRCE-DDS Agent 2.4.3, the version the upstream README shows), unit `mbot-microros-agent.service` (ours), started by the upstream udev rule | `30-mbot-system.sh` |
| `mbot_interfaces` | Underlay `/opt/mbot/ros` from `upstream/mbot_ros2_ws` (v1.0.4), used by system services only | `30-mbot-system.sh` |
| MBot services | `mbot-start-network.service` (upstream unit and script), `mbot-oled.service` (our unit, upstream script), udev rules `99-ros-mbot.rules`, `mbot-upload-firmware`, `/boot/firmware/mbot_config.txt` template | `30-mbot-system.sh` |
| Boot config | Ubuntu defaults plus `dtoverlay=uart0-pi5` (servos, `/dev/ttyAMA0`). Kernel and initrd on the boot partition are the base image originals (G-11). Automatic bootloader EEPROM update disabled (P-28) | `30-mbot-system.sh` |
| Camera | rc2: libcamera `v0.5.1+rpt20250722` and rpicam-apps `v1.8.1` in `/usr/local` (the versions of the course image, P-21); rpicam-apps with the libav encoder, without Qt, EGL and DRM preview. rc3: no ROS libcamera or libpisp in `/opt/ros` (placeholder package, P-30) | `40-camera.sh` |
| Firmware tools | `gcc-arm-none-eabi`, newlib, pico-sdk `2.2.0` in `/opt/pico-sdk` (`PICO_SDK_PATH`), picotool `2.2.0` | `50-firmware-tools.sh` |
| Visualization | `ros-jazzy-foxglove-bridge` installed, no service. `mbot-viz` starts it on demand and prints `ws://<IP>:8765` | `system/tools/mbot-viz` |
| Tools | `git`, `gh`, `tmux`, `minicom`, `i2c-tools`, `v4l-utils`, `fonts-dejavu-core`, `wireless-tools`, `python3-luma.oled`, `python3-gpiozero`, `python3-lgpio`, `magic-wormhole` | `apt-packages.txt` |
| OLED | `mbot-oled.service` runs `/opt/mbot/oled` (`python3 -m mbot_oled`). Pages and alerts in `system/oled/README.md`. `oled_animation=off` in `mbot_config.txt` turns the animations off | `30-mbot-system.sh`, `system/oled/` |
| Home | `/home/mbot` like the course image (section 0), `MBOT_COMMANDS.md`, `mbot-help` | `60-home.sh`, `system/home/` |
| Not in the image | Student repositories (firmware, `mbot_ros2_ws`, labs), solution code, any Wi-Fi profile, NoMachine, desktop | by design, checked by `90-sanitize.sh` |

## 3. PROVISIONAL decisions

Each follows the recommendation in `docs/feasibility-review.md` unless noted. None is approved yet.

| # | Decision | Source | Note |
|---|----------|--------|------|
| P-01 | Base: Ubuntu Server 24.04.3 preinstalled Raspberry Pi image, pinned by SHA256 | D-01 | |
| P-02 | ROS 2 Jazzy from `ros-base`, packages added from an explicit list | D-02 | Nav2: individual packages instead of `navigation2`/`nav2_bringup` (review 5.2 "install the individual Nav2 packages actually used"). List taken from `mbot_navigation/config/nav2_params.yaml` and its launch files |
| P-03 | Server image definition: default target `multi-user.target`, no display manager, desktop, VNC or NoMachine. The build fails otherwise | D-03 | GUI libraries pulled in by required packages are allowed and listed in the reports |
| P-04 | Track B built first in this session; Track A not built | D-04 | Track A needs `tools/customize-image.sh`, which is missing |
| P-05 | System layer in `/opt/mbot` and `/etc/mbot`; services never read `~/.bashrc` or the student home | D-05 | Agent and OLED units replaced; `mbot-start-network` unit used unchanged because it already runs as root without student files |
| P-06 | Upstream files copied unchanged; behavior changed only by our units, wrapper and config files | D-08 | No patches were needed |
| P-07 | NetworkManager is the netplan renderer; hotspot kept | D-09 | `systemd-networkd` and its wait-online unit disabled |
| P-08 | Foxglove bridge installed but not started automatically; `mbot-viz` helper | D-10 | |
| P-09 | `ros-jazzy-camera-calibration` stays on the robot | D-11 | The terminal calibration workflow (FOX-008) is not part of rc0 |
| P-10 | Built by scripts, sanitized, checksummed, manifest written | D-15 | Built in an arm64 container, not on Pi hardware as D-15 says. Reason: no robot may be used yet. To revisit |
| P-11 | unattended-upgrades limited to security pockets; kernel **not held** | D-16 | See risk K-01 |
| P-12 | New OLED service not built; upstream OLED script run by our unit | D-17 | D-17 is later work (OLED-003) |
| P-13 | `noble-updates` added to apt sources | [INFER] | The Raspberry Pi preinstalled image lists only `noble` and `noble-security`. Standard Ubuntu installs include `-updates`, and ROS binaries are built against an updated noble |
| P-14 | Packages installed with apt's default (Recommends included) | [ASSUME] | `--no-install-recommends` is an OPT-004 experiment, not rc0 |
| P-15 | Kernel and boot firmware of the base image held during the build, released at the end | [INFER] | Avoids a kernel change inside a chroot that cannot be boot-tested; userspace security updates are applied |
| P-16 | micro-ROS agent built directly from `micro-ROS-Agent` at a pinned commit with `micro_ros_msgs` at the commit listed in the firmware's `built_packages`, using the CMake options of `micro_ros_setup`'s `build_agent.sh` | ROS-004 | Not built through `micro_ros_setup`'s `create_agent_ws.sh`, because that script follows branch heads, so the result would not be pinned |
| P-17 | Agent unit no longer waits for `network-online.target` | [INFER] | Discovery is `LOCALHOST`, so the agent does not need the network. The firmware stops pinging after 180 s, so a faster start is safer |
| P-18 | OLED unit: no `network-online.target`, `Restart=always` | W1, W3, W9 | The upstream script exits with status 0 when the OLED is missing, so `on-failure` would never retry |
| P-19 | `/opt/mbot/ros` underlay sourced by services and `mbot-viz`, not by student shells | ROS-005 | Avoids colcon "overriding package" warnings when students build `mbot_interfaces` |
| P-20 | pico-sdk installed system-wide in `/opt/pico-sdk` with `PICO_SDK_PATH` set for all shells | OS-006 | Upstream installs it in `~/pico-sdk`. Students who run the upstream installer will get a second copy |
| P-21 | rc2: libcamera `v0.5.1+rpt20250722` and rpicam-apps `v1.8.1`, the versions the course image was built with | [CODE] | The course image has libcamera 0.5.1 and rpicam-apps files dated 2025-08-15 (`results/course-image-2026-01-15/`); these are the last tags before that date. rc0 and rc1 used `v0.6.0+rpt20251202` and `v1.11.0` ("last tags before 2026-01-15"). That was wrong: the student `camera_ros` (`mbot_ros2_ws` at `80fc3cb`) does not compile against libcamera 0.6 or newer (`control_type<std::string>` no longer exists). Found by the new `camera_ros` test build in step 40. Students on rc1 would have hit this when building `mbot_ws` |
| P-22 | rpicam-apps without DRM preview as well as Qt and EGL | D-03 | Use `rpicam-hello -n` or `--list-cameras` |
| P-23 | `dtoverlay=uart0-pi5` added to `config.txt` | OS-003, HW-007 | The course servo guide asks students to add it by hand |
| P-24 | No extra `gpio` or `i2c` groups | [CODE] | The base image's udev rule `60-gpio.rules` gives group `dialout` access to `pinctrl-rp1` GPIO chips and `i2c-dev`; `mbot` is in `dialout`. Upstream also sets `i2c-dev` to 0666 |
| P-25 | cloud-init: no default user, `preserve_hostname: true`, network config disabled, `ssh_pwauth: true` | OS-005 | Base `user-data` created user `ubuntu` with password `ubuntu` and disabled SSH passwords |
| P-26 | Root file system shrunk to minimum plus 1 GiB; cloud-init grows it on first boot | REL-003 | |
| P-27 | Default password kept: the course default from the setup guide | Q10 | **Policy question.** It is public, and SSH password login is on. Options: keep (as today), expire on first login, or per-robot passwords |
| P-28 | `rpi-eeprom-update.service` disabled | D-16, AGENTS.md section 8 | Ubuntu enables it with `rpi-eeprom-update -a`, which stages a Pi 5 bootloader EEPROM update at boot on its own. The build upgraded `rpi-eeprom` from 26.3 to 28.14, so a first boot would likely have flashed the bootloader of every robot. Staff can still run `sudo rpi-eeprom-update -a` on purpose. The course image has this service enabled [CODE: `results/course-image-2026-01-15/systemd-system.txt`], so it does update automatically today. Disabling it is a change from the course image that needs agreement |
| P-29 | rc2: rpicam-apps built with the libav encoder again, as upstream `install_camera.sh` does | [CODE] | rc0 and rc1 had it off because rpicam-apps v1.11.0 needs a newer libavcodec than Ubuntu 24.04 has. v1.8.1 builds against it (see the rc2 build log) |
| P-30 | rc3: `ros-jazzy-camera-ros` and `ros-jazzy-libcamera` are kept out of the image by a placeholder package, `mbot-camera-ros-placeholder` (Provides `ros-jazzy-camera-ros`, Conflicts with both) | [CODE] rc2 robot test | `ros-jazzy-apriltag-ros` 3.4.0 (course image: 3.2.2) depends on `ros-jazzy-camera-ros`. Its libcamera and libpisp in `/opt/ros/jazzy/lib` break the Pi camera stack in every ROS shell (rc2: symbol lookup error). rc2's `dpkg-divert` of the pkg-config files only fixed builds. Students build `camera_ros` themselves (course docs). Step 40 fails if `rpicam-hello` or the IPA module load anything from `/opt/ros` with the ROS environment, and test-builds the student `camera_ros`. If a student installs `ros-jazzy-camera-ros`, `sudo apt install /opt/mbot/share/mbot-camera-ros-placeholder.deb` undoes it |
| P-31 | New OLED service (D-17) replaces the upstream script on the image | D-17 | Earlier than the task order (OLED-001 measurements not done), on Hemanth's request. Upstream script still copied to `/usr/local/etc/`, not started |
| P-32 | Home folder like the course image, with links to `/opt` instead of copies of `pico-sdk` and `microros_ws` | D-05 | Students can delete the links without breaking the robot. `git pull` inside `~/pico-sdk` no longer works (root-owned) |
| P-33 | `nav2_bringup` not installed | D-03 | It pulls Gazebo (`ros_gz_sim`) and `navigation2` (with `nav2_rviz_plugins`). No MBot launch file uses it [CODE]; only the `mbot_navigation` README names it |
| P-34 | Ubuntu `10-help-text` and `50-motd-news` login messages off; MBot summary added | [INFER] | Less noise at login; no news download |
| P-35 | rc3: rosdep cache shipped in `/home/mbot/.ros/rosdep`, release-upgrade prompt off | [CODE] rc2 robot test | Same as the course image (its `~/.ros` has the cache). The cache is public data |
| P-36 | OLED alerts only after a condition holds for a raise delay, and cleared after a clear delay; battery rules on a 30 s median | [INFER] Hemanth: no false alarms | Delays per rule in `system/oled/README.md`. Short dropouts (flashing firmware, agent restarts, motor start sag, one under-voltage blip) never show; covered by unit tests |
| P-37 | (Removed in rc7: voltage only.) Battery percentage from voltage with a 3-cell Li-ion curve, 9.0 V to 12.6 V | [ASSUME] MBot Classic battery is a 3-cell Li-ion pack | Shown as an estimate. On rc2 a robot read 9.9 V, which this curve shows as about 5 %; check the real pack range and set `battery_empty_v` and `battery_full_v` if it differs |
| P-39 | Pi 5 fan checked by `mbot health` only: warning when it is driven but reports 0 rpm | [ASSUME] The Ubuntu raspi kernel exposes the cooler as hwmon `pwmfan` with `pwm1` and `fan1_input` (`CONFIG_SENSORS_PWM_FAN=m` and `cooling_fan` in the rc6 kernel and device tree) | Not seen on a robot yet. A missing fan on a cool Pi is not detectable, since the fan is off below about 50 C |
| P-38 | The Pi never drives the Pico RUN and BOOTSEL pins (GPIO 17 and 4): our `mbot-upload-firmware` (USB request or buttons), and `mbot_start_networking.sh` patched at install to set both pins to inputs | [CODE] course staff report 2026-10-21 | Upstream files unchanged in `upstream/`. `autostart` in `mbot_config.txt` no longer has an effect. Needs a robot test: flash with the buttons, then with firmware that has the USB BOOTSEL change |

## 4. Assumptions

| # | Assumption | Tag |
|---|------------|-----|
| A-01 | The RP1 GPIO chip is still `gpiochip4` on kernel `6.8.0-1031-raspi`, as `mbot-start-network` and `mbot-upload-firmware` expect | [ASSUME] (W12) |
| A-02 | `serial0` is the Pi 5 debug UART (`ttyAMA10`), so the kernel console does not use `ttyAMA0` (servos) | [INFER] from the course servo guide listing `ttyAMA0` and `ttyAMA10` |
| A-03 | The micro-ROS agent at `7c93232` (jazzy branch, 2026-09-04) speaks the same XRCE-DDS protocol as the firmware's prebuilt `libmicroros` | [ASSUME] |
| A-04 | `python3-lgpio` is enough for gpiozero on the Pi 5 | [INFER] |
| A-05 | The NetworkManager hotspot (shared mode, 5 GHz) works with the US regulatory domain set on the kernel command line | [INFER] |
| A-06 | Base image URL in `versions.lock` is where 24.04.3 can be downloaded again | [ASSUME] |
| A-07 | Students keep using `~/mbot_ws`; `mbot-viz` sources `~/mbot_ws/install` if it exists | [ASSUME] |
| A-08 | The `ubuntu:24.04` container tag and Colima VM do not affect the image contents (only host tools run there) | [INFER] |
| A-09 | Reproducibility: the rc0 manifest records commit `3d51139` plus uncommitted changes; the rc1 manifest records commit `2ff750f` (made on `local/image-build` outside this session) plus uncommitted changes. Neither commit contains `image/build/`, because the colcon rule `build/` in `.gitignore` ignored it; the uncommitted-path counts in both manifests are therefore too low. `.gitignore` now has `!image/build/` (uncommitted). A later rebuild from a commit will also differ in apt package versions (apt is not snapshot-pinned) | [CODE] |

## 5. Known gaps

| # | Gap | Impact | Next task |
|---|-----|--------|-----------|
| G-01 | `mwireless-setup` is installed, but these parts of its package are still missing: the `mbot-start-network` boot-timing drop-in (`10-wait-mwireless.conf`), the weekly certificate refresh (`mwireless-cert-refresh.timer`) and the SSH login banner (`motd/90-mwireless`). Minor: no `mwireless.conf` (built-in defaults are used), no `/etc/mwireless/build-epoch` clock floor, no opt-in `mwireless-boot.service` | On campus the hotspot may start at boot before MWireless connects; certificates are refreshed only after a successful connection; students must run `sudo mwireless-setup --status` to see the result | NET-001 (complete package from Hemanth) |
| G-02 | Track A not built (`tools/customize-image.sh` missing) | No low-risk fallback image yet | OS-007 |
| G-03 | Terminal camera calibration workflow not provided | Checkpoint 4.1 needs X11 forwarding or a desktop | FOX-008 |
| G-04 | rc2: new OLED service built and installed; not tested on an OLED | Unknown on hardware: readability on the panel, frame rate over I2C at 100 kHz, CPU use, values read from `/sys` on the Pi 5 (throttling file path, temperature) | OLED-001, OLED-008 |
| G-05 | Kernel not held; unattended-upgrades can install a new kernel from the security pocket | A kernel change could renumber GPIO chips (W12) | OS-008 |
| G-06 | `usb_max_current_enable` not set (Ubuntu default). Unknown what the current image sets | USB current for LiDAR and Pico on some power banks | BASE-003 (Q20) |
| G-07 | rc2: `avahi-daemon` installed, as on the course image. Not checked whether it picks up the hostname that `mbot-start-network` sets after avahi has started | If not, `<hostname>.local` shows the old name until `sudo systemctl restart avahi-daemon`; use the IP on the OLED | NET-006 |
| G-08 | libcamera Python bindings install under `/usr/local`; not checked whether `import libcamera` works for students | Only affects Python camera code | HW-005 |
| G-09 | snapd, ModemManager and other server defaults left as they are | No optimization in rc0 | OPT-001 |
| G-10 | Built in a container, not on a Pi; no boot test | Everything below is untested | First-boot test plan |
| G-11 | The boot partition still has the base image's kernel and initrd. Inside the chroot, package upgrades regenerated `/boot/initrd.img-6.8.0-1031-raspi`, but flash-kernel did not copy it to `/boot/firmware`. The robot boots the original, unmodified kernel and initrd of 24.04.3. The regenerated initrd in `/boot` is unused until the next kernel update on the robot runs flash-kernel | Low for rc0 (known-good boot files). The first on-robot kernel or initramfs update will replace them | OS-003, OS-008 |
| G-12 | GUI libraries on disk: Qt5, GTK3, VTK, Mesa and the RViz libraries (`rviz_common`, `rviz_default_plugins`, `rviz_ogre_vendor`), 77 packages matching the GUI pattern. They come from `slam_toolbox` (RViz panel plugin) and from OpenCV's GUI module (`cv_bridge`, `image_proc`, `apriltag_ros`, `camera_calibration`). Nothing starts them. `rviz2`, `rqt` and any desktop are not installed | Disk space only; allowed by D-03 | ROS-002, OPT-004 |
| G-13 | Student `rosdep install` for `mbot_ros2_ws` will still install 4 lint and test tools used by `camera_ros` tests (`clang-format`, `ament_cmake_clang_format`, `ament_cmake_mypy`, `ament_cmake_pyflakes`). With the course command (`--skip-keys=libcamera` only) it also installs `rviz2` and `ros2_controllers` (W7) | Extra downloads during student setup | Add the 4 to `ros-packages.txt` in rc1; course docs change for W7 |
| G-14 | rc2: closed. rpicam-vid can record H.264 again (P-29) | | |

## 6. Verified during the build, and not verified

Verified in the build container or by reading the finished image (no hardware):

- Base image checksum matches `SHA256SUMS` (on the Mac and in the container). Output checksum verified with `shasum -a 256 -c`.
- All scripts pass `shellcheck` and `bash -n`.
- Each source build checked out the exact pinned commit (the build fails otherwise).
- Default target `multi-user.target`; no display manager, desktop session, VNC, NoMachine or `xserver-xorg-core` installed.
- Enabled: `NetworkManager`, `NetworkManager-wait-online`, `ssh.socket`, `mbot-start-network`, `mbot-microros-agent`, `mbot-oled`, `mbot-ssh-hostkeys`. Not enabled: `systemd-networkd`, `systemd-networkd-wait-online`, `rpi-eeprom-update`. No Foxglove service.
- `/etc/machine-id` empty, no SSH host keys, no NetworkManager profiles, empty `/var/lib/cloud`, no log files, no `policy-rc.d`, `/etc/sudoers.d` holds only `README`, no apt holds.
- Leak check: 16,396 source files under `/home`, `/root`, `/opt`, `/srv`, `/usr/local` hashed; none matches the 18 solution-only file hashes. No `mbot_ros_labs*` directory. `mbot_config.txt` identical to the upstream template.
- `mbot_interfaces` imports through `mbot-ros-exec` (`BatteryADC import OK`), so the OLED can show the battery without a student workspace.
- `picotool version` prints `picotool v2.2.0`; `rpicam-hello --version` printed `v1.11.0` in rc1 (rc2 values: section 1); libcamera pkg-config version `0.6.0`.
- The pinned `mbot_firmware_ros` (v1.1.6) builds with `/opt/pico-sdk` 2.2.0 and produces 6 `.uf2` files, including `mbot_classic_ros.uf2` and `mbot_calibrate_classic.uf2` (hashes in `firmware-test-build.txt`). The firmware build was not kept in the image.
- rc1, step 35 (report `mwireless-setup.txt`): installed file identical to the repository copy (SHA256 `e6442873...4af60c`); `mwireless-setup --version` prints `mwireless-setup 1.1.0`; `--help` prints the usage text; `/etc/ssl/certs/USERTrust_RSA_Certification_Authority.pem` exists and its SHA-256 fingerprint equals the one pinned in the script; the script's hotspot name `mbot_wifi_ap` is the one `mbot_start_networking.sh` creates; `mbot-start-network.service` is installed and enabled; `nmcli`, `openssl`, `flock`, `systemd-run`, `timedatectl`, `journalctl`, `curl`, `rfkill`, `ss` and `ping` are present; NetworkManager 1.46 (the script needs 1.42 or newer). The sanitizer passed again after step 35 (no Wi-Fi profile, no `/var/lib/mwireless`).
- To watch on first boot: `networkd-dispatcher.service` is still enabled although `systemd-networkd` is off. Check `systemctl --failed`.

rc2, also verified in the build (reports in `results/image-build/mbot-server-24.04.3-20261015-rc2/`):

- OLED: 27 unit tests pass with the image's Python 3.12, Pillow 10.2 and fonts (`oled-tests.txt`). Smoke test as user `mbot`: subscribes to `/battery_adc` through the system underlay, keeps running without an OLED (logs and retries), exits 600 ms after SIGTERM without errors (`oled-smoke-test.txt`). The Fast DDS shared memory errors in that log come from the chroot's `/dev/shm` and are filtered from the check.
- Student `camera_ros` (`mbot_ros2_ws` `80fc3cb`) builds with colcon in the ROS environment and links `/usr/local/lib/aarch64-linux-gnu/libcamera.so.0.5` (`camera-ros-test-build.txt`). `pkg-config --modversion libcamera` gives 0.5.1 with and without the ROS environment.
- Home folder matches the course image layout; a login shell of `mbot` has `ROS_DISTRO=jazzy`, `PICO_SDK_PATH=/opt/pico-sdk`, finds `micro_ros_agent` and `~/pico-sdk/pico_sdk_init.cmake` (`home.txt`).
- Enabled units include `avahi-daemon`, `mbot-oled`, `mbot-microros-agent`, `mbot-start-network`, `mbot-ssh-hostkeys`. `rviz2`, `rqt`, `nav2_bringup` and any desktop are not installed (RViz libraries from `slam_toolbox` remain, G-12).
- Sanitizer passed; the firmware test build produced 6 `.uf2` files.

**Not verified (needs hardware):** boot, OLED, Wi-Fi and hotspot, SSH login, first-boot partition growth and new host keys, GPIO chip numbering, firmware flashing, agent connection, all ROS topics, LiDAR, camera, servos, Foxglove connection, HDMI console.

## 7. Build reports

Copied to `results/image-build/<image name>/` (full set in `../images/<image name>.reports/`):

| File | Content |
|------|---------|
| `manifest.txt` | Base image and checksum, pins, submodule commits, ROS packages, full package list, output checksum |
| `ros-gui-deps.txt` | For each ROS package: size of its dependency closure and the GUI or rendering libraries in it |
| `installed-gui-packages.txt` | GUI-related packages actually installed |
| `rosdep-check.txt` | Which rosdep keys of the student repositories are still missing, with and without the extra skip keys |
| `mwireless-setup.txt` | rc1: results of the `mwireless-setup` checks in step 35 |
| `firmware-test-build.txt` | SHA256 of the `.uf2` files from a test build of the pinned firmware (not kept in the image) |
| `oled-tests.txt`, `oled-smoke-test.txt` | rc2: OLED unit tests and the 8 s service run in the image |
| `camera-ros-test-build.txt` | rc2: which libcamera the student `camera_ros` links |
| `home.txt` | rc2: `/home/mbot` and the login-shell check |
| `only-in-course-image.txt`, `only-in-server-image.txt` | rc2: package comparison with the course image |
| `enabled-units.txt`, `config.txt`, `cmdline.txt`, `disk-usage.txt` | Facts about the built image |

Build log: `../images/work/build-<timestamp>.log`.

## 8. First-boot test plan (when the test robots are ready)

Use only `mbot-test-a` and `mbot-test-b`. Physical steps are done by the developer. The agent asks before every command on a robot that uses `sudo`, flashes firmware, moves the robot or changes networking. Record results in `results/validation/rc4/<robot>/<date>.md` using the run sheet in `CHECKLIST.md`.

**Preparation (developer)**

1. Check the download: `shasum -a 256 -c mbot-server-24.04.3-20261016-rc4.img.xz.sha256`.
2. Flash the `.img.xz` to a test SD card (32 GB or larger) with Raspberry Pi Imager ("Use custom"), with no Imager customisation.
3. Before ejecting, open the `system-boot` volume and edit `mbot_config.txt`: `mbot_hostname=mbot-test-a`, and leave the home Wi-Fi lines as placeholders for the first boot (tests the hotspot).
4. Connect an HDMI monitor and a USB keyboard (recovery path, Gate 4). Robot on a stand, wheels off the floor.

**Boot and console**

5. Power on. Start a stopwatch. Expected on HDMI: kernel messages, then a text login prompt within about 2 minutes. Note the time to the OLED's first output and to an IP on the OLED.
6. Log in on the HDMI console as `mbot`. Check: `systemctl get-default` is `multi-user.target`; `systemctl --failed` lists nothing; `df -h /` shows the full card size (partition grown); `cat /etc/machine-id` is not empty.

**Network and SSH**

7. With no known Wi-Fi: the hotspot `mbot-test-a-AP` appears (5 GHz). Connect a laptop. The laptop gets an address in `192.168.3.0/24`. `ssh mbot@192.168.3.1` works with the default password.
8. Record the SSH host key fingerprint. Flash a second card from the same image for `mbot-test-b`; its fingerprint and `/etc/machine-id` must differ.
9. Set home Wi-Fi in `mbot_config.txt` (on the boot partition), reboot: the robot joins it and the OLED shows the new IP. VS Code Remote SSH connects and opens a terminal; `echo $ROS_DISTRO $ROS_AUTOMATIC_DISCOVERY_RANGE` prints `jazzy LOCALHOST`.
10. `iw reg get` shows `country US`. `timedatectl` shows the clock synchronized once online.

**MWireless (on campus; network change, ask first, Gate 4)**

Use a course test account, never personal credentials (NET-003). Keep the HDMI console connected. Start with no home Wi-Fi in `mbot_config.txt`, so the robot is on its hotspot, and SSH in over the hotspot (`ssh mbot@192.168.3.1`).

M1. `mwireless-setup --version` prints `mwireless-setup 1.1.0`. `sudo mwireless-setup --status` shows `Profile : (none)`.
M2. **Wrong password once:** `sudo mwireless-setup --user <test account>`, then type a wrong password. Expected: the SSH session drops after about 5 s; the hotspot comes back within about 1 to 2 minutes. Reconnect over the hotspot. `sudo mwireless-setup --status` shows `FAILED AUTH` and `autoconnect=no`. Save the output of `sudo mwireless-setup --diagnose` to the results folder (confirms the error strings, NET-003). Check that only one connection attempt was made, so the shared account is not locked.
M3. **Correct password:** `sudo mwireless-setup --user <test account>` with the right password. Expected: SSH drops, the OLED shows a campus IP (not `192.168.3.x`) within about 2 minutes. Put the laptop on MWireless and SSH to that IP. `sudo mwireless-setup --status` shows `OK`, `autoconnect=yes`, the clock `NTP-synced=yes`, and the CA bundle listed. `sudo ls -l /etc/NetworkManager/system-connections/` shows a root-only (0600) `MWireless` profile.
M4. **Reboot and reconnect:** `sudo reboot`. Expected: the robot comes back on MWireless with a campus IP on the OLED, without running the script again. Record the time from power-on to the campus IP. Because the boot-timing drop-in is not installed (G-01), also record whether the hotspot appears first, and if so, whether MWireless takes over and how long it takes.
M5. Clean up after the test: `sudo mwireless-setup --forget`. The hotspot comes back. Do not reuse this SD card as a release image (it now holds a saved profile; the sanitizer would remove it).

**Firmware and agent**

11. `ls -l /dev/gpiochip*` and `gpioinfo gpiochip4 | head` confirm the RP1 chip is `gpiochip4` (A-01).
12. Clone the firmware as a student would, build with `cmake` and `make` (uses `/opt/pico-sdk`), then flash with `sudo mbot-upload-firmware flash mbot_classic_ros.uf2` (ask first). Repeat the flash 3 times.
13. `ls -l /dev/mbot_*` shows `mbot_microros` and `mbot_debug`. `systemctl status mbot-microros-agent` is active and its process runs from `/opt/mbot/microros`.
14. `ros2 topic list` shows `/odom /imu /encoders /battery_adc /tf /motor_vel`. `ros2 topic hz /imu` near 100 Hz, `/odom` near 25 Hz. `ros2 service list` shows `/reset_odometry` and `/lidar_power`.
15. OLED (rc4): the main screen alternates with the health page; battery percentage and voltage match `mbot health`; unplugging the Pico shows "No Pico" after about 20 s and "Resolved" 3 s after plugging it back; no alert during a normal boot or while flashing firmware. Earlier checks: the boot animation appears within about 20 s of power-on; "Ready!" once there is an IP; then the network, health, system and animation pages rotate. The battery voltage shows on the health page (not `--.--V`) without any student workspace built. With `mbot_hostname=mbot-AM-team6-johndoe` the hostname scrolls. Unplug the Pico USB cable: after about 90 s the alert page shows "Pico not found (USB)". Record a short video for OLED-008. Check `journalctl -u mbot-oled -b` for errors and `top` for the CPU use of `python3 -m mbot_oled`.
15a. Home folder (rc2): `ls ~` shows the eight standard folders, `SecureW2_JoinNow.run`, `pico-sdk`, `microros_ws`, `MBOT_COMMANDS.md`. `mbot-help lidar` prints the LiDAR section. The SSH login message shows the MBot summary. `ros2 pkg prefix micro_ros_agent` works in a new shell. `ssh mbot@<hostname>.local` from a laptop on home Wi-Fi.
16. `sudo minicom -D /dev/mbot_debug -b 115200` shows the firmware status table.

**LiDAR, camera, servos**

17. Clone and build `mbot_ros2_ws` as in the course docs (`rosdep install ... --skip-keys=libcamera`, `colcon build`). Record what rosdep installs and the build time.
18. `ros2 launch mbot_bringup mbot_bringup.launch.py`: `/scan` at 7 to 10 Hz. Call `/lidar_power` off and on.
19. In a normal SSH shell (ROS environment loaded): `rpicam-hello --list-cameras` lists the camera; `rpicam-still -n -o test.jpg` writes an image. Then `ros2 launch mbot_vision camera.launch.py` publishes `/camera/image_raw` and a compressed topic.
20. Servos (if fitted): `ls /dev/ttyAMA*` shows `ttyAMA0` and `ttyAMA10`; run `check_servo_id.py`.

**Foxglove and teleop**

21. Run `mbot-viz`. Open the printed `ws://<IP>:8765` in Foxglove on the laptop. Check robot model, `/scan`, TF and the compressed camera image. Stop with Ctrl+C and confirm port 8765 is closed.
22. Teleop on the stand (ask first): `ros2 run teleop_twist_keyboard teleop_twist_keyboard`; wheels turn in the expected directions and stop.

**After the test**

23. Repeat steps 5, 6, 13 and 14 for 5 cold boots per robot, as in BASE-003, and run the baseline scripts (BASE-002) once they exist, so rc0 can be compared with the current image.
24. Record failures with the exact error text. Do not fix on the robot; fix in the build scripts and rebuild.
