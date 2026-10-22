#!/bin/bash
# Step 30: MBot system layer (D-05, ROS-004, ROS-005, HW-001, OS-003).
# - micro-ROS agent built at pinned commits into /opt/mbot/microros
# - mbot_interfaces underlay built from upstream/mbot_ros2_ws into /opt/mbot/ros
# - MBot scripts, udev rules and services from upstream/mbot_sys_utils, installed by this
#   script; the agent uses our own unit file so no service reads the student home
# - the new OLED service (system/oled, D-17) in /opt/mbot/oled, with its unit tests run here
# - mbot_config.txt template, mbot-upload-firmware (ours, P-38), mbot-viz, boot config for servos
# Upstream files are copied, never edited. Safe to run more than once.
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
require_image_chroot

SYS_UTILS="$UPSTREAM/mbot_sys_utils/ros2_mbot_sys_utils"

mapfile -t pkgs < <(manifest_packages "$MANIFESTS/apt-packages.txt" 30)
apt_install "${pkgs[@]}"

mkdir -p /opt/mbot/bin /etc/mbot
install_file "$SYSTEM_DIR/bin/mbot-ros-exec" /opt/mbot/bin/mbot-ros-exec 0755
install_file "$SYSTEM_DIR/tmpfiles/mbot.conf" /etc/tmpfiles.d/mbot.conf 0644
install -d -m 0775 -o root -g "$MBOT_USER" /var/log/mbot

# ---------------------------------------------------------------- micro-ROS agent
agent_id="agent=${MICRO_ROS_AGENT_COMMIT} msgs=${MICRO_ROS_MSGS_COMMIT}"
if stamp_matches micro-ros-agent "$agent_id" && [[ -x /opt/mbot/microros/lib/micro_ros_agent/micro_ros_agent ]]; then
    log "micro-ROS agent already built ($agent_id)"
else
    log "micro-ROS agent: build $agent_id"
    ws="$MBOT_BUILD_TMP/microros_ws"
    rm -rf "$ws" /opt/mbot/microros
    mkdir -p "$ws/src"
    git_pinned "$MICRO_ROS_AGENT_REPO" "" "$MICRO_ROS_AGENT_COMMIT" "$ws/src/micro-ROS-Agent"
    git_pinned "$MICRO_ROS_MSGS_REPO" "" "$MICRO_ROS_MSGS_COMMIT" "$ws/src/micro_ros_msgs"
    export ROS_HOME="$MBOT_BUILD_TMP/rosdep-home"
    with_ros rosdep update --rosdistro "$ROS_DISTRO" >/dev/null
    with_ros rosdep install --rosdistro "$ROS_DISTRO" --from-paths "$ws/src" --ignore-src -y
    unset ROS_HOME
    # Same CMake options as micro_ros_setup's build_agent.sh.
    (cd "$ws" && with_ros colcon build --merge-install --event-handlers console_cohesion- \
        --install-base /opt/mbot/microros --packages-up-to micro_ros_agent \
        --cmake-args -DCMAKE_BUILD_TYPE=Release -DUAGENT_BUILD_EXECUTABLE=OFF \
        -DUAGENT_P2P_PROFILE=OFF --no-warn-unused-cli)
    [[ -x /opt/mbot/microros/lib/micro_ros_agent/micro_ros_agent ]] || die "agent binary missing after build"
    # Record the Micro XRCE-DDS Agent version the superbuild fetched.
    find /opt/mbot/microros/lib -maxdepth 1 -name 'libmicroxrcedds_agent.so.*.*.*' -printf '%f\n' \
        > "$MBOT_REPORTS/micro-ros-agent-superbuild.txt"
    rm -rf "$ws"
    stamp_write micro-ros-agent "$agent_id"
fi

# ---------------------------------------------------------------- mbot_interfaces underlay
iface_id="mbot_ros2_ws=${MBOT_ROS2_WS_COMMIT:-unknown}"
if stamp_matches mbot-interfaces "$iface_id" && [[ -f /opt/mbot/ros/local_setup.bash ]]; then
    log "mbot_interfaces underlay already built ($iface_id)"
