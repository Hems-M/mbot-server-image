#!/bin/bash
# Step 20: ROS 2 Jazzy (D-02, ROS-001, ROS-002, ROS-003).
# Pinned ROS apt source, ros-base plus the packages in image/manifests/ros-packages.txt,
# one ROS environment file for services and shells, rosdep initialized.
# Writes reports: which GUI libraries each package pulls in, and whether the student
# repositories' rosdep keys are already satisfied. Safe to run more than once.
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
require_image_chroot

# Packages that must never be listed in our manifest (review section 5.2, D-03).
FORBIDDEN_RE='^(ros-jazzy-desktop.*|ros-jazzy-rviz2|ros-jazzy-rqt.*|ros-jazzy-image-pipeline|ros-jazzy-navigation2|ros-jazzy-nav2-bringup)$'
# Names that indicate GUI or 3D rendering libraries.
GUI_RE='^(libqt[0-9]|qt[56]-|qt6-|libogre|ros-jazzy-rviz|ros-jazzy-rqt|libgtk|libgdk|libx11-6$|libxcb[0-9a-z-]*$|libwayland|libgl1|libglx|libegl1|libopengl0|libvtk|tk8|libtk8|python3-tk$|python3-pyqt|libsdl|libxrender|libxext6$|libxi6$|libxrandr|libxcursor|libxinerama)'

mapfile -t ros_pkgs < <(manifest_packages "$MANIFESTS/ros-packages.txt")
for p in "${ros_pkgs[@]}"; do
    if [[ "$p" =~ $FORBIDDEN_RE ]]; then
        die "forbidden package in ros-packages.txt: $p"
    fi
done

log "ROS apt source ${ROS_APT_SOURCE_VERSION}"
installed="$(dpkg-query -W -f '${Version}' ros2-apt-source 2>/dev/null || true)"
if [[ "$installed" != "${ROS_APT_SOURCE_VERSION}"* ]]; then
    deb="$MBOT_BUILD_TMP/ros2-apt-source.deb"
    curl -fsSL -o "$deb" "$ROS_APT_SOURCE_URL"
    echo "$ROS_APT_SOURCE_SHA256  $deb" | sha256sum -c - || die "ros2-apt-source checksum mismatch"
    dpkg -i "$deb"
fi
apt-get "${APT_RETRY[@]}" update

log "GUI dependency check (apt-cache depends, before install)"
report="$MBOT_REPORTS/ros-gui-deps.txt"
{
    echo "# GUI and rendering libraries pulled in by each package in ros-packages.txt"
    echo "# Method: apt-cache depends --recurse (Depends and PreDepends only), names matching:"
    echo "# $GUI_RE"
    echo
} > "$report"
for p in "${ros_pkgs[@]}"; do
    closure="$(apt-cache depends --recurse --no-recommends --no-suggests --no-conflicts \
        --no-breaks --no-replaces --no-enhances "$p" | grep -v '^ ' | grep -v '^<' | sort -u)"
    gui="$(grep -E "$GUI_RE" <<< "$closure" | tr '\n' ' ' || true)"
    printf '%-40s deps=%-4s gui: %s\n' "$p" "$(wc -l <<< "$closure")" "${gui:-none}" >> "$report"
done
log "report written: $report"

# ros-jazzy-apriltag-ros 3.4.0 (newer than the course image's 3.2.2) depends on
# ros-jazzy-camera-ros, which brings a second libcamera and libpisp into /opt/ros/jazzy/lib.
# Every ROS shell has that folder in LD_LIBRARY_PATH, so rpicam-apps and the student
# camera_ros then load the wrong libpisp and fail ("symbol lookup error", rc2 on a robot).
# Students build camera_ros themselves (mbot_ros2_ws), so satisfy the dependency with a
# placeholder that also keeps the real packages out (P-30).
if ! dpkg-query -W -f '${Status}' mbot-camera-ros-placeholder 2>/dev/null | grep -q 'install ok installed'; then
    log "placeholder package for ros-jazzy-camera-ros (P-30)"
    ph="$MBOT_BUILD_TMP/mbot-camera-ros-placeholder"
    rm -rf "$ph"
    mkdir -p "$ph/DEBIAN"
    cat > "$ph/DEBIAN/control" <<CONTROL
