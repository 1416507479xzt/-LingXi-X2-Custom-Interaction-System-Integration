# 自主回答、表情与全部官方预设动作

更新于2026-11-19。按用户要求，main已从“仅右手挥手”扩展到官方预设动作表中的全部29个motion/area组合；当前20种交互表情继续开放。输入原话、会话记忆、语义说明和能力目录共用同一次Mini请求，由模型统一生成回答、表情和一个动作或null，不额外请求一个动作规划模型。

## 目录来源与版本

[官方v0.9.0动作表](https://x2-aimdk.agibot.com/zh-cn/v0.9.0/Interface/control_mod/preset_motion.html)与[当前1.1动作表](https://x2-aimdk.agibot.com/zh-cn/latest/Interface/control_mod/preset_motion.html)在此次核对时包含相同的29个组合。机载SDK仍为v1.0.0-ga424add：调用使用已核对的请求字段及当前时间戳，不新增本机没有的input_source，也不更换SDK、改原生服务或进入PC1。枚举类未列出的某个int32数值，不会由代码改成另一个动作编号。

全部列入目录是按用户本轮要求扩展能力，不等于全部获得实际机器人支持/动作完整性验收。当前右手挥手和双手比心已实际完成并收回，站立稳定；其余27项必须逐项观察服务响应、真实动作和收回状态。不把code0或state400当作动作完成。

## 完整动作表

| 模型名称 | 含义 | motion | area | 验证状态 |
|---|---|---|---|---|
| wave_hands | 右手挥手，问候或告别 | 1002 | 2 | 已完整执行并收回 |
| wave_left | 左手挥手 | 1002 | 1 | 已核对文档，未逐项实机验收 |
| raise_right | 右手举手 | 1001 | 2 | 已核对文档，未逐项实机验收 |
| raise_left | 左手举手 | 1001 | 1 | 已核对文档，未逐项实机验收 |
| clap | 鼓掌，祝贺或鼓励 | 3017 | 11 | 已核对文档，未逐项实机验收 |
| salute_right | 右手敬礼 | 1013 | 2 | 已核对文档，未逐项实机验收 |
| salute_left | 左手敬礼 | 1013 | 1 | 已核对文档，未逐项实机验收 |
| heart_both | 双手比心，表达关怀 | 1007 | 3 | 已完整执行并收回 |
| heart_right | 右手比心 | 1007 | 2 | 已核对文档，未逐项实机验收 |
| heart_left | 左手比心 | 1007 | 1 | 已核对文档，未逐项实机验收 |
| open_arms | 拥抱姿态；Unity仅张开双臂的近似展示，无接触；真机须保持安全距离 | 3008 | 11 | 已核对文档，未逐项实机验收 |
| encourage | 加油，鼓励 | 3011 | 11 | 已核对文档，未逐项实机验收 |
| arms_level | 双手平举 | 1010 | 3 | 已核对文档，未逐项实机验收 |
| arm_level_right | 右手平举 | 1010 | 2 | 已核对文档，未逐项实机验收 |
| arm_level_left | 左手平举 | 1010 | 1 | 已核对文档，未逐项实机验收 |
| bye | 拜拜 | 3031 | 11 | 已核对文档，未逐项实机验收 |
| cross_arms | 双手打叉 | 3009 | 11 | 已核对文档，未逐项实机验收 |
| wave_chest | 胸前右手挥手 | 1011 | 2 | 已核对文档，未逐项实机验收 |
| bow | 鞠躬 | 3001 | 11 | 已核对文档，未逐项实机验收 |
| scratch_head | 挠头 | 3024 | 11 | 已核对文档，未逐项实机验收 |
| shake_right | 右手握手的预设伸手姿态，需要对方配合 | 1003 | 2 | 已核对文档，未逐项实机验收 |
| shake_left | 左手握手的预设伸手姿态，需要对方配合 | 1003 | 1 | 已核对文档，未逐项实机验收 |
| air_kiss_right | 右手飞吻 | 1004 | 2 | 已核对文档，未逐项实机验收 |
| air_kiss_left | 左手飞吻 | 1004 | 1 | 已核对文档，未逐项实机验收 |
| lightwave | 动感光波，夸张表演动作 | 3007 | 11 | 已核对文档，未逐项实机验收 |
| high_five_right | 右手击掌的预设姿态，需要对方配合 | 1008 | 2 | 已核对文档，未逐项实机验收 |
| high_five_left | 左手击掌的预设姿态，需要对方配合 | 1008 | 1 | 已核对文档，未逐项实机验收 |
| wave_chest_left | 胸前左手挥手 | 1011 | 1 | 已核对文档，未逐项实机验收 |
| scratch_hip | 抓屁股，滑稽表演动作，不作为普通关怀动作 | 3025 | 11 | 已核对文档，未逐项实机验收 |

## 模型如何决策

- 开场和正常问答都由模型生成语言；保留此前已确认的首次回应招呼、上下文、健康问询和食堂确认规则，不改成动作专属固定台词。
- 模型根据当前语义可自主选择问候、关怀、鼓励、讲解、告别等表现，也可以只说话；不强制每轮动作、不轮流展示动作目录。
- 明确动作指令应区分左右手，以及挥手、握手、鼓掌、击掌等动作。用户拒绝时gesture为null；冷却或控制权不可用时目录不提供动作。
- 握手、击掌、拥抱等需要对方配合的动作，在用户明确提出或确认愿意交互时选；只代表预设姿态，不宣称已经接触或抓住对方。
- 滑稽、飞吻、夸张表演动作只在明确请求或已建立的表演情境使用，不拿来处理不适、用药或急迫求助。它们仍在目录中，不以额外关键词路由替换模型理解。
- 当前20种交互表情由模型按语义选择；不把故障、充电等系统状态伪装成普通情绪，不提高priority1来覆盖系统显示。既有屏幕优先级协调继续保留。

每轮仍只接收一个受约束JSON（reply/emotion/gesture及业务intent/action）。模型不能输出任意SDK数字、脚本路径、关节指令、走跑命令或自定义动作文件。新增的是文档中的预设动作，不是开放整个运控API。

## 执行边界

二开代码只运行在PC2。启用需要现有 --presentation-backend aimdk --enable-robot-presentation --enable-robot-motion；没有动作开关时仍只显示表情。切换only_voice及恢复normal沿用README，程序不自动切模式。

发送前查询code0、STAND_DEFAULT/status100，最小动作间隔8秒，interrupt=False；动作请求带当前时间戳、play_timestamp0，最多等待8秒、未知结果不重发。模型和代码都不把“准备做”当作“已经完成”。不排队积压动作，不自动运行整张表测试。

无手势轮次的表情在明确priority拒绝后等待新低优先级状态再尝试一次；带动作轮次先发送一次动作，再在从原拒绝起算的6秒总期限内协调表情，绝不重发动作。若动作响应很慢耗尽期限，跳过表情补发；实际显示仍须观察。模型自主选择并不保证所有显示请求都能抢占原生显示。

## 离线与真实模型验证

224项相关离线回归通过；新增表格核对覆盖29个组合，无重复别名，逐个验证正确参数、当前时间戳、非打断及非稳定站立时阻止。覆盖模型允许29种名称或null、禁止任意数值SDK参数，保留原语音、表情和食堂回归。

另用现有Mini做10个合成文本测试，均有有效结构；7个明确动作/拒绝指令7个匹配：左手挥手、鼓掌、双手比心、右手敬礼、拒绝动作、邀请右手握手、动感光波。自主鼓励情境选择happy/clap，疲惫情境选择sympathy/heart_left；选择示例不是固定动作模板。原始合成结果见[文本测试结果](model-evaluation/2026-11-19/presentation_autonomy.json)。未调用ROS、TTS或物理动作，不能当作真机29项动作验收或语音延迟指标；疲惫回答出现额外条件表达，本测试不评价临床或全部回答质量。

开发电脑复测（需要自己的.env，会调用云端模型）：

```powershell
python scripts/check_presentation_autonomy_live.py --live
```

不发起ROS请求的目录查看：

```bash
python3 scripts/aimdk_motion_probe.py --list
```

单项受控测试可用 --gesture 选择上表名字；不加--execute只读查询模式。确认当前稳定站立、手臂空间和急停操作条件后，一次只验证一个动作，例如：

```bash
python3 scripts/aimdk_motion_probe.py --gesture wave_left --execute
```

该命令会发送一次左手挥手，非只读。不要批量循环执行29项，也不要在无响应后重复发送。更换--gesture不能绕过稳定站立检查。

## 主Agent启动（新版完整包已部署后）

在PC2的/home/agi/eldercare-x2/eldercare_x2目录，加载AimDK、预检，并核对only_voice实际生效。操作者确认当前稳定站立及活动空间后：

```bash
mkdir -p logs
SESSION_ID=$(date +%Y%m%d_%H%M%S)
export DOUBAO_ASR_HOTWORDS='["灵犀"]'
export X2_ONLY_VOICE_CONFIRMED=1
python3 scripts/run_robot_agent.py --transport aimdk --enable-robot-audio --competition-mode --health-semantic model --llm-model doubao-seed-2-0-mini-260428 --presentation-backend aimdk --enable-robot-presentation --enable-robot-motion --vad-idle-seconds 1.5 --aimdk-streaming-asr --dining-feedback-records data/dining_feedback.jsonl --log-file "logs/autonomy_${SESSION_ID}.log" --metrics-file "logs/autonomy_${SESSION_ID}_metrics.json"
```

模型现在可以从29项中选动作，启动后不能再按“只会右挥手”布置现场；初次实测建议逐项提出明确动作请求，观察完整执行、收回及站立，并留足冷却时间。再验证情境自主选择、拒绝动作、健康/用药及食堂记录。测试结束Ctrl+C，再执行unset X2_ONLY_VOICE_CONFIRMED DOUBAO_ASR_HOTWORDS。需要原生问答时按README恢复normal。

第三版标签v0.3.0不移动；本次为main后续开发。复现原已验收范围可检出旧标签，复现本次目录应使用本次提交和同提交构建的离线包。


## 全目录真机首轮与同轮动作/表情修正

11:38—11:42共12条表现计划：两次wave_hands、一次heart_both均收到code0/state400；其他计划没有手势。12项表情最终10次受理、2次被priority60拒绝，两次拒绝恰好带有动作。当时实现仅对无手势轮次协调表情，造成同轮动作受理而表情未补发。

用户确认双手比心完整执行并收回、站立稳定；食堂反馈本轮未测试，本轮语音情况也未单独明确确认，不从缺少保存日志推断反馈失败。没有逐轮原话/ASR完整日志，不将这12条回执当作语义判断全通过。

已修正混合计划：动作单次发送后再协调被明确拒绝的原表情，保留priority1、最多两次表情请求、新状态时间戳校验及6秒总期限；无响应不重发、不循环尝试、慢动作响应后不额外延长等待。四个新增回归覆盖调用顺序、动作不重发、未知表情结果不重发、超时期限及第二次拒绝不循环；224项相关测试通过。修正后的混合计划尚待真机复测。
