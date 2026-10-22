# microros_ws

On the course desktop image this folder held the micro-ROS agent workspace.
On the MBot server image the agent is built once into `/opt/mbot/microros` (owned by root),
and `install` here is a link to it, so the old `.bashrc` line still works:

    source ~/microros_ws/install/local_setup.sh

The agent runs as a service. You do not need to start it by hand:

    systemctl status mbot-microros-agent
    journalctl -u mbot-microros-agent -b

Deleting this folder does not break the robot.
