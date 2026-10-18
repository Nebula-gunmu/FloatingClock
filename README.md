# FloatingClock 桌面悬浮时钟

一个 iOS 风格的 Windows 桌面悬浮时钟：无边框、透明、可拖动、可缩放，支持日期、天气、月历、倒计时、秒表、置顶、Win10 磨砂背景与开机自启。

- 运行平台：Windows 10 / 11 x64
- 技术栈：Python 3.11+ / PySide6 / ctypes（Win32、DWM）/ QNetworkAccessManager / PyInstaller（目录式打包）
- 交付形态：`dist/FloatingClock/FloatingClock.exe` 双击即用，目标机器无需安装 Python 或任何运行环境

---

## 一、快速开始（开发运行）

```powershell
cd FloatingClock
python -m pip install -r requirements.txt
python main.py
```

不想看到控制台窗口时用：

```powershell
pythonw main.py
```

## 二、直接使用打包好的成品

本目录已包含实际构建并启动验证过的两个版本：

```
dist/FloatingClock/          ← Windows 10 / 11 x64（PySide6 / Qt 6）
├─ FloatingClock.exe
└─ _internal/                ← 全部依赖（PySide6、Qt 插件、图标）

dist-win7/FloatingClock/     ← Windows 7 x64（PySide2 / Qt 5.15 + Python 3.8）
├─ FloatingClock.exe
├─ PySide2/                  ← 全部依赖（Qt5、平台插件）
├─ resources/
└─ *.dll                     ← Python 3.8 运行时 + VC++ 运行库
```

把对应文件夹整体拷到目标电脑即可运行，**不需要安装 Python / PySide / vcredist，也不需要联网**。
注意：**不要只拷 exe**，必须连同同目录的依赖一起拷贝。

### Windows 7 说明

- Win7 版使用 **Python 3.8 + PySide2 5.15（Qt 5.15）**——Qt 6 不支持 Win7，这是唯一可行组合。
- 包内已附带 `msvcp140.dll`、`vcruntime140.dll`、`vcruntime140_1.dll`、`concrt140.dll`，**无需安装 VC++ 运行库**。
- 系统要求：Windows 7 **SP1 x64**，并已安装通用 C 运行库更新（KB2999226，2015 年后的自动更新都会带上；绝大多数机器已有）。
- 磨砂背景在 Win7 上使用 **Aero 玻璃**（`DwmEnableBlurBehindWindow`），需开启 Aero 主题；未开启 Aero 时自动降级为半透明圆角纯色。
- 开机自启、置顶、天气、日历、倒计时/秒表、色盘、字体选择与 Win10/11 版完全一致。

## 三、一键打包

```bat
build.bat
```

或 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

