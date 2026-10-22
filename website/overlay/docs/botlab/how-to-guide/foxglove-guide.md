---
layout: default
title: Foxglove Guide
parent: How-to Guide
grand_parent: Botlab
nav_order: 0
last_modified_at: 2026-10-16 12:00:00 -0400
---

Foxglove is the visualization tool for the MBot. It runs in the browser on your laptop and replaces NoMachine, RViz and rqt. The Foxglove bridge is already installed on the MBot image, you do not need to install anything on the robot.

In this guide, we list the Foxglove tips you need in the checkpoints. The first steps are the same as in [Set up foxglove](/docs/botlab/mbot-system-setup-Pi5#set-up-foxglove).

### Contents
* TOC
{:toc}

## Connect to the MBot
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
5. When you are done, stop the bridge with `ctrl+C`.

{: .warning }
While the bridge runs, anyone on the same network can see your topics and send commands to your robot, including `/cmd_vel`. Stop it when you do not need it.

## LiDAR scan or robot model not showing
1. Make sure the bringup is running, in **one** terminal only. A second bringup cannot open the LiDAR and stops with `SL_RESULT_OPERATION_TIMEOUT`.
2. Check that the scan is published, in another **VSCode Terminal**:
    ```bash
    ros2 topic hz /scan
    ```
    - You should see about 10 Hz.
3. In Foxglove, open the settings of the **3D** panel -> **Topics**, and turn on `/scan` and `/robot_description`.

You do not need to import a layout. Use the layout Foxglove opens with, and change it in Foxglove as described on this page. If Foxglove asks, save the layout so it keeps your settings for next time.

- Run the bridge in **one** terminal only, too. A second bridge stops with "Address already in use".

## Set the initial pose and the goal pose
The publish button is in the toolbar at the top right of the **3D** panel. Click and hold it to choose:
- **Pose estimate**: publishes `/initialpose`, used to initialize localization.
- **Pose**: publishes the goal for your path planner.

Then click on the map where the robot should be, and drag in the direction it should face.

- Foxglove publishes **Pose** to `/move_base_simple/goal` by default, which the MBot code does not listen to. In the 3D panel settings -> **Publish**, set the Pose topic to `/goal_pose`.

## Camera
- Add an **Image** panel and select `/camera/image_raw/compressed` while a camera node runs. Use the compressed topic over Wi-Fi, the raw image is slow.
- To see the rectified image (Checkpoint 4), select `/image_rect` in the panel settings.

## Plot
- In a **Plot** panel, add a series per value, for example `/odom.twist.twist.linear.x` and `/cmd_vel.linear.x` for Checkpoint 1.

## Tips
- Every topic shown in a panel is sent over Wi-Fi. Close panels you do not need.
- If Foxglove stops updating, check the robot is still on the network (the IP on the OLED) and restart the bridge.
- `mbot-viz` on the MBot starts the same bridge, prints the address to open, and tells you when the bridge or the LiDAR is not running.
