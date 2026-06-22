# 安装与故障排查

这份文档整理 Helm 3、Helm 4、二进制包安装，以及常见平台问题。

## 推荐安装方式

Helm 3：

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
```

Helm 4：

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade --verify=false
```

Helm 4 引入了插件来源验证。当前 GitHub 源码安装路径还没有提供 Helm 插件
provenance 元数据，所以 Helm 4 用户需要加 `--verify=false`。这个参数只是跳过
Helm 的插件来源验证，不会跳过本插件自己的二进制下载逻辑。

## 前置要求

- `helm` 已安装，并且在 `PATH` 中。
- `kubectl` 已安装，并且在 `PATH` 中；检查或修改集群资源的命令会用到它。
- 已配置目标 Kubernetes 集群凭据。
- 安装 hook 需要访问 GitHub Releases，除非显式使用源码模式。

## 安装 Hook 做了什么

从源码仓库安装插件时，Helm 会先把仓库下载到本地插件目录。插件 install hook 会：

1. 识别当前操作系统和 CPU 架构。
2. 选择匹配的 GitHub Release asset。
3. 下载当前平台的二进制插件包。
4. 把 `bin/fine-upgrade` 或 `bin/fine-upgrade.exe` 复制到已安装的插件目录。

下载的可执行文件内置 Python 和 Python 依赖，但仍然会调用外部 `helm` 和 `kubectl`
命令。

## 源码模式

开发调试或暂时没有二进制包的平台，可以使用源码模式：

```bash
HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL=1 helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
cd "$(helm env | grep HELM_PLUGINS | awk -F '"' '{print $2}')/helm-fine-upgrade"
python -m pip install -r requirements.txt
```

Windows PowerShell：

```powershell
$env:HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL = "1"
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade --verify=false
Remove-Item Env:\HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL
```

## 常见问题

### Helm 4 提示 plugin source does not support verification

错误：

```text
plugin source does not support verification. Use --verify=false to skip verification
```

使用：

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade --verify=false
```

### Windows 本地路径安装提示 symlink 权限不足

错误：

```text
symlink ... A required privilege is not held by the client
```

在 Windows 上从本地目录安装插件时，Helm 的本地开发安装模式可能会创建符号链接。
建议优先使用 GitHub URL 安装；如果确实要本地开发，可以开启 Windows Developer
Mode，或使用具备相应权限的 shell。

### 安装时二进制下载失败

检查：

- 机器可以访问 `https://github.com/DevinZhong/helm-fine-upgrade`。
- `plugin.yaml` 中对应的 release tag 已存在。
- 当前平台已有发布的 release asset。
- Linux/macOS 上有 `curl` 或 `wget`。
- Windows 上 PowerShell 可以执行 `Invoke-WebRequest`。

### 暂不支持 linux-arm64 二进制安装

当前还没有发布 Linux ARM64 二进制包。可以使用源码模式，或在对应平台上构建原生
二进制包。

### helm 或 kubectl 不在 PATH 中

运行：

```bash
helm version
kubectl version --client
```

安装缺失命令，并确认它在 `PATH` 中。

### PowerShell 执行策略阻止脚本

插件 hook 和运行脚本使用 `powershell.exe -ExecutionPolicy Bypass -File ...`。如果
你的环境仍然阻止脚本执行，请检查本地安全策略，或改用 release asset 手动安装。

## 手动安装 Release 包

手动安装 release asset 可以绕过源码安装 hook：

```bash
VERSION=v1.6.0
helm plugin install "https://github.com/DevinZhong/helm-fine-upgrade/releases/download/${VERSION}/helm-fine-upgrade-${VERSION}-linux-amd64.tar.gz"
```

Windows：

```powershell
$Version = "v1.6.0"
helm plugin install "https://github.com/DevinZhong/helm-fine-upgrade/releases/download/$Version/helm-fine-upgrade-$Version-windows-amd64.tar.gz"
```
