# 完整交互应用镜像构建结果 — 2026-11-20

## 已完成

- 源码提交：`1ba57901e60c2ab03fb5176577f1f2fc0da55a8a`，包含此前全部语音、对话、表情、动作及食堂反馈优化。
- [ARM64云端构建](https://github.com/1416507479xzt/-X2-/actions/runs/44667095940)全部步骤成功：镜像构建、启动/导入、逐文件源码摘要对照、缺SDK时退出22、234项离线回归、Compose及Bash语法、镜像导出、附件及GHCR发布。
- 镜像：`ghcr.io/1416507479xzt/eldercare-x2:sha-1ba57901e60c2ab03fb5176577f1f2fc0da55a8a`。
- 本次成品digest：`sha256:a3732bf1df818b2b63009c1d31d564af196bd02850b304da9def906fb15fad60`；本轮发布时latest指向同一digest。日后latest会随成功构建变化，复现以提交号和digest为准。
- [离线交付附件](https://github.com/1416507479xzt/-X2-/actions/runs/44667095940/artifacts/14597997167)：288137926字节，约275MiB，保留至2026-11-27 11:21:51（北京时间）。附件访问需要相应仓库权限；请另行保存交接，不依赖临时附件永久可用。

## 交付内容

镜像tar.gz、SHA256SUMS、source-commit.txt、源码摘要清单、image-inspect.json、VALIDATION.txt、image.env、run.sh、私有配置模板、操作说明及电脑容器网页入口。

full-agent以当前已实测ZIP参数启动语音、Mini、表情、动作、流式ASR、缺END收尾及食堂保存；日志和记录放在交付目录state中，镜像替换不删除它们。电脑网页入口与Agent读取同一份state记录，不误读旧ZIP路径。实际密钥和真实记录不在镜像内。

运行Python代码、脚本、公开资料、依赖或容器配置改变时，main自动触发新构建。源码摘要与该次提交逐文件一致才通过，之后才发布镜像；旧镜像不会自行更新为未来代码。

## 仍待完成

这是云端构建和离线业务回归结果，未在目标PC2容器里验证SDK动态库、DDS发现、真实收音/播音、表情、动作或反馈闭环。不能将镜像构建成功写成“导入即已获得全部物理效果”。

按[官方容器开发说明](https://x2-aimdk.agibot.com/zh-cn/latest/quick_start/container_dev.html)，目标X2 Ultra须具备获准Podman环境及设备SDK/ROS/DDS挂载；手头历史AimDK v1.0.0的运行器现状仍需只读核对。没有安装容器引擎、升级机器人、修改PC1或切换当前原生交互模式。

在目标机器满足条件后，按[交付操作](../../docker/CONTAINER-QUICKSTART.md)导入、预检，再完成[容器验收清单](docker-reproduction.md#验收门槛)，才可标记“跨设备容器完整效果复现通过”。
