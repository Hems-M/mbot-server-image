#!/bin/bash
# Step 60: home folder of the mbot user, laid out like the current course image.
# Compared with /home/mbot of 2026-01-15-mbot-ros2-base-ubuntu24.img (docs/build-notes.md):
# - the eight standard folders (Desktop, Documents, ... Videos)
# - SecureW2_JoinNow.run (from upstream/mbot_sys_utils; mwireless-setup is the headless way)
# - pico-sdk and microros_ws: links to the root-owned system copies in /opt, so the paths
#   in course docs and old .bashrc lines still work and a student cannot break them
# - the MBot lines at the end of ~/.bashrc, adapted to the server image
# - MBOT_COMMANDS.md: the command manual (also: mbot-help)
# - the terminal tools mbot, mbot-help, mbot-status (mbot health), mbot-report and the Foxglove layout
# - a rosdep cache in ~/.ros/rosdep, as on the course image
# Not copied: snap/, .nx/ (NoMachine), caches and history (desktop or personal state).
# Safe to run more than once.
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
require_image_chroot

home="$(getent passwd "$MBOT_USER" | cut -d: -f6)"
[[ -d "$home" ]] || die "home of $MBOT_USER not found"

log "standard folders"
for d in Desktop Documents Downloads Music Pictures Public Templates Videos; do
    install -d -m 0755 -o "$MBOT_USER" -g "$MBOT_USER" "$home/$d"
done

log "SecureW2_JoinNow.run (course image file; upstream mbot_sys_utils copy)"
install -m 0755 -o "$MBOT_USER" -g "$MBOT_USER" \
    "$UPSTREAM/mbot_sys_utils/install_scripts/SecureW2_JoinNow.run" "$home/SecureW2_JoinNow.run"

log "pico-sdk -> /opt/pico-sdk"
[[ -f /opt/pico-sdk/pico_sdk_init.cmake ]] || die "/opt/pico-sdk missing (run step 50 first)"
if [[ -e "$home/pico-sdk" && ! -L "$home/pico-sdk" ]]; then
    die "$home/pico-sdk exists and is not a link"
fi
ln -sfn /opt/pico-sdk "$home/pico-sdk"
chown -h "$MBOT_USER:$MBOT_USER" "$home/pico-sdk"

log "microros_ws/install -> /opt/mbot/microros"
[[ -r /opt/mbot/microros/local_setup.sh ]] || die "/opt/mbot/microros missing (run step 30 first)"
install -d -m 0755 -o "$MBOT_USER" -g "$MBOT_USER" "$home/microros_ws"
ln -sfn /opt/mbot/microros "$home/microros_ws/install"
chown -h "$MBOT_USER:$MBOT_USER" "$home/microros_ws/install"
install -m 0644 -o "$MBOT_USER" -g "$MBOT_USER" "$SYSTEM_DIR/home/microros_ws-README.md" "$home/microros_ws/README.md"

log ".bashrc of $MBOT_USER: MBot lines"
bashrc="$home/.bashrc"
[[ -f "$bashrc" ]] || install -m 0644 -o "$MBOT_USER" -g "$MBOT_USER" /etc/skel/.bashrc "$bashrc"
if ! grep -q '^# >>> MBot >>>' "$bashrc"; then
    cat "$SYSTEM_DIR/home/bashrc-mbot.sh" >> "$bashrc"
fi

log "command manual: ~/MBOT_COMMANDS.md, /opt/mbot/share/MBOT_COMMANDS.md, mbot-help"
install_file "$SYSTEM_DIR/home/MBOT_COMMANDS.md" /opt/mbot/share/MBOT_COMMANDS.md 0644
install -m 0644 -o "$MBOT_USER" -g "$MBOT_USER" "$SYSTEM_DIR/home/MBOT_COMMANDS.md" "$home/MBOT_COMMANDS.md"
install_file "$SYSTEM_DIR/tools/mbot-help" /usr/local/bin/mbot-help 0755

