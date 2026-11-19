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


## 优先级60的播放内容与有界协调实现

用户在自研Agent停止时，用BEST_EFFORT + VOLATILE成功取得20秒状态样本：默认眨眼/平静为priority0、mode2；其间交替出现adore(id200)和thinking(id170)，priority60、mode1，随后回落至priority0。证明高优先级项不是持续占用，本次样本的素材属于已知表情；未取得调用者或trace_id，不把具体发起模块写成定论。

新增协调只在仅表情模式生效：第一次请求若明确收到success=False且message包含“优先级低于当前播放”和Current priority，则订阅同一节点上的FaceEmojiStatus（BEST_EFFORT/VOLATILE），后台最多等待6秒。必须收到拒绝后的新低优先级事件（priority<=1），接收时间及消息header.stamp均通过新鲜度检查，才以同一id/mode/priority1再尝试一次。最多共两次调用；等待超时、无状态类型、失去控制权、其他拒绝、无响应或结果不明时不重发。不依赖time_to_end_ms猜测空闲，不关闭系统模块或覆盖priority60及其他高优先级显示。消息时间戳与ROS时钟不一致时可能保守跳过，不能把它当作显示成功。

下一轮表现计划到来时，仅表情模式取消旧的等待任务（包括下一轮选择null），避免积压过时表情；显式肢体动作模式保持不替换在途计划，且不使用上述表情等待重发流程。语音不等待这6秒，实际表情可能晚于语音开始，也可能因没有空闲窗口被跳过；不承诺严格同步。

203项相关离线回归通过，包含明确拒绝后低优先级重试、保持priority1、未获空闲不重发、旧接收/发布状态不作为空闲依据、控制权丢失、等待取消释放锁及新轮次替换。暂无更新后的真机结果。需要同时更新presentation.py和agent.py，使用新离线包部署，再重复问候、疲惫及食堂确认；核对attempts、wait_ms、message及实际屏幕/语音效果。


## 协调后的首轮真机联动验收

用户更新95049a6对应离线包、预检通过后，在only_voice、零力矩、肢体动作开关关闭的条件下复测：

- 10:42:40：neutral(id10)，priority1，attempts1，wait_ms0，accepted，message成功。
- 10:42:49：sympathy(id120)，首次因当前priority60被明确拒绝；收到低优先级新状态后，等待421ms，以原priority1第二次请求，accepted，message成功。
- 用户进一步确认：“表情显示了，语音也正常”。至此本轮语音与屏幕表情联动获得服务回执及现场观察双重确认。

421ms仅是这一轮表情协调等待，不是端到端语音延迟。此样本证明有空闲窗口时的协调路径可用，不代表所有网络/噪声条件下均成功或完全同步；本轮未提供全链路计时、食堂新增记录数或动作结果，不补记未测项目。肢体动作仍未开启及验收；第三版标签不移动。

下一步先只读查询GetMcAction实际响应，并由现场人员核对稳定站立准备条件，再考虑单个挥手动作。程序不自动从零力矩切换运动模式。


## 单次右手挥手测试：无响应、无可见动作

只读GetMcAction先返回PASSIVE_DEFAULT/status100，用户调整后再次查询返回code0、STAND_DEFAULT/status100；因此此次确有稳定站立模式响应证据，不能把status100单独解读为稳定站立。

随后操作者单次执行 timeout 10s ros2 service call /aimdk_5Fmsgs/srv/SetMcPresetMotion aimdk_msgs/srv/SetMcPresetMotion 请求：area.value2、motion.value1002、interrupt=false、play_timestamp0；请求头时间戳保持默认0。终端显示requester: making request后返回提示符，未出现response；用户观察机器人没有任何反应。未采集该命令退出码，不将其记为明确拒绝、受理或完成。测试尚未通过，不能仅凭服务在ROS图中存在就断定服务链路可用。

目前不重复发送，不自动改运动模式、原生模块或SDK。下一步只读复核GetMcAction当前响应及运动/桥接服务节点，确认查询链路和动作服务提供方后再定位。表情与语音既有验收不变，肢体动作对话开关继续关闭。


## 动作服务提供方核对