else
    log "mbot_interfaces underlay: build from $iface_id"
    ws="$MBOT_BUILD_TMP/mbot_interfaces_ws"
    rm -rf "$ws" /opt/mbot/ros
    mkdir -p "$ws/src"
    cp -a "$UPSTREAM/mbot_ros2_ws/mbot_interfaces" "$ws/src/"
    (cd "$ws" && with_ros colcon build --merge-install --event-handlers console_cohesion- \
        --install-base /opt/mbot/ros --cmake-args -DCMAKE_BUILD_TYPE=Release)
    rm -rf "$ws"
    stamp_write mbot-interfaces "$iface_id"
fi
log "underlay check: $(/opt/mbot/bin/mbot-ros-exec python3 -c 'from mbot_interfaces.msg import BatteryADC; print("BatteryADC import OK")')"

# ---------------------------------------------------------------- upstream scripts and rules
log "mbot_sys_utils scripts (upstream paths kept: interface contract for mwireless-setup)"
install_file "$SYS_UTILS/services/mbot_start_networking.sh" /usr/local/etc/mbot_start_networking.sh 0755
# P-38: the boot script must not drive the Pico RUN/BOOTSEL pins (GPIO 17 and 4).
log "patch mbot_start_networking.sh: Pico pins as inputs instead of outputs"
patch --forward --silent /usr/local/etc/mbot_start_networking.sh \
    < "$SYSTEM_DIR/firmware/mbot_start_networking-release-gpio.patch" \
    || die "mbot_start_networking-release-gpio.patch does not apply (upstream script changed?)"
! grep -q gpioset /usr/local/etc/mbot_start_networking.sh \
    || die "mbot_start_networking.sh still drives GPIO (gpioset)"
# Same path as the current course image. No unit starts it any more (replaced by system/oled).
install_file "$SYS_UTILS/services/mbot_ros_oled_display.py" /usr/local/etc/mbot_ros_oled_display.py 0755
# P-38: our upload script (USB or buttons, never GPIO) instead of the upstream one.
install_file "$SYSTEM_DIR/firmware/mbot-upload-firmware" /usr/local/bin/mbot-upload-firmware 0755
! grep -qE 'gpioset|pinctrl' /usr/local/bin/mbot-upload-firmware \
    || die "mbot-upload-firmware drives GPIO"
install_file "$SYS_UTILS/udev_rules/ros-mbot.rules" /etc/udev/rules.d/99-ros-mbot.rules 0644
install_file "$SYSTEM_DIR/tools/mbot-viz" /usr/local/bin/mbot-viz 0755

if [[ -f /boot/firmware/mbot_config.txt ]]; then
    log "keep existing /boot/firmware/mbot_config.txt"
else
    install_file "$SYS_UTILS/mbot_config.txt" /boot/firmware/mbot_config.txt 0644
fi

# ---------------------------------------------------------------- OLED service (D-17)
log "OLED service: system/oled to /opt/mbot/oled"
rm -rf /opt/mbot/oled
mkdir -p /opt/mbot/oled
cp -r "$SYSTEM_DIR/oled/mbot_oled" /opt/mbot/oled/
find /opt/mbot/oled -name __pycache__ -prune -exec rm -rf {} +
# The service user cannot write here, so compile now.
python3 -m compileall -q /opt/mbot/oled
chmod -R u=rwX,go=rX /opt/mbot/oled
log "OLED unit tests (with the image's Python, Pillow and fonts)"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s "$SYSTEM_DIR/oled/tests" 2>&1 \
    | tee "$MBOT_REPORTS/oled-tests.txt" | tail -3
