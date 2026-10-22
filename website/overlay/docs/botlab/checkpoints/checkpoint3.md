---
layout: default
title: Checkpoint 3
nav_order: 4
parent: Checkpoints
grand_parent: Botlab
last_modified_at: 2026-10-16 12:00:00 -0400
---


Using the SLAM algorithm you implemented previously, you can now construct a map of an environment with the MBot. In this checkpoint, you will add path planning and autonomous exploration capabilities.

### Contents
* TOC
{:toc}

## Task 3.1 Path Planning
 
Implement a path planner. Given start pose, end pose, and the map, output the path in waypoints.

### TODO
1. All work for this task is in the package `mbot_nav`. Start with `navigation_node.cpp` as main. Under `planners` folder, we have A star and Theta star planning template, and an example skeleton. After finishing the A star, feel free to try any other planners.
   - You also need to complete `obstacle_distance_grid.cpp`. We pre-compute the obstacle map in the file.
2. When finished, compile your code:
    ```bash
    cd ~/mbot_ros_labs
    colcon build --packages-select mbot_nav
    source install/setup.bash
    ```
   - {: .text-red-200} **Important: You must source the workspace in every relevant terminal after each build. If you don’t, ROS will keep using the old code, and your changes will not take effect.**
  
### Planning-only test
In this test, the navigation node listens to `/initialpose` and `/goal_pose` topics. Publishing both in Foxglove triggers the A* planner, and the planned path will be displayed if successful. No real robot movement occurs, purely to test the path calculation.
  
1. Run launch file to publish map and run nagivation node in **VSCode Terminal**:
  ```bash
  cd ~/mbot_ros_labs
  source install/setup.bash
  ros2 launch mbot_nav path_planning.launch.py map_name:=maze1
  ```
1. Run Foxglove bridge in **VSCode Terminal**, then set initial pose and goal pose in Foxglove:
  ```bash
  ros2 launch foxglove_bridge foxglove_bridge_launch.xml
  ```
  - In the Foxglove **3D** panel, use the publish button: **Pose estimate** publishes `/initialpose` and **Pose** publishes `/goal_pose`. Foxglove publishes **Pose** to `/move_base_simple/goal` by default: in the 3D panel settings -> **Publish**, set the Pose topic to `/goal_pose`.

**Video Demo**: shows both rviz and foxglove usage (RViz is not available on the MBot image, use the Foxglove part)
<iframe width="560" height="315" src="https://www.youtube.com/embed/SjNBaVulPzw?si=70njmZFXUyDTvZif" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

### Real world test

After validating your planner, we can test the full stack in real world.

1. Construct a map and save it in `mbot_ros_labs/src/mbot_nav/maps`. You may use your own mbot_slam code or use slam_toolbox to map. 
   - Good map quality is important, so we provide a guide on [how to use slam_toolbox](/docs/botlab/how-to-guide/slam-toolbox-guide)! If you’re not satisfied with your mapping performance, but still need a map to test your A* or exploration algorithms, feel free to take a look.
2. Then compile the `mbot_nav` package:
   ```bash
   cd ~/mbot_ros_labs
   colcon build --packages-select mbot_nav
   source install/setup.bash
   ```
3. Launch the robot model, TF, LiDAR node in **VSCode Terminal**.
   ```bash
   ros2 launch mbot_bringup mbot_bringup.launch.py 
   ```
4. Run launch file to publish map and run nagivation node in **VSCode Terminal**:
   ```bash
   cd ~/mbot_ros_labs
   source install/setup.bash
   ros2 launch mbot_nav path_planning.launch.py map_name:=your_map pose_source:=tf
   ```
5. Run localization node in **VSCode Terminal**:
   ```bash
   cd ~/mbot_ros_labs
   source install/setup.bash
   ros2 run mbot_slam localization_node --ros-args -p publish_tf:=true
   ```
6. Start Foxglove bridge in **VSCode Terminal** and **set the initial pose** with **Pose estimate** in the Foxglove **3D** panel. This pose should be your best estimate of the robot’s location in the maze. Use the maze view to place it as close as possible to the robot’s actual position, see the demo video below for details. The localization node uses this pose to initialize its particles. In Task 2.2, you do not need to set it manually because the ROS bag already contains this information.
   ```bash
   ros2 launch foxglove_bridge foxglove_bridge_launch.xml
   ```
7. Run motion controller in **VSCode Terminal**:
   ```bash
   cd ~/mbot_ros_labs
   source install/setup.bash
   ros2 run mbot_nav controller_node --ros-args -p use_localization:=true
   ```
