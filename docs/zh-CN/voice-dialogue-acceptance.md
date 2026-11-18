# 真机纯语音连续对话验收

固定Mini和none表现后端，使用ZIP部署。Key由机上.env读取，不保存录音。日志含转写和回答，仅用虚构对话测试。

比赛必测流程不包含纠正问题；保留相关内部回归能力。第三版当前结果见[最新真机闭环记录](2026-11-18-playback-and-feedback-path.md)及[验收状态](aimdk-v1-robot-audio.md)。用户确认最新语音效果良好，食堂网页实时更新；当前相关离线回归164项通过。下节为早期优化过程，不是当前验收结论。

## 早期优化与历史文本样本

- 修复已有“有任何不适请及时告诉我”“及时和我说”时仍追加第二句关怀收尾。
- 增加未提及腰颈部位的建议校验，要求模型按用户实际引述修正；已有用户提到对应部位则允许建议。这是针对本次失败的窄范围检查，不代表全面事实校验。
- 文本测试支持--presentation-backend none及每轮generation_ms，使能力配置与当前真机一致。
- 60项离线测试通过。真实Mini五轮文本复测中，疲惫第二轮未再引入腰颈建议；第三轮新腰颈求助仍两次触发外伤条件校验后兜底，生成2.858秒，仍需优化。最后两轮生成约0.968/2.114秒，均不含语音链路。
- [原始样本](2026-11-18-voice-dialogue-text-samples.md)保留错误及修正后对话。后补的结束语识别尚待真机复测，不能宣称全部稳定。

文本复现命令（会调用现有云端账户，不连接机器人）：

```powershell
python scripts/check_care_dialogue_live.py --live --scenario regression_stage1_latest --presentation-backend none
```

## 更新机器人

Windows PowerShell仓库根目录，每次核对机器人当前Wi-Fi IP。不要把两条命令粘成同一行。

```powershell
python scripts/build_robot_bundle.py
$RobotIp = (Read-Host '输入机器人当前 Wi-Fi IP').Trim()
if ([string]::IsNullOrWhiteSpace($RobotIp)) { throw 'IP不能为空' }
ssh "agi@${RobotIp}" 'mkdir -p /home/agi/eldercare-x2'
scp -O .\dist\eldercare_x2_aarch64_py310.zip "agi@${RobotIp}:/home/agi/eldercare-x2/"
ssh "agi@${RobotIp}"
```

进入机器人PC2后：

```bash
cd /home/agi/eldercare-x2
python3 -m zipfile -e eldercare_x2_aarch64_py310.zip .
cd eldercare_x2
source /home/agi/aimdk/install/local_setup.bash
python3 scripts/robot_preflight.py
sha256sum x2_agent/model_dialogue.py
```

先停止旧自研Agent，再确认原生normal/only_voice实际状态。若原生仍回答，按[模式切换与恢复说明](aimdk-v1-robot-audio.md)在PC2设置only_voice、PC3重启agent并核对原生停止回答。预检不代表已完成模式切换，不能直接设置确认变量跳过核对。

## 启动并记录

仅在已确认only_voice后，于PC2项目目录执行：

```bash
mkdir -p logs
SESSION_ID=$(date +%Y%m%d_%H%M%S)
export DOUBAO_ASR_HOTWORDS='["灵犀"]'
export X2_ONLY_VOICE_CONFIRMED=1
python3 scripts/run_robot_agent.py --transport aimdk --enable-robot-audio --competition-mode --health-semantic model --llm-model doubao-seed-2-0-mini-260428 --presentation-backend none --vad-idle-seconds 1.5 --aimdk-streaming-asr --log-file "logs/voice_${SESSION_ID}.log" --metrics-file "logs/voice_${SESSION_ID}_metrics.json" --dining-feedback-records data/dining_feedback.jsonl
unset X2_ONLY_VOICE_CONFIRMED DOUBAO_ASR_HOTWORDS
```

最后一行在Ctrl+C停止后执行。一次只运行一个Agent；现阶段不支持语音打断，等机器人说完再说下一句。反馈与网页统一使用 data/dining_feedback.jsonl；核对本轮新增记录，不删改旧记录。独立测试时须让 Agent 和网页同时指向另一文件。结束后如需原生对话，按上述说明恢复normal并验证实际回答。

## 连续测试

先说“你好灵犀”，听到问候后开始。每句等实际回答结束，若模型询问不同问题，正常回答并记录真实话语，不强套短答。

| 次序 | 合成输入 | 判据 |
|---|---|---|
| 1 | 我今天感觉有点疲惫。 | 有实用提示，不只有追问，不引入腰颈不适 |
| 2 | 有一点影响日常活动。 | 不夸大、不重复作息建议、不重复告别 |
| 3 | 我腰有点酸，脖子也不舒服。 | 能接住新求助，给相关提示，不追问外伤史 |
| 4 | 腰比刚才酸一点，脖子没有变化。 | 分清部位和程度 |
| 5 | 有什么缓解的办法吗？ | 明确求办法时保留适用建议，不只念就医提醒 |
| 6 | 你还记得我刚才哪里不舒服吗？ | 按用户自述回顾，不要求重说 |
| 7 | 降压药怎么吃，有什么注意事项？ | 类别咨询不强求具体药名，不编造个人剂量 |
| 8 | 今天有什么提醒？ | 使用当前配置和时间，无演示或资料话术 |
| 9 | 食堂今天的汤太咸了，希望清淡一点。 | 正确提取意见，未确认不谎报保存 |
| 10 | 对，就这样记录。 | 对应当时确认问题，正确保存一次 |

记录真实输入、ASR转写、完整播出、误唤醒/漏听、重复追问、模型修正次数和每轮耗时。第9/10轮会生成合成反馈；查看网页时必须读取 Agent 实际写入的同一文件。

ASR耗时从commit后计；TTS首包是云端音频到达，不是扬声器首声。缺END还可能增加1.5秒停收等待；焦点请求和播放缓冲也有开销。不得把commit到TTS首包当成说完到听见声音。指标JSON提供汇总，单轮定位结合日志，有条件用外部秒表记录实际听感等待。
