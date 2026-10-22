#!/bin/bash
# Step 40: camera stack (HW-005, risk R-H1, R-H2).
# Raspberry Pi libcamera and rpicam-apps built from pinned tags into /usr/local.
# rpicam-apps is built without Qt, EGL and DRM preview (no desktop; use rpicam-hello -n).
# Ubuntu's libcamera packages are blocked by the apt pin installed in step 00.
# With the ROS environment loaded, the camera stack and a test build of the student
# camera_ros must load only the Raspberry Pi libcamera and libpisp in /usr/local (P-30).
# Safe to run more than once.
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
require_image_chroot

mapfile -t pkgs < <(manifest_packages "$MANIFESTS/apt-packages.txt" 40)
apt_install "${pkgs[@]}"

jobs="$(nproc)"

# ---------------------------------------------------------------- libcamera
if stamp_matches libcamera "$LIBCAMERA_COMMIT" && [[ -f /usr/local/lib/aarch64-linux-gnu/pkgconfig/libcamera.pc ]]; then
    log "libcamera already built ($LIBCAMERA_TAG)"
else
    src="$MBOT_BUILD_TMP/libcamera"
    git_pinned "$LIBCAMERA_REPO" "$LIBCAMERA_TAG" "$LIBCAMERA_COMMIT" "$src"
    # Options from upstream install_camera.sh (mbot_sys_utils).
    (cd "$src" && meson setup build --buildtype=release --prefix=/usr/local \
        -Dpipelines=rpi/vc4,rpi/pisp -Dipas=rpi/vc4,rpi/pisp -Dv4l2=true \
        -Dgstreamer=enabled -Dtest=false -Dlc-compliance=disabled -Dcam=disabled \
        -Dqcam=disabled -Ddocumentation=disabled -Dpycamera=enabled)
    ninja -C "$src/build" -j "$jobs"
    ninja -C "$src/build" install
    # Record what the meson subprojects (libpisp) resolved to.
    { cat "$src"/subprojects/*.wrap 2>/dev/null; git -C "$src/subprojects/libpisp" rev-parse HEAD 2>/dev/null; } \
        > "$MBOT_REPORTS/libcamera-subprojects.txt" || true
    ldconfig
    rm -rf "$src"
    stamp_write libcamera "$LIBCAMERA_COMMIT"
fi

# ---------------------------------------------------------------- rpicam-apps
if stamp_matches rpicam-apps "$RPICAM_APPS_COMMIT" && [[ -x /usr/local/bin/rpicam-hello ]]; then
    log "rpicam-apps already built ($RPICAM_APPS_TAG)"
else
    src="$MBOT_BUILD_TMP/rpicam-apps"
    git_pinned "$RPICAM_APPS_REPO" "$RPICAM_APPS_TAG" "$RPICAM_APPS_COMMIT" "$src"
    # libav on, as in upstream install_camera.sh (H.264 recording with rpicam-vid on the Pi 5).
    # rc1 had it off because v1.11.0 needs a newer libavcodec than Ubuntu 24.04 has (P-29).
    (cd "$src" && meson setup build --buildtype=release --prefix=/usr/local \
        -Denable_libav=enabled -Denable_drm=disabled -Denable_egl=disabled \
        -Denable_qt=disabled -Denable_opencv=disabled -Denable_tflite=disabled \
        -Denable_hailo=disabled)
    meson compile -C "$src/build" -j "$jobs"
    meson install -C "$src/build"
    ldconfig
    rm -rf "$src"
    stamp_write rpicam-apps "$RPICAM_APPS_COMMIT"
fi

log "camera check: $(/usr/local/bin/rpicam-hello --version 2>&1 | head -2 | tr '\n' ' ')"
log "libcamera pkg-config version: $(pkg-config --modversion libcamera)"
if dpkg-query -W -f '${Package} ${Status}\n' 'libcamera*' 2>/dev/null | grep -q 'install ok installed'; then
    die "an Ubuntu libcamera package is installed; the apt pin did not work"
fi

# ---------------------------------------------------------------- ROS environment check (P-30)
# rc2 failed on a robot because the ROS library path held a second libpisp. Check what the
# camera stack loads with the ROS environment, the way every student shell has it.
log "libraries of the camera stack with the ROS environment loaded"
ros_ldd="$(with_ros ldd /usr/local/bin/rpicam-hello \
    /usr/local/lib/aarch64-linux-gnu/libcamera/ipa/ipa_rpi_pisp.so | grep -E 'libcamera|libpisp' | sort -u)"
{
    echo "# ldd of rpicam-hello and the Pi 5 IPA module with /opt/ros/jazzy/setup.bash sourced"
    echo "$ros_ldd"
} > "$MBOT_REPORTS/camera-ros-env-check.txt"
if grep -q '/opt/ros' <<< "$ros_ldd"; then
    die "camera stack loads libraries from /opt/ros in a ROS shell: $ros_ldd"
fi
log "libcamera pkg-config version with the ROS environment: $(with_ros pkg-config --modversion libcamera)"

log "test build of the student camera_ros (upstream/mbot_ros2_ws), not kept"
ws="$MBOT_BUILD_TMP/camera_ros_ws"
rm -rf "$ws"
mkdir -p "$ws/src"
cp -a "$UPSTREAM/mbot_ros2_ws/camera_ros" "$ws/src/"
(cd "$ws" && with_ros colcon build --event-handlers console_cohesion- \
    --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF)
component="$(find "$ws/install" -name 'libcamera_component.so' | head -1)"
[[ -n "$component" ]] || die "camera_ros test build produced no libcamera_component.so"
linked="$(with_ros ldd "$component" | grep -E 'lib(camera|camera-base|pisp)\.so' || true)"
{
    echo "# camera_ros from upstream/mbot_ros2_ws built as a student would (colcon, ROS environment)."
    echo "# Libraries it links (must be the Raspberry Pi libcamera in /usr/local):"
    echo "$linked"
} > "$MBOT_REPORTS/camera-ros-test-build.txt"
grep -q '/usr/local/lib/.*/libcamera\.so\.0\.5' <<< "$linked" \
    || die "camera_ros test build did not link /usr/local libcamera 0.5: $linked"
! grep -q '/opt/ros' <<< "$linked" || die "camera_ros test build loads libraries from /opt/ros: $linked"
rm -rf "$ws"
log "camera_ros test build links the Raspberry Pi libcamera"

log "done"
