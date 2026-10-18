# 发布与更新说明

## 仓库

<https://github.com/Nebula-gunmu/FloatingClock>

- 主分支：`main`，当前版本提交 `6a86cf3`
- 标签：`v1.0.0`
- 共 55 个文件，其中 `release/` 下是两个可直接分发的压缩包

## 下载地址

| 版本 | 直链 |
| --- | --- |
| Windows 10 / 11 x64 | [FloatingClock-1.0.0-win64.zip](https://github.com/Nebula-gunmu/FloatingClock/raw/main/release/FloatingClock-1.0.0-win64.zip) |
| Windows 7 SP1 x64 | [FloatingClock-1.0.0-win7-x64.zip](https://github.com/Nebula-gunmu/FloatingClock/raw/main/release/FloatingClock-1.0.0-win7-x64.zip) |

下载后解压，双击 `FloatingClock.exe` 即可运行；不需要安装 Python / Qt / vcredist，也不需要联网。

## 校验和

```
436f9af1dad7431980e81b8e4f5ae7bf1cf41ebd66bda00817cf59a938b6efba  FloatingClock-1.0.0-win64.zip   (45.0 MB)
7057145f5fe7b67c3f14840dd523432b1e36b93c4bba82bc078ba8645e3519ec  FloatingClock-1.0.0-win7-x64.zip (40.4 MB)
```

```powershell
Get-FileHash .\FloatingClock-1.0.0-win64.zip -Algorithm SHA256
```

## 建议：建一个 Release

仓库里已有 tag `v1.0.0`，网页两步即可：

1. 打开 <https://github.com/Nebula-gunmu/FloatingClock/releases/new?tag=v1.0.0>
2. 标题填 `FloatingClock 1.0.0`，把 `release/` 里两个 zip 拖进附件区，Publish

Release 附件下载比 raw 链接更稳定（raw 大文件偶尔会断），也方便别人一眼看到有成品。

## 后续更新代码

```powershell
cd "E:\DeepSeek\PC Time\FloatingClock"

# 改完代码后
git add -A
git commit -m "描述这次改动"
git push

# 发新版本时
git tag -a v1.0.1 -m "FloatingClock 1.0.1"
git push origin v1.0.1
```

重新构建成品后，把新的 zip 覆盖到 `release/` 再提交即可。

## 两个环境变量

本机 `git` 使用自己的 DNS 解析器，**不受 hosts 屏蔽影响**（`curl` 和浏览器才受影响），所以推送不需要代理。若某天 `git push` 也失败，再考虑给 git 配代理：

```powershell
git config --global http.proxy http://127.0.0.1:端口
```

## 仓库为什么不含 dist/

`dist/`（113 MB）和 `dist-win7/`（102 MB）是构建产物，内容与 `release/` 里的 zip 重复，已在 `.gitignore` 中排除。想自己打包看 [打包说明.md](打包说明.md)。
