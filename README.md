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

## 后续开发：表情与动作

2026-11-19 开始在第三版语音基线上核对机载表情/动作接口。当前零力矩，仅准备表情单项测试；动作目录存在版本差异，尚未启用或验收。详见[本轮接入记录](docs/zh-CN/2026-11-19-presentation-integration.md)。

## 原生交互模块：切换、重启与恢复

以下是手头 X2 Ultra / AimDK v1.0.0 已验证过的操作流程。**PC2 负责调用模式设置服务，PC3 负责重启原生 agent。** 两台机器的提示符都可能是 `agi@agi`，不能只靠提示符区分：登录横幅中 PC2 为 SoC1，PC3 为 SoC2。这里重启的是原生交互应用，不是重启整台机器人，也不删除原生代码。

| 模式/操作 | 用途 |
|---|---|
| `only_voice` + 重启原生 agent | 切换到自研语音接入模式；实际核对原生大模型不再回答，再启动本项目 Agent。原生应用需要重新启动，不能一直停着。 |
| `normal` + 重启原生 agent | 恢复机器人的原生语音问答；先停止本项目 Agent，避免两套系统同时使用音频。 |
| `stop-app` / `start-app` | 分别停止、启动 PC3 上的原生 agent，让修改后的模式生效。两种模式都使用这一对命令，具体模式由此前设置的属性决定。 |

### 1. 从电脑连接 PC2

**在电脑 Windows PowerShell 执行**。先从机器人信息页查看当次 Wi-Fi IP，不沿用旧地址；输入密码时不显示字符是正常现象。

```powershell
$RobotIp = (Read-Host '输入机器人当前 Wi-Fi IP').Trim()
if ([string]::IsNullOrWhiteSpace($RobotIp)) { throw '机器人 IP 不能为空' }
ssh -o ServerAliveInterval=15 -o ServerAliveCountMax=3 "agi@${RobotIp}"
```

看到机器人 Ubuntu 登录信息后才执行后面的 Linux 命令。若已经在 PC2 SSH 窗口，跳过这一步。`client_loop ... Connection reset` 表示 SSH 已断开，回到 `PS C:\...>` 后应重新连接，不能继续输入 `source` 或 Linux 路径。

### 2. 选择一种模式，在 PC2 设置

先在正在运行自研 Agent 的窗口按 `Ctrl+C`，等程序退出；诊断脚本也先停止。**下面 A、B 二选一，不要依次都运行。**

**A. 接入自研大模型：暂停原生大模型回答。** 在 PC2 SSH 窗口执行：

```bash
source /home/agi/aimdk/install/local_setup.bash
ros2 service call /aimdk_5Fmsgs/srv/SetAgentPropertiesRequest aimdk_msgs/srv/SetAgentPropertiesRequest "{contents: {properties: [{key: {value: 2}, value: 'only_voice'}]}}"
```

**B. 恢复原生交互：让机器人重新用原生大模型回答。** 在 PC2 SSH 窗口执行：

```bash
source /home/agi/aimdk/install/local_setup.bash
ros2 service call /aimdk_5Fmsgs/srv/SetAgentPropertiesRequest aimdk_msgs/srv/SetAgentPropertiesRequest "{contents: {properties: [{key: {value: 2}, value: 'normal'}]}}"
```

等出现 `response` 后再继续。手头机器曾返回 `code=0`、`status.value=0 (UNKNOWN)`；这不能单独证明模式已生效，还必须执行下一节重启并按实际问答行为确认。若一直没有响应或报错，先记录输出并排查，不要当作设置成功。

### 3. 登录 PC3，逐行重启原生 agent

仍在 **PC2 SSH 窗口**执行：

```bash
ssh agi@10.0.1.42
```

`10.0.1.42` 是手头机器人曾多次实测的 **PC3 机内网络地址**，不是会变化的 Wi-Fi 地址，也不是所有机器通用的地址；其他机器人需核对其内部拓扑。自行输入 SSH 密码，看到 SoC2 登录横幅后，再在 **PC3** 逐行执行：

```bash
aima em stop-app agent
```

等显示停止成功，再执行：

```bash
aima em start-app agent
```

等显示启动成功，再执行：

```bash
exit
```

`exit` 退出本次 PC3 登录，返回原来的 PC2 SSH 会话。**若停止或启动任何一步失败，停在该步骤核对错误，不要继续启动自研 Agent。** 不要用 `stop-all`，也不要省略 `start-app agent`。

### 4. 用真实语音确认结果

等待模块启动后，先不运行本项目 Agent，说原生唤醒词，再问“现在几点”：

- 选择 `only_voice` 时：核对原生大模型不再回答；再按[真机启动步骤](docs/zh-CN/reproduce-on-x2.md)启动自研 Agent。`X2_ONLY_VOICE_CONFIRMED=1` 只是操作者的确认标志，不会替你切换模式。
- 选择 `normal` 时：应重新听到原生语音回答。确认恢复后即可保留原生系统运行；本项目自研 Agent 保持停止。

停止自研程序或退出 SSH 都不会自动恢复 `normal`。也不能把“没有回答”单独当作模式设置成功的充分证据：若模块未启动、网络或收音异常，同样可能没有回答，应结合启动结果和已验证的收音链路核对。

### 常见错误

| 现象 | 处理 |
|---|---|
| `The passed service type is invalid` | 在 PC2 当前 SSH 会话重新执行 `source /home/agi/aimdk/install/local_setup.bash`，再核对服务类型。 |
| `agent 不存在`，应用列表没有 agent | 检查是否误在 PC2 执行了 aima 命令；手头机器的原生 agent 位于 PC3。 |
| PowerShell 提示 source、python3 或 Linux 路径不存在 | 当前仍在 Windows，先 SSH 登录机器人。 |
| 已设置 normal，但仍不回答 | 确认自研 Agent 已停止、PC3 启动成功；保留输出核查，不把重启命令成功等同于语音恢复成功。 |

模式切换与恢复的历史实测证据见[11月8日联调记录](docs/zh-CN/2026-11-08-x2-real-robot-integration.md)和[复现指南](docs/zh-CN/reproduce-on-x2.md)。

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