Package: mbot-camera-ros-placeholder
Version: 1.0
Architecture: all
Maintainer: MBot server image <mbot@localhost>
Provides: ros-jazzy-camera-ros
Conflicts: ros-jazzy-camera-ros, ros-jazzy-libcamera
Replaces: ros-jazzy-camera-ros
Description: Stands in for ros-jazzy-camera-ros on the MBot server image
 Students build camera_ros from mbot_ros2_ws against the Raspberry Pi libcamera in
 /usr/local. The ROS package would add a second libcamera and libpisp to the ROS
 library path and break the camera. Installing ros-jazzy-camera-ros removes this.
CONTROL
    dpkg-deb --build "$ph" "$MBOT_BUILD_TMP/mbot-camera-ros-placeholder.deb" >/dev/null
    dpkg -i "$MBOT_BUILD_TMP/mbot-camera-ros-placeholder.deb"
    # Kept so a student can undo an accidental "apt install ros-jazzy-camera-ros".
    install_file "$MBOT_BUILD_TMP/mbot-camera-ros-placeholder.deb" /opt/mbot/share/mbot-camera-ros-placeholder.deb 0644
fi

apt_install "${ros_pkgs[@]}"
for p in ros-jazzy-camera-ros ros-jazzy-libcamera; do
    if dpkg-query -W -f '${Status}' "$p" 2>/dev/null | grep -q 'install ok installed'; then
        die "$p is installed; it breaks the Raspberry Pi camera stack (P-30)"
    fi
done

log "installed packages that match the GUI pattern (after install)"
dpkg-query -W -f '${Package}\n' | grep -E "$GUI_RE" | sort > "$MBOT_REPORTS/installed-gui-packages.txt" || true
log "$(wc -l < "$MBOT_REPORTS/installed-gui-packages.txt") GUI-related packages installed (see installed-gui-packages.txt)"
for p in ros-jazzy-rviz2 ros-jazzy-rqt-gui ros-jazzy-desktop ros-jazzy-image-pipeline ros-jazzy-navigation2 ros-jazzy-nav2-bringup; do
    if dpkg-query -W -f '${Status}' "$p" 2>/dev/null | grep -q 'install ok installed'; then
        log "WARNING: $p installed as a dependency of: $(apt-cache rdepends --installed "$p" | tail -n +3 | tr -d ' ' | tr '\n' ' ')"
    fi
done

log "ROS environment: /etc/mbot/ros.env and /etc/profile.d/90-mbot.sh"
install_file "$SYSTEM_DIR/env/ros.env" /etc/mbot/ros.env 0644
install_file "$SYSTEM_DIR/profile/90-mbot.sh" /etc/profile.d/90-mbot.sh 0644
# Interactive non-login shells (VS Code terminals) read /etc/bash.bashrc, not /etc/profile.
ensure_line /etc/bash.bashrc '[ -r /etc/profile.d/90-mbot.sh ] && . /etc/profile.d/90-mbot.sh  # MBot server image'

log "rosdep init"
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
    rosdep init
fi

log "rosdep check of the student repositories (keys not yet installed)"
export ROS_HOME="$MBOT_BUILD_TMP/rosdep-home"
rosdep update --rosdistro "$ROS_DISTRO" >/dev/null
{
    echo "# rosdep check against the pinned student repositories (upstream submodules)."
    echo "# Skip keys as in the course docs, plus rviz2 and ros2_controllers (review section 5.3)."
    for repo in mbot_ros2_ws mbot_ros_labs mbot_servo_lib; do
        echo "== $repo"
        with_ros rosdep check --rosdistro "$ROS_DISTRO" --from-paths "$UPSTREAM/$repo" --ignore-src \
            --skip-keys "libcamera rviz2 ros2_controllers" 2>&1 || true
        echo "-- same check without the extra skip keys (what the course command installs today):"
        with_ros rosdep check --rosdistro "$ROS_DISTRO" --from-paths "$UPSTREAM/$repo" --ignore-src \
            --skip-keys "libcamera" 2>&1 || true
    done
} > "$MBOT_REPORTS/rosdep-check.txt"
unset ROS_HOME
log "report written: $MBOT_REPORTS/rosdep-check.txt"

log "ROS check: $(with_ros ros2 pkg list | wc -l) packages visible to ros2 pkg list"
log "done"