8. Then **set the goal pose** with **Pose** in the Foxglove **3D** panel.

**Video Demo**

<iframe width="560" height="315" src="https://www.youtube.com/embed/1k5I7wipIsQ?si=v6b-GWF3y0NzjLpK" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

After testing all features, we also provide a launch file `navigation.launch.py`, it can start all nodes at once. **This is not recommended during development**; running each node manually exposes errors earlier and provides clearer diagnostics.
1. Bring up the mbot:
    ```bash
    ros2 launch mbot_bringup mbot_bringup.launch.py
    ```
2. Launch navigation (map server + localization + planner + controller):
    ```bash
    cd ~/mbot_ros_labs
    source install/setup.bash
    ros2 launch mbot_nav navigation.launch.py map_name:=your_map
    ```
3. Open Foxglove, set **Pose estimate** (needed by the particle filter), then **Pose** (the goal pose):
   ```bash
   ros2 launch foxglove_bridge foxglove_bridge_launch.xml
   ```

{: .required_for_report } 
Provide a figure showing the planned path in the map.


## Task 3.2 Map Exploration

Until now, the MBot has only moved using teleop commands or manually set goal poses. For this task, you will implement a frontier-based exploration algorithm that allows the MBot to autonomously select targets and explore the full environment.

This task is useful for competition but **not required for Checkpoint 3 submission**.

### TODO
1. All work is in `mbot_nav`. Start with `exploration_node.cpp`.
2. When finished, compile your code:
    ```bash
    cd ~/mbot_ros_labs
    colcon build --packages-select mbot_nav
    source install/setup.bash
    ```
   - {: .text-red-200} **Important: You must source the workspace in every relevant terminal after each build. If you don’t, ROS will keep using the old code, and your changes will not take effect.**
  
**How to test?**
1. Run foxglove bridge in **VSCode Terminal**
   ```bash
   ros2 launch foxglove_bridge foxglove_bridge_launch.xml
   ```
2. Launch the robot model, TF, LiDAR node in **VSCode Terminal**.
   ```bash
   ros2 launch mbot_bringup mbot_bringup.launch.py 
   ```
3. Run slam in **VSCode Terminal**.
   ```bash
   cd ~/mbot_ros_labs
   source install/setup.bash
   ros2 run mbot_slam slam_node
   ```
4. Run the navigation node (TF mode, SLAM provides the pose) in **VSCode Terminal**.
   ```bash
   cd ~/mbot_ros_labs
   source install/setup.bash
   ros2 run mbot_nav navigation_node --ros-args -p pose_source:=tf
   ```
5. Run the controller in **VSCode Terminal**.
   ```bash
   cd ~/mbot_ros_labs
   source install/setup.bash
   ros2 run mbot_nav controller_node --ros-args -p use_localization:=true
   ```
6. Run the exploration node:
   ```bash
   cd ~/mbot_ros_labs
   source install/setup.bash
   ros2 run mbot_nav exploration_node
   ```

**Video Demo**:
<iframe width="560" height="315" src="https://www.youtube.com/embed/9ukhlCYGw0Y?si=LzgiCsqAPhFecLwA" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

After testing all features, we also provide a launch file `exploration.launch.py`, it can start all nodes at once. **This is not recommended during development**; running each node manually exposes errors earlier and provides clearer diagnostics.
1. Bring up the mbot:
    ```bash
    ros2 launch mbot_bringup mbot_bringup.launch.py
    ```
2. Launch exploration (SLAM + planner + controller + frontier explorer):
    ```bash
    cd ~/mbot_ros_labs
    source install/setup.bash
    ros2 launch mbot_nav exploration.launch.py
    ```
3. Open Foxglove to watch the map grow:
    ```bash
    ros2 launch foxglove_bridge foxglove_bridge_launch.xml
    ```

{: .required_for_report } 
Explain the strategy used for finding frontiers and any other details about your implementation that you found important for making your algorithm work.

## Task 3.3 Localization with Estimated and Unknown Starting Position

For advanced competition levels, the MBot must localize itself in a known map without knowing its initial pose. This will require initializing your particles in some distribution in open space on the map, and converging on a pose. This is useful in the competition but **does not required any submission in the Checkpoint 3**.

Details please check competition event 2 - level 3.

{: .required_for_report } 
Explain the methods used for initial localization.

## Checkpoint Submission

Demonstrate your path planner (task 3.1) by showing your robot navigating a maze.
- Submit a video of your robot autonomously navigating in a maze environment.
   - Your video should include the following:
      - Set goal pose, then the robot driving in the real-world lab maze.
      - Your visualization tool (Foxglove) displaying the map and planned path.
