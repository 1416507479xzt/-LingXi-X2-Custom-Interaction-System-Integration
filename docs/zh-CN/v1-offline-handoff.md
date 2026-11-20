# 新电脑＋新X2 v1.0.0：离线包复现

当前v1.0.0采用已在手头真机跑通的ZIP方案，不需要Docker、Podman或升级机器人。包内包含应用Python源码和锁定的第三方依赖；调用目标机器人已有的AimDK/ROS。新机器人仍须逐项验收，不能仅凭同为v1.0.0保证全部接口和现场条件一致。

## 1. 交付前提

- 目标为兼容的X2 Ultra，PC2允许SSH、文件传输及运行二开程序；Linux aarch64、Python3.10，已有匹配的AimDK v1.0.0、ROS2及消息包。
- 允许切换/恢复原生交互；原生agent在PC3，固定机内地址为 `10.0.1.42`，从PC2连接。PC2的Wi-Fi IP随网络变化，需要每次确认。
- 机器人运行时能够访问豆包语音与方舟；自备已开通服务和Mini权限的两把Key。离线指免去下载Python依赖，语音及模型调用仍需联网。
- 新电脑可用Windows PowerShell及OpenSSH的ssh/scp；只复制现成交付包时不用安装Docker或Python。需要修改、重建源码时再安装Git/Python。

## 2. 取得一套固定交付包

开发电脑在当前仓库执行 `python scripts/build_v1_handoff.py`，生成 `dist/x2_v1_handoff/`。首次构建缺wheel时加 `--download-wheels`，只在电脑下载。将整个文件夹复制到新电脑，保留结构：

```text
x2_v1_handoff/
  eldercare_x2_aarch64_py310.zip
  open_dining_dashboard.cmd
  scripts/open_dining_dashboard.ps1
  scripts/robot_project.py
  .env.example
  START-HERE.md
  source-commit.txt
  SHA256SUMS
```

source-commit记录Git提交及是否有未提交的跟踪文件；正式交接应为source_dirty=False。ZIP里另有逐文件摘要和依赖清单。不同电脑交付相同文件，并用Get-FileHash或sha256sum核对SHA256SUMS，不在交接中重新下载未锁定的依赖。

## 3. 新电脑上传到新机器人

PowerShell先进入新电脑实际的 `x2_v1_handoff`目录，再逐行执行：

```powershell
$RobotIp = (Read-Host '输入新机器人当前 Wi-Fi IP').Trim()
if ([string]::IsNullOrWhiteSpace($RobotIp)) { throw '机器人 IP 不能为空' }
ssh "agi@${RobotIp}" 'mkdir -p /home/agi/eldercare-x2'
scp -O .\eldercare_x2_aarch64_py310.zip "agi@${RobotIp}:/home/agi/eldercare-x2/"
ssh -o ServerAliveInterval=15 -o ServerAliveCountMax=3 "agi@${RobotIp}"
```

账号/用户目录以设备方实际提供为准，上述agi用于当前已验证机型环境。SSH登录成功后在PC2执行：

```bash
cd /home/agi/eldercare-x2
python3 -m zipfile -e eldercare_x2_aarch64_py310.zip .
cd eldercare_x2
source /home/agi/aimdk/install/local_setup.bash
python3 scripts/robot_preflight.py
python3 -c 'import json; m=json.load(open("bundle_manifest.json")); print("源码提交：", m["source_revision"], "未提交修改：", m["source_dirty"])'
```

预检不通过先核对环境；不替换原生SDK、不绕过检查、不进入PC1修改运控。source-commit和bundle_manifest只包含公开元数据，没有Key。依赖可导入不等于收音、网络、表情和动作都已验证。

## 4. 私有Key单独准备

新电脑复制 `.env.example` 为 `.env`，在本地编辑器填入自己的DOUBAO_SPEECH_API_KEY及ARK_API_KEY。已有.env时不覆盖；不公开发送或提交该文件。另开电脑PowerShell，在同一交付目录、重新确认当前IP后上传：

```powershell
$RobotIp = (Read-Host '输入机器人当前 Wi-Fi IP').Trim()
scp -O .\.env "agi@${RobotIp}:/home/agi/eldercare-x2/eldercare_x2/.env"
```

PC2执行 `chmod 600 /home/agi/eldercare-x2/eldercare_x2/.env`。Agent和语音探针自动读取，不用每次手输。真实食堂记录和会话数据不随交付包迁移，新机器人默认从自己的记录开始。

## 5. 接入和启动

使用包内 `eldercare_x2/README.md` 的“每次启动自研交互与查看食堂反馈”步骤：PC2设置only_voice→进入已核对的PC3逐条重启原生agent→回PC2实际确认模式→运行完整Agent。该README在ZIP解压后的机器人目录中，也可在电脑解压ZIP后阅读；线上参考仓库main，而不是较早的v0.3.0纯语音标签。

完整入口须同时包含 `--presentation-backend aimdk --enable-robot-presentation --enable-robot-motion`，才能复现当前语音＋表情＋动作联动；动作前由操作者确认稳定站立。程序不会自行改变机器人姿态。运行中的Agent窗口保留。

## 6. 新电脑打开反馈表

另开Windows PowerShell进入同一交付目录：

```powershell
.\open_dining_dashboard.cmd
```

输入当前IP，在新SSH窗口自行输入密码并保留窗口。这里使用ZIP部署入口，不使用open_container_feedback.cmd。网页自动查找用户目录下一层的ZIP部署，兼容带提交号的部署目录；多套部署时提示选择与当前Agent相同的目录，不扫描隔离备份。网页与Agent读取同一机器人项目下的data/dining_feedback.jsonl。保存由Agent在用户明确确认后完成，不打开网页也可记录；网页不会替代运行中的Agent。

## 7. 逐项验收，再宣布复现

| 项目 | 通过标准 |
|---|---|
| 部署与版本 | 预检通过，源码提交和摘要与交付包一致 |
| 语音 | 唤醒后完整识别用户目标句，回答实际连续播出 |
| 对话 | 健康状态承接、后续上下文、用药与日程话题切换符合本轮输入 |
| 表情 | 现场实际看到开心/关切等相应表情；不只看accepted日志 |
| 动作 | 已核对动作完整执行并收回、站立稳定；保留至少8秒间隔 |
| 食堂 | 描述→复述→明确确认→JSONL新增→新电脑网页可见 |
| 退出与恢复 | Ctrl+C停止，normal＋PC3重启后原生语音实际恢复 |

记录新机器SDK/固件、交付提交、网络条件、日志及上述结果。当前仅手头一台机器已完成整体实测，第二套设备未验收前不标记“跨设备复现已通过”。保留上一套ZIP及各自提交号，可在停止Agent后重新解压旧包回滚；私有配置、真实记录先备份，数据格式兼容性另行核对。