产物：`dist\FloatingClock\`，内含 `FloatingClock.exe` 与全部依赖。分发时把整个文件夹压缩发给用户即可。

> 详细步骤、干净机器验证方法与常见问题见 [打包说明.md](打包说明.md)；日常操作见 [使用说明.md](使用说明.md)。

---

## 四、项目结构

```
FloatingClock/
├─ main.py                      # 入口：高 DPI、字体、主题初始化
├─ app/
│  ├─ constants.py              # 常量、颜色令牌、尺寸、WMO 天气代码映射
│  ├─ settings_model.py         # 集中设置模型（dataclass + JSON 持久化）
│  ├─ theme.py                  # iOS 风格主题、字体工厂、QSS、明暗切换
│  └─ qtcompat.py               # Qt5/Qt6 兼容层（Win7 走 PySide2，代码只写一套）
├─ core/
│  ├─ time_modes.py             # 时钟/倒计时/秒表枚举 + 统一显示控制器
│  ├─ timer_controller.py       # 倒计时与秒表状态机（monotonic 计时）
│  └─ app_controller.py         # 应用协调器：把设置/服务/窗口连起来
├─ services/
│  ├─ weather_service.py        # Open-Meteo 异步请求、缓存、降级
│  └─ autostart_service.py      # HKCU Run 注册表读写
├─ winplatform/
│  └─ win_effects.py            # ctypes：亚克力磨砂、置顶、圆角
├─ ui/
│  ├─ main_clock_window.py      # 无边框悬浮窗：拖动、缩放、齿轮、副行、日历挂载
│  ├─ settings_panel.py         # 设置面板（iOS Inset Grouped 分组列表）
│  └─ widgets/
│     ├─ ios_switch.py          # 胶囊开关（带 160ms 动画）
│     ├─ ios_slider.py          # 细轨道 + 圆形手柄滑块
│     ├─ ios_segmented.py       # 分段控件（胶囊底槽 + 滑动白块）
│     ├─ ios_calendar.py        # 月历卡片
│     └─ clock_face.py          # 主时钟数字绘制（逐字符等宽格，不抖动）
├─ resources/                   # icon.png / icon.ico（tools/make_icon.py 生成）
├─ tools/
│  ├─ make_icon.py              # 生成图标资源
│  ├─ selftest.py               # 无界面自检（格式化/设置/计时/天气降级）
│  ├─ preview.py                # 离屏渲染截图（含模拟壁纸合成）
│  ├─ list_fonts.py             # 列出系统字体（排查字体回退用）
│  └─ smoke_qt5.py              # PySide2（Qt5）冒烟测试
├─ dist/FloatingClock/          # Win10/11 打包成品（exe + _internal 全部依赖）
├─ dist-win7/FloatingClock/     # Win7 打包成品（exe + PySide2/Qt5 全部依赖）
├─ check/                       # 预览截图（开发期产物，可删除）
├─ requirements.txt             # 固定版本依赖（PySide6 版）
├─ FloatingClock.spec           # 打包配置（自动适配 PySide6 / PySide2）
├─ build.bat / build.ps1        # 一键打包脚本
├─ README.md / 使用说明.md / 打包说明.md
```

### 关于 `winplatform/`

提示词建议的目录名是 `platform/`，但 `platform` 是 Python 标准库模块名，作为包名会让 PyInstaller 与部分第三方库导入到错误模块，因此改名为 `winplatform`，职责与 `platform/win_effects.py` 完全一致。

## 五、架构约定

- **设置唯一来源**：`app/settings_model.py` 的 `SettingsStore`，所有 UI 只读写它；变更通过 `changed(key, value)` 广播。
- **界面不含业务规则**：`ui/` 只负责绘制与把鼠标事件翻译成信号；写入设置、调用服务、切换置顶/自启等动作都在 `core/app_controller.py` 完成。
- **显示模式可扩展**：新增模式只需在 `core/time_modes.py` 的 `TimeMode`、`MODE_TEMPLATES` 和 `_compose()` 中登记，主窗口与设置面板无需改动。
- **失败优雅降级**：网络失败回退缓存、注册表失败只提示、Win32 API 不可用时退回 Qt 自绘半透明背景。

## 六、功能一览

| 模块 | 说明 |
| --- | --- |
| 主悬浮窗 | 无边框、透明、无控制台；默认完全无背景；按住数字拖动；悬停右下角出现齿轮 |
| 缩放 | 设置面板滑块 60–300px，滚轮 ±5%（受"滚轮缩放"开关控制），缩放时窗口中心保持稳定 |
| 透明与磨砂 | 文字透明度与背景透明度互相独立；开启背景时调用 Windows 原生亚克力磨砂（实时模糊背后内容、随拖动跟手），失败时退回 Win11 系统 backdrop 或半透明圆角纯色 |
| 显示内容 | 时间 HH:MM:SS（等宽格绘制，宽度不抖动）、日期、天气摘要 |
| 设置面板 | iOS Inset Grouped 分组：外观 / 显示 / 置顶 / 功能 / 天气 / 日历 / 系统，实时生效并持久化；数字颜色带自绘色盘（饱和-明度方块 + 色相条 + iOS 系统色预设） |
| 天气 | Open-Meteo 免费接口，异步请求 8 秒超时，30 分钟自动刷新，本地缓存 + 离线标注 |
| 日历 | iOS 风格月历卡片，当天强调色圆底，左右箭头切月，"今天"回到本月 |
| 倒计时 / 秒表 | 面板内控制，主窗口显示；功能总开关关闭后强制回到时钟模式 |
| 置顶 | `WindowStaysOnTopHint` + `SetWindowPos(HWND_TOPMOST)` 双保险，并每 2.5 秒重申一次，被别的置顶窗口压住后会自动夺回 |
| 开机自启 | HKCU Run 注册表，无需管理员权限；开发环境只提示"打包后生效" |

## 七、配置文件位置

- 设置：`%APPDATA%\FloatingClock\settings.json`
- 天气缓存：`%APPDATA%\FloatingClock\weather_cache.json`

删除这两个文件即可恢复出厂状态。

## 八、系统限制（务必知悉）

- Windows 的 UAC 安全弹窗、任务管理器、系统级错误对话框属于系统强制顶层窗口，**任何普通应用都无法覆盖**，这是操作系统限制。
- 开机自启写入 `HKCU` 后若被安全软件拦截，需要用户手动放行（或在安全软件中把 `FloatingClock.exe` 加入白名单）。
- 磨砂背景使用 Windows 原生亚克力（`SetWindowCompositionAttribute`）：模糊的是窗口背后**实时**内容，拖动窗口时背景会跟着走，磨砂区域为矩形（系统不支持给亚克力做自定义圆角）。若亚克力不可用，Windows 11 上退回 DWM 系统 backdrop（有原生圆角，但只采样壁纸），再失败则降级为 Qt 自绘的半透明圆角纯色背景。
- 需要系统开启"透明效果"（设置→个性化→颜色）；远程桌面会话或精简系统可能不提供合成能力。

## 九、构建与验证结果（本次实测）

| 项目 | 结果 |
| --- | --- |
| 语法检查 | 26 个 Python 文件全部通过 `ast.parse` |
| 无界面自检 `tools/selftest.py` | 30 项全部 PASS（格式化、设置夹取与持久化、倒计时/秒表状态机、模式切换、天气降级） |
| 离屏渲染 `tools/preview.py` | 生成 `check/*.png`（含模拟壁纸合成），确认浅色/深色/日历/设置面板布局正常 |
| 打包 | PyInstaller 6.22.3 目录式构建成功，`dist/FloatingClock` 约 113 MB |
| 产物启动 | `FloatingClock.exe` 在 offscreen 与 windows 两种平台下均稳定驻留运行，无 stderr 输出 |
| 依赖完整性 | `_internal/PySide6/plugins/platforms/qwindows.dll`、`_internal/resources/icon.png` 均存在 |

构建环境：Windows + Python 3.14.4 + PySide6 6.12.0 + PyInstaller 6.22.3。

## 十、许可证

示例工程，可自由修改与分发；PySide6 与 Qt 遵循 LGPL v3。
