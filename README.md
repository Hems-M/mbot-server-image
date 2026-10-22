# MBot Ubuntu Server image

A Raspberry Pi 5 image for the MBot Classic: **Ubuntu Server 24.04.3 with ROS 2 Jazzy, without a desktop.** It replaces the desktop image used in ROB550. Students work over SSH or VS Code like before and use Foxglove in the browser for visualization. Without a desktop running, more memory and CPU are left for the students' own code.

Everything students already know stays the same: the `mbot` user, the home folder, `mbot_ws`, the Pico SDK, the firmware build, the LiDAR, camera and ROS commands, and the checkpoints. Only the setup steps that needed the desktop are different.

This repository has the image itself (as a download), the scripts that build it, the ROB550 website pages for it, and every MBot repository it uses as a submodule.

## Download

**Release 2026-10-22:** `2026-10-22-MBOT-UBUNTU-SERVER_IMAGE.img.xz` (2.44 GB, 12 GB on the SD card)

- Download: *link to be added*
- SHA256: `1af1148410ae8aec73227b72c2d04822c77c20ffad5d846ec118bd40ea79dfe8`

Check the download before flashing (macOS: `shasum -a 256`, Linux: `sha256sum`):

```bash
shasum -a 256 2026-10-22-MBOT-UBUNTU-SERVER_IMAGE.img.xz
```

## Set up a robot

