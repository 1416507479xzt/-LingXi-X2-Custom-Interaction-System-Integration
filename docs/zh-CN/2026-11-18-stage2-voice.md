# 环节二：类别用药咨询和提醒连续对话

## 前置反馈

用户在部署d67ff28对应优化后反馈“检测下来没什么问题”，并要求进入下一步。将其记录为真机主观验收反馈；未附新日志，不新增具体耗时或声学指标，也不推断环节二四已验收。表情动作保持none，继续Mini。

## 当前环节二范围

预设每天08:00核对用药、09:30复诊提醒、10:00喝水、15:00确认社区活动安排。运行时按真实当前时间查询；这些是项目预设事项，不是机器人自行诊断、处方或医院预约。复诊不提示携带资料。用药按类别提供既有教育资料，不强求具体药名，不凭类别编造个人每次片数。服药时间和每次用量让老人对照本人处方或药盒说明，不要求老人逐项报出。

本轮测试的是语音查询、咨询和短答承接，现有health_reminders模块没有后台定时调度器。不能把“查询预设提醒成功”写成“到点自主提醒已验收”，主动定时触发须另行设计和验证。

## 发现与修复

第一组真实Mini十轮文本测试，类别咨询、全天/下一项、已吃过药承接可用，但“喝水提醒是几点”连续两次选错结构化标记，最终落到泛化兜底。

新增normalize_explicit_water_time：只针对完整的、单一明确喝水时间问句，将已有提醒查询标记规范成REMINDER_WATER。实际时间仍由配置及当前时钟计算，不预填10点，不处理修改/取消/已喝水确认/多主题问题，不执行任何写入。原有错误检测与模型重试保留。新增用例验证选错复诊标记时一次请求即可得到配置中的喝水时间，同时排除修改、多主题、完成确认和用药问题。

原55项环节二相关回归扩为57项，加上纯语音63项，共120项通过，离线包已重新生成。

## 真实Mini复测

新增stage2_voice场景，使用none能力、完整生活协助资料、合成固定时钟2026-11-18 09:45（Asia/Shanghai）；固定时钟仅用于此文本测试，未改机器人时钟或真实运行配置。没有机器人连接、音频播放、计时器或持久写入。

修复后十轮均得到非空回答。喝水时间查询成功，服药自述在当前会话可承接，复诊回复不要求准备资料。药名记不清时没有强制追问具体药名。首轮药品回答有一次medicine_dose_not_authorized校验后修正，总生成2.817秒；不能称所有轮次无重试。两次降压药回答仍偏长且重复，待真机听感和后续优化；生成时间不含ASR/TTS/扬声器。

