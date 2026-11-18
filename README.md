# 灵犀 X2 自研语音交互 Agent

本项目将长者陪护对话接入灵犀 X2 真机：AimDK 提供麦克风、扬声器、表情和预设动作接口；豆包语音服务完成 ASR/TTS；火山方舟上的 Doubao-Seed 模型负责语义理解、回答和受约束的表现选择。迎宾健康问询、生活协助与社区食堂意见共用一套会话逻辑。Unity 仿真用于回归对照，真机通过独立传输适配层运行同一套业务代码。

## 从另一台电脑开始

完整的克隆、离线包构建、SSH 复制、真机预检、逐层联调和原生交互恢复步骤见 **[从新电脑复现 X2 自研语音 Agent](docs/zh-CN/reproduce-on-x2.md)**。核心命令在 Windows PowerShell 的仓库根目录执行：

```powershell
git clone https://github.com/1416507479xzt/-X2-.git
Set-Location .\-X2-
python scripts/build_robot_bundle.py --download-wheels
python -m zipfile -t .\dist\eldercare_x2_aarch64_py310.zip
```

构建需要开发电脑联网下载锁定版本的 Linux aarch64 / CPython 3.10 Python 依赖。生成的 ZIP 位于 `dist/`，不会提交到 Git。真机运行云端 ASR、LLM、TTS 仍需要联网；API Key 在机器人运行时单独提供，不在源码仓库或部署包中。

机器人 Wi-Fi IP 会随网络变化。部署时从机器人信息页面确认当前 IP，并在 PowerShell 中输入；源码和启动配置不预设历史 IP。

## 当前验证状态

最新现场进展见[2026-11-18 ASR 完整性排查](docs/zh-CN/2026-11-18-x2-asr-diagnosis.md)：普通完整句及“你好灵犀”已有准确转写样本；后者缺少VAD END，经诊断工具停收提交后识别成功。正式Agent新增可选 --vad-idle-seconds 1.5 设置，与热词提示一起完成了下述两轮真机语音实测。当前最后确认模式为 only_voice。

后续正式Agent复测已完成唤醒问候和疲惫回答，用户确认两句都由机器人完整播出，证明真机语音链路可用；仍需优化约4.5秒首包延迟和回答重复。表情动作及多环节连续演示尚未验收。详见上述联调记录末节。

后续[回答与延迟优化](docs/zh-CN/2026-11-18-dialogue-latency-optimization.md)已通过34项本地回归；真实Mini两轮文本测试均只请求一次模型，生成约1.25秒和1.66秒。新增改动尚待真机验证，文本生成时间不等于端到端首音时间。

后续真机疲惫首轮已降到约2.95秒首包且没有重试，但建议被问句改写误删，已补充修复。新增可选 --aimdk-streaming-asr 将ASR连接及上传提前到收音期间；与建议保留等相关56项本地测试通过，新增实时路径尚待真机对照。完整进度以回答与延迟优化记录末节为准。

实时路径首轮真机日志已确认BEGIN起上传，两轮TTS首包约2.20秒、2.48秒，均没有模型重试，建议内容保留。该计时不包含缺END时的停收等待和实际扬声器首声；唤醒仍有误识别，收尾仍可精简，尚未达到稳定低于2秒的完整交互验收。

手头一台 AimDK v1.0.0 的 X2 已实测麦克风 VAD PCM、普通短句 ASR、云端 TTS 和优先级 6 的机器人扬声器完整播报及焦点释放；更新后的离线依赖预检也已通过。完整 Agent 已通过唤醒问候和疲惫回答的两轮真机语音实测；长期稳定性、表情动作及赛方统一机器人的运行仍待验收。v1.1.0 音频参数依据官方文档做了静态适配，尚未实机验证。详见[当前验收状态](docs/zh-CN/aimdk-v1-robot-audio.md)及[2026-11-08 真机联调记录](docs/zh-CN/2026-11-08-x2-real-robot-integration.md)。

项目的目标是**业务对话代码不因仿真或真机而改动**；设备接口、固件、网络和运行环境仍需用实际机器人验证。未知 AimDK 版本或不兼容字段会在预检中停止，避免直接运行未核对的接口。

## 代码位置

| 路径 | 作用 |
|---|---|
| `x2_agent/agent.py`、`x2_agent/model_dialogue.py` | 会话调度、模型对话、上下文记忆与表现选择 |
| `x2_agent/asr.py`、`x2_agent/tts.py` | 豆包语音识别和合成 |
| `x2_agent/aimdk_audio.py`、`x2_agent/aimdk_transport.py`、`x2_agent/aimdk_playback.py` | 真机 ROS 音频输入、事件适配和播放 |
| `x2_agent/presentation.py` | 表情与预设动作的受限映射 |
| `data/`、`x2_agent/life_assistance.py`、`x2_agent/dining_feedback.py` | 用药资料、健康提醒和食堂意见处理 |
| `scripts/robot_preflight.py`、`scripts/aimdk_*_probe.py` | 只读兼容性与语音探针 |
| `scripts/build_robot_bundle.py`、`scripts/run_robot_agent.py` | 离线打包与真机启动入口 |
| `tests/` | 无机器人时的回归测试 |

## 仿真回归

Windows 便携模拟器运行时，在仓库根目录安装 `requirements.txt`，在本地 `.env` 配置两把 API Key，再执行 `python agent.py --competition-mode --health-semantic model`。这一入口默认走 Unity WebSocket；真机入口与步骤见上方复现指南。仿真细节见[中文指南](docs/zh-CN/README.md)。

四款 Doubao-Seed 对话模型的同题测试、赛事分档暂估、逐轮原始结果与复现脚本见[2026-11-08 模型对比记录](docs/zh-CN/model-evaluation/2026-11-08/赛事评分对比.md)。当前默认模型仍为 `doubao-seed-2-0-mini-260428`。

## 数据与来源

`.gitignore` 排除了 `.env`、录音、历史反馈、缓存与生成的 ZIP。药品资料和提醒内容为项目配置，不能代替个人处方或真实预约记录。开源基础与改动说明见[开源引用说明](开源引用说明.md)及仓库提交历史。