只读node info确认 /ros2_bridge_node 只有参数服务，不提供目标运控RPC；/mc_ros2_node3606 同时提供GetMcAction、SetMcPresetMotion、GetMcPresetMotionState、GetMcMotions等服务。GetMcAction再次返回STAND_DEFAULT/status100；因此不是整个MC节点不可查询，但仍未证明动作RPC已被处理。没有重发动作、重启MC或改控制来源。

后续优先比较二开SDK与机载运行服务的动作请求定义。当前PC2二开环境SetMcPresetMotion没有input_source；可访问的1.1官方变更记录说明该字段为新增预留字段。机载服务是否使用含该字段的定义尚未核实，只有版本差异假设，不能据此直接安装新版SDK或修改消息。应先只读定位 /agibot/software 中实际部署的 .srv/.idl，对比字段顺序。GetMcAction能通信不代表所有srv均匹配。

官方1.1预设动作文档还明确，GetCurrentInputSource不能用来查询谁在控制预设动作；不能据此将修改输入源当作挥手修复的先决条件。此项引用仅用于排查边界，不把1.1的结构直接套到本机。参考[变更记录](https://x2-aimdk.agibot.com/zh-cn/latest/changelog.html)及[预设动作](https://x2-aimdk.agibot.com/zh-cn/latest/Interface/control_mod/preset_motion.html)。


## 原生消息环境探查受阻，保留原二开环境

PC2用户直接查看 /agibot/software/v0/common 和share返回Permission denied。此前Path.rglob未找到接口文件不能作为文件不存在的证据，也未取得服务端schema。aima em load-env --source-msgs无参实际报requires an argument；help虽有无参说明，但该安装版本实际要求TEXT。用户因此未进入子shell，随后exit退出了原SSH，未停止任何机器人服务。

重连后使用 --source-msgs common（符合实际help的参数形式），工具报File not found: /agibot/software/v0/entry/bin/cfg/env.yaml，仍未成功建立原生环境。此后新SSH中import aimdk_msgs失败，是当前终端尚未加载二开SDK的结果之一，不能认定原SDK损坏或需要重装。先 source /home/agi/aimdk/install/local_setup.bash 恢复已验证环境。

截至此时，动作schema不一致仍是待验证假设。停止此条加载路线，不创建伪造env.yaml、不改目录权限、不sudo加载整个交互环境、不重编译或替换原生SDK。曾提出登录PC1只读查看mc配置的建议；用户提醒官方二开边界后，该步骤已撤回，不作为后续操作步骤，也无用户已执行此步骤的证据。后续排查限定在PC2，通过官方二开接口和匹配版本的SDK/例程核对；如需PC1内部资料，应由官方技术支持提供。原单次动作请求结果仍未明，不重发，不切换运动模式或停运控进程。


## 开发边界纠正

用户明确提醒PC1不能作为二开开发环境。核对[官方计算单元说明](https://x2-aimdk.agibot.com/zh-cn/latest/about_agibot_X2/onboard_computer.html)，官方明确禁止使用运控计算单元PC1作为二开程序开发运行环境。官方这条原文针对开发运行环境，不能改写成“所有只读登录均被官方禁止”；但本项目没有必要为当前排查进入PC1，因此撤回此前只读登录建议，后续不要求操作者登录PC1，不在其上部署、安装、修改、停止或重启MC。

本项目二开程序继续在PC2运行。PC3仅沿已验证流程进行原生交互模式生效所需的agent重启，不能类推成允许操作PC1运控模块。此前动作无响应及schema兼容性仍未解决，不将开发边界纠正写成动作问题已经修复。


## PC2只读动作诊断入口

新增 scripts/aimdk_motion_diagnostic.py，完全留在PC2运行：打印二开SDK来源/版本及动作相关请求/响应字段、图中服务提供方、已安装preset例程路径；使用一个ROS节点只查询GetMcAction和（类型存在时）GetSystemState。查询每项只发一次，发现和响应等待有界；无类型/无服务/超时分别报告，不自动迁移系统状态或切换运动模式。

脚本从不创建SetMcPresetMotion、SetMcAction、SetMcInputSource或MigrateSystemState写客户端，不发送挥手、不加载原生环境、不访问PC1、不读取.env、不联系云服务。四项离线测试覆盖写接口被拒绝、超时不重发及清理、服务缺失时不发送、正常只读响应。诊断已纳入离线包，但仅更新该脚本即可使用；无需重新部署已验证业务代码。

依据[官方Python例程](https://x2-aimdk.agibot.com/zh-cn/latest/example/Python.html)关注跨板ROS服务问题；只读模式查询使用当前时间戳。不把文档中的重试写法未经核对直接用于结果不明的动作请求。当前仍未查明挥手无响应的根因，SDK版本差异仅为假设，等待诊断输出。

PC2加载原SDK后执行：python3 /home/agi/eldercare-x2/eldercare_x2/scripts/aimdk_motion_diagnostic.py。该脚本不依赖Agent运行，保持自研Agent停止，完成后把JSON输出作为下一步判断依据。


## PC2只读诊断输出：模式响应、类型缺失与系统状态超时

SDK仍是/home/agi/aimdk/install的v1.0.0-ga424add；SetMcPresetMotion请求不含input_source。GetMcAction一次返回STAND_DEFAULT/status100；GetSystemState服务存在（/soc0_sm3599），本次一次只读请求超时。/mc_ros2_node3606提供GetMcMotions和GetMcPresetMotionState，但本地SDK中二者类型缺失。这是接口覆盖差异的直接证据，不是SetMcPresetMotion序列化必然不兼容的证据，也不能因单次读超时断定开发者模式或系统状态。

诊断找到实际官方例程 /home/agi/aimdk/src/py_examples/py_examples/preset_motion_client.py；后续只读其源码，核对机载版本的构造、时间戳和调用方式，不直接运行含写请求/重试的例程。

检查诊断实现时还发现GetSystemState使用header/CommonRequest布局，原脚本只给request/CommonRequest布局填当前时间；本地已兼容这两种只读请求头并补测试。该遗漏不证明超时根因，修正后仍未取得真机系统状态。收窄例程路径查找，避免将生成的消息Python文件误标作例程。五项诊断离线测试通过；目前无需为了该修正再次上传/运行诊断，优先读取现有官方例程。


## 机载官方预设动作例程核对与单次探针

用户只读提供/home/agi/aimdk/src/py_examples/py_examples/preset_motion_client.py完整源码。它使用当前已导入的SetMcPresetMotion、RequestHeader、McPresetMotion及McControlArea，area/motion赋value、interrupt=False，发送前将header.stamp设为node当前时间。例程对跨板通信使用最多8次、每次0.25秒等待的发送循环。这说明安装例程没有额外input_source字段；不能因此推断远端服务schema必然相同，也没有证据支持立即替换SDK。

此前手工CLI请求header.stamp为0，和机载例程的当前时间戳不同；这只是可验证差异，尚未证实是无响应原因。当前不直接运行含多次写重试的官方例程。

新增scripts/aimdk_motion_probe.py：默认只查询模式；显式--execute才允许右手挥手（area2/motion1002）一次。沿用一个PC2节点，先查询GetMcAction，要求header.code0、STAND_DEFAULT/status100，动作服务发现后才构造当前时间戳请求；interrupt=False、play_timestamp0，等待响应最多8秒且不重发。保留code/task_id/state的响应数据，不把服务受理当作动作完成。无响应、失去明确模式或非稳定站立时不继续动作；不进入PC1、不切换模式、不修改SDK。

四项探针离线测试通过，连同五项只读诊断测试共九项：默认不创建写客户端、零力矩/切换中阻止、单次当前时间戳及任务响应保留、超时清理且不重发。真实挥手仍待用户执行单次探针并观察，现有生产语音/表情和动作开关不变。

部署只需将scripts/aimdk_motion_probe.py复制到PC2项目scripts目录。先加载原SDK，默认运行脚本不加参数可只读核对；现场确认站稳、手臂空间和急停操作条件后，才单次运行 python3 scripts/aimdk_motion_probe.py --execute。若未知结果，先观察并回传JSON，不重复执行。


## 单次右手挥手实际通过及主Agent接入准备

用户执行新版单次探针，模式查询code0、STAND_DEFAULT/status100；motion_requests=1，动作服务有response：code0、task_id0、state400。state400为RUNNING，不是完成回执；task_id0也不能当作可靠非零任务关联ID。随后用户明确确认“完整挥手并收回，站立稳定”，单项右手挥手由服务响应和实际观察共同验证。

这次使用当前时间戳的单节点单次请求成功，之前零时间戳CLI无响应；但两次工具、发现等待和调用时机也不同，不是严格同条件A/B，不能宣称时间戳就是唯一根因。无需更换或重编译SDK，也没有访问PC1。此前版本不兼容假设未被证明，现有SDK已能跑通这个动作。

主Agent同步采用当前请求时间戳，play_timestamp0、interruptFalse，GetMcAction前也填当前时间；动作响应等待上限8秒（模式3秒、表情0.6秒），只等待不重发。日志保留code/task_id/state，不宣称动作完成。每次动作仍重新核对稳定站立及8秒冷却。运行时动作白名单现在仅已实际验证的右手挥手wave_hands（1002/2），左手、举手等参考映射不开放。

开启总动作开关后，无手势的纯表情计划继续使用priority60协调；带手势计划不等待表情空闲，避免延后执行旧动作。正在等待的旧纯表情计划可被新计划替换，但在途肢体计划不取消、不排队重发。模型可选null，不强制开场挥手；需要用明确“请挥挥右手”先验收联动。

214项相关离线回归通过，包括生产时间戳/任务回执、未实测动作阻止、动作开关开启时纯表情协调仍可用及原语音/食堂回归。本次仅探针实际通过，更新后的主Agent语音/表情/挥手联动仍待部署测试，第三版标签保留不动。

## 主Agent右手挥手联动命令（单项通过后）

上传并解压新版完整ZIP、source机载SDK、预检通过。自研Agent停止时实际核对only_voice状态（若原生仍回答，先按README流程切换），由现场人员确认稳定站立、手臂活动空间与急停条件。PC2项目目录启动：

```bash
mkdir -p logs
SESSION_ID=$(date +%Y%m%d_%H%M%S)
export DOUBAO_ASR_HOTWORDS='["灵犀"]'
export X2_ONLY_VOICE_CONFIRMED=1
python3 scripts/run_robot_agent.py --transport aimdk --enable-robot-audio --competition-mode --health-semantic model --llm-model doubao-seed-2-0-mini-260428 --presentation-backend aimdk --enable-robot-presentation --enable-robot-motion --vad-idle-seconds 1.5 --aimdk-streaming-asr --dining-feedback-records data/dining_feedback.jsonl --log-file "logs/motion_${SESSION_ID}.log" --metrics-file "logs/motion_${SESSION_ID}_metrics.json"
```

先“你好灵犀”，开场期间如已挥手则等完全收回、至少8秒后再发新动作请求；否则回答结束后说“请挥挥右手”。观察语音、表情、实际动作及站立；不要连续快速重复动作请求。之后再测试疲惫回答和食堂确认，检查无手势轮次表情及反馈记录不退化。结束Ctrl+C，执行unset X2_ONLY_VOICE_CONFIRMED DOUBAO_ASR_HOTWORDS；需要恢复原生问答时按README恢复normal。结果不明先观察并查日志，不反复唤起同一动作。


## 主Agent联动首轮回执（11:16—11:17）

用户部署并预检后启动带--enable-robot-motion的主Agent：11:16:58同一表现计划中，neutral(id10/priority1)一次accepted，同时wave_hands返回accepted、code0、task_id0、state400。11:17:17的下一条纯表情neutral计划先因priority60拒绝，等待915ms后以priority1第二次请求accepted。

这些回执证明主Agent已实际发出并收到右挥手的服务受理、开启肢体动作后纯表情协调仍有成功样本；915ms仅为表情协调等待，不是端到端语音延迟。state400仍不等于动作完成。本次已向用户核对实际挥手收回、站立、语音与表情，尚待现场观察回复；未将服务accepted直接标成完整联动验收通过。


## 本轮现场补充：动作与语音正常，表情选择neutral

用户回复“动作和语音都正常但是我没看见表情，我不知道agent没下发还是下发失败了”。据此，主Agent右挥手及语音的现场效果得到确认；本轮表情实际可见效果仍不确定。

回看两条回执，情绪均为neutral(id10)，且最终accepted，没有happy或sympathy。neutral对应平静表情，本就可能接近默认外观；不能把没看到明显变化记成没有发送，也不能把accepted当作持续可见且未被原生显示覆盖。没有证据要求再提高优先级、改SDK或关闭原生模块。

下一步使用明确且可见的开心表情请求核对模型选择、最终回执和屏幕效果，动作开关可在本次纯表情对照中关闭，避免新增挥手干扰。此处不改成每轮强制表情，不因neutral正常选择而自动判错。