```text
agent     [LLM HTTP 538ms]
agent     [LLM 首 token 538ms] 文本
{"greeting_trial": 1, "answer": {"reply": "您好，今天过得怎么样呀？", "emotion": null, "gesture": null, "intent": "greeting", "action": "continue"}}
Synthetic clock: 2026-11-18 09:45 Asia/Shanghai; no scheduler or robot writes
agent     [LLM HTTP 544ms]
agent     [LLM 首 token 544ms] 文本
agent     [LLM HTTP 1306ms]
agent     [LLM 首 token 1306ms] 文本
{"turn": 1, "user": "降压药怎么吃，有什么注意事项？", "answer": {"intent": "other", "action": "continue", "reply": "降压药需按照本人处方规定的时间、频次和剂量规律服用，不要因为一次血压正常就自行停药或加减量；服后明显头晕应联系医护核对。请对照本人处方或药盒说明确认服用时间和每次用量。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 2817, "presentation_backend": "none"}
agent     [LLM HTTP 1221ms]
agent     [LLM 首 token 1221ms] 文本
{"turn": 2, "user": "药名记不清了，你就说一般怎么吃。", "answer": {"intent": "other", "action": "continue", "reply": "降压药需按照本人处方规定的时间、频次和剂量规律服用，不要因为一次血压正常就自行停药或加减量；服后明显头晕应联系医护核对。请对照本人处方或药盒说明确认服用时间和每次用量。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 1729, "presentation_backend": "none"}
agent     [LLM HTTP 1193ms]
agent     [LLM 首 token 1193ms] 文本
{"turn": 3, "user": "感冒药有什么注意事项？", "answer": {"intent": "other", "action": "continue", "reply": "部分鼻塞类的感冒药成分不适合高血压、心脏病等人群，用前请药师核对；同时吃其他药时也要先问药师，避免成分冲突。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 1821, "presentation_backend": "none"}
agent     [LLM HTTP 726ms]
agent     [LLM 首 token 727ms] 文本
{"turn": 4, "user": "今天有什么提醒？", "answer": {"intent": "reminder", "action": "continue", "reply": "您今天有这些提醒：8点整核对用药安排，9点30分复诊，10点整喝水，15点整确认社区活动安排。有些时间已经过了，您是否做过还需要确认。最近一项还有15分钟。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 1156, "presentation_backend": "none"}
agent     [LLM HTTP 825ms]
agent     [LLM 首 token 825ms] 文本
{"turn": 5, "user": "下一项是几点？", "answer": {"intent": "reminder", "action": "continue", "reply": "下一项是今天10点整喝水。还有15分钟。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 1123, "presentation_backend": "none"}
agent     [LLM HTTP 820ms]
agent     [LLM 首 token 820ms] 文本
{"turn": 6, "user": "该吃药了吗？", "answer": {"intent": "reminder", "action": "continue", "reply": "今天的用药提醒时间是今天8点整。这只是预设时间，实际服药请按医嘱。现在已经过了这个时间，您今天已经吃过药了吗？", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": {"kind": "medication_taken", "occurrence_id": "demo-medication@2026-11-18"}}}, "generation_ms": 1743, "presentation_backend": "none"}
agent     [LLM HTTP 557ms]
agent     [LLM 首 token 558ms] 文本
{"turn": 7, "user": "我已经吃过了。", "answer": {"intent": "reminder", "action": "continue", "reply": "既然您说已经服过这次药，就不要因为这条提醒再重复服用。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null, "self_report": {"occurrence_id": "demo-medication@2026-11-18", "status": "taken"}}}, "generation_ms": 1218, "presentation_backend": "none"}
agent     [LLM HTTP 1576ms]
agent     [LLM 首 token 1577ms] 文本
{"turn": 8, "user": "那我现在还要再吃一次吗？", "answer": {"intent": "reminder", "action": "continue", "reply": "您刚才说今天这次药已经服过，不要因为提醒重复服用。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 1700, "presentation_backend": "none"}
agent     [LLM HTTP 618ms]
agent     [LLM 首 token 618ms] 文本
{"turn": 9, "user": "我什么时候复诊？", "answer": {"intent": "reminder", "action": "continue", "reply": "今天的复诊提醒时间是今天9点30分。这个时间已经过了，是否完成还需要您确认。这只是预设提醒，具体复诊日期请以医院安排为准。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 841, "presentation_backend": "none"}
agent     [LLM HTTP 751ms]
agent     [LLM 首 token 751ms] 文本
{"turn": 10, "user": "喝水提醒是几点？", "answer": {"intent": "reminder", "action": "continue", "reply": "今天的喝水提醒时间是今天10点整。还没到这个时间。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 998, "presentation_backend": "none"}
```

复现命令（使用现有云端账户，有调用费用）：

```powershell
python scripts/check_care_dialogue_live.py --live --scenario stage2_voice --presentation-backend none
```

## 真机测试步骤

沿用电脑上传ZIP、PC2解压、source SDK、预检和原启动命令，API Key自动读取.env。only_voice实际行为需保持确认，旧自研Agent先停止。没有更换模型或启用表情动作，不需要改原生服务。

先说“你好灵犀”，按实际问题回答开场，然后每句等播报结束：

1. 降压药怎么吃，有什么注意事项？
2. 药名记不清了，你就说一般怎么吃。
3. 今天有什么提醒？
4. 下一项是几点？
5. 该吃药了吗？
6. 若机器人询问本次是否已服用，使用合成测试回答“我已经吃过了”。
7. 那我现在还要再吃一次吗？
8. 我什么时候复诊？
9. 喝水提醒是几点？

服药短答以机器人当时提问为准，不把合成测试当成真实服药指导。提醒日期/下一项以机器人实际时钟为准，夜间下一项可能在次日，不能拿文本测试的09:45结果当真机唯一正确答案。检查无演示/资料话术、无具体药名追问、无编造个人剂量、无重复服药引导、时刻准确、复诊不提准备资料、实际语音完整和耗时。需要本次日志及用户听感才能判定真机环节二效果。
