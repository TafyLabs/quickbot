# QuickBot robot-side image (Pi 5).
# Extends kilted-base with realsense + serial deps + python serial driver libs.
# Build: docker build -f docker/robot.Dockerfile -t quickbot:robot-kilted .

FROM quickbot:kilted-base

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-serial \
        usbutils \
        v4l-utils \
        udev \
    && rm -rf /var/lib/apt/lists/*

# RealSense ROS wrapper: try debs first; fall back to source build in CI.
# Kept conditional so this Dockerfile still builds when debs are unavailable.
RUN apt-get update && (apt-get install -y --no-install-recommends \
        "ros-${ROS_DISTRO}-realsense2-camera" \
        "ros-${ROS_DISTRO}-realsense2-description" \
        || echo "realsense2 debs not available for ${ROS_DISTRO} — build from source in ws/src per docs/runbook.md") \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ws
CMD ["bash"]
