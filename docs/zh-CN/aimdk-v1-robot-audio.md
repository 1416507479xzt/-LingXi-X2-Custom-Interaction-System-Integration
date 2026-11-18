# 灵犀 X2 真机音频验收状态

更新于 2026-11-18。以下只适用于手头一台 X2 Ultra，不代表赛方统一提供的机器人已通过验收。完整操作、错误与解决办法见[11月8日联调记录](2026-11-08-x2-real-robot-integration.md)和[11月18日ASR复测](2026-11-18-x2-asr-diagnosis.md)；从新电脑部署见[复现指南](reproduce-on-x2.md)。

| 环节 | 本机结果 | 证据或边界 |
|---|---|---|
| PC2 环境 | 已通过 | Linux aarch64、Python 3.10.12、ROS 2 Humble、AimDK `v1.0.0-ga424add`；加载 `/home/agi/aimdk/install/local_setup.bash` 后接口可用 |
| 内置麦 PCM | 已通过 | `/agent/process_audio_output`、`stream_id=1`；60 秒探针收到 7 段完整非空语音，VAD 为 1/2/3 |
| 云端 ASR | 普通完整句、唤醒词已有成功样本 | 普通句有正常END且准确识别；后续“你好灵犀”没有END，经诊断工具停收提交后准确转写。启用了灵犀热词，但没有同录音对照，尚不能量化其收益 |
| 离线依赖 | 已通过 | 补齐 Python 3.10 的 `exceptiongroup`、`typing-extensions` 后，真机 `robot_preflight.py` 通过 |
| 云端 TTS | 已通过 | PC2 生成约 3 秒 PCM，首包约 0.7–0.9 秒；必须使用豆包语音 Key |
| 扬声器和焦点 | 单句已通过 | 焦点优先级 6；实机完整播出测试句，程序确认释放焦点。优先级 4 被拒 |
| `only_voice` 与 `normal` | 两个方向均通过行为核对 | 11月8日验证切换与恢复；11月18日再次 PC2 设置模式、PC3 重启 agent 后原生问答停止。最后确认状态为 only_voice，今天尚未恢复 normal |
| 完整自研语音对话 | 两轮样本已通过 | 热词+停收1.5秒设置下，“你好林夕”命中同音唤醒，Mini问候；疲惫回答也完整播出，用户确认。仍有约4.5秒首包延迟、修正重试与表达质量问题，尚非全面验收 |
| 表情、动作、赛方机器人 | 未验收 | 今天没有完成相关真机测试；v1.1.0 仅做静态适配 |

当前首要工作是用热词提示与新加入的 --vad-idle-seconds 1.5 运行正式Agent，验证完整语音链路。停收恢复已在诊断工具上识别成功，正式传输接入通过本地测试，仍待实机验收；不能据此宣称所有音频截断问题已解决。随后验证表情动作，并在赛方机器上重新预检。结束联调时按复现指南恢复 normal 并确认原生问答。

真机入口 `scripts/run_robot_agent.py` 复用 `x2_agent/agent.py` 的对话逻辑；`aimdk_audio.py`、`aimdk_transport.py`、`aimdk_playback.py` 负责输入、事件适配和播音。离线包只解压在用户目录，不修改机载 AimDK 或系统 Python。IP 随 Wi-Fi 变化，API Key 不进入 Git 或离线包。
