# ramtaskman

[Italiano](../../README.md) · [English](README.en.md) · [中文（简体）](README.zh.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [日本語](README.ja.md)

### 在终端中看清内存都用到了哪里。

ramtaskman 是一款适用于 Linux、Windows 和 macOS 的实验性内存监视器。它源于好奇心和研究，希望让人在不同系统上理解内存使用情况时，无须依赖复杂工具。这是一个 Vibeware 项目。

![ramtaskman](../images/overview.png)

*在 Linux 上捕获的真实 Textual 界面，使用合成演示数据。截图目前展示意大利语界面。*


![Multilingual dashboard](../images/multilingual.png)

*六种语言的部分本地化主界面；在 Linux 上使用合成数据截图。*

## 主要功能

1. 一览系统内存、可用内存、缓存和历史图表；切换精简与完整诊断模式。
2. 浏览应用和进程，按可用指标排序，并查看测量覆盖情况。
3. 查看 RSS 和 USS；在 Linux 上还可查看 PSS、交换空间和 SwapPSS，并明确标出缺失数据。
4. 按名称、可执行文件或精确 PID 搜索，并按用户、交换空间或不完整数据筛选。
5. 在 Linux 上浏览进程内存区域；Windows 虚拟地址视图仍属实验性功能。
6. 比较两个样本，在本地保存和重新打开采集文件，也支持离线查看。

## 界面一览

![Full diagnostics](../images/full-diagnostics.png)

![Process regions](../images/regions-resident.png)

## 开始使用

需要 Python 3.11 或更高版本以及 uv。Linux 需要 /proc 和 smaps_rollup。首次运行需要网络安装锁定的依赖；环境和缓存保存在项目目录中。

```bash
git clone https://github.com/umbertotechnopreneur/ramtaskman.git
cd ramtaskman
./run.sh
```

在 Windows Terminal 中进入项目目录并运行：

```powershell
.\run.cmd
```

使用 --once 输出一次采样，或用 --json 输出 JSON。不要在不同操作系统之间共用 .venv；请在本地重新创建。项目尚未发布到 PyPI。

常用按键：m 切换模式，g 切换应用/进程，/ 搜索，f 筛选，d 查看详情，r 打开区域，? 解释指标，q 退出。完整技术指南目前为意大利语。

使用 `./run.sh --language zh` 启动中文主界面（Windows：`.\run.cmd --language zh`）。本地化尚不完整：详细说明、区域、错误及部分控件仍为意大利语或英语。

## 实验性项目：请谨慎解读数据

采样是顺序进行的，权限可能限制可见性，应用分组采用启发式方法。不可用数据标为 n/a，而不是零。RSS 可能重复计算共享页；进程 PSS 不等于系统总内存。缓存与可用内存重叠；不会把 commit 推算为进程交换空间。

Linux 在可读取时提供 PSS 和每进程交换空间；本项目在 Windows 和 macOS 上不提供这些指标。Linux 区域使用 smaps；Windows 仅提供实验性虚拟区间；macOS 尚无区域地图。已在 Linux 实机验证，Windows 和 macOS 仍需原生验证。

## 灵感与致谢

感谢 Scott Hanselman 和 GPU Taskman 带来的灵感。ramtaskman 复用了该项目的部分内容，并将终端界面改用于内存监视；它是独立项目，并非官方版本。 [Scott Hanselman](https://github.com/shanselman) · [GPU Taskman](https://github.com/shanselman/gputaskman) · [Provenance](../upstream.md)

翻译由 AI 辅助完成，欢迎翻译人员和母语使用者提出修正。

[完整技术指南（意大利语）](../guida.md) · [MIT 许可证；保留原始版权声明。](../../LICENSE)
