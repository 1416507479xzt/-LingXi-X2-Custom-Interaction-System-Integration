# 容器复现与镜像交接（已构建候选，待真机验收）

Dockerfile、Compose配置与启动脚本已纳入Git。镜像包含项目业务代码、预设资料、锁定的Python依赖及ROS 2 Humble基础环境；API Key在运行时单独挂载，食堂记录写入独立卷。**2026-11-18已通过GitHub Actions原生ARM64构建和离线检查，尚未做容器真机验收。**当前开发电脑没有Docker/Podman，本次使用云端构建，没有安装软件或重启电脑。完整结果见[首次构建记录](2026-11-18-container-build.md)。

已完成Bash语法及构建上下文检查；云端实际运行docker build、镜像help入口、Python/ROS/应用导入、缺少SDK时拒绝启动、56项离线测试及docker compose config。目标机器的AimDK SDK、共享库、DDS发现和真实收音播音仍须验收，不能据此宣称一键复现完整机器人效果。

## 与当前机器人版本的关系

手头机器已知AimDK v1.0.0、aarch64、Python 3.10。官方v1.0.0 FAQ说明开发沙盒暂不支持Docker；不能直接在机器人安装Docker或更改原生系统。新版[官方容器开发流程](https://x2-aimdk.agibot.com/zh-cn/latest/quick_start/container_dev.html)使用Podman与对应机器人环境，版本要求以目标机器官方说明为准。它的基础镜像、SDK挂载和宿主共享库处理并不等于通用Docker镜像可直接套用。

目标机器有两个可行前提：官方提供获准的容器运行通道，或者使用获准的外部Linux上位机并正确配置ROS跨机通信。后一条在本项目尚未验收，Windows电脑装Docker也不会自动获得机器人的ROS音频。当前已实测的ZIP方案继续保留。赛方部署权限、固件与SDK版本仍须现场确认。

机器人驱动、固件、ROS通信配置与匹配的AimDK SDK属于设备环境，不在仓库镜像中再分发。镜像内有ROS基础环境，但AimDK消息包和其依赖库需要以目标机器匹配的构建产物接入；如有动态库缺失，使用官方容器基础环境或按官方流程重建SDK，不能绕过预检。语音服务及Mini仍在云端，镜像不包含模型权重，运行需要联网及自备Key。灵创作品、Unity Windows模拟器和真机运控固件也不是这个应用镜像的一部分。

## 镜像构建

以下命令在**安装并已启动Docker的开发电脑/Linux构建机**上执行，工作目录是仓库根目录。ARM64是机器人目标；普通x86电脑需要Docker Buildx的ARM仿真或原生ARM构建节点。

```bash
docker buildx build --platform linux/arm64 --load -t eldercare-x2:dev .
docker run --rm eldercare-x2:dev help
```

默认基础镜像是ROS官方 `ros:humble-ros-base-jammy`。需要联网拉取镜像、Ubuntu系统依赖与锁定Python wheel。它是候选基础环境，并非智元官方镜像；实际SDK兼容性须运行预检。构建时若使用官方许可的本地基础镜像，可加 `--build-arg BASE_IMAGE=实际基础镜像名称`，该基础环境必须兼容Ubuntu22.04/Python3.10/ROS Humble，且仍需核对官方挂载要求。标签可能变化，交付时保存已验收镜像并记录其digest；requirements-lock只固定Python依赖，不能称整个OS依赖已固定。

Git保存构建定义和源码；镜像文件不放进Git。可交付离线镜像文件：

正式发布还应传入 `--build-arg APP_VERSION=已验收版本 --build-arg VCS_REF=对应Git完整提交`，使镜像元数据与源码对应；具体版本约定见[版本管理说明](version-management.md)。

```bash
docker image inspect eldercare-x2:dev --format '{{.Id}}'
docker save -o eldercare-x2-arm64.tar eldercare-x2:dev
# 在另一台获准运行容器的Linux ARM64机器
docker load -i eldercare-x2-arm64.tar
```

这种方式无需重新下载构建依赖，但仍需要运行时云服务网络。目前GitHub Actions提供候选构建、检查和离线镜像附件，不自动发布正式版本或上传GHCR。候选附件保留7天，下载与导入方法见[构建记录](2026-11-18-container-build.md)。使用Podman的官方目标按其镜像导入/导出命令和官方启动方式操作。

## PC2获准容器环境中的预检

以下是Docker运行方式示例，不能作为在v1.0.0沙盒安装或启用Docker的指令。保持镜像与主机同为ARM64。操作者先准备匹配的SDK与本地.env，确认SDK install中绝对路径在容器内仍成立。容器用户默认UID/GID1000；如目标agi用户不同，调整--user并核对卷权限。配置文件保持仅操作者可读。

```bash
# 在允许容器运行的目标Linux终端、仓库根目录
chmod 600 .env
docker compose build
docker compose run --rm robot preflight
```

Compose默认共享host网络与IPC，挂载SDK到 `/home/agi/aimdk`（只读）、.env（只读）和食堂记录卷。宿主SDK路径可用X2_SDK_DIR覆盖，密钥路径可用ELDERCARE_ENV_FILE覆盖，镜像名可用ELDERCARE_IMAGE覆盖。默认命令仅预检，不会自动播放声音、控制动作、设置only_voice或重启原生agent。

目标机器人还可能要求特定RMW、ROS_DOMAIN_ID、DDS XML以及额外共享库。应先按官方容器流程接通ROS图，再用本镜像的预检与探针。启动脚本支持X2_ENV_SETUP读取已挂载的官方环境脚本，但该变量不会自动替你挂载其依赖文件。Docker/Podman网络发现配置未匹配时，仅Python能导入不等于已经接通机器人。

确认依赖预检后，先做只读麦克风测试：

```bash
docker compose run --rm robot mic-probe --duration 30 --stream-id 1
docker compose run --rm robot asr-diagnostic --duration 45 --count 1 --stream-id 1 --wake-hotwords
```

## 显式启动自研Agent

必须先在容器外按已验证的PC2设置、PC3重启流程切换only_voice并确认行为。每次会话明确设置确认变量，不能把它写入镜像或长期凭据文件。真机的Wi-Fi IP不进入镜像或Compose；PC2本地ROS使用host网络，不依赖历史Wi-Fi地址。

```bash
export X2_ONLY_VOICE_CONFIRMED=1
docker compose run --rm robot agent \
  --transport aimdk --enable-robot-audio --competition-mode \
  --health-semantic model --llm-model doubao-seed-2-0-mini-260428 \
  --presentation-backend none --vad-idle-seconds 1.5 --aimdk-streaming-asr \
  --dining-feedback-records /var/lib/eldercare/dining_feedback.jsonl
unset X2_ONLY_VOICE_CONFIRMED
```

若需要灵犀热词，可在本地.env增加 `DOUBAO_ASR_HOTWORDS=["灵犀"]`。Ctrl+C停止容器内程序后，仍须按官方流程恢复normal并验证原生语音。容器退出本身不会恢复机器人模式。

食堂反馈网页可在另一个终端使用同一记录卷启动：`docker compose run --rm robot dashboard --port 8765`。它默认仅在目标机器本机地址监听；Windows远程查看仍需SSH端口转发。不要为展示网页关闭访问边界。

## 验收与交接清单

1. 在可用构建机完成ARM64镜像构建，记录Git提交、基础镜像digest、成品镜像digest。
2. 确认没有把.env、录音、旧反馈、SSH资料放入镜像。Dockerfile只COPY列明的源码与静态资料；.dockerignore使用允许清单。
3. 在目标机器获准的容器环境确认SDK与依赖库可用、预检通过、ROS话题/服务发现正常。
4. 验证麦克风、ASR、焦点、扬声器、Mini上下文、环节一二四与食堂持久记录；验证Ctrl+C及normal恢复。
5. 完成后再发布镜像，向后来同学交付镜像、Git源码版本、操作手册、SDK获取方式及自备Key配置说明。
