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

## 本机交付与PC2只读核对

完整附件已下载并解压到开发电脑仓库 `dist/eldercare_container_1ba5790/`，ZIP CRC、交付包SHA256SUMS均通过；另核对了镜像归档内存在上述提交号标签。该目录包含镜像和运行文件，不包含下载分块、个人Key或实际反馈，适合后续获准时复制。生成的镜像文件不进入Git。

用户在PC2回传的只读结果：

| 项目 | 实际输出 |
|---|---|
| SDK | `aimdk v1.0.0-ga424add` |
| Podman | command not found |
| Docker客户端 | `/usr/bin/docker`，27.5.1（Ubuntu22.04构建） |
| Docker上下文 | default，`unix:///var/run/docker.sock` |
| Docker连接 | Cannot connect to the Docker daemon |
| Docker服务 | LoadState=masked，ActiveState=inactive，UnitFileState=masked，FragmentPath=/etc/systemd/system/docker.service |
| dockerd | `/usr/bin/dockerd`存在 |
| containerd服务 | LoadState=loaded，ActiveState=active，UnitFileState=enabled |
| socket | `/var/run/docker.sock`和当前用户`/run/user/1001/docker.sock`均不存在 |

因此当前PC2不能直接load/run镜像。masked是明确禁用状态，不能简单当作没有安装；不通过unmask、启动系统Docker或复用正在运行的原生containerd绕过限制，不进入PC1。尚不能确认由哪个组件设置禁用，需设备提供方核对官方允许的Podman/容器开发方案及与当前固件的兼容性，再进行容器真机验收。

本次没有修改机器人服务或容器权限。当前用户UID显示为1001，run.sh按实际UID/GID映射；Compose的固定镜像用户默认1000，目标机器如不同应优先使用运行器并核对目录权限，不能直接把云端默认用户当作机载用户。
