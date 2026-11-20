# Candidate ROS image: validate against the target X2 before operating it.
# For official Podman environments, BASE_IMAGE may be an approved local image
# that provides Ubuntu 22.04, CPython 3.10 and ROS 2 Humble.
ARG BASE_IMAGE=ros:humble-ros-base-jammy
FROM ${BASE_IMAGE}
ARG APP_VERSION=development
ARG VCS_REF=unknown

USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3-pip python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/eldercare
COPY requirements-lock.txt ./
# Keep third-party modules separate from the ROS system Python packages.
RUN python3 -m pip install --no-cache-dir --only-binary=:all: \
      --target /opt/eldercare/vendor -r requirements-lock.txt
COPY x2_agent/ ./x2_agent/
COPY data/life_assistance.json data/medicine-education.json data/medicine-template.json ./data/
COPY scripts/ ./scripts/
COPY agent.py feedback_dashboard.py skills.yaml LICENSE README.md VERSION ./
COPY docker/entrypoint.sh /usr/local/bin/eldercare-entrypoint
COPY docker/ ./docker/
RUN python3 scripts/container_manifest.py --write /opt/eldercare/source-manifest.json
RUN sed -i 's/\r$//' /usr/local/bin/eldercare-entrypoint \
    && chmod 755 /usr/local/bin/eldercare-entrypoint \
    && mkdir -p /var/lib/eldercare/logs /tmp/eldercare-home \
    && chown -R 1000:1000 /var/lib/eldercare /tmp/eldercare-home

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HOME=/tmp/eldercare-home ROS_HOME=/tmp/eldercare-home/.ros \
    PYTHONPATH=/opt/eldercare/vendor \
    X2_AIMDK_SETUP=/home/agi/aimdk/install/local_setup.bash
LABEL org.opencontainers.image.title="Lingxi X2 eldercare voice agent" \
      org.opencontainers.image.source="https://github.com/1416507479xzt/-X2-" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}"
USER 1000:1000
# Default to a read-only compatibility check, never unsolicited playback.
ENTRYPOINT ["/usr/local/bin/eldercare-entrypoint"]
CMD ["preflight"]
