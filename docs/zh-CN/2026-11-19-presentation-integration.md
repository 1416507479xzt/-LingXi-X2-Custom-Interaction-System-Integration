# 2026-11-19：表情与动作接入核对

本轮在第三版纯语音基线上开展。机器人当前由用户确认为零力矩状态，暂不发送肢体动作，不由程序切换运动模式。Wi-Fi IP由操作者每次确认，不写入配置。

## 已取得的机载证据

PC2 source AimDK 后，ROS 图可见 PlayEmoji、SetMcPresetMotion 和 GetMcAction 服务。

PlayEmoji 请求含 header、emotion_id、mode、priority；响应含 CommonResponse header、bool success、string message。机载枚举明确 happy=90、neutral=10、sympathy=120；mode=1为单次。已按 emotion_id=90、mode=1、priority=1 调用，返回 success=True、message=成功；用户确认屏幕实际显示了快乐表情。响应 header.status.value=0，不能误用该字段否定外层 success。

SetMcPresetMotion 请求含 RequestHeader header、area.value、motion.value、interrupt、ani_path、play_timestamp；响应为 response.header.code、task_id、state.value。机载枚举包含 WAVE_HAND=1002、RAISE_HAND=1001、RIGHT_HAND=2、LEFT_HAND=1。当前仓库目录还包含按1.1文档准备的若干编号，机载枚举并未逐项印证，不得直接开放整个目录。服务请求被受理也不等于动作完成。

GetMcAction 在 ros2 interface show 展开 McActionInfo 时抛出 InvalidResourceName: //，报错指向生成IDL的注释行解析。已知只读命令展示失败，不能据此断定Python类型或ROS服务不可用；随后Python导入及实例化GetMcAction.Response成功：header、info；info字段为current_action、action_desc、status。这里只是默认实例结构，不是机器人实际运动模式响应，后续仍需只读查询实际模式。不要为解决展示报错修改或重编译机器人原生SDK。

## 分阶段验证

1. 保持当前运动模式，先验证一次屏幕表情；无模型调用、无肢体动作、无音频焦点操作。
2. 核对GetMcAction Python字段及实际模式响应，补齐匹配1.0.0的适配与失败处理。
3. 先使对话支持仅表情的能力范围，验证不会对语音或食堂记录产生回退，再逐项验收动作。
4. 动作测试前由现场人员按机器人既有操作流程准备稳定站立及空间条件；程序不从零力矩自动切换，也不在服务超时后盲目重复发送动作。

## 当前结论

目前只有快乐表情单项已实机通过；对话联动和肢体动作尚未验收。第三版语音与食堂闭环的既有验收保持有效，v0.3.0标签不变。后续实测须另记实际显示、动作结果、服务响应及对语音延迟的影响。


## 仅表情对话实现

主分支增加独立 --enable-robot-motion 开关，默认关闭。--presentation-backend aimdk --enable-robot-presentation 现在仅启用屏幕表情；不传动作开关时，模型能力目录没有手势，后端不导入或创建动作查询/控制客户端，绕过模型传入动作也会被阻止。表情根据模型选择；不会每轮强制固定表情。真机动作目录缩减为机载字段已核对的左右挥手和举手；即使显式开启，执行前仍须实际查询STAND_DEFAULT且status=100，不自动切换姿态，不重发不确定请求。编号核对不是动作实机验收。

表情/动作表现请求在语音首包交付时异步发起，最多一个在处理，新请求遇忙跳过，不排队积压旧动作。请求失败不阻止语音，超时不自动重发；退出先取消/收集任务，再销毁ROS节点。该实现避免等待表现RPC阻塞首包，不承诺屏幕与声音严格同步。

196项相关离线测试通过，包含原语音/食堂回归及仅表情能力、无动作客户端、直接传入手势阻止、异步不阻塞/不积压和退出清理。修正两条旧测试对首次问候台词的过期断言，运行逻辑沿用已确认的“我在呢”。未连接机器人或调用模型，尚需更新包后验证联动。

## 本轮部署及联动复测

