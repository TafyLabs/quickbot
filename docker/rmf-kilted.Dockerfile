# Open-RMF workstation image (Kilted).
# Build: docker build -f docker/rmf-kilted.Dockerfile -t quickbot:rmf-kilted .

FROM quickbot:kilted-base

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && (apt-get install -y --no-install-recommends \
        "ros-${ROS_DISTRO}-rmf-dev" \
        || echo "rmf-dev not yet packaged for ${ROS_DISTRO} — use Docker demos per docs/runbook.md") \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ws
CMD ["bash"]
