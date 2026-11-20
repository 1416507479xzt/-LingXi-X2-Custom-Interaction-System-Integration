# PC2自研项目文件清单 — 2026-11-20

依据用户在PC2执行ls、find及du后的输出整理，仅列本次核查到的自研目录。没有读取密钥值、日志正文或实际反馈正文，没有删除、移动、安装或修改机器人文件。此清单不是全盘取证，也不是原生代码未变化的校验报告。

## 目录及占用

| 位置 | 实际结果 | 归属/用途 |
|---|---|---|
| /home/agi/eldercare-probe | 36K | 早期只读麦克风探针及两个Python缓存 |
| /home/agi/eldercare-x2 | 17M | 正式应用及部署文件的父目录；以下子目录大小已计入总数 |
| /home/agi/eldercare-x2/eldercare_x2/x2_agent | 768K | 自研应用模块及可能的运行缓存；顶层33个Python源码文件 |
| /home/agi/eldercare-x2/eldercare_x2/scripts | 68K | 10个启动、预检、诊断及网页辅助脚本 |
| /home/agi/eldercare-x2/eldercare_x2/vendor | 12M | 项目专用Python第三方依赖，不是系统Python目录 |
| /home/agi/eldercare-x2/eldercare_x2/data | 24K | 三份公开配置/资料及一份食堂反馈JSONL |
| /home/agi/eldercare-x2/eldercare_x2/logs | 1.4M | 22份.log与22份_metrics.json，共44份普通文件 |
| /home/agi/eldercare-x2/eldercare_x2/docs | 360K | 随包说明文档 |
| /home/agi/logs | 4.0K | 曾在主目录执行mkdir -p logs；本次find未列出顶层普通文件 |
| /home/agi/eldercare-container | 不存在 | 未在此位置部署容器交付目录；镜像交付保存在Windows开发电脑 |

du的结果是磁盘占用，包含目录/缓存分配，并非运行内存；父子目录不能相加重复计算。原始输出有取整，不据此计算精确字节数。

## 早期探针

```text
eldercare-probe/
  scripts/aimdk_mic_probe.py
  x2_agent/aimdk_audio.py
  x2_agent/__init__.py
  x2_agent/__pycache__/aimdk_audio.cpython-310.pyc
  x2_agent/__pycache__/__init__.cpython-310.pyc
```

这是最初测试用的独立副本，正式运行入口在eldercare-x2内，不依赖这个旧目录。

## 正式源码和脚本

x2_agent顶层33个源码文件：

```text
__init__.py  __main__.py  agent.py  agent_config.py
aimdk_audio.py  aimdk_playback.py  aimdk_runtime.py
aimdk_streaming.py  aimdk_transport.py  asr.py  audio.py
care_reference.py  competition_flow.py  config.py  demo.py
dialogue_quality.py  dining_feedback.py  error_codes.py  gateway.py
health_memory.py  health_reminders.py  health_semantics.py
life_assistance.py  llm.py  logging_config.py  medicine_consultation.py
metrics.py  model_dialogue.py  presentation.py  sentence_tts.py
skill_loader.py  speech_protocol.py  tts.py
```

scripts顶层10个文件：

```text
run_robot_agent.py
robot_preflight.py
aimdk_mic_probe.py
aimdk_asr_probe.py
aimdk_asr_diagnostic.py
aimdk_tts_probe.py
aimdk_motion_diagnostic.py
aimdk_motion_probe.py
check_presentation_autonomy_live.py
open_dining_dashboard.ps1
```

它们分别负责主程序启动、环境预检、收音/识别/合成诊断、只读动作接口诊断、显式动作探针、云端文本规划对照和Windows网页入口。

## 配置、数据和根目录文件

- `.env`：实际私有Key配置，本机120字节、权限-rw-------。仅核对文件名、权限、大小，未查看值；不入Git。
- `.env.example`：公开模板，不包含实际Key。
- data的公开文件：`life_assistance.json`、`medicine-education.json`、`medicine-template.json`。
- 实际反馈：`data/dining_feedback.jsonl`，不入Git。本次没有查询其内容或记录数。
- 根目录另有：`agent.py`、`feedback_dashboard.py`、`skills.yaml`、`requirements-lock.txt`、`bundle_manifest.json`、`VERSION`、`README.md`、`CHANGELOG.md`、`LICENSE`、`open_dining_dashboard.cmd`。
- 运行生成的Python `__pycache__`可能存在，属于缓存，不是原生运控代码。

部署记录还表明曾上传 `/home/agi/eldercare-x2/eldercare_x2_aarch64_py310.zip`。本次只列了父目录属性和项目内部文件，未单独列父目录普通文件，因此不以历史记录断言该ZIP当前一定仍在。

## 与原生环境的边界

`/home/agi/aimdk`是原生SDK，不属于上述自研目录；`/agibot/software`等机器人系统路径不属于本项目交付。此前source环境、读取官方例程和ROS服务调用，不等于往SDK目录写入了自研源码。模式切换、原生agent重启和文件修改也是不同事项，不能混为一谈。

共享的ROS运行日志目录、SSH known_hosts或shell历史可能记录联调操作，与原生程序共用，不能整体认定为本项目独有文件。本次未检查这些共享目录，也未做全盘基线比对，不宣称除上述位置外绝无任何运行痕迹。用户本轮只要求盘点，不包含清理授权。