The full student steps are on the ROB550 website pages in `website/` (see [Course website](#course-website)). In short:

1. Flash the image to a 32 GB or larger SD card with [Balena Etcher](https://etcher.balena.io/) or Raspberry Pi Imager.
2. On the SD card's `bootfs` partition, open `mbot_config.txt` and set `mbot_hostname` (and your home Wi-Fi if you have one).
3. Put the card in the robot and turn it on. After about a minute the OLED shows the robot's IP address in large digits. Without a known Wi-Fi it starts its own hotspot (`192.168.3.1`, shown with `AP`).
4. Connect: `ssh mbot@<IP on the OLED>`. The default password is the course default, `i<3robots!`. Change it with `passwd`.
5. On campus, connect to MWireless: `sudo mwireless-setup`.
6. Check the robot: `mbot health`. See all commands: `mbot --help`.

## What is on the image

| Feature | What it does |
|---------|--------------|
| OLED | IP address in large digits, Wi-Fi name, battery voltage. A health page (temperature, CPU, RAM, disk), an MBot animation, and warning or error cards only for problems that last (Pico unplugged, low battery, no network, Pi power too low), with what to do |
| `mbot --help` | The commands students need, by topic: network, firmware, ROS, reading the code, building, sensors, Foxglove, data, fixing problems. `mbot-help find <word>` searches the manual |
| `mbot health` | Everything about the robot in one report: network, Pico, battery voltage, LiDAR and camera topics, temperature, Pi 5 fan, memory, disk, services, and what to do about any problem |
| `mbot health --live` | The same every second, with a list of what changed (Pico unplugged, LiDAR started, new IP, problem resolved) |
| `mbot report` | One file with the health check, logs and settings (passwords removed) to send to the GSIs |
| `sudo mwireless-setup` | Connects the robot to MWireless from the terminal, in Maize and Blue |
| Foxglove | `ros2 launch foxglove_bridge foxglove_bridge_launch.xml` as on the course site, or `mbot-viz`, which also prints the address and checks that the LiDAR is running |
| Firmware flashing | `sudo mbot-upload-firmware flash <file>.uf2`. Never uses the white/green wire (see below) |
| Camera | Raspberry Pi libcamera and rpicam-apps built for the Pi 5, `camera_ros` works from `mbot_ws`. The calibration window opens on the laptop with `ssh -Y` |
| Command manual | `~/MBOT_COMMANDS.md` in the home folder, also `mbot-help manual` |

Versions: Ubuntu Server 24.04.3 (kernel 6.8 raspi), ROS 2 Jazzy, pico-sdk 2.2.0, libcamera v0.5.1+rpt20250722, rpicam-apps v1.8.1, Foxglove bridge 3.6.0. Every pinned version and checksum is in `image/manifests/versions.lock`.

## Firmware flashing and the white/green wire

The white/green wire between the Pi and the control board shorts the Pi's GPIO pins when BOOTSEL or RST is pressed, which damages the Pi and makes it overheat. On this image:

- `mbot-upload-firmware` never drives the Pi's GPIO pins, and the boot script sets those pins to inputs. Keep the wire unplugged.
- If the firmware on the Pico supports it, the Pi asks the Pico over USB to enter flashing mode, and no buttons are needed.
- Otherwise the command asks for the buttons (hold RST and BOOTSEL, release RST, then BOOTSEL) and continues by itself.

The USB part needs a small change in the firmware, which is in the firmware submodule: [Hems-M/mbot_firmware_ros](https://github.com/Hems-M/mbot_firmware_ros), a fork of mbot-project/mbot_firmware_ros with one extra commit. That commit changes two files:

- `comms/src/dual_cdc.c`: when the Pi opens the debug console at 1200 baud, the Pico restarts in flashing mode.
- `tests/mbot_calibrate_classic.c`: the calibration program keeps answering USB after it finishes, so the next flash needs no buttons either.

Firmware built from this fork needs the buttons only for the very first flash on a robot. To use it in the course, the staff bring the same commit into the firmware repository students fork, for example:

```bash
git remote add hems https://github.com/Hems-M/mbot_firmware_ros.git
git fetch hems && git cherry-pick hems/main
```

## Course website

`website/` has the ROB550 pages for this image: the setup guide, the checkpoints and a Foxglove guide. The pages, style and wording are the same as on the current site; only the commands and instructions for the new image changed. To open the site on your own computer (needs Docker for the first build, and python3):

```bash
website/serve.sh
```

Then open http://localhost:4000/docs/botlab/mbot-system-setup-Pi5.html. More in `website/README.md`, including a patch for the course-site owners.

## Repository layout

| Folder | What is in it |
|--------|---------------|
| `image/` | `build.sh` builds the image; `build/` has the build steps; `manifests/` lists every package and pinned version |
| `system/` | Everything installed into the image: OLED service and `mbot health` (`oled/`), command-line tools (`tools/`), MWireless setup (`network/`), firmware upload (`firmware/`), home folder and manual (`home/`), services and settings |
| `website/` | ROB550 website pages for this image, with `serve.sh` to open it locally |
| `upstream/` | The MBot repositories, as submodules at the versions the image uses |
| `docs/build-notes.md` | Why each choice was made, how each release was built and checked |

## Submodules

| Path | Repository | Version |
|------|------------|---------|
| `upstream/mbot_firmware_ros` | Hems-M/mbot_firmware_ros (fork) | `main`: mbot-project's latest (`2aeb657`) plus the USB flashing commit |
| `upstream/mbot_sys_utils` | mbot-project/mbot_sys_utils | v1.3.2 |
| `upstream/mbot_ros2_ws` | mbot-project/mbot_ros2_ws | v1.0.4 |
| `upstream/mbot_ros_labs` | mbot-project/mbot_ros_labs | `rob550/W26-student` |
| `upstream/mbot_ros_labs_solution` | mbot-project/mbot_ros_labs | `rob550/W26-main` (only used to check that no solution code ends up in the image; never copied into it) |
| `upstream/mbot_servo_lib` | mbot-project/mbot_servo_lib | main |
| `upstream/mbot_vision` | mbot-project/mbot_vision | main |
| `website/rob550-docs` | rob550-docs/rob550-docs.github.io | main, 2026-10-13 |

Clone with the submodules:

```bash
git clone --recurse-submodules https://github.com/Hems-M/mbot-server-image.git
```

Apart from the firmware fork, the submodules are the MBot project's repositories, unchanged. The image build copies files from them; changes to their files on the robot are made by the build (see `docs/build-notes.md`).

## Change the firmware

The firmware submodule is your own fork, so changes go there and this repository records which commit to use:

```bash
cd upstream/mbot_firmware_ros
git switch main                      # submodules start detached
# edit, build and test, then:
git commit -am "Describe the change"
git push                             # to Hems-M/mbot_firmware_ros
cd ../..
git add upstream/mbot_firmware_ros   # this repository now uses the new commit
git commit -m "firmware: describe the change"
git push
```

To bring in new commits from the MBot project's repository (remote `mbot-project`; after a fresh clone add it once with `git remote add mbot-project https://github.com/mbot-project/mbot_firmware_ros.git`):

```bash
cd upstream/mbot_firmware_ros
git fetch mbot-project && git merge mbot-project/main && git push
```

Then commit the new submodule commit in this repository as above.

## Build the image yourself

Needs a Mac with Apple silicon or an arm64 Linux machine, Docker (on macOS for example with Colima), about 40 GB of free disk, and the Ubuntu base image:

1. Next to this repository, make a folder `images/` with `ubuntu-24.04.3-preinstalled-server-arm64+raspi.img.xz` from [cdimage.ubuntu.com](https://cdimage.ubuntu.com/releases/24.04.3/release/) and its `SHA256SUMS`.
2. Run:

   ```bash
   ./image/build.sh
   ```

The build takes about 25 minutes and writes `images/<OUTPUT_NAME>.img.xz` with its checksum, a package manifest and the build reports. The name and the release label are set in `image/build/build.conf`. The build checks itself as it goes: it runs the OLED unit tests, test-builds the firmware and `camera_ros`, and fails if a desktop, Wi-Fi credentials or solution code end up in the image.

## Status

Release 2026-10-22 is the seventh build (rc7) plus the latest firmware repository. Tested on a robot during development (earlier builds): booting, SSH over the hotspot, MWireless with `mwireless-setup`, the firmware build and minicom, building `mbot_ws` with the course commands, the LiDAR (10 Hz), the camera and its feed in Foxglove, the OLED, and flashing with the buttons using the new upload script.

Not yet tested on a robot with this release: flashing without buttons (needs the firmware change above), the fan check, `mbot health --live`, `mbot report`, and a full run through the website steps by a student. Please report what you find.
