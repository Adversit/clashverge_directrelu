# 永劫无间通道检测

检测日期：2026-10-02（Asia/Shanghai）。

Clash Verge 内核 Mihomo v1.19.31，规则模式，TUN 开启，进程识别 strict。通过 Windows 服务生产命名管道读取 /configs、/rules、/connections；未开放新的控制端口。

检测初期没有目标连接。后续观察到 d90.gdl.netease.com 的补丁下载连接，原有规则 netease.com 匹配「国内网站」策略组，实际链为 DIRECT → 国内网站，已经直连。

应用默认直连规则后，观察到至少 8 条新下载连接直接命中 d90-06.gdl.netease.com 规则，实际链为 DIRECT。旧连接继续保留旧策略组链，符合内核行为。下载连接未提供进程路径，因此不把它当作游戏对局证据。

本工具默认创建四个域名规则和一个目录规则，放在规则前部。目录正则为 `(?i)^G:[\\/]Naraka[\\/].*`，覆盖游戏本体、启动器、更新器与其子目录，不匹配 G:/NarakaOther。

目录发现 22 个可执行文件，包括 LauncherGame.exe、program/NarakaBladepoint.exe、ClientRepair.exe、yjwj_patcher.exe、yjwj_updater.exe 和录像、崩溃上报等辅助程序。目录规则按用户要求覆盖全部程序，不仅游戏本体。

网址来源：

- [国服官网](https://www.yjwujian.cn/)：yjwujian.cn。
- [国际官网](https://www.narakathegame.com/)：narakathegame.com。
- G:/Naraka/patch/repair_2026_10_02_09_31_45.log 和 repair_2026_10_02_09_42_49.log：update.yjwujian.cn、d90.gdl.netease.com、d90-06.gdl.netease.com。
- 工具日志还出现通用云游戏或遥测域名，未添加全网易或全 163 域名直连。

尚未观察到 NarakaBladepoint.exe 对局连接。当前确认的是规则已安装和补丁下载实际直连。请运行游戏并进入对局，刷新管理页面，核对进程路径、规则和 chains；TUN 关闭时，绕过内核的连接不会出现在该页面。
