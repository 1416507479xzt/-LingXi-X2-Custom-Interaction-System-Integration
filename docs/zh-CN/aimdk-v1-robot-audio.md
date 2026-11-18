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
| 完整自研语音对话 | 当前 ZIP 版本已获用户实机确认 | Mini 完成唤醒、问候及健康/生活协助问答；后续优化后用户确认效果良好。早期约4.5秒首包属于历史样本，不是当前版本指标；尚无本轮完整计时日志 |
| 食堂意见与网页 | 已获用户实机确认 | 明确确认后保存至 data/dining_feedback.jsonl，电脑经 SSH 隧道查看，用户确认反馈表实时更新 |
| 表情、动作、赛方机器人 | 未验收 | 今天没有完成相关真机测试；v1.1.0 仅做静态适配 |

第三版 v0.3.0 以完整语音交互和食堂反馈闭环为基线；164项相关离线回归通过，播放节奏与反馈路径修正后，用户确认效果良好且网页实时更新。详细证据见[最新闭环记录](2026-11-18-playback-and-feedback-path.md)。长期运行、不同网络/噪声条件、表情动作及赛方机器人仍待验证。当前保持纯语音，不开发到点主动提醒；需要原生交互时按复现指南恢复 normal 并确认实际回答。

真机入口 `scripts/run_robot_agent.py` 复用 `x2_agent/agent.py` 的对话逻辑；`aimdk_audio.py`、`aimdk_transport.py`、`aimdk_playback.py` 负责输入、事件适配和播音。离线包只解压在用户目录，不修改机载 AimDK 或系统 Python。IP 随 Wi-Fi 变化，API Key 不进入 Git 或离线包。
