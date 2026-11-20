#!/usr/bin/env bash
set -eo pipefail
umask 077

mode="${1:-preflight}"
if [[ $# -gt 0 ]]; then shift; fi
if [[ "$mode" == "help" || "$mode" == "--help" ]]; then
    printf '%s\n' 'Modes: dependencies | preflight | full-agent | agent | asr-diagnostic | asr-probe | tts-probe | mic-probe | motion-diagnostic | motion-probe | dashboard | sim'
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
if [[ "$mode" != "sim" && "$mode" != "dashboard" && "$mode" != "dependencies" ]]; then
    if [[ ! -r "${X2_AIMDK_SETUP:-}" ]]; then
        printf '%s\n' 'Mount the matching AimDK SDK at /home/agi/aimdk (or set X2_AIMDK_SETUP).' >&2
        exit 22
    fi
    source "$X2_AIMDK_SETUP"
fi
# Set paths last: robot environment scripts must not shadow bundled libraries.
export PYTHONPATH="/opt/eldercare/vendor:/opt/eldercare:${PYTHONPATH:-}"
case "$mode" in
    dependencies) exec /usr/bin/python3 -c "import sys,platform,rclpy,websockets,httpx,httpcore,anyio,sniffio,exceptiongroup,typing_extensions,yaml,pypinyin; import x2_agent.agent; assert sys.version_info[:2] == (3,10); print('Python/ROS/application imports OK:',platform.machine())" ;;
    preflight) exec /usr/bin/python3 scripts/robot_preflight.py "$@" ;;
    agent) exec /usr/bin/python3 scripts/run_robot_agent.py "$@" ;;
    full-agent)
        if [[ "${X2_ONLY_VOICE_CONFIRMED:-0}" != 1 ]]; then
            printf '%s\n' 'Confirm only_voice on this session before full-agent.' >&2
            exit 23
        fi
        mkdir -p /var/lib/eldercare/logs
        session_id="$(date +%Y%m%d_%H%M%S)_$$"
        export DOUBAO_ASR_HOTWORDS="${DOUBAO_ASR_HOTWORDS:-[\"灵犀\"]}"
        exec /usr/bin/python3 scripts/run_robot_agent.py \
            --transport aimdk --enable-robot-audio --competition-mode \
            --health-semantic model --llm-model doubao-seed-2-0-mini-260428 \
            --presentation-backend aimdk --enable-robot-presentation --enable-robot-motion \
            --vad-idle-seconds 1.5 --aimdk-streaming-asr \
            --dining-feedback-records /var/lib/eldercare/dining_feedback.jsonl \
            --log-file "/var/lib/eldercare/logs/autonomy_${session_id}.log" \
            --metrics-file "/var/lib/eldercare/logs/autonomy_${session_id}_metrics.json" "$@"
        ;;
    asr-diagnostic) exec /usr/bin/python3 scripts/aimdk_asr_diagnostic.py "$@" ;;
    asr-probe) exec /usr/bin/python3 scripts/aimdk_asr_probe.py "$@" ;;
    tts-probe) exec /usr/bin/python3 scripts/aimdk_tts_probe.py "$@" ;;
    mic-probe) exec /usr/bin/python3 scripts/aimdk_mic_probe.py "$@" ;;
    motion-diagnostic) exec /usr/bin/python3 scripts/aimdk_motion_diagnostic.py "$@" ;;
    motion-probe) exec /usr/bin/python3 scripts/aimdk_motion_probe.py "$@" ;;
    sim) exec /usr/bin/python3 agent.py "$@" ;;
    dashboard) exec /usr/bin/python3 feedback_dashboard.py --records /var/lib/eldercare/dining_feedback.jsonl "$@" ;;
    *) printf '%s\n' "Unknown mode: $mode. Use help." >&2; exit 2 ;;
esac
