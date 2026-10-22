# image

Scripts and manifests that build the MBot server image (Track B: Ubuntu Server 24.04, ROS 2 Jazzy, no desktop).

Status: rc3, PROVISIONAL, not tested on hardware. See `docs/build-notes.md`.

## Build

Needs Docker with an arm64 engine (tested only with Colima on an Apple silicon Mac) and at least 40 GB free next to the repository.

```bash
./image/build.sh
```

Inputs and outputs live outside the repository, in `../images/`:

| Path | Role |
|------|------|
| `../images/ubuntu-24.04.3-preinstalled-server-arm64+raspi.img.xz`, `../images/SHA256SUMS` | Base image and its checksum. Only read |
| `../images/work/` | Working copy (`build.img`) and build logs |
| `../images/mbot-server-24.04.3-<date>-<label>.img.xz` | Output image, with `.sha256`, `.manifest.txt` and `.reports/`. The label (`rc3`) is set in `build/build.conf` |

To rerun some steps on the existing working image (steps are idempotent):

```bash
./image/build.sh --resume --steps "40 50"
```

## Layout

| Path | Content |
|------|---------|
| `build.sh` | Host launcher (checks, then runs the container) |
| `build/build-image.sh` | Runs in the container: working copy, mounts, chroot steps, sanitize, shrink, compress |
| `build/00-*.sh` to `build/60-*.sh` | Steps run as root inside the image chroot: 00 base, 10 network, 20 ROS, 30 MBot system layer and OLED, 35 MWireless, 40 camera, 50 firmware tools, 60 home folder |
| `build/90-sanitize.sh` | Runs against the mounted image root; fails on leaked secrets or solution code |
| `build/build.conf` | Release label, default user, `FK_MACHINE` |
| `manifests/apt-packages.txt`, `manifests/ros-packages.txt` | Every package with a reason |
| `manifests/versions.lock` | Every pinned version, commit and checksum |

Files installed into the image come from `system/`. Upstream files are copied from `upstream/` unchanged.

After flashing, the robot's own manual is `system/home/MBOT_COMMANDS.md` (on the robot: `mbot-help` or `~/MBOT_COMMANDS.md`).
