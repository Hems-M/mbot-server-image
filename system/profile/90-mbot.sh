# MBot shell environment. Installed to /etc/profile.d/90-mbot.sh.
# Login shells read it through /etc/profile. Interactive non-login shells (for example
# VS Code terminals) read it through a line in /etc/bash.bashrc.
# The MBot system underlay (/opt/mbot/ros) is not sourced here on purpose, so a student
# build of mbot_interfaces does not trigger colcon "overriding package" warnings.

if [ -z "${MBOT_PROFILE_LOADED:-}" ]; then
    MBOT_PROFILE_LOADED=1

    if [ -r /etc/mbot/ros.env ]; then
        set -a
        # shellcheck source=/dev/null
        . /etc/mbot/ros.env
        set +a
    fi

    # ROS setup scripts are written for bash and zsh.
    if [ -n "${BASH_VERSION:-}" ] && [ -r "/opt/ros/${ROS_DISTRO:-jazzy}/setup.bash" ]; then
        # shellcheck source=/dev/null
        . "/opt/ros/${ROS_DISTRO:-jazzy}/setup.bash"
    fi

    # Pico firmware build (mbot_firmware_ros reads PICO_SDK_PATH).
    export PICO_SDK_PATH=/opt/pico-sdk
    export PICO_TOOLCHAIN_PATH=/usr/bin/
fi
