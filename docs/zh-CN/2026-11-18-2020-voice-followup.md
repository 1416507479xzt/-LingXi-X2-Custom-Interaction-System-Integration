# 20:20真机复测与健康回顾修复

> 历史联调记录：保留当时问题、命令和结果。第三版当前状态见[验收汇总](aimdk-v1-robot-audio.md)，实际部署请使用[当前复现指南](reproduce-on-x2.md)。

## 真机结果

本轮沿用已核对指纹d85bf8d9的版本，Mini、实时ASR、none表现后端；正常Ctrl+C停止。已收到日志，尚未单独确认每轮实际完整播出。

| 输入 | commit后ASR | 回复生成 | commit后TTS首包 |
|---|---:|---:|---:|
| 我今天感觉有点疲惫 | 503ms | 1423ms | 2264ms |
| 有一点影响 | 657ms | 1148ms | 2144ms |
| 我今天脖子疼、腰酸 | 492ms | 1569ms | 2398ms |
| 纠正仅脖子不舒服（旧测试项） | 488ms | 1066ms | 1841ms |
| ASR转写为“现在哪里住” | 633ms | 1791ms | 2712ms |
| 你不记得我哪里不舒服了吗 | 461ms | 1110ms | 1888ms |

本轮没有模型修正/重试日志，也没有空ASR或缺END超时提交；有一段重复BEGIN后取消的片段。样本不同，不能仅凭这些值承诺稳定提速。首包仍不等于说完到扬声器首声，13至15秒的整轮时长包含语音本身。

疲惫及腰颈均有实际建议，短答正确承接。第二轮末尾“随时跟我说”后又追加告别；旧结束语规则支持“和我说”，漏了“跟我说”。

回顾有两个独立问题：第一句识别为住址，因此不能强行改成健康问题；第二句已明确提到哪里不舒服，模型仍要求重说，属于未利用已有用户记录。代码仍把用户原话存入verbatim_turns，没有证据显示内存被清空。先前机器人说“记不清住址”的错误回答可能影响后续，不能拿这句自述当作已无记忆的事实。

## 修复

- 结束语识别补充“随时跟我说”，不再追加第二句。
- 提示回顾优先读取verbatim_turns的用户原话，考虑最新纠正；未告知住址时说明未提供，不能自称忘记。
- 对明确的健康记忆请求，若已有相关用户引述却回答“忘了/记不清/再说”，要求模型在原有有界修正流程中重答。未提供历史、真正的住址问题不强制转换成健康回顾。不预填固定症状答案。
- 新比赛测试使用疲惫→影响→腰颈→缓解办法→回顾；纠正问题不再列为比赛必测，已有纠正功能保留作内部回归。
- 新纯语音文本复测使用完整生活协助资料，以贴近真机上下文。首次复测发现“有什么缓解的办法吗”未命中重复建议豁免，建议被删得只剩条件提醒；补上明确求办法/建议的问法后，保留请求中的建议。普通“一两天”等短答仍执行去重。
- 63项离线回归通过，覆盖跟我说结束语、错误住址回答后的健康回顾、无历史/住址请求边界、明确求缓解时保留建议。

## 修复后真实Mini文本复测

仅是开发电脑的合成文本输入，没有真实收音、TTS、扬声器和音频焦点。六轮生成约0.885至1.750秒，均无模型重试输出；一组样本不能代表稳定性能。未再追加双重告别，明确求缓解保留办法；误识别住址后，明确健康回顾正确使用疲惫、脖子疼和腰酸历史。腰颈及缓解回答仍偏长，需真机听感验证。

```text
agent     [LLM HTTP 526ms]
agent     [LLM 首 token 527ms] 文本
{"greeting_trial": 1, "answer": {"reply": "您好，今天状态怎么样呀？", "emotion": null, "gesture": null, "intent": "greeting", "action": "continue"}}
agent     [LLM HTTP 574ms]
agent     [LLM 首 token 575ms] 文本
{"turn": 1, "user": "我今天感觉有点疲惫。", "answer": {"intent": "health", "action": "followup", "reply": "可以在睡前安排阅读或听音乐这类放松活动，尽量营造舒适的睡眠环境，这种疲惫影响您今天做事了吗？", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 1066, "presentation_backend": "none"}
agent     [LLM HTTP 501ms]
agent     [LLM 首 token 501ms] 文本
{"turn": 2, "user": "有一点影响。", "answer": {"intent": "health", "action": "close", "reply": "已经有点影响了，您多留意自己的状态，有需要随时告诉我。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 885, "presentation_backend": "none"}
agent     [LLM HTTP 657ms]
agent     [LLM 首 token 657ms] 文本
{"turn": 3, "user": "我今天脖子疼，腰酸。", "answer": {"intent": "other", "action": "continue", "reply": "颈部避免长时间保持同一姿势；腰背若没有受伤且活动不会加重疼痛，可在可承受范围内维持日常活动，若近期摔倒或扭伤、疼痛加重，要联系医护。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 1127, "presentation_backend": "none"}
agent     [LLM HTTP 709ms]
agent     [LLM 首 token 710ms] 文本
{"turn": 4, "user": "有什么缓解的办法吗？", "answer": {"intent": "other", "action": "continue", "reply": "颈部避免长时间保持同一姿势，选择较低结实的枕头，睡觉时头部与身体保持同一高度；腰背在没有受伤且活动不加重疼痛的范围内维持日常活动，若近期摔倒或扭伤、疼痛加重，要联系医护。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 1304, "presentation_backend": "none"}
agent     [LLM HTTP 1182ms]
agent     [LLM 首 token 1183ms] 文本
{"turn": 5, "user": "你还记得我现在哪里住吗？", "answer": {"intent": "other", "action": "continue", "reply": "您还没告诉过我您的住址呢。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 1491, "presentation_backend": "none"}
agent     [LLM HTTP 1450ms]
agent     [LLM 首 token 1450ms] 文本
{"turn": 6, "user": "你不记得我哪里不舒服了吗？", "answer": {"intent": "other", "action": "continue", "reply": "您之前说有点疲惫，还有脖子疼、腰酸的情况。", "emotion": null, "gesture": null, "_reminder_transition": {"pending_question": null}}, "generation_ms": 1750, "presentation_backend": "none"}
```

复现：`python scripts/check_care_dialogue_live.py --live --scenario voice_competition --presentation-backend none`。住址误识别是内部健壮性测试，不要求参赛演示时询问住址。

## 下一次真机只测正常比赛流程

1. 你好灵犀。
2. 我今天有点疲惫。
3. 有一点影响。
4. 我腰有点酸，脖子也不舒服。
5. 有什么缓解的办法吗？
6. 你还记得我刚才哪里不舒服吗？

旁人保持安静，每句等实际播出结束。查看实际ASR是否完整；不要求说纠正句，不把住址误识别强行判为正确。仍使用既有部署、预检和日志命令，API Key从.env自动读取。
