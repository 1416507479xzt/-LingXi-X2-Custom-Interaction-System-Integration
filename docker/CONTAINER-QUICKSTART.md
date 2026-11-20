# ARM64镜像交付包

本包封装对应Git提交的应用源码、锁定Python依赖和ROS Humble基础环境；不是机器人固件。只在官方允许的PC2容器环境使用，优先Podman，不在机器人上自行安装Docker或更改原生环境。

## 一次性交接

1. 下载Actions成功构建的完整附件并解压，保留所有文件。`source-commit.txt`记录源码提交，`source-manifest.json`记录全部运行源码摘要，`image.env`指定同一提交的镜像。
2. 复制解压内容到PC2 `/home/agi/eldercare-container/`。镜像内没有Key，在此目录创建私有 `.env`，参考 `.env.example`，填入自己的两把Key；执行 `chmod 600 .env`。
3. 确认机器人已具备官方允许的Podman/Docker、匹配SDK及DDS配置。按机载版本的官方容器说明准备SDK，不删除或重编现有SDK来尝试解决兼容性问题。
4. 在该目录执行：

```bash
bash run.sh load
bash run.sh dependencies
bash run.sh preflight
```

load先校验再导入镜像，不下载Python包。默认SDK位置 `/home/agi/aimdk`，可用 `X2_SDK_DIR`覆盖；默认挂载已有ROS、共享库和官方DDS配置，只读接入。若目标机器使用其他路径或策略，需要现场适配并验收。预检不等于已接通ROS图，更不等于真实声音和动作已完成。

## 每次启动完整交互

先按仓库README完成only_voice及PC3原生agent重启、实际行为确认，并让机器人稳定站立。PC2目录 `/home/agi/eldercare-container`执行：

```bash
export X2_ONLY_VOICE_CONFIRMED=1
bash run.sh full-agent
```

该入口等价于当前真机的语音、Mini对话、表情、动作、流式ASR、缺END收尾和食堂保存参数。默认保留日志；没有自动切换机器人模式。运行后先说“你好灵犀”。Ctrl+C退出后执行 `unset X2_ONLY_VOICE_CONFIRMED`；恢复原生normal仍按仓库README执行。

## 电脑查看反馈表

保持Agent窗口运行。在电脑解压目录或仓库根目录Windows PowerShell执行：

```powershell
.\open_container_feedback.cmd
```

输入当前Wi-Fi IP和SSH密码，保持新SSH窗口。容器专用入口会调用PC2上述固定交付目录的 `run.sh dashboard`，与Agent读取相同的 `state/dining_feedback.jsonl`。镜像中的只读默认资料与这份可写记录分开；不启动网页仍可保存，删除/替换镜像不删除交付目录state。

旧ZIP部署的记录在另一个目录，不自动迁移或合并。若需要保留历史，先停止两套Agent并备份，再人工核对迁移；不要同时运行两套交互。

## 更新

每次应用运行源码、脚本、公开资料或锁定依赖更新，main自动构建新镜像；成功后发布提交号标签及latest。已有本地镜像不会自行变化。领取新附件，保留自己的 `.env`、`state/`，停止旧Agent后校验并load；不要覆盖旧数据。需要回滚时使用上一份附件的image.env与镜像，数据结构兼容性另行核对。

镜像不能包含尚未开发的未来代码，也不包含云端模型权重、个人Key及机器人SDK/固件。后续优化进入各自的新镜像；交付包中的VALIDATION.txt是该次构建验证范围，容器真机验收未完成前不得标为全部效果已复现。
