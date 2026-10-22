# MBot command manual (server image)

What to do after you flash the MBot server image, step by step, and the commands you will use every day.
On the robot, `mbot --help` shows the command guide by topic (`mbot help network`, `mbot help code`, ...), `mbot help find <word>` searches this file and `mbot help manual` opens it.
`mbot health` shows everything the robot knows about itself: network, Pico, firmware, battery voltage, temperature, fan, RAM, disk, services, and what to do about any problem. `mbot report` packs it with the logs into one file for the GSIs.
A copy of this file you can edit is in `~/MBOT_COMMANDS.md`.

The server image is Ubuntu Server 24.04 with ROS 2 Jazzy and no desktop. You work over SSH (terminal or VS Code Remote SSH) and visualize with Foxglove in your laptop's browser. NoMachine, RViz and rqt are not installed.

Default login: user `mbot`, password `i<3robots!`. Change it in step 4.

---

## 1. Before the first boot (on your laptop)

1. Flash the `.img.xz` file to a microSD card (32 GB or larger) with Raspberry Pi Imager ("Use custom") or balenaEtcher. Do not use the Imager's OS customisation.
2. Open the `system-boot` volume of the card and edit `mbot_config.txt`:

   | Key | What to put |
   |-----|-------------|
   | `mbot_hostname` | Your robot name, for example `mbot-AM-team6-johndoe` |
   | `new_wifi_ssid`, `new_wifi_password` | Your home Wi-Fi, if you will use the robot at home |
   | `mbot_ap_password` | Password of the robot's own hotspot (default `iloverobots`) |
   | `oled_animation` | Optional. Add `oled_animation=off` to turn off the OLED animations |

3. Eject the card and put it in the Raspberry Pi 5.

## 2. First boot: read the OLED

Turn the robot on. While Linux starts, the OLED shows an MBot being put together and "Waiting for network". After that it shows three screens in turn. The IP address is on every one of them:

| Screen | Shows |
|--------|-------|
| Main | Robot name and signal bars (or `AP` for the hotspot, `ETH` for a cable); the IP address in large digits; the network name; at the bottom `READY` with the battery voltage |
| Health | Battery voltage at the top (with "low", "motor power off" or "no jumper" when something is wrong); temperature, CPU, RAM and disk gauges that fill up when the screen appears (a value past its limit is shown inverted); the IP address and uptime at the bottom |
| MBot | The MBot drives in, stops, scans the walls with its LiDAR and drives off; the IP address and battery voltage at the bottom. Not shown with `oled_animation=off` |

| What you see | Meaning |
|--------------|---------|
| `192.168.3.1` and `AP` | No known Wi-Fi was found. The robot runs its own hotspot |
| Any other address | The robot is on a network |
| `Starting` at the bottom | The robot has not heard from the Pico yet (normal for the first minute) |
| Inverted bottom line with a triangle, and a `WARNING` card | A problem that has lasted long enough to be real, with what to do. It goes away by itself when the problem is fixed ("Resolved: ...") |
| Flashing bottom line with a filled disc, and an `ERROR` card | A serious problem (no network, Pi power too low, ROS link stopped). The OLED has one colour, so errors flash instead of turning red |
| "Bye!" and a sleeping MBot | The robot is shutting down. This picture stays on the OLED after shutdown |
| One pixel blinking at the bottom right | The display is live, not frozen |

The OLED only reports a problem after it has lasted a while (for example 20 s for a missing Pico, 30 s of low battery readings), so flashing firmware or starting the motors does not cause false alarms. `mbot health` shows the same checks right away.

The first boot takes longer than later boots, because the system creates new SSH keys and grows the file system to the card size.

## 3. Connect to the robot

### At home (Wi-Fi from `mbot_config.txt`)

Your laptop must be on the same Wi-Fi. Use the IP on the OLED:

```bash
ssh mbot@192.168.1.37
```

Replace the address with the one on your OLED. On most home networks the name also works:

```bash
ssh mbot@mbot-AM-team6-johndoe.local
```

### Through the robot's hotspot

Connect your laptop to the Wi-Fi network `<hostname>-AP` (password: `mbot_ap_password` from `mbot_config.txt`), then:

```bash
ssh mbot@192.168.3.1
```

### "REMOTE HOST IDENTIFICATION HAS CHANGED"

Every new flash of the card gives the robot new SSH keys. If your laptop has connected to the same address before, SSH refuses to connect. Remove the old key for that address on your laptop, then connect again:

```bash
ssh-keygen -R 192.168.3.1
```

### On campus: MWireless

Do this over the hotspot connection above. Use the course account you were given, not your personal account.

1. Check that the clock is right. A wrong date makes the MWireless certificate check fail.

   ```bash
   timedatectl
   ```

   If the date is wrong, set it (use the current date and time):

   ```bash
   sudo date -s "2026-08-24 08:00:00"
   ```

2. Connect:

   ```bash
   sudo mwireless-setup
   ```

   It asks for the user name and password. Your SSH session drops when the Wi-Fi switches. After about 1 minute the OLED shows a campus IP (not `192.168.3.x`). Put your laptop on MWireless and SSH to that IP.
3. If the hotspot comes back instead, reconnect to it and check what happened:

   ```bash
   sudo mwireless-setup --status
   ```

   ```bash
   sudo mwireless-setup --diagnose
   ```

   To remove the MWireless profile and return to the hotspot:

   ```bash
   sudo mwireless-setup --forget
   ```

`~/SecureW2_JoinNow.run` (the tool the course used on the desktop image) is still in the home folder, but on 2026-10-15 it stopped with "your license has expired". Use `mwireless-setup`.

### VS Code

Install the "Remote - SSH" extension on your laptop, then "Connect to Host" with `mbot@<IP>`. The VS Code server is installed in `~/.vscode-server` on the first connection.

## 4. Change your password

```bash
passwd
```

## 5. Check the robot

```bash
mbot health
```

It lists the network, the Pico, the firmware data, the battery voltage, the LiDAR and camera topics, temperature, the Pi fan, RAM, disk, the MBot services and any problem with what to do. `mbot health --brief` shows only the problems.

`mbot health --live` shows the same every second, with a list of what changed while it runs (the Pico unplugged, the LiDAR started, a new IP, a problem that appeared or went away). Quit with `Ctrl+C`; the list of changes is printed when it stops.

The fan is checked only here, not on the OLED: if the Pi drives the fan but it reports 0 rpm, the Pi 5 Active Cooler is missing or its cable is not in the FAN socket. Below about 50 °C the fan is off, so this shows up as the Pi warms up, before it throttles.

When you ask the GSIs for help, send them a report:

```bash
mbot report
```

It writes `~/mbot-report-<robot>-<date>.tar.gz` with the health check, the logs of this and the previous boot, and the network, hardware and ROS state. Passwords from `mbot_config.txt` are removed. It prints the `scp` command to copy the file to your laptop.

The individual checks, if you want them:

```bash
systemctl status mbot-microros-agent mbot-oled mbot-start-network --no-pager
```

```bash
ls -l /dev/mbot_*
```

You should see `/dev/mbot_microros` and `/dev/mbot_debug` when the Pico is connected over USB.

```bash
echo $ROS_DISTRO $ROS_AUTOMATIC_DISCOVERY_RANGE
```

This should print `jazzy LOCALHOST`.

## 6. Build and flash the firmware

The Pico SDK is already installed (`/opt/pico-sdk`, also reachable as `~/pico-sdk`; `PICO_SDK_PATH` is set).

**Keep the green/white jumper wire between the Pi and the control board unplugged.** Pressing BOOTSEL or RST while it is plugged in shorts the Pi's GPIO pins (the Pi then overheats). The image never uses these pins: `mbot-upload-firmware` flashes over the USB-C cable.