grep -q '^OK' "$MBOT_REPORTS/oled-tests.txt" || die "OLED unit tests failed (see oled-tests.txt)"
log "OLED import check: $(cd /opt/mbot/oled && /opt/mbot/bin/mbot-ros-exec python3 -c 'import luma.oled, mbot_oled.service, mbot_interfaces.msg; print("luma.oled", luma.oled.__version__, "and mbot_interfaces OK")')"
log "OLED service smoke test: 8 s as $MBOT_USER without an OLED, then SIGTERM"
smoke="$MBOT_REPORTS/oled-smoke-test.txt"
(
    cd /opt/mbot/oled
    runuser -u "$MBOT_USER" -- env PYTHONDONTWRITEBYTECODE=1 ROS_LOG_DIR=/var/log/mbot/ros \
        /opt/mbot/bin/mbot-ros-exec python3 -m mbot_oled &
    sleep 8
    pid="$(pgrep -u "$MBOT_USER" -f 'python3 -m mbot_oled' | head -1)"
    [[ -n "$pid" ]] || { echo "service not running after 8 s"; exit 0; }
    kill -TERM "$pid"
    for i in $(seq 1 50); do
        if ! kill -0 "$pid" 2>/dev/null; then echo "exited ${i}00 ms after SIGTERM"; break; fi
        sleep 0.1
    done
    if kill -0 "$pid" 2>/dev/null; then echo "still running 5 s after SIGTERM"; kill -KILL "$pid"; fi
    wait
) > "$smoke" 2>&1
grep -v RTPS "$smoke"
grep -q 'subscribed to /battery_adc' "$smoke" || die "OLED smoke test: no ROS subscription (see oled-smoke-test.txt)"
grep -q 'OLED not found' "$smoke" || die "OLED smoke test: missing-OLED path not reached"
grep -q 'exited .* ms after SIGTERM' "$smoke" || die "OLED smoke test: did not stop on SIGTERM"
! grep -qE 'Traceback|terminate called|core dumped' "$smoke" \
    || die "OLED smoke test: error or unclean exit (see oled-smoke-test.txt)"
install_file "$SYSTEM_DIR/modules-load/mbot.conf" /etc/modules-load.d/mbot.conf 0644

log "systemd units"
# mbot-start-network: upstream unit unchanged (runs as root, no student files).
install_file "$SYS_UTILS/services/mbot-start-network.service" /etc/systemd/system/mbot-start-network.service 0644
# Agent and OLED: our units (system layer, no ~/.bashrc). The OLED unit runs /opt/mbot/oled.
install_file "$SYSTEM_DIR/systemd/mbot-microros-agent.service" /etc/systemd/system/mbot-microros-agent.service 0644
install_file "$SYSTEM_DIR/systemd/mbot-oled.service" /etc/systemd/system/mbot-oled.service 0644
systemctl enable mbot-start-network.service mbot-microros-agent.service mbot-oled.service
# The Foxglove bridge is not a service (D-10). mbot-viz starts it on demand.

# ---------------------------------------------------------------- boot configuration
log "config.txt: UART0 on GPIO 14/15 for the Design Lab servos"
config=/boot/firmware/config.txt
if ! grep -q '^dtoverlay=uart0-pi5' "$config"; then
    {
        echo
        echo "[all]"
        echo "# MBot server image: UART0 on GPIO 14/15 for the Dynamixel servo board (Design Lab)."
        echo "# Gives /dev/ttyAMA0. The serial console stays on the Pi 5 debug UART (ttyAMA10)."
        echo "dtoverlay=uart0-pi5"
    } >> "$config"
fi

# Ubuntu enables rpi-eeprom-update.service, which runs "rpi-eeprom-update -a" at boot and
# stages a bootloader EEPROM update on its own. Firmware changes on robots are a deliberate
# staff action (D-16), so turn the automatic update off. Staff can still run rpi-eeprom-update.
log "bootloader EEPROM: disable automatic updates at boot"
systemctl disable rpi-eeprom-update.service 2>/dev/null || true
log "rpi-eeprom-update.service: $(systemctl is-enabled rpi-eeprom-update.service 2>&1 || true)"

log "done"
