# 环节四：社区食堂膳食意见收集（真机纯语音）

当前与环节一、二共用Mini语音Agent，保持--presentation-backend none。模型判断食堂意见和提取原话片段；机器人复述并征求确认，确认后才写入本地JSONL表，网页只读显示。同一待提交记录ID防止重试重复写入；取消不写入。未确认草稿只在当前会话，已确认记录留在机上。

## 更新

在Windows PowerShell源码目录上传新版离线包；每次重新输入当前机器人Wi-Fi IP。

```powershell
cd 'C:\Users\LENOVO\Desktop\2026浙江省数智【具身智能应用实践赛道】文件\智慧养老\智慧养老_参赛源码'
$RobotIp = Read-Host '输入机器人当前 Wi-Fi IP'
scp -O .\dist\eldercare_x2_aarch64_py310.zip "agi@${RobotIp}:/home/agi/eldercare-x2/"
```

显示100%后，使用原SSH窗口；若已断线，在PowerShell执行ssh "agi@${RobotIp}"重新登录。看到agi@agi提示符后执行：

```bash
cd /home/agi/eldercare-x2
python3 -m zipfile -e eldercare_x2_aarch64_py310.zip .
cd eldercare_x2
source /home/agi/aimdk/install/local_setup.bash
python3 scripts/robot_preflight.py
```

旧Agent先Ctrl+C停止。新版不会自动改机器人原生模式；保持此前已验证的only_voice。API Key自动读取机上.env，不会因解压包覆盖。

## PC2启动Agent

在机器人项目目录执行，当前统一使用data/dining_feedback.jsonl，与已存在的反馈和网页启动器一致。该文件可能已有记录；先记下已有行数，只核对本轮新增数，不删除或覆盖旧数据。如需独立测试文件，Agent的--dining-feedback-records和网页启动器的-RecordsPath必须同时指向同一文件。

```bash
mkdir -p logs
SESSION_ID=$(date +%Y%m%d_%H%M%S)
export DOUBAO_ASR_HOTWORDS='["灵犀"]'
export X2_ONLY_VOICE_CONFIRMED=1
python3 scripts/run_robot_agent.py --transport aimdk --enable-robot-audio --competition-mode --health-semantic model --llm-model doubao-seed-2-0-mini-260428 --presentation-backend none --vad-idle-seconds 1.5 --aimdk-streaming-asr --dining-feedback-records data/dining_feedback.jsonl --log-file "logs/voice_${SESSION_ID}.log" --metrics-file "logs/voice_${SESSION_ID}_metrics.json"
```

结束Ctrl+C后：`unset X2_ONLY_VOICE_CONFIRMED DOUBAO_ASR_HOTWORDS`。到点主动提醒不在开发范围，本流程不会启用它，也不执行表情动作。

## 电脑查看机器人反馈表

推荐在Windows电脑双击仓库根目录的`open_dining_dashboard.cmd`，或在电脑PowerShell执行：

```powershell
& 'C:\Users\LENOVO\Desktop\2026浙江省数智【具身智能应用实践赛道】文件\智慧养老\智慧养老_参赛源码\open_dining_dashboard.cmd'
```

输入当前机器人IPv4地址；启动器另开SSH窗口，在新窗口自行输入密码。它自动选择18765至18775之间的空闲本地端口，建立仅127.0.0.1监听的SSH转发，并在机器人相同端口启动反馈表，仍读取data/dining_feedback.jsonl。检查HTTP 200及反馈表标题成功后才打开浏览器。请使用自动打开的地址，不继续刷新旧8765页面；保留标注“食堂反馈表 SSH”的窗口。它不停止原语音Agent，不修改原生服务，不复制记录到外网。

