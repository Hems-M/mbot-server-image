---
layout: default
title: Competition
nav_order: 7
parent: Checkpoints
grand_parent: Botlab
last_modified_at: 2026-10-15 12:00:00 -0400
---

<a class="image-link" href="/assets/images/botlab/checkpoints/doge-meme.png">
<img src="/assets/images/botlab/checkpoints/doge-meme.png" alt=" " style="max-width:250px;"/>
</a>

## Contents
* TOC
{:toc}

## Event 1: Competition Runs [300 points max]

You will complete two runs: one judged on **accuracy** and one on **speed**.

### 1. Accuracy Run
- The MBot must **follow the given path** while running **SLAM** to generate a map of the arena.
- After completing the path, the MBot should **return to the starting pose**.
- Full autonomy using motion controller only, no teleop.
- Judging criteria:
  - Final pose error (position and heading)
  - Map quality

Pose Error Scoring:
- 100 points: < (3 cm, 3 cm, 15°)
- 75 points: < (5 cm, 5 cm, 15°)
- 50 points: < (10 cm, 10 cm, 30°)
- 25 points: < (20 cm, 20 cm, 45°)

Map Quality Scoring: [+100, +50, +25] for [Excellent, Good, OK] quality

### 2. Speed Run
- The MBot must **drive quickly** along the path: **Start → End → Start**
- You will be judged only on speed, not on final pose accuracy.
- Full autonomy using motion controller only, no teleop.
- Judged only on speed, but the final position must still be within (20 cm, 20 cm, 45°) of the starting location, or no points will be given.

Time Scoring:
- 100 points: ≤ 50s
- 75 points: ≤ 80s
- 50 points: ≤ 100s
- 25 points: ≤ 150s

Note: Speed thresholds may be adjusted based on actual times on the first competition day.


## Event 2: Factory Patrol Challenge [500 points max]

**Time Limit:** 10 minutes

Event 2 consists of three progressive levels, each simulating stages of a factory workflow:
  - Level 1 focuses on explore the facility.
  - Level 2 adds worksite patrol tasks.
  - Level 3 tests autonomous recovery and localization.

You may attempt any level directly and still earn partial credit if a level is not fully completed.

### Level 1 - Facility Exploration

Starting from the designated position, explore the area and generate a map, then return to the starting pose.
- Alternative ways to complete this level:
  - Use Foxglove to set goal poses for exploration -> 25% deduction
  - Use manual teleop for exploration -> points awarded **only for map quality, no points for pose return**.
  - Use `slam_toolbox` for mapping -> 50% deduction

**Scoring**

Pose Return Accuracy:
- 200 points: < (3 cm, 3 cm, 15°)
- 150 points: < (5 cm, 5 cm, 15°)
- 100 points: < (10 cm, 10 cm, 30°)
- 50 points: < (20 cm, 20 cm, 45°)

Map Quality: [+100, +50, +25] for map quality [Excellent, Good, OK]

### Level 2 - Worksite Patrol

Goal: Patrol the inspection points (AprilTags). Four unique AprilTags (no duplicates) will be placed in the area.
1. First, perform mapping as in Level 1.
2. When mapping is complete, inform the instructor. You may stop your code, save the map, recompile, or adjust configurations. Your Level 1 points will be evaluated at this time.
3. Then the MBot must **navigate autonomously** from start point to the tags in ascending order (by tag ID) and return to the starting point, no teleop or manual goal-setting.
  - For the patrol requirement, each AprilTag must come within 50 cm of the MBot’s camera view, then the robot should stop, rotate 360 degrees before continuing to the next tag.

**Scoring**

Earn Level 1 points, plus
- +25 points for each apriltag survey in the correct order
- Level 1 deduction only affects Level 1 points
- Max Total: Level 1 points + 100


### Level 3 - Autonomous Recovery
Goal: Restart operations from an unknown location using the saved map.
1. First, perform mapping as in Level 1.
2. When mapping is complete, inform the instructor. You may stop your code, save the map, recompile, or adjust configurations. Your Level 1 points will be evaluated at this time.
3. The instructor will place the robot at a random location. The location will be unique to avoid ambiguous symmetries.
4. Then the robot must operate **fully autonomously** to localize itself and complete the Worksite Patrol (as in Level 2). No teleop or manual goal-setting is allowed.
  - For example, if the robot wakes up near ID 3, it should autonomously visit ID 1 first, then return to 3, and continue to 4, 5, etc.

Tip: Save your map and AprilTag positions to initialize your particle filter with a detected tag and refine localization using wall data.

**Scoring**

Earn all Level 1 + Level 2 points, plus
- +100 points for completing Level 3
- Level 1 deduction only affects Level 1 points
- Max Total: Level 1 points + 100 + 100


## Event 3: Warehouse Chanllenge [400 points max]

**Time limit:** 10 minutes

Apriltag crates will be placed in the maze. Their positions are fixed, and all teams will have the same setup (the final layout may differ slightly from the image below).

The goal is to **locate the Apriltag crates and stack them together by matching their IDs**, simulating warehouse operations.
- You may map the area before starting.
- You may use `slam_toolbox` for mapping — no point deductions.

Below is an example of the warehouse arena:

<a class="image-link" href="/assets/images/botlab/checkpoints/competition.png">
<img src="/assets/images/botlab/checkpoints/competition.png" alt=" " style="max-width:400px;"/>
</a>

- Start in the red box area. The red boxes contain four ID pairs: 1–2, 3–4, 5–6, 7–8.
- The green boxes contain the same four pairs. Pick up each green box and stack it onto the matching red box.

Note: Each box has two Apriltag IDs. The even-numbered tags mark the two sides that cannot be forklifted, while the odd-numbered tags mark the two sides with forklift slots, where the pallet can be lifted.

**Scoring**
- +50 points for moving a crate to match its ID but failing to stack. (If the two crates with matching IDs physically touch, you earn +50 points. Simply lifting a crate does **not** count.)
- +100 points for successfully stacking crates with the same ID (e.g., stacking all ID 1 crates and all ID 3 crates yields 200 pts)
- 50% deduction if the robot navigates by teleop to get closer to the tag, **BUT** autonomously uses the forklift to lift the tag box (instead of manually driving the fork into the pallet).
- 75% deduction if the robot navigates by teleop **AND** the forklift is manually controlled (i.e., you manually drive the fork into the tag box).

## Score Calculation
Your overall score will be the sum of your best run on each event. Each event can be completed multiple times at different levels.
- The 3 top scoring teams **in each section** will receive bonus points on the report: [+3, +2, +1] points. 
- The top score **in each event** will receive +1 bonus point on the report for the team.
