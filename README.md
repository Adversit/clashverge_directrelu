# 手动智能路由

基于 Clash Verge 的 Windows 本地网页工具，用于管理国内网站、游戏和其他本地程序的 DIRECT 规则，并查看目标的真实连接通道。

双击 **start.vbs** 静默启动并打开 [管理页面](http://127.0.0.1:17891)。也可双击 start.cmd。页面仅监听本机 127.0.0.1:17891。重复启动会复用当前服务。

首次使用需要 Python 3.10+、Node.js 和 Clash Verge Rev。启动脚本创建独立 .venv 并安装 requirements.txt 中固定版本的 PyYAML。当前机器环境已准备好。

使用步骤：

1. 打开 Clash Verge，选择规则模式。
2. 在页面添加完整网址或域名，工具自动取域名；目录须为存在的 Windows 本地目录。
3. 点击「应用直连规则」，等待「已写入 / 已生效」。
4. 让游戏重新连接，然后刷新查看实际通道。未观察到连接不能证明直连。

默认覆盖：yjwujian.cn、narakathegame.com、d90.gdl.netease.com、d90-06.gdl.netease.com，以及存在时的 G:/Naraka。域名及其子域名直连，目录包含所有子目录程序。官网地址见 [国服官网](https://www.yjwujian.cn/) 和 [国际官网](https://www.narakathegame.com/)，下载地址来自本机游戏修复日志。

TUN 负责接管流量，规则模式决定通道。关闭 TUN 后，遵循系统代理的应用仍按规则分流；不使用系统代理的游戏连接可能绕过 Clash。页面只观察经过内核的连接。建议保持现有设置，先验证规则。规则类型与顺序见 [Mihomo 规则文档](https://wiki.metacubex.one/config/rules/)。

「撤销本工具规则」移除本工具写入的全局脚本块及运行规则，保留清单以便重新应用。失败时尝试回滚；出现中断状态时先点击「恢复中断操作」。原配置与脚本备份保存在 data/backups，包含原订阅凭据，仅存于本机，不上传 Git。

默认 Clash Verge 数据目录为 `%APPDATA%/io.github.clash-verge-rev.clash-verge-rev`，默认内核为 `D:/clash verge/verge-mihomo.exe`。不同安装位置可在启动前设置 `CLASH_VERGE_DATA` 与 `MIHOMO_EXE`。后端优先使用 Windows 命名管道，不开放新的内核控制端口，也不把内核密钥发送到浏览器。

本工具追加带标记的全局 Script 包装函数，原有 main 函数保持不变。Clash Verge 重新生成配置时，该全局脚本将再次加入规则；不能在 Clash Verge 内删除这段包装函数，否则规则不会保留。已有连接不会被强制关闭。

本地数据位于 data/targets.json；规则变更需显式应用。不要把 data/ 或 Clash 配置上传仓库。项目测试记录见 [TEST_RECORD.md](TEST_RECORD.md)，检测范围和限制见 [DETECTION_REPORT.md](DETECTION_REPORT.md)。

开发验证：`.venv\Scripts\python.exe -m unittest discover -s tests -v`。直接运行服务：`.venv\Scripts\python.exe app.py`。

需要停止服务时，可用 `Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 17891 -State Listen` 找到本工具监听进程，核对进程命令行确实指向本项目 app.py 后再停止。关闭网页不会停止服务，已写入规则也会保留。
