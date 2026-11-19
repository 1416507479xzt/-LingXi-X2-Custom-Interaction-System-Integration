# 2026-11-19：表情与动作接入核对

本轮在第三版纯语音基线上开展。机器人当前由用户确认为零力矩状态，暂不发送肢体动作，不由程序切换运动模式。Wi-Fi IP由操作者每次确认，不写入配置。

## 已取得的机载证据

PC2 source AimDK 后，ROS 图可见 PlayEmoji、SetMcPresetMotion 和 GetMcAction 服务。

PlayEmoji 请求含 header、emotion_id、mode、priority；响应含 CommonResponse header、bool success、string message。机载枚举明确 happy=90、neutral=10、sympathy=120；mode=1为单次。下一步先低优先级单次播放 happy，观察屏幕并核对响应；目前尚未实际验证播放。

SetMcPresetMotion 请求含 RequestHeader header、area.value、motion.value、interrupt、ani_path、play_timestamp；响应为 response.header.code、task_id、state.value。机载枚举包含 WAVE_HAND=1002、RAISE_HAND=1001、RIGHT_HAND=2、LEFT_HAND=1。当前仓库目录还包含按1.1文档准备的若干编号，机载枚举并未逐项印证，不得直接开放整个目录。服务请求被受理也不等于动作完成。

GetMcAction 在 ros2 interface show 展开 McActionInfo 时抛出 InvalidResourceName: //，报错指向生成IDL的注释行解析。已知只读命令展示失败，不能据此断定Python类型或ROS服务不可用；待用GetMcAction.Response().info的运行时字段核对，后续再只读查询运动模式。不要为解决展示报错修改或重编译机器人原生SDK。

## 分阶段验证

1. 保持当前运动模式，先验证一次屏幕表情；无模型调用、无肢体动作、无音频焦点操作。
2. 核对GetMcAction Python字段及实际模式响应，补齐匹配1.0.0的适配与失败处理。
3. 先使对话支持仅表情的能力范围，验证不会对语音或食堂记录产生回退，再逐项验收动作。
4. 动作测试前由现场人员按机器人既有操作流程准备稳定站立及空间条件；程序不从零力矩自动切换，也不在服务超时后盲目重复发送动作。

## 当前结论

这是接口核对记录，不是表情/动作验收通过记录。第三版语音与食堂闭环的既有验收保持有效，v0.3.0标签不变。后续实测须另记实际显示、动作结果、服务响应及对语音延迟的影响。