脚本UTF-8带BOM，兼容PowerShell5.1；ExecutionPolicy Bypass仅对启动进程生效，不持久修改系统策略。SSH密码由OpenSSH自行交互输入，脚本不读取或保存。无法建立连接时查看SSH窗口报错；端口占用不关闭其他程序，会尝试其他空闲本地端口。如果已打开过一个正常反馈表窗口，直接使用那个窗口，结束时Ctrl+C关闭后再重新启动，避免反复开多个服务。

手动方式仍可使用以下步骤：

保留Agent SSH窗口。另开一个Windows PowerShell，变量不会从旧窗口自动继承，要重新输入IP。下面一条SSH同时建立端口转发、在机器人上运行本机网页服务：

```powershell
$RobotIp = Read-Host '输入机器人当前 Wi-Fi IP'
ssh -t -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -L 8765:127.0.0.1:8765 "agi@${RobotIp}" "cd /home/agi/eldercare-x2/eldercare_x2 && python3 -u feedback_dashboard.py --records data/dining_feedback.jsonl --port 8765"
```

自行输入SSH密码。看到本地反馈表地址后，在电脑浏览器打开 **http://127.0.0.1:8765/**，使用HTTP而非HTTPS。保持这个PowerShell窗口打开，刷新页面查看新增记录。

网页读的是机器人文件，通过SSH隧道传到电脑；不是读取Windows项目目录里的另一份JSONL。网页访问本身不需要VPN，模型仍需要云端网络。若转发端口已被其他程序占用，可仅把-L后的本地端口改成8766:127.0.0.1:8765，浏览器改访问http://127.0.0.1:8766/。若机器人8765端口已被占用，先核对是否已有同一反馈表服务，不要盲目启动第二个。连接断开或服务停止时网页无法访问，应恢复该窗口，不是修改机器人原生服务。

## 真机测试输入

先“你好灵犀”完成正常开场，每句等实际说完后再继续：

1. 今天食堂的汤有点咸，希望下次少放盐。应复述并征求确认，页面还不增加记录，“有点咸”不能变成“太咸”。
2. 对，就这样记录。应保存一条口味意见；刷新页面核对汤、有点咸、少放盐。
3. 食堂以后能做清蒸鱼吗？应作为想吃的菜征求确认，不假称今天已有该菜。
4. 好的，记下来吧。应新增第二条菜品愿望。
5. 今天食堂的菜有点辣。应征求确认，不沿用旧的“汤”或“清蒸鱼”作菜名。
6. 这条先不提交了。取消，不新增第三条记录。

可选边界测试：问“今天食堂有什么菜”，没有菜单资料时应说明无资料，不编造菜单；没有待确认意见时说“确认提交”，应说明暂无待确认内容，不写入。

用户提出更正时仍可修改待确认内容，但纠正不是本轮比赛必测项；同音不确定时保留现有菜名核对。涉及用药或急迫健康求助时优先处理，不作为食堂意见写入。

记录路径修复背景见[断续声音与反馈保存路径核查](2026-11-18-playback-and-feedback-path.md)。

## 记录和范围

记录字段包括提交时间、类别、菜品/对象、感受、期望和状态。只有程序成功保存才回复已经记入；保存失败不谎报成功。愿望菜名必须来自原话，若模型将“能做清蒸鱼吗”改写成不在原话中的“想吃清蒸鱼”，短请求保留原句作为期望，而不是伪造逐字引述。

这是本地结构化表及网页查看闭环，尚未对接外部社区服务中心API，不承诺意见已采纳、菜单已更改或已发送外部平台。不要把真实老人资料加入测试记录或Git；JSONL默认被忽略。

开发电脑复现合成文本/存储/真实HTTP闭环：

```powershell
python scripts/check_dining_voice_live.py --live --output logs/stage4_voice_check.json
```

需要自备云端Key并会产生模型调用费用；使用临时目录，结束后删除合成记录，不接触真实反馈表。不包含麦克风、TTS、机器人或跨机SSH隧道验收。最后结果见[开发检查记录](2026-11-18-stage4-real-voice-preparation.md)。
