---
layout: default
title: slam_toolbox Guide
parent: How-to Guide
grand_parent: Botlab
nav_order: 1
last_modified_at: 2026-10-16 12:00:00 -0400
---

Slam Toolbox is a set of tools and capabilities for 2D SLAM. More details can be found on its [GitHub page](https://github.com/SteveMacenski/slam_toolbox).

In this guide, we list all the commands you’ll need for tasks related to the final competition. Basically whenever you would normally run mbot_slam, simply replace those commands with the corresponding slam_toolbox commands.

### Contents
* TOC
{:toc}

## Teleop mapping

1. **VSCode Terminal #1**: launch the robot model, TF, LiDAR node.
    ```bash
    ros2 launch mbot_bringup mbot_bringup.launch.py 
    ```
2. Put the robot in the maze
3. **VSCode Terminal #2**: launch slam_toolbox
    ```bash
    ros2 launch mbot_navigation slam_toolbox_online_async_launch.py
    ```
4. **VSCode Terminal #3**: Run teleop node to drive robot to explore the area
    ```bash
    ros2 run teleop_twist_keyboard teleop_twist_keyboard
    ```
5. Start foxglove
    ```bash
    # VSCode Terminal #4
    ros2 launch foxglove_bridge foxglove_bridge_launch.xml
    ```
6. **VSCode Terminal #5**: Save the map. In this example, we save it to the `mbot_nav/maps` folder so it can be used for A* path-planning tests.
    ```bash
    cd ~/mbot_ros_labs/src/mbot_nav/maps
    ros2 run nav2_map_server map_saver_cli -f map_name
    ```

## Goal setting exploration

1. **VSCode Terminal #1**: launch the robot model, TF, LiDAR node.
    ```bash
    ros2 launch mbot_bringup mbot_bringup.launch.py 
    ```
2. Put the robot in the maze
3. **VSCode Terminal #2**: launch slam_toolbox
    ```bash
    ros2 launch mbot_navigation slam_toolbox_online_async_launch.py
    ```
4. **VSCode Terminal #3**: Run motion controller
    ```bash
   cd ~/mbot_ros_labs
   source install/setup.bash
   ros2 run mbot_nav controller_node --ros-args -p use_localization:=true
    ```
5. **VSCode Terminal #4**: Run path planner
    ```bash
    cd ~/mbot_ros_labs
    source install/setup.bash
    ros2 run mbot_nav navigation_node --ros-args -p pose_source:=tf
    ```
1. Start foxglove. You can use **Pose** in the Foxglove **3D** panel (pose topic `/goal_pose`) to set the goal pose to lead the mbot to explore.
    ```bash
    # VSCode Terminal #5
    ros2 launch foxglove_bridge foxglove_bridge_launch.xml
    ```
2. **VSCode Terminal #6**: Save the map
    ```bash
    cd ~/mbot_ros_labs/src/mbot_nav/maps
    ros2 run nav2_map_server map_saver_cli -f map_name
    ```

### Video Demo

<iframe width="560" height="315" src="https://www.youtube.com/embed/HTP2kHmTvoQ?si=Ke9m9sMpRcZUkIQ_" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>