log "terminal tools: mbot, mbot-status (mbot health), mbot-report, UM theme, Foxglove layout"
install_file "$SYSTEM_DIR/lib/mbot-theme.sh" /opt/mbot/lib/mbot-theme.sh 0644
install_file "$SYSTEM_DIR/tools/mbot" /usr/local/bin/mbot 0755
install_file "$SYSTEM_DIR/tools/mbot-status" /usr/local/bin/mbot-status 0755
install_file "$SYSTEM_DIR/tools/mbot-report" /usr/local/bin/mbot-report 0755
install_file "$SYSTEM_DIR/foxglove/mbot-layout.json" /opt/mbot/share/foxglove/mbot-layout.json 0644
python3 -m json.tool /opt/mbot/share/foxglove/mbot-layout.json >/dev/null || die "Foxglove layout is not valid JSON"

# The course image ships a rosdep cache in ~/.ros, so "rosdep install" works without
# "rosdep update" first (rc2 on a robot: "rosdep installation has not been initialized").
log "rosdep cache for $MBOT_USER (~/.ros/rosdep)"
runuser -u "$MBOT_USER" -- env HOME="$home" bash -c "source /opt/ros/$ROS_DISTRO/setup.bash && rosdep update --rosdistro $ROS_DISTRO" >/dev/null
[[ -d "$home/.ros/rosdep/sources.cache" ]] || die "rosdep cache missing in $home/.ros/rosdep"

log "login message: MBot summary; Ubuntu advertising and help links off"
install_file "$SYSTEM_DIR/motd/99-mbot" /etc/update-motd.d/99-mbot 0755
for f in 10-help-text 50-motd-news; do
    [[ -f "/etc/update-motd.d/$f" ]] && chmod -x "/etc/update-motd.d/$f"
done
[[ -f /etc/default/motd-news ]] && sed -i 's/^ENABLED=1/ENABLED=0/' /etc/default/motd-news
# The release-upgrade check contacts changelogs.ubuntu.com at login and fails on campus
# ("Failed to connect to https://changelogs.ubuntu.com/meta-release-lts"). Robots stay on 24.04.
[[ -f /etc/update-manager/release-upgrades ]] && sed -i 's/^Prompt=.*/Prompt=never/' /etc/update-manager/release-upgrades

chown "$MBOT_USER:$MBOT_USER" "$home" "$bashrc"
{
    echo "# /home/$MBOT_USER after step 60"
    ls -la "$home"
    echo
    echo "# MBot lines in .bashrc"
    sed -n '/^# >>> MBot >>>/,/^# <<< MBot <<</p' "$bashrc"
} > "$MBOT_REPORTS/home.txt"
log "check: as $MBOT_USER, a login shell sees ROS, the pico-sdk and the agent package"
# shellcheck disable=SC2016  # expanded by the login shell of the user, not here
runuser -u "$MBOT_USER" -- bash -lic \
    'echo "ROS_DISTRO=$ROS_DISTRO PICO_SDK_PATH=$PICO_SDK_PATH"; ros2 pkg prefix micro_ros_agent; test -f "$HOME/pico-sdk/pico_sdk_init.cmake" && echo "pico-sdk link OK"' \
    2>&1 | tail -3 | tee -a "$MBOT_REPORTS/home.txt"
grep -q 'pico-sdk link OK' "$MBOT_REPORTS/home.txt" || die "home check failed (see home.txt)"

log "check: mbot --help and mbot health run as $MBOT_USER (no Pico here, so problems are expected)"
report="$MBOT_REPORTS/mbot-health.txt"
runuser -u "$MBOT_USER" -- env HOME="$home" ROS_LOG_DIR=/tmp/mbot-health-ros-log bash -c \
    'mbot --help >/dev/null && mbot help code >/dev/null && mbot health --no-color' > "$report" 2>&1 || true
cat "$report"
grep -q '^PROBLEMS' "$report" || die "mbot health did not finish (see mbot-health.txt)"
! grep -q 'Traceback' "$report" || die "mbot health raised an error (see mbot-health.txt)"

log "done"
