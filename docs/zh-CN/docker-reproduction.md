# 当前应用镜像：构建、交付和真机验收

目标是把同一提交的全部应用代码和依赖封装好，在兼容、获准的PC2容器环境中导入镜像，配置自己的Key和设备接口后运行完整语音、表情、动作及食堂反馈。当前真机ZIP仍保留为已实测基线；容器真机效果必须另行验收。

## 官方运行路径

[灵犀X2官方容器开发文档](https://x2-aimdk.agibot.com/zh-cn/latest/quick_start/container_dev.html)适用于X2 Ultra及Ultra(new version)，使用Podman，挂载机载SDK、ROS、共享库和DDS。官方页面说明v1.1.0是过渡版本，v1.2.0起要求容器开发。它不表示手头AimDK v1.0.0的机器人已具备同样环境；不自动安装Docker、升级固件、清理SDK或改PC1。

应用镜像默认基于ROS Humble/Ubuntu22.04，目标ARM64/Python3.10。设备固件、原生SDK及动态库、容器权限和DDS通信仍来自获准的目标环境。机器人自己的SDK预编译产物是否兼容容器，要通过预检和实测确认；不是任意机器人导入就可运行。

## 后续优化如何进入镜像

- main的x2_agent、scripts、公开data、tests、入口、skills、锁定依赖和容器配置改变时自动触发[ARM64应用镜像工作流](../../.github/workflows/container-candidate.yml)，也可手动触发。
- 全部运行Python模块、脚本、公开资料、依赖清单和容器Shell脚本生成SHA256清单，并对照同次Git提交；缺文件、旧文件或意外额外文件均拒绝通过。
- 云端ARM64构建后核查导入、缺SDK拒绝启动、业务及容器回归、Compose配置、Shell语法，再生成交付附件并尝试发布GHCR。
- 镜像名称为 `ghcr.io/1416507479xzt/eldercare-x2`；成功发布后 `sha-完整提交号` 对应固定源码，`latest`指最近成功构建。首次发布结果以Actions为准；包访问权限由GitHub管理，不自动改变可见性。
- 原本保存的镜像不会自行获得未来代码；每次优化进入新镜像。更新必须停止旧Agent、领取新镜像并导入，私有配置和state保留。回滚使用此前提交的镜像及交付文件，不能移动旧版本标签冒充更新。

旧的758b377候选只有当时的代码，不能代表当前优化。历史构建记录保留在[首次容器构建](2026-11-18-container-build.md)。

## 下载与导入

从本次成功Actions运行的Artifacts下载完整附件，含镜像tar.gz、校验、image.env、源码清单、启动脚本、模板和说明；附件保留7天。若镜像已成功推送，也可登录获准的镜像仓库拉取提交号标签。GitHub包可能默认私有，不能假定其他同学可匿名拉取；离线附件可由仓库所有者另行保存和交接。

解压内容复制到PC2 `/home/agi/eldercare-container/`，按[随包快速指南](../../docker/CONTAINER-QUICKSTART.md)配置Key及设备条件。在该目录：

```bash
bash run.sh load
bash run.sh dependencies
bash run.sh preflight
```

load先校验再导入，不安装Python包。运行器优先使用已存在的Podman，也支持已获准的Docker；可用CONTAINER_ENGINE指定。SDK、宿主ROS/共享库和DDS只读挂载，记录写入交付目录state；不开特权模式、不映射原始设备、不改原生服务。

正式镜像交付建议记录成品digest和源码提交，并保存附件。Python依赖锁定不意味着基础镜像标签及apt仓库永久不变；只有保留的已构建镜像及校验值可作为完全相同的镜像副本。

## 运行当前完整效果

先按README在容器外切换only_voice、PC3重启并确认原生行为，操作者确认稳定站立。PC2交付目录执行：

```bash
export X2_ONLY_VOICE_CONFIRMED=1
bash run.sh full-agent
```

full-agent包含当前Mini、音频、表情、动作、流式ASR、缺END收尾、食堂保存和日志参数。不是只运行旧的纯语音配置。它不会设置机器人模式；未确认时拒绝启动。

电脑在解压目录/仓库根目录执行：

```powershell
.\open_container_feedback.cmd
```

输入当前Wi-Fi IP和SSH密码。容器网页与容器Agent共用 `state/dining_feedback.jsonl`，不读取旧ZIP目录。网页只用于查看；不打开仍可保存。Ctrl+C停止Agent，`unset X2_ONLY_VOICE_CONFIRMED`，需要原生交互时按README恢复normal。

## Compose替代入口

交付默认使用run.sh，无需Compose或源码构建。仓库开发者在已获准环境可使用 `docker compose run --rm robot preflight`、`docker compose --profile interaction run --rm interaction` 和 `docker compose --profile dashboard run --rm dashboard`。Compose使用命名卷records；run.sh使用state绑定目录，两者不自动共享记录，选定一种后不要混用。Compose默认SDK路径、.env、ROS_DOMAIN_ID可覆盖，特殊官方DDS/共享库环境优先用run.sh并现场核对。

## 验收门槛

镜像构建通过后仍需在目标PC2逐项验收：ROS图发现、收音、ASR、音频焦点、完整播音、Mini上下文、表情、已核对动作的完整收回与站立、食堂确认和网页、Ctrl+C、normal恢复。逐项记录镜像digest、源码提交、SDK/固件、运行器及设备结果。没有容器真机证据前，不称“复制镜像已达到全部效果”。
