# 上传到 GitHub 的步骤

## 0. 先解决网络问题（重要）

本机 `hosts` 文件把 GitHub 相关域名指向了 `127.0.0.1`，所以直连必然失败：

```
127.0.0.1 github.dev
127.0.0.1 api.github.com
127.0.0.1 github.githubassets.com
127.0.0.1 uploads.github.com
127.0.0.1 raw.github.com
127.0.0.1 githubusercontent.com
127.0.0.1 raw.githubusercontent.com
127.0.0.1 camo.githubusercontent.com
127.0.0.1 cloud.githubusercontent.com
127.0.0.1 avatars.githubusercontent.com
...（还有 huggingface.co 等）
```

这通常是某个"屏蔽/加速"工具或安全软件写入的。三种解决办法，任选一种：

1. **清理 hosts**（推荐）：用管理员权限打开 `C:\Windows\System32\drivers\etc\hosts`，删除所有 `127.0.0.1` 开头的 GitHub 相关行，执行 `ipconfig /flushdns`。
2. **用代理**：代理软件走自己的 DNS，不受 hosts 影响；给 git 配上 `git config --global http.proxy http://127.0.0.1:端口` 即可。
3. **换一台能访问 GitHub 的电脑**：把本目录整体拷过去再上传。

清理后用 `curl -I https://github.com` 确认返回 200/301 再往下走。

## 1. 新建公开仓库

网页方式：<https://github.com/new> 填写
- Repository name：`FloatingClock`
- Public
- **不要**勾选 "Add a README file"（本地已经有）
- Create repository

然后用其中一种方式上传。

## 2. 方式 A：网页拖拽（不需要装 git）

GitHub 网页单次上传上限 25 MB/文件，而两个 zip 分别是 45 MB 和 40 MB，**网页拖拽传不上去**。
所以要么：

- 把 zip 拆成 <25 MB 的分卷再传（不推荐，麻烦）；
- 或者用 **Release 附件**（单文件上限 2 GB）：仓库页 → Releases → Draft a new release → Tag `v1.0.0` → 把两个 zip 拖进附件区 → Publish。

源码（除 `dist/`、`dist-win7/`、`check/` 外）仍可以用网页 `Add file → Upload files` 拖上去。

## 3. 方式 B：命令行（可传大文件，推荐）

```powershell
cd "E:\DeepSeek\PC Time\FloatingClock"

# 首次使用需要配置身份（只做一次）
git config --global user.name  "你的名字"
git config --global user.email "你的邮箱"

# 初始化并提交（.gitignore 已排除 dist/、dist-win7/、check/ 等构建产物）
git init
git add .
git commit -m "FloatingClock 1.0.0：iOS 风格 Windows 悬浮时钟（Win10/11 + Win7 双版本）"
git branch -M main

# 关联远程仓库（换成你自己的地址）
git remote add origin https://github.com/你的用户名/FloatingClock.git

# 推送（会要求输入用户名 + Personal Access Token 作为密码）
git push -u origin main
```

推送时 GitHub 不再接受账号密码，密码位置请填 **Personal Access Token**（Settings → Developer settings → Personal access tokens → Fine-grained tokens，勾选该仓库的 `Contents: Read and write`）。

如果网络需要代理：

```powershell
git config --global http.proxy http://127.0.0.1:端口
git config --global https.proxy http://127.0.0.1:端口
```

## 4. 仓库里会包含什么

```
FloatingClock/
├─ main.py                     源码入口
├─ app/ core/ services/ ui/ winplatform/ tools/ resources/
├─ FloatingClock.spec          打包配置（自动适配 PySide6 / PySide2）
├─ requirements.txt
├─ build.bat / build.ps1
├─ README.md / 使用说明.md / 打包说明.md
├─ UPLOAD.md                   本文件
└─ release/
   ├─ FloatingClock-1.0.0-win64.zip      45.0 MB   Win10/11 x64
   ├─ FloatingClock-1.0.0-win7-x64.zip   40.4 MB   Win7 SP1 x64
   └─ SHA256SUMS.txt
```

`dist/`（113 MB）与 `dist-win7/`（102 MB）已在 `.gitignore` 中排除——它们和 `release/` 里的 zip 内容一致，没必要重复进仓库。

## 5. 校验和

```
436f9af1dad7431980e81b8e4f5ae7bf1cf41ebd66bda00817cf59a938b6efba  FloatingClock-1.0.0-win64.zip
7057145f5fe7b67c3f14840dd523432b1e36b93c4bba82bc078ba8645e3519ec  FloatingClock-1.0.0-win7-x64.zip
```

下载后可用 `Get-FileHash .\FloatingClock-1.0.0-win64.zip -Algorithm SHA256` 对照。

## 6. 建议补充（可选）

- 仓库 About 里写：`iOS 风格 Windows 桌面悬浮时钟，支持 Win10/11 与 Win7，目录式打包免安装`
- 打一个 tag `v1.0.0`，再基于 tag 建 Release，把两个 zip 作为附件，方便别人直接下载。