1. Fork `mbot_firmware_ros` to your group and clone your fork into the home folder:

   ```bash
   cd ~
   ```

   ```bash
   git clone <your_group_forked_url>
   ```

   For a private repository, GitHub does not accept your account password in `git clone`. Log in once with the GitHub CLI (it shows a code to enter in your laptop's browser), then clone:

   ```bash
   gh auth login
   ```

2. Build:

   ```bash
   cd ~/mbot_firmware_ros && mkdir -p build && cd build && cmake .. && make
   ```

3. Put the robot on the floor with free space around it, then flash the calibration program and let it finish:

   ```bash
   sudo mbot-upload-firmware flash mbot_calibrate_classic.uf2
   ```

4. Flash the firmware:

   ```bash
   sudo mbot-upload-firmware flash mbot_classic_ros.uf2
   ```

5. Watch the firmware's status table (exit with `Ctrl+A`, then `X`, then `Enter`):

   ```bash
   sudo minicom -D /dev/mbot_debug -b 115200
   ```

How `mbot-upload-firmware` gets the Pico into BOOTSEL mode (the mode for flashing):

1. The Pico is already in BOOTSEL mode: it flashes.
2. The firmware on the Pico supports USB BOOTSEL: it asks over USB, no buttons needed. Firmware from the course repository does this only after the USB BOOTSEL change is added to `comms/src/dual_cdc.c`.
3. Otherwise it prints "No accessible RP-series devices in BOOTSEL mode were found" and waits 30 s for the buttons: hold down **RST** and **BOOTSEL**, release **RST** first, then **BOOTSEL**. It then flashes by itself.

If it still fails, check the USB-C cable from the Pico to the Pi and the Pico power cable.

## 7. Drive the robot

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Press `x` a few times to slow down first. `i` forward, `,` back, `j` left, `l` right, `k` stop.

## 8. Set up the ROS workspace (`mbot_ws`)

Fork `mbot_ros2_ws` to your group, then:

```bash
mkdir -p ~/mbot_ws && cd ~/mbot_ws
```

```bash
git clone --recurse-submodules <your_group_url> src
```

```bash
sudo apt update
```

```bash
rosdep install -y --from-paths src --ignore-src --rosdistro $ROS_DISTRO --skip-keys=libcamera
```

```bash
colcon build --symlink-install
```

```bash
echo "source $HOME/mbot_ws/install/local_setup.bash" >> ~/.bashrc && source ~/.bashrc
```

Most of what `rosdep` needs is already in the image. It may still install `rviz2` and a few test tools that `mbot_ros2_ws` lists; on this image they are not used.

## 9. Camera

Do not plug or unplug the camera while the robot is on. Power off, wait 30 s, then change it.

```bash
rpicam-hello --list-cameras
```

```bash
rpicam-still -n -t 1 -o ~/test.jpg
```

There is no preview window on this image, so always use `-n`. Open `test.jpg` in VS Code to look at it. The image is upside down; that is expected.

ROS camera driver (after step 8):

```bash
ros2 run camera_ros camera_node --ros-args -p orientation:=180 -p width:=640 -p height:=480 -p format:=BGR888
```

Look at `/camera/image_raw` (or the compressed topic) in Foxglove (step 11) instead of `rqt_image_view`.

Camera calibration (Checkpoint 4) opens a window on your laptop through SSH X11 forwarding:

1. Start the camera node in a VS Code terminal and keep it running. The calibrator window opens only after it receives images.
2. On a Mac, install XQuartz once, then log out and back in. On Windows, use MobaXterm.
3. From the laptop's own terminal (macOS: the Terminal app, not VS Code), `ssh -Y mbot@<robot IP>`.
4. On the robot, `echo $DISPLAY` must print something like `localhost:10.0`. If it prints nothing, open XQuartz and SSH again with `-Y`.
5. Run `ros2 run camera_calibration cameracalibrator ...` (the command is on the Checkpoint 4 page) in that SSH terminal.

## 10. LiDAR and robot bringup

```bash
ros2 launch mbot_bringup mbot_bringup.launch.py
```

Run it in one terminal only. A second bringup cannot open the LiDAR and stops with `SL_RESULT_OPERATION_TIMEOUT`. `Package 'mbot_bringup' not found` means `mbot_ws` is not built yet, or this terminal was opened before you added the `source` line (step 8): run `source ~/.bashrc`.

```bash
ros2 topic hz /scan
```

Turn the LiDAR off and on (saves battery and noise):

```bash
ros2 service call /lidar_power std_srvs/srv/SetBool "{data: false}"
```

```bash
ros2 service call /lidar_power std_srvs/srv/SetBool "{data: true}"
```

Reset odometry to zero:

```bash
ros2 service call /reset_odometry std_srvs/srv/Trigger
```

## 11. Visualize with Foxglove (replaces RViz and rqt)

On the robot, start the bridge (the same command as on the course website):

```bash
ros2 launch foxglove_bridge foxglove_bridge_launch.xml
```

For the LiDAR scan and the robot model, also run the bringup in a second terminal:

```bash
ros2 launch mbot_bringup mbot_bringup.launch.py
```

On your laptop open Foxglove (app.foxglove.dev), choose "Open connection", "Foxglove WebSocket", replace `localhost` with the IP on the OLED (`ws://<robot IP>:8765`), and open. In the **3D** panel, open the panel settings, Topics, and switch on `/scan` and `/robot_description`.

- Run the bridge and the bringup in one terminal each. A second bridge stops with "Address already in use", a second bringup with `SL_RESULT_OPERATION_TIMEOUT`.
- Stop the bridge with `Ctrl+C` when you are done: while it runs, anyone on the same network can send commands to the robot.
- Shortcut: `mbot-viz` starts the same bridge, prints the address to open, says so if a bridge is already running, and warns when the LiDAR is not running.
- Setting poses: in the 3D panel, **Pose estimate** publishes `/initialpose`. **Pose** publishes `/move_base_simple/goal` by default; set it to `/goal_pose` in the panel settings, Publish.

## 12. Everyday ROS commands

| Task | Command |
|------|---------|
| List topics | `ros2 topic list` |
| Rate of a topic | `ros2 topic hz /odom` |
| Print messages | `ros2 topic echo /battery_adc --once` |
| List services | `ros2 service list` |
| Record a bag | `ros2 bag record -s mcap /scan /odom /tf /tf_static` |
| Play a bag | `ros2 bag play <bag folder>` |
| TF tree to a PDF | `ros2 run tf2_tools view_frames` |
| Rebuild one package | `cd ~/mbot_ws && colcon build --packages-select <name>` |

Use `tmux` for programs that must keep running when your SSH connection drops: `tmux new -s run`, detach with `Ctrl+B` then `D`, come back with `tmux attach -t run`.

## 13. Copy files

| From | Command (on your laptop) |
|------|--------------------------|
| Robot to laptop | `scp mbot@<IP>:~/test.jpg .` |
| Laptop to robot | `scp map.yaml mbot@<IP>:~/` |
| Folder | `scp -r mbot@<IP>:~/bags .` |

In VS Code you can also drag files into the Explorer panel, or right-click a file and choose "Download".

## 14. Troubleshooting

| Problem | What to run or check |
|---------|----------------------|
| OLED blank or frozen | `systemctl status mbot-oled`, then `journalctl -u mbot-oled -b`. `i2cdetect -y 1` should show `3c` |
| OLED shows "Pico not found" | USB-C cable from the Pico to the Pi. `ls -l /dev/mbot_*` |
| No topics from the robot | `systemctl status mbot-microros-agent`, `journalctl -u mbot-microros-agent -b` |
| "No data from Pico" | Flash the firmware again (step 6) |
| `rpicam-hello` stops with "symbol lookup error ... libpisp" | Something installed `ros-jazzy-camera-ros` or `ros-jazzy-libcamera`. Put the placeholder back (apt removes both and keeps `apriltag_ros`): `sudo apt install /opt/mbot/share/mbot-camera-ros-placeholder.deb` |
| `rosdep` says it is not initialized | `rosdep update` |
| Battery warnings on the OLED | "No voltage jumper": put the jumper cap on the control board. "Board not powered": plug in the barrel connector. "LOW": charge the battery |
| "Pi power supply LOW" | Use the right power bank output and cable for the Pi |
| Wi-Fi did not connect | `cat /var/log/mbot/mbot_start_networking.log`, `nmcli device status`, `sudo mwireless-setup --status` |
| Robot has the wrong name | Fix `mbot_hostname` in `/boot/firmware/mbot_config.txt`, then `sudo reboot` |
| Disk full | `df -h /`, then `du -sh ~/*` to find large folders |
| Clock wrong | `timedatectl` |

Restart a service:

```bash
sudo systemctl restart mbot-oled
```

Turn off the robot safely (wait until the green LED on the Pi stops flashing before you switch the power off):

```bash
sudo poweroff
```

```bash
sudo reboot
```

## 15. What is different from the desktop image

| Desktop image | Server image |
|---------------|--------------|
| NoMachine desktop | SSH and VS Code Remote SSH |
| RViz, `rqt_image_view` | Foxglove through `mbot-viz` |
| `SecureW2_JoinNow.run` for MWireless | `sudo mwireless-setup` (the JoinNow file is still in `~`) |
| micro-ROS agent in `~/microros_ws` | `/opt/mbot/microros`; `~/microros_ws/install` links to it |
| Pico SDK in `~/pico-sdk` | `/opt/pico-sdk`; `~/pico-sdk` links to it |
| OLED: three text pages | Boot animation; main screen with the IP; health page; MBot animation; alert cards; shutdown animation |
| `rpicam-hello` opens a preview window | Use `-n` (no preview) |

Where the system parts live: `/opt/mbot` (agent, OLED service, ROS messages for system services), `/etc/mbot/ros.env` (ROS settings for services and shells), `/boot/firmware/mbot_config.txt` (robot name and Wi-Fi).