用户确认原生语音当前会回答，因此部署后必须先切换only_voice并重启PC3 agent、核对原生问答停止；不能因屏幕表情能播就跳过音频模式核对。按[README切换步骤](../../README.md#原生交互模块切换重启与恢复)操作。

Windows PowerShell仓库根目录执行（先停止旧自研Agent）：

```powershell
$RobotIp = (Read-Host '输入机器人当前 Wi-Fi IP').Trim()
if ([string]::IsNullOrWhiteSpace($RobotIp)) { throw '机器人 IP 不能为空' }
scp -O .\dist\eldercare_x2_aarch64_py310.zip "agi@${RobotIp}:/home/agi/eldercare-x2/"
```

机器人PC2 SSH执行：

```bash
cd /home/agi/eldercare-x2
python3 -m zipfile -e eldercare_x2_aarch64_py310.zip .
cd eldercare_x2
source /home/agi/aimdk/install/local_setup.bash
python3 scripts/robot_preflight.py
```

确认only_voice实际生效后，在PC2项目目录启动（不添加 --enable-robot-motion）：

```bash
mkdir -p logs
SESSION_ID=$(date +%Y%m%d_%H%M%S)
export DOUBAO_ASR_HOTWORDS='["灵犀"]'
export X2_ONLY_VOICE_CONFIRMED=1
python3 scripts/run_robot_agent.py --transport aimdk --enable-robot-audio --competition-mode --health-semantic model --llm-model doubao-seed-2-0-mini-260428 --presentation-backend aimdk --enable-robot-presentation --vad-idle-seconds 1.5 --aimdk-streaming-asr --dining-feedback-records data/dining_feedback.jsonl --log-file "logs/expression_${SESSION_ID}.log" --metrics-file "logs/expression_${SESSION_ID}_metrics.json"
```

测试招呼、疲惫求助及食堂意见确认；观察屏幕、听语音连续性、查看记录及日志“模型表现下发结果”。服务accepted不等于用户看到显示，模型选null也不应当作接口失败。机器人应没有肢体动作。结束Ctrl+C后执行 unset X2_ONLY_VOICE_CONFIRMED DOUBAO_ASR_HOTWORDS；如需原生问答再按README恢复normal。

第三版标签继续保留原始语音基线；本轮为main后续开发，离线包清单使用Git提交号区分，不把本轮待联动验证的功能追认到v0.3.0标签。


## 对话中未见表情的首轮排查

用户反馈只有默认表情；10:26日志中，neutral两次accepted、一次rejected，sympathy一次rejected。模型有选表情，不是全部输出null；accepted的neutral本来就可能与默认外观接近。旧日志丢弃服务message，不能据此确定拒绝原因。

停止自研Agent后，用户再次直接请求emotion_id=120、mode=1、priority=1，返回success=True、message=成功，且屏幕实际显示表情；ROS图存在 /face_ui_proxy/status [aimdk_msgs/msg/FaceEmojiStatus]。证明关切素材/编号及单次服务调用可用，不证明对话时的间歇拒绝已解决。优先级冲突只是候选原因，尚无该次拒绝的message或同期状态证据；也可能存在其他显示资源条件。

本轮仅补齐表现回执的emotion_id、mode、priority和外层message（限240字符）；无响应明确记unknown，不把超时等同拒绝。保持priority=1、不重试、不关闭系统显示模块，不修改对话、音频或肢体动作开关。相关34项聚焦回归通过；下一次先更新presentation.py，重复对话并查看完整服务message，再决定修复办法。


## 拒绝原因已确认：当前播放优先级60

10:31:19的neutral请求（id10、单次、priority1）成功；10:31:28的confused和10:31:39的sympathy均返回rejected，外层message明确说明“优先级低于当前播放，操作被忽略, extra: Current priority: 60, request priority: 1”。至此确认拒绝机制为显示优先级竞争，不再只是候选原因。

仍未知priority60播放项的素材、发起模块、有效时段及是否含系统状态提示。不能把显示优先级60当作表情编号60，也不能推断它来自音频焦点优先级6；两者是不同接口的参数。下一步只读查看/face_ui_proxy/status的发布者、QoS及当前播放状态，必要时做对话期间对照，再选择协调办法。当前没有提高表情优先级、关闭task_manager/interaction_slave、修改原生SDK或启用肢体动作。

当前可访问的[官方屏幕文档](https://x2-aimdk.agibot.com/zh-cn/latest/Interface/interactor/screen.html)标为1.1.0，说明低优先级请求会被忽略，并提醒高优先级覆盖可能遮挡系统提示；本机具体priority60来源必须依据1.0.0实测核对，不把新版文档中的系统优先级数值当作本机全量配置。


## 状态采集QoS修正（机载1.0.0）

用户只读查询确认 /face_ui_proxy/status 的发布者为 face_ui_proxy，QoS 为 RELIABLE + VOLATILE；订阅者 app_proxy、soc0_task_manager4288 为 BEST_EFFORT + VOLATILE。此前依据可访问1.1文档给出的TRANSIENT_LOCAL订阅触发DURABILITY不兼容警告，未收到消息。这是诊断命令的参数不匹配，不是话题不存在或播放服务故障。

后续诊断必须使用 --qos-reliability best_effort --qos-durability volatile，订阅建立后再触发实际显示事件。VOLATILE不保证返回订阅前的历史消息，空闲时超时没有输出不能证明没有优先级60。task_manager在此是订阅者，不能用该列表认定它是优先级60的请求来源。仍未提高优先级或改动系统模块。
