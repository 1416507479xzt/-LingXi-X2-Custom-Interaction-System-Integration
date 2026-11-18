# 灵犀 X2 自研语音交互 Agent

本项目将长者陪护对话接入灵犀 X2 真机：AimDK 提供麦克风、扬声器、表情和预设动作接口；豆包语音服务完成 ASR/TTS；火山方舟上的 Doubao-Seed 模型负责语义理解、回答和受约束的表现选择。迎宾健康问询、生活协助与社区食堂意见共用一套会话逻辑。Unity 仿真用于回归对照，真机通过独立传输适配层运行同一套业务代码。

当前版本：**[v0.3.0（第三版）](docs/zh-CN/releases/v0.3.0.md)**。源码版本见 VERSION；与第二版的变化见[版本对比](https://github.com/1416507479xzt/-X2-/compare/v0.2.0...v0.3.0)。

## 从另一台电脑开始

版本节点、比较和旧版复测见[版本管理说明](docs/zh-CN/version-management.md)及[CHANGELOG](CHANGELOG.md)。ARM64 Docker候选镜像已通过云端构建、依赖检查及56项离线测试；下载和验证范围见[首次容器构建记录](docs/zh-CN/2026-11-18-container-build.md)及[容器复现说明](docs/zh-CN/docker-reproduction.md)。尚未完成容器真机验收，当前真机ZIP方案继续保留。

完整的克隆、离线包构建、SSH 复制、真机预检、逐层联调和原生交互恢复步骤见 **[从新电脑复现 X2 自研语音 Agent](docs/zh-CN/reproduce-on-x2.md)**。核心命令在 Windows PowerShell 的仓库根目录执行：

```powershell
git clone https://github.com/1416507479xzt/-X2-.git
Set-Location .\-X2-
git checkout --detach v0.3.0
python scripts/build_robot_bundle.py --download-wheels
python -m zipfile -t .\dist\eldercare_x2_aarch64_py310.zip
```

构建需要开发电脑联网下载锁定版本的 Linux aarch64 / CPython 3.10 Python 依赖。生成的 ZIP 位于 `dist/`，不会提交到 Git。真机运行云端 ASR、LLM、TTS 仍需要联网；API Key 在机器人运行时单独提供，不在源码仓库或部署包中。

机器人 Wi-Fi IP 会随网络变化。部署时从机器人信息页面确认当前 IP，并在 PowerShell 中输入；源码和启动配置不预设历史 IP。

## 当前验证状态

截至2026-11-18，项目已从早期音频探针推进到完整自研 Agent 的真机语音交互与食堂反馈闭环。当前使用 `doubao-seed-2-0-mini-260428`，在手头一台 AimDK v1.0.0（`ga424add`）的 X2 上，以 `only_voice` 模式运行；表情和动作保持关闭。

| 内容 | 当前证据与状态 |
|---|---|
| 真机语音链路 | 麦克风 VAD PCM → 豆包 ASR → Mini 对话 → 豆包 TTS → 机器人扬声器已跑通；优先级6的音频焦点申请、完整播报和释放已实测。 |
| 唤醒与对话 | 已完成首次招呼后询问状态、后续问答及健康/生活协助的真机测试；用户确认回答完整，后续反馈本轮效果非常不错。首次招呼流程和上下文逻辑已有回归覆盖。 |
| 延迟与播音优化 | 已接入收音期间上传 ASR、LLM 连接保温及有界 PCM 提前发送；用户在最新版部署后确认体验良好。历史首包耗时留在联调记录中，不作为当前版本指标；本轮没有新的完整耗时日志，尚不能宣称稳定低于2秒。 |
| 食堂反馈闭环 | 语音描述 → 整理反馈 → 用户明确确认 → JSONL 保存 → 电脑网页查看已获用户真机确认，反馈表可实时更新。常用 Agent 命令和网页入口统一读取 `data/dining_feedback.jsonl`，保存路径参数遗漏问题已修复。 |
| 本地回归 | 最近一次相关离线回归共164项通过，覆盖播放时序、焦点释放、确认条件及 CLI 配置到反馈保存路径等；离线测试与用户真机反馈分别记录。 |
| 部署与复现 | 当前真机使用独立 ZIP 离线依赖包，依赖和 ROS 字段预检已通过；Windows 网页入口使用当前动态 IP 建立 SSH 隧道。API Key 与实际反馈数据不随仓库或部署包分发。 |

最新修正、测试范围和用户真机复测结果见[播音与食堂反馈闭环记录](docs/zh-CN/2026-11-18-playback-and-feedback-path.md)、[版本记录](CHANGELOG.md)。本轮基线实现提交为 `bbaf7a1`，用户验收记录提交为 `5a9bc0b`。后续同学应结合[复现指南](docs/zh-CN/reproduce-on-x2.md)和[食堂反馈步骤](docs/zh-CN/stage4-dining-feedback.md)复测。

**尚未验证的范围：**长时间运行及不同噪声/网络条件下的稳定性、表情与动作联动、比赛方统一机器人的版本兼容性、Docker 容器在真机上的运行。AimDK v1.1.0 音频参数只有静态适配，尚无实机验证。到点主动提醒已按开发范围排除，不列入待开发功能。

项目的目标是**业务对话代码不因仿真或真机而改动**；设备接口、固件、网络和运行环境仍需用实际机器人验证。未知 AimDK 版本或不兼容字段会在预检中停止。

早期排查过程保留在[ASR 完整性记录](docs/zh-CN/2026-11-18-x2-asr-diagnosis.md)、[回答与延迟优化记录](docs/zh-CN/2026-11-18-dialogue-latency-optimization.md)及[2026-11-08 联调记录](docs/zh-CN/2026-11-08-x2-real-robot-integration.md)，用于追溯问题与比较版本，不代表当前只完成了两轮问答。

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

当前纯语音优化与十轮连续对话测试见[真机对话验收步骤](docs/zh-CN/voice-dialogue-acceptance.md)，包含日志和耗时记录方式；表情动作继续关闭。

环节四真机语音确认、独立反馈记录及电脑SSH隧道查看网页，见[社区食堂意见收集测试步骤](docs/zh-CN/stage4-dining-feedback.md)。

Windows查看机器人食堂反馈表可双击仓库根目录`open_dining_dashboard.cmd`，输入当前IP并在新SSH窗口输入密码；连通后自动打开网页，保留该SSH窗口。
