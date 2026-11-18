#!/usr/bin/env bash
set -eo pipefail
umask 077

mode="${1:-preflight}"
if [[ $# -gt 0 ]]; then shift; fi
if [[ "$mode" == "help" || "$mode" == "--help" ]]; then
    printf '%s\n' 'Modes: preflight | agent | asr-diagnostic | asr-probe | tts-probe | mic-probe | dashboard | sim'
    exit 0
fi
cd /opt/eldercare
if [[ ! -f /opt/ros/humble/setup.bash ]]; then
    printf '%s\n' 'Missing ROS 2 Humble in the selected image.' >&2
    exit 20
fi
source /opt/ros/humble/setup.bash
# Optionally mount and source the approved robot DDS/environment script.
if [[ -n "${X2_ENV_SETUP:-}" ]]; then
    if [[ ! -r "$X2_ENV_SETUP" ]]; then
        printf '%s\n' 'Configured X2_ENV_SETUP is not readable.' >&2
        exit 21
    fi
    source "$X2_ENV_SETUP"
fi
if [[ "$mode" != "sim" && "$mode" != "dashboard" ]]; then
    if [[ ! -r "${X2_AIMDK_SETUP:-}" ]]; then
        printf '%s\n' 'Mount the matching AimDK SDK at /home/agi/aimdk (or set X2_AIMDK_SETUP).' >&2
        exit 22
    fi
    source "$X2_AIMDK_SETUP"
fi
# Set paths last: robot environment scripts must not shadow bundled libraries.
export PYTHONPATH="/opt/eldercare/vendor:/opt/eldercare:${PYTHONPATH:-}"
case "$mode" in
    preflight) exec /usr/bin/python3 scripts/robot_preflight.py "$@" ;;
    agent) exec /usr/bin/python3 scripts/run_robot_agent.py "$@" ;;
    asr-diagnostic) exec /usr/bin/python3 scripts/aimdk_asr_diagnostic.py "$@" ;;
    asr-probe) exec /usr/bin/python3 scripts/aimdk_asr_probe.py "$@" ;;
    tts-probe) exec /usr/bin/python3 scripts/aimdk_tts_probe.py "$@" ;;
    mic-probe) exec /usr/bin/python3 scripts/aimdk_mic_probe.py "$@" ;;
    sim) exec /usr/bin/python3 agent.py "$@" ;;
    dashboard) exec /usr/bin/python3 feedback_dashboard.py --records /var/lib/eldercare/dining_feedback.jsonl "$@" ;;
    *) printf '%s\n' "Unknown mode: $mode. Use help." >&2; exit 2 ;;
esac
