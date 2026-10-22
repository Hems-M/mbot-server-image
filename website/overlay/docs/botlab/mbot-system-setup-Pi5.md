---
layout: default
title: MBot System Setup
parent: Botlab
nav_order: 2
last_modified_at: 2026-10-16 12:00:00 -0400
---

The following items are needed:
1. microSD card
2. SD adapter
3. A laptop can read and write SD card

**Notice #1**: You do not need an external monitor during the set up process. However, if you want to connect to external monitor at any point, you need to plug into **HDMI-0 port**. The Pi5 has 2 HDMI ports, plug into the one closer to USB C port. The MBot image has no desktop, the monitor shows a text login screen.

**Notice #2**: This guide will walk you through the steps needed to setup the MBot Classic system. The guide is intended to be followed in order, do not jump back and forth.

### Contents
- TOC
{:toc}

## Set up RPi 5 System
### 1. Flash the image
1. Download the custom image `2026-10-22-MBOT-UBUNTU-SERVER_IMAGE.img.xz` from this [link](https://www.dropbox.com/scl/fo/2x70dspqzdd3rrxu60g9n/AIrzrIsXB5RSlizuFKRoO2U?rlkey=6zx5hzsry09gxthtzed7afu9s&st=3z4jw5jq&dl=0) to your laptop.
2. Download [Balena Etcher](https://etcher.balena.io/) to your laptop, it is a tool to flash the OS image to the SD card. Plug in the SD card to your laptop using SD card reader then following the steps in Balena Etcher. (The download is 2.5 GB and expands to 12 GB on the card, this can take 10 min).

Once you have the SD card with the OS image flashed on it, don't insert the SD card in the Pi 5 yet, continue to the next step.

{: .warning }
If you do the flashing on a Windows computer, you may see many file explorer windows and error messages pop up when you insert the SD card and when you finish flashing. Those are expected, and you can safely close the file explorer windows and dismiss the error messages. However, if Windows asks you to format the SD card through a popup dialog box, close the message through the "Cancel" button and **do not** click the "Format Disk" button.


### 2. Set up system utilities

If the flash was successful, insert the SD card into your laptop, you should see a folder named “system-boot” or something similar based on your laptop's OS.

Find the file `mbot_config.txt` on this volume and modify it as follows:
- Set `mbot_hostname` following this format: `mbot-<section>-<team#>-<unique_name>`
    - For example: if you are in the AM section team 6, and your unique_name is johndoe, you should name the robot as `mbot-AM-team6-johndoe`
- Enter your home Wi-Fi details for `new_wifi_ssid` and `new_wifi_password` if you intend to use it at home later.
- Leave all other variables unchanged.

Then save the file. Now you can eject the SD card.


### 3. Boot the Pi5
1. Insert the SD card into your Pi5. The SD card slot is located on the bottom on the side opposite the USB ports.

    <a class="image-link" href="https://projects-static.raspberrypi.org/projects/raspberry-pi-setting-up/94c43714c0e0536158409093ba28931e0fa5c9bc/en/images/pi-sd.png">
    <img src="https://projects-static.raspberrypi.org/projects/raspberry-pi-setting-up/94c43714c0e0536158409093ba28931e0fa5c9bc/en/images/pi-sd.png" alt="Image from RPi Foundation" style="max-width:300px;"/>
    </a>

2. Turn on the power bank and ensure that the power cables are connected as per the [assembly guide](https://mbot.robotics.umich.edu/docs/hardware/classic/assembly/mbot-wiring/).
3. **Wait for about 1 minute until the OLED screen shows the IP** like the image below. While the robot boots, the OLED shows an MBot being put together and "Waiting for network" at the bottom. The IP should be something like `192.168.X.X` meaning it is part of a local network and not directly accessible from the public internet. Once you see this, you can proceed to the next step.

    <a class="image-link" href="/assets/images/botlab/system-setup-oled-server.png">
    <img src="/assets/images/botlab/system-setup-oled-server.png" alt="" style="max-width:300px;"/>
    </a>

    - The first boot takes longer than later boots.
    - If no Wi-Fi is found, the OLED shows `192.168.3.1` with `AP` at the top right: the MBot runs its own access point.
    - If the bottom line of the OLED turns white with a warning triangle (or flashes), the OLED also shows a `WARNING` or `ERROR` card that says what is wrong and what to do (for example "Pico not connected" or "Battery low"). Run `mbot health` for the details.


### 4.1 Connect to the Internet on UM Campus - MWireless

**Steps:**
1. Connect to the MBot's local access point. See the instructions on the official MBot website [here](https://mbot.robotics.umich.edu/docs/setup/networking/#connecting-to-the-mbots-access-point) under the "Connecting to the MBot’s Access Point" section.
2. SSH to the MBot from your laptop terminal. The password is below in [Remote Access](#5-remote-access).
    ```bash
    ssh mbot@192.168.3.1
    ```
3. Once you are logged in, verify that MBot's date and time. If the date and time are not current, update it using the following command. NOTE: if the date and time are incorrect, you will not be able to connect to WiFi.
   ```bash
   timedatectl
   ```
   ```bash
        sudo date -s "2026-08-24 8:00:00"
   ```
   **Replace `2026-08-24 8:00:00` with today's date and time.**
4. Connect the MBot to the Internet. Run the following command in the MBot terminal:
    ```bash
    sudo mwireless-setup
    ```
5. When prompted for your unique name and password, use the 550 course credentials, it will be distributed during lab. Avoid using your own UM credentials for your privacy safety.
6. After entering your credentials, your SSH session will freeze or disconnect during the process, that is expected. Close the terminal and wait for about 1 minute. Check the OLED screen to see if the IP address has changed from `192.168.X.X` to a different one. This indicates that the MBot has successfully connected to the Internet.
   - If the access point comes back instead (the OLED shows `192.168.3.1` with `AP` again), connect to it again, SSH in, and run `sudo mwireless-setup --status` to see what went wrong. You might have typo when input the UM account password.
   - If the OLED shows "No IP address" (or a "No network" error card) for over two minutes, you aren't connected to the network, find GSIs and ask to connect to an external monitor.


### 4.2 Connect to the Internet at Home
1. Ensure the `new_wifi_ssid` and `new_wifi_password` are correctly set in the `mbot_config.txt` file (check for any typos). They should be your home wifi name, and home wifi password.

2. Start the MBot, wait for about 1~2 minute, please be patient. You may hear the fan start a couple of times, and eventually, the OLED screen will display the MBot's IP address (since you are at home, the IP be `192.168.x.x` is normal unlike on campus), meaning the mbot is connected to your home Wi-Fi.


If you have successfully connected your MBot to MWireless or your home Wi-Fi, you can use its IP address to remotely access the MBot. From now on, you can always find the IP address on the OLED screen. Proceed to the next step for more details.

### 5. Remote Access
**At this point, your laptop functions only as a gateway for the SSH connection to your MBot. All programming is executed on the MBot, all the commands should be run in the MBot terminal, not on your laptop.**
{: .text-red-200}

To access the mbot, your laptop and the MBot must always be on the same network. And there are 2 options to connect:
1. Using VSCode (Recommended), here is the tutorail: [link](https://mbot.robotics.umich.edu/docs/tutorials/vscode/#connecting-to-the-robot)
2. Using your laptop terminal: `ssh mbot@your_mbot_ip`

The MBot image has no desktop, NoMachine is not used anymore. For visualization we use Foxglove, see [Set up foxglove](#set-up-foxglove).

Username: mbot <br>
Password: i<3robots!
{: .note }

If SSH says "REMOTE HOST IDENTIFICATION HAS CHANGED", you flashed a new image and your laptop remembers the old one. Remove the old entry on your laptop, then connect again:
```bash
ssh-keygen -R your_mbot_ip
```


### 6. Change your mbot's password

For mbot network security, you may change your password once you have set up your mbot. The default password is `i<3robots!`, which everyone uses. Here's how to change your mbot's password:
1. SSH to the mbot using VSCode or your laptop terminal.
2. Enter this command in the mbot terminal: `passwd`. You will be prompted to enter your current password.
3. Next, you will be asked to enter your new password and retype it to confirm.
4. If the passwords match, you will see a message indicating that your password has been updated successfully.

    The output will look like this:
    ```bash
    mbot@mbot-0018-shaw:~ $  passwd
    Changing password for mbot.
    Current password:
    New password:
    Retype new password:
    passwd: password updated successfully
    ```

### 7. Check your mbot

Run the following in the MBot terminal:
```bash
mbot health
```
It shows the network, the Pico, the battery voltage, temperature, the Pi fan, RAM, disk and any problem with what to do. Run it whenever something does not work. The OLED runs the same checks (except the fan).
- `mbot health --live` shows the same every second, with a list of what changed (for example the Pico unplugged, or the LiDAR started). Quit with `ctrl+C`.
- When you ask the GSIs for help, run `mbot report`. It puts the health check, the logs and the settings (without passwords) into one file and tells you how to copy it to your laptop. Send that file with your question.

To see the commands you will use in this course, grouped by topic:
```bash
mbot --help
```

## Flash MBot firmware
In this session, we are going to work on setup of the Control Board, which is the board located at the bottom of the mbot.

### 1. Compile the firmware
1. Go to the Class **GitLab** page, and find `mbot_firmware_ros` repository.
2. Fork it to your GitLab group.
3. Clone the forked repository to your home directory.
    ```bash
    # cd to the home directory
    cd ~
    git clone your_group_forked_url
    ```
    - When we say `your_group_forked_url`, we mean the URL shown in the image. Go to your group’s forked repository on GitLab, click Code, and copy that URL.
    <a class="image-link" href="/assets/images/botlab/gitlab-group-url.png">
    <img src="/assets/images/botlab/gitlab-group-url.png" alt="" style="max-width:300px;"/>
    </a>
4. Compile the firmware files.
    ```bash
    # cd to the firmware folder
    cd ~/mbot_firmware_ros
    # create the build folder
    mkdir build
    cd build
    # compile the firmware
    cmake ..
    make
    ```
    - After it's done, `~/mbot_firmware_ros/build` directory is going to have all the executables we need.

### 2. Calibrate the MBot and flash the firmware
In this step, we are going to calibrate the mbot and then flash the firmware.

{: .warning }
**Unplug the GREEN/WHITE jumper wire** between the Raspberry Pi and the control board, and keep it unplugged. When the BOOTSEL or RST button is pressed, this wire shorts the Pi's GPIO pins, which damages the Pi and makes it overheat. The MBot image does not use it: the firmware is flashed over the USB-C cable.

1. **Place the MBot on the floor** in a spot with at least 2 feet of clear space around the robot, preferably on the same type of surface you plan to use it on.
2. First, flash the calibration file to calibrate your MBot.
    ```bash
    cd ~/mbot_firmware_ros/build
    sudo mbot-upload-firmware flash mbot_calibrate_classic.uf2
    ```
    `mbot_calibrate_classic.uf2` is one of the files we compiled from step 1.
    - If the command asks for it, put the Pico in BOOTSEL mode with the buttons on the control board: hold down both **RST** and **BOOTSEL**, release **RST** first, then release **BOOTSEL**. The command waits 30 seconds and continues by itself.

    Expected output:
    ```bash
    $ sudo mbot-upload-firmware flash mbot_calibrate_classic.uf2
    [sudo] password for mbot: 
    Detected Raspberry Pi 5, entering flash mode...
    Flashing action for mbot_calibrate_classic.uf2...
    Loading into Flash:   [==============================]  100%
    The device was rebooted into application mode.
    ```

    Here is a video showing the expected calibration routine:

    <iframe width="400" height="227" src="https://www.youtube.com/embed/iIghZzf8ZQY?si=w_ultg6PtCwJVr2_" title="YouTube video player" frameborder="2" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
    - **Allow the Pico to finish its calibration routine without interference.** The calibration script will save the parameters onto the Pico’s memory.
3. Then, you can flash the firmware that will run on the Pico during operation.
    ```bash
    sudo mbot-upload-firmware flash mbot_classic_ros.uf2 
    ```

If you didn't see the expected output above, but having the following output:
```bash
No accessible RP-series devices in BOOTSEL mode were found.
```
1. Check if the cables are connected correctly (USB-C from Pico to Pi; Pico's power cable). The GREEN/WHITE jumper wire stays unplugged.
2. Put the Pico in BOOTSEL mode with the buttons (hold down both **RST** and **BOOTSEL**, release **RST** first, then release **BOOTSEL**) and run the command again.

### 3. Minicom to verify the flash operation

Minicom is a program designed for serial communication that connects devices to a Linux PC via serial ports, we will use Minicom to read the pico printouts during the flash process.
- After flashing the firmware to the Pico, run the following command to start minicom
    ```bash
    sudo minicom -D /dev/mbot_debug -b 115200
    ```
    You should see output like this:

    <a class="image-link" href="/assets/images/botlab/minicom-table.png">
    <img src="/assets/images/botlab/minicom-table.png" alt="" style="max-width:300px;"/>
    </a>
    - **Successful Firmware Flashing:** After flashing the firmware successfully, Minicom will display the table above. Manually turning the wheel will update the encoder counts in the Minicom terminal. All these are calculated and displayed by the firmware.
      - **Common confusion:** When both wheels rotate forward, the left wheel encoder counts and motor velocity (`ENC L` and `MOT L`) increase positively, while `ENC R` and `MOT R` are negative. Why aren’t they both positive?
          - This is the expected behavior. The wheel frames have their z-axes pointing outward, so based on right hand rule, rotating the right wheel forward corresponds to a negative rotation about its local z-axis. One purpose of calibration is to ensure the signs are correct and consistent with the coordinate definitions.
    - **Unsuccessful Firmware Flashing:** If the firmware doesn't flash correctly, repeat the calibration and firmware flashing steps. This time, open a second terminal window with Minicom running, so we can monitor its outputs for debugging. If there was an error, take a screenshot and send to the GSIs for better troubleshooting.

- **To exit Minicom**, press `CTRL + A`, then press `X`, then press `Enter` to quit.
   
## Drive the mbot
Run the following command in the VSCode terminal:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```
- Press `x` a few times to reduce the linear speed to 0.2, so the robot doesn't sprint out.
- Use your keyboard to drive the robot. As shown in the terminal:
    - `i` = forward
    - `,` = backward
    - `j` = turn left
    - `l` = turn right

If you’ve successfully driven your robot around, your control board setup is complete!
- If the robot does not drive straight forward when you press `i` and instead turns, but your calibration results look correct and the minicom table shows reasonable motor velocities, then the issue is likely related to the PID gains. We will address PID tuning in **Checkpoint 1**, so don’t worry about this for now.

## Setup mbot_ws
> This repository contains hardware ROS drivers, custom ROS messages, MBot URDF files, and the other ROS packages.

1. Go to the Class **GitLab** page, fork the `mbot_ros2_ws` repository to your group, and clone it to your mbot home directory.
   ```bash
    cd ~
    mkdir mbot_ws
    cd ~/mbot_ws
    git clone --recurse-submodules your_group_url src
   ```
    - The repository is called `mbot_ros2_ws`, but here we clone it into `~/mbot_ws/src`, the repo's name is irrelevant.
2. Run the following commands:
    ```bash
    cd ~/mbot_ws
    # Update package list
    sudo apt update
    # install ros dependencies
    rosdep install -y --from-paths src --ignore-src --rosdistro $ROS_DISTRO --skip-keys=libcamera
    # build the packages
    colcon build --symlink-install
    # source the env
    echo "source $PWD/install/local_setup.bash" >> ~/.bashrc
    source install/local_setup.bash
    ```
    - There might be warnings after running colcon build from sllidar_ros2 package: `1 package had stderr output: sllidar_ros2`, it is normal, if you re-run the command the warnings will be gone.
    - If `rosdep` says "your rosdep installation has not been initialized yet", run `rosdep update` and then run the `rosdep install` command again.

## Set up foxglove
Foxglove is a web-based visualization tool, it replaces NoMachine on the MBot image. The Foxglove bridge is already installed on the MBot, you do not need to install it.

Test:
1. Go to: [foxglove](https://app.foxglove.dev/) -> Sign in with Google -> Sign in with you UM account
2. Run the Foxglove bridge in the **VSCode terminal**:
    ```bash
    ros2 launch foxglove_bridge foxglove_bridge_launch.xml
    ```
3. Run the following in a second **VSCode terminal**:
    ```bash
    ros2 launch mbot_bringup mbot_bringup.launch.py 
    ```
4. Open connection -> Foxglove WebSocket -> Replace `localhost` with your IP address -> Open
5. If you use chrome, foxglove will pop up a window, follow the instruction there.
6. In the **3D** panel, open the panel settings -> **Topics**, and turn on `/scan` and `/robot_description`. You should see the robot model and the LiDAR scan.
    - You do not need to import a layout. If Foxglove asks, save the layout so it keeps these settings for next time.

- Run each command in **one** terminal only. A second bridge stops with "Address already in use", a second bringup stops with `SL_RESULT_OPERATION_TIMEOUT`.
- The LiDAR scan and the robot model only show up while `mbot_bringup` is running.
- Setting poses, camera and plots: see the [Foxglove Guide](/docs/botlab/how-to-guide/foxglove-guide).

Demo video:
<iframe width="560" height="315" src="https://www.youtube.com/embed/xWfMV1e5gKg?si=ucnY2If-2owgw8bM" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## Test Camera

Test your camera by going through the following steps in order. **If any of the steps produce unexpected results, contact the GSIs for assistance.**

1. To test if camera is detected, run this in the **VSCode terminal**:
    ```
   rpicam-hello
   ```
   - If the terminal didn't say "ERROR: *** no cameras available ***", your camera is detected. Everything is good, use `ctrl+C` to quit.
   - The MBot image has no desktop, so "Preview window unavailable" is expected.
2. To test if camera is working, run:
   ```bash
   cd ~
   rpicam-still -t 1 -o test.jpg
   ```
   - This will take a photo and save it in the home directory, you can use VSCode to check the photo. The photo will be upside-down, that's expected.
3. To test if camera ROS driver is working, run the following in the **VSCode terminal**:
   ```bash
    # bring up the camera node and flip the image
    ros2 run camera_ros camera_node --ros-args \
    -p orientation:=180 \
    -p width:=640 -p height:=480 \
    -p format:=BGR888
   ```
   - **Ignore** the errors about calibration files.
   - You can visualize the camera view in an **Image** panel in Foxglove (topic `/camera/image_raw/compressed`). Run the Foxglove bridge in a second **VSCode terminal** and connect as in [Set up foxglove](#set-up-foxglove).

{: .warning }
**Do not hot-swap the camera!** Hot swap will leave the camera on ghost state. If you need to replace the camera, the correct procedure is: Power OFF → Wait 30 seconds → Swap cameras or Re-insert ribbon cable → Power ON


## Test LiDAR
1. Run the following in the **VSCode terminal**:
    ```bash
    ros2 launch mbot_bringup mbot_bringup.launch.py 
    ```
    - This will bring up the lidar driver, the robot description for visualization, and the static tf.
    - Run it in one terminal only. If it is already running in another terminal, the second LiDAR driver stops with `SL_RESULT_OPERATION_TIMEOUT`.
2. Run the Foxglove bridge in a second **VSCode terminal** and connect Foxglove as in [Set up foxglove](#set-up-foxglove).
    ```bash
    ros2 launch foxglove_bridge foxglove_bridge_launch.xml
    ```
   You should see the robot model and the LiDAR scan show up in the **3D** panel. And if you look closely, the lidar scan is actually "floating", because it is shooting out from the lidar frame.


## Useful commands
### Turn LiDAR ON/OFF
This LiDAR switch command is for the mbots that have done the [hardware setup](/docs/botlab/mbot-hardware-setup-Pi5), in which the LiDAR is powered through the Bottom Board’s SV3 slot.
{: .text-red-200}

If you don’t need the LiDAR but it keeps spinning (which is loud and drains the power bank), you can turn it off using the following command:
```bash
# Turn the power off
ros2 service call /lidar_power std_srvs/srv/SetBool "{data: false}"
```
To turn the LiDAR back on:
```bash
# Turn the power on
ros2 service call /lidar_power std_srvs/srv/SetBool "{data: true}"
```
### Reset odometry
If you need to re-run motion controller test, or slam test, or any tests, and the odometry has already accumulated drift, you can reset all odometry calculations back to zero by:
```bash
ros2 service call /reset_odometry std_srvs/srv/Trigger
```
### Command list on the MBot
To see more commands grouped by topic (network, firmware, ROS, understanding the code, build, sensors, Foxglove, data, troubleshooting), run this on the MBot:
```bash
mbot --help
```
For example, `mbot help code` lists commands that help you find your way in the code: message fields, programs in a package, launch file arguments, the TF tree.
