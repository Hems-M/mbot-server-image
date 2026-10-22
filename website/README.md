# website: the ROB550 course site for the MBot server image

The ROB550 course website (the `rob550-docs` submodule) changed for the MBot server image. Same pages, style and wording; only the commands and instructions that depend on the desktop image are different.

Only the changed pages are kept here (`overlay/`). `build-site.sh` copies the course site from the submodule to `_build/`, puts the overlay on top, and builds the complete site. This way the 61 MB of course images stay in the course site's own repository.

- **Base:** `rob550-docs` at `6255db3` (2026-10-13).
- **Status:** draft for the course-site owners. Built and checked in a browser on a laptop. **The new instructions were not followed on a robot yet.**

## What changed

Only BotLab pages. ArmLab and the legacy guides do not use the MBot image and are unchanged.

| Page | Change |
|------|--------|
| `docs/botlab/mbot-system-setup-Pi5.md` | New image file name and size (download link left as `#` for staff). OLED description and picture of the new OLED. MWireless with SSH over the hotspot and `sudo mwireless-setup` instead of NoMachine and `SecureW2_JoinNow.run` (its video removed, it shows NoMachine). Remote access without NoMachine; `ssh-keygen -R` for the "host identification has changed" message. New step 7 "Check your mbot" (`mbot health`, `mbot --help`). `rosdep update` hint. Flashing: unplug the green/white jumper wire (it shorts the Pi GPIO), buttons when the upload asks for them. "Install and test foxglove" becomes "Set up foxglove" (already installed; same bridge and bringup commands as the course; turn on `/scan` in the 3D panel; one terminal per command), moved before the camera and LiDAR tests, which use Foxglove instead of RViz and rqt. "Command list on the MBot" (`mbot --help`) |
| `docs/botlab/how-to-guide/foxglove-guide.md` | **New page.** Connect (course commands), LiDAR or robot model not showing, setting the initial and goal pose (`/goal_pose`), camera, plots. No layout import. Linked once from the setup page |
| `docs/botlab/checkpoints/checkpoint2.md` | "Visualization, either thru NoMachine (RViz) or Foxglove" becomes "Visualization with Foxglove" with the same `ros2 launch foxglove_bridge` command (5 places) |
| `docs/botlab/checkpoints/checkpoint3.md` | RViz blocks removed; initial pose and goal pose with Foxglove (**Pose estimate**, **Pose**, Pose topic `/goal_pose`) |
| `docs/botlab/checkpoints/checkpoint4.md` | Camera calibrator GUI through SSH X11 forwarding (`ssh -Y`, XQuartz or MobaXterm on the laptop) instead of NoMachine, with the checks that make the window open (camera node running, XQuartz log out and in, `echo $DISPLAY`, test window); camera feed in a Foxglove Image panel instead of rqt |
| `docs/botlab/checkpoints/competition.md` | "Use RViz to set goal poses" becomes "Use Foxglove to set goal poses" |
| `docs/botlab/how-to-guide/slam-toolbox-guide.md` | RViz blocks removed, Foxglove bridge only |
| `assets/images/botlab/system-setup-oled-server.png` | New: the OLED main screen, rendered by `system/oled` (`mbot_oled.preview`) |

`docs/botlab/checkpoints/checkpoint1.md` is in the overlay unchanged (the same text as the course). Foxglove is started with the course command everywhere; `mbot-viz` is only mentioned as a shortcut in the guide.

The checkpoint tasks, TODOs, report items and submissions are unchanged. Only how to start and use the tools changed.

`course-docs.patch` has the same text changes as a patch, for a pull request to the course-site repository (`git apply course-docs.patch`). Copy the new PNG separately.

## Open it on your computer

Needs Docker (Docker Desktop on macOS or Windows) for the first build, and python3. From the repository folder:

```bash
website/serve.sh
```

The first run builds the site (a few minutes: it downloads the Jekyll theme and gems). Then open
`http://localhost:4000/docs/botlab/mbot-system-setup-Pi5.html`. Stop it with `Ctrl+C`.
Later runs serve the built pages right away; `website/serve.sh --rebuild` builds again after a change in `overlay/`.
Another port: `website/serve.sh 4001`. (GitHub Pages serves the same pages without `.html`.)

`build-site.sh` alone only builds the site into `_build/src/_site`. It also writes `course-docs.patch`, the same text changes as a patch for the course-site owners.

## Not tested

- Every new instruction on a robot, in particular: camera calibration over `ssh -Y` from macOS and Windows, and setting the goal pose with the Foxglove publish tool (default pose topic and `/goal_pose`).
- `mbot-system-setup-Pi5.md` names `2026-10-22-MBOT-UBUNTU-SERVER_IMAGE.img.xz`. Change it to the released image name.
- "Turn on `/scan` and `/robot_description` in the 3D panel settings" and the Pose topic setting follow Foxglove's panel settings; check them in the current Foxglove version.
- Flashing with the buttons and the green/white wire unplugged, and the camera calibrator over `ssh -Y` from macOS and Windows.
