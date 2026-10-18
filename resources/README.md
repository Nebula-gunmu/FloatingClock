# resources

本目录存放应用图标等静态资源。

图标由 `tools/make_icon.py` 用 PySide6 绘制生成，无需手工准备：

```powershell
python tools\make_icon.py
```

生成文件：

- `icon.png`（256×256，窗口图标、任务栏/Alt-Tab 图标）
- `icon.ico`（打包 exe 图标，供 `FloatingClock.spec` 使用）
- `icon_128.png` / `icon_64.png` / `icon_48.png` / `icon_32.png` / `icon_16.png`（快捷方式与文档用）

打包时该目录会整体复制进 `dist/FloatingClock/_internal/resources/`，
运行时通过 `app/constants.py:resource_dir()` 定位（兼容 PyInstaller `_MEIPASS`）。
