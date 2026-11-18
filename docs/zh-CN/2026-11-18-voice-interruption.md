# 17:17真机连续对话：串话、重试和回顾

## 本轮事实

已部署8b3c8ea对应包，机上model_dialogue.py指纹a90f6eb7e47e906651e034e88d876ec28018176fd15b5d6140a1d03d8a9c5632。AimDK v1.0.0、麦流1、BEGIN起实时ASR、Mini、none表现后端、缺END停收1.5秒。原生交互此前不再回答。日志最后先显示Agent已停止，随后SSH连接被reset；不能把退出后的网络断开当成对话中崩溃。

| 输入/事件 | commit后ASR | 回复生成 | commit后TTS首包 | 结论 |
|---|---:|---:|---:|---|
| 今天累死我了 | 794ms | 1660ms | 2726ms | 保留生活提示和影响追问，无模型重试 |
| 现场功率聊天 | 674ms | 1472ms | 2422ms | 用户确认是旁人真实聊天，并非ASR错识；当前会收入同一会话 |
| 有一点影响 | 593ms | 2322ms | 3230ms | 重复问句复核后仍追问影响指哪方面，没有接上原健康问题 |
| 我腰疼，脖子酸 | 325ms | 2538ms | 3159ms | 外伤边界检查导致第二次模型请求 |
| 纠正为腰不酸、仅脖子不舒服 | 362ms | 2485ms | 3145ms | 最终只给颈部建议，但又有一次外伤边界重试 |
| 回顾请求仅转写“你还记得我现在拿” | 415ms | 2070ms | 2749ms | 输入不完整，机器人澄清；无法据此判定完整回顾功能通过或失败 |

三段ASR为空、两次缺END停收恢复；这些现象不能仅凭日志断言麦克风损坏、用户离得远或某一句一定被截断。日志可见音频下发，仍需要用户确认真实听到的完整程度。疲惫整轮10.855秒、腰颈整轮18.077秒包含生成和语音时长，不是开始回答前一直沉默。TTS首包也不是扬声器实际首声。

## 代码优化

1. 提示模型用最近语义匹配的问题承接短答，考虑中间无关插话，不只绑定最后一个问号；无关话语澄清优先chat以保留开场问询，但本次复测分类仍有波动。
2. 腰颈建议首次生成时就保留既有资料要求的外伤条件边界；明确这些说明只针对已提及腰颈问题，不套进疲惫回答。保留现有安全校验，未为减少重试而删除检查。
3. 普通回答倾向1到2句、70字内，必要安全内容允许更长，无硬截断。
4. none能力配置在普通和复核提示末尾明确要求emotion/gesture为null，减少无效表现选择。
5. 新增voice_interruption合成测试场景，复现疲惫→无关功率插话→短答→腰颈→纠正→完整回顾；没有增加声纹或说话人识别，不能宣称已防旁人串话。

## 最终提示版本的真实Mini文本样本

以下为开发电脑合成输入，不是本轮真实老人录音，不含ASR/TTS/扬声器。两次试跑有模型和网络波动，不能与真机耗时直接算提速百分比。最终一轮短答能承接疲惫，纠正后完整回顾正确；腰颈仍触发一次重试。上一轮开场HTTP曾等待3.417秒，本轮605ms，说明网络/服务延迟仍有波动。

```text
模型输出失败 reason=health_injury_unconfirmed_advice output_chars=142 elapsed_ms=1000 history_turns=4 health_quotes=1
agent     [LLM HTTP 605ms]
agent     [LLM 首 token 605ms] 文本
{"greeting_trial": 1, "answer": {"reply": "您好，今天过得怎么样呀？", "emotion": null, "gesture": null, "intent": "greeting", "action": "continue"}}
agent     [LLM HTTP 642ms]
agent     [LLM 首 token 642ms] 文本
{"turn": 1, "user": "我今天感觉有点疲惫。", "answer": {"intent": "health", "action": "followup", "reply": "可以试试睡前安排阅读或听音乐这类放松活动，帮您舒缓疲惫感，这种疲惫影响您今天做事了吗？", "emotion": null, "gesture": null}, "generation_ms": 998, "presentation_backend": "none"}
agent     [LLM HTTP 1309ms]
agent     [LLM 首 token 1310ms] 文本
{"turn": 2, "user": "这个不是67瓦，我让你用67瓦。", "answer": {"intent": "other", "action": "continue", "reply": "您是想调整设备功率相关设置吗？可以跟我说说具体情况。", "emotion": null, "gesture": null}, "generation_ms": 1740, "presentation_backend": "none"}
agent     [LLM HTTP 511ms]
agent     [LLM 首 token 512ms] 文本
{"turn": 3, "user": "有一点影响。", "answer": {"intent": "other", "action": "continue", "reply": "您今天做事受疲惫影响，要是这种情况持续不缓解，您可以咨询医护人员。", "emotion": null, "gesture": null}, "generation_ms": 897, "presentation_backend": "none"}
agent     [LLM HTTP 534ms]
agent     [LLM 首 token 534ms] 文本
agent     [LLM HTTP 422ms]
agent     [LLM 首 token 423ms] 文本
{"turn": 4, "user": "我腰疼，脖子酸。", "answer": {"intent": "other", "action": "continue", "reply": "颈部避免长时间保持同一姿势；腰背若没有受伤且活动不会加重疼痛，可在可承受范围内维持日常活动、避免久卧。若近期摔倒或扭伤、疼痛迅速加重，应联系医护。", "emotion": null, "gesture": null}, "generation_ms": 1998, "presentation_backend": "none"}
agent     [LLM HTTP 394ms]
agent     [LLM 首 token 394ms] 文本
{"turn": 5, "user": "不对，腰已经不酸了，现在只是脖子不舒服。", "answer": {"intent": "other", "action": "continue", "reply": "颈部避免长时间保持同一姿势，若近期摔倒或扭伤、疼痛迅速加重，应联系医护。", "emotion": null, "gesture": null}, "generation_ms": 720, "presentation_backend": "none"}
agent     [LLM HTTP 1501ms]
agent     [LLM 首 token 1501ms] 文本
{"turn": 6, "user": "你还记得我现在哪里不舒服吗？", "answer": {"intent": "recall", "action": "continue", "reply": "您现在是脖子不舒服，之前说过腰疼现在已经不酸了。", "emotion": null, "gesture": null}, "generation_ms": 1879, "presentation_backend": "none"}
```

## 下一次真机测试

保持模型、距离、音量、网络和1.5秒停收设置相近，先在旁人安静时测试疲惫→有一点影响→腰颈→纠正→完整回顾，每句等实际播报结束。不要让旁人再次说功率话语来代替安静基准。保留实际原话、ASR、修正次数和真实播出反馈；特别核对完整回顾那句话是否收到完整音频。

若安静基准仍有漏词，再对同一测试句做只读ASR诊断，不通过缩短停收、任意拼接VAD片段或把背景话语强行识别成测试句解决。说话人选择/声源方向过滤须先确认官方可用接口和实际能力，另行设计与验收。
