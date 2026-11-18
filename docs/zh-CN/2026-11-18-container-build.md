# 2026-11-18：首次ARM64容器候选构建

> 历史联调记录：保留当时问题、命令和结果。第三版当前状态见[验收汇总](aimdk-v1-robot-audio.md)，实际部署请使用[当前复现指南](reproduce-on-x2.md)。

## 结果和版本

- 构建源码：`758b3770be180e9919b2c2aec1bd443d581f5b0f`。
- [成功运行与检查记录](https://github.com/1416507479xzt/-X2-/actions/runs/44272155330)：GitHub原生ubuntu-24.04-arm节点；镜像linux/arm64、Python 3.10、ROS Humble。
- 本地镜像标签：`eldercare-x2:candidate`，镜像ID：`sha256:9e9433b9246dabf6cb02b4d2a20192fee2e4948e989781b3890604beb1fa4ca3`。这是构建节点的镜像ID，不是GHCR地址。
- 已通过：构建、启动help、Python/ROS/应用导入、默认启动缺少SDK时退出22、56项离线回归、Compose配置检查、镜像导出和附件上传。
- 未验证：目标SDK及共享库挂载、DDS通信、真实麦克风与播音、容器内环节一二四完整业务、机器人部署权限。

本次没有更改机器人环境或交互模式，也没有安装Windows Docker/WSL。当前已验证的ZIP真机部署继续作为基线；不能把云端离线检查等同于真机容器验收。

## 下载与复现

登录GitHub后打开[候选附件](https://github.com/1416507479xzt/-X2-/actions/runs/44272155330/artifacts/14413161487)，或进入成功运行页面底部Artifacts下载。附件约275MiB，名称包含完整源码提交，保留至2026-11-25约17:03（北京时间），请及时保存。

解压附件可得：`eldercare-x2-arm64.tar.gz`、`SHA256SUMS`、`image-inspect.json`、`source-commit.txt`、`VALIDATION.txt`。附件ZIP摘要为`sha256:678775021c75f7fd79c5890fbc0d308fa6760ecd72cbd9b49141a4fb72c4d185`；ZIP摘要与内部tar.gz摘要是不同的值，内部文件用SHA256SUMS验证。

在获准使用Docker的Linux ARM64开发机上进入解压目录：

```bash
sha256sum -c SHA256SUMS
docker load -i eldercare-x2-arm64.tar.gz
docker run --rm --network none eldercare-x2:candidate dependencies
docker run --rm eldercare-x2:candidate help
```

连接机器人还需匹配的AimDK SDK、官方运行通道及ROS配置，按[容器复现说明](docker-reproduction.md)操作。镜像没有API Key、机器人固件或云端模型权重，未发布可docker pull的GHCR地址。

## 遇到的问题及修复

首次运行44271897828构建成功，但依赖检查用`--entrypoint /usr/bin/python3`绕过了ROS环境加载，导致`ModuleNotFoundError: rclpy`。改为容器`dependencies`入口：先source ROS，再检查Python/ROS/应用导入；此入口不需要AimDK、不访问网络、不控制机器人。第二次全部检查通过。

## 后续开发规则

源码和构建定义同步维护，稳定节点保留Git标签；真机语音v0.1.0/v0.2.0继续用于效果对比，不移动已有标签。候选镜像记录源码提交、镜像ID及离线文件校验值，完成目标机器验收后再发布正式容器版本。

修改Dockerfile、锁定依赖、构建上下文或docker目录会触发云端候选构建。日常业务源码改动提交后，可到Actions → ARM64 container candidate → Run workflow，选择main重新构建；当前路径过滤不会因每次业务改动自动构建，旧附件始终只对应其记录的提交。构建附件到期后也可以从对应Git提交重新构建，但基础OS标签和apt仓库可能变化；精确复用应保存已构建镜像及校验值。
