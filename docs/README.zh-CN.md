# helm-fine-upgrade 中文文档

[![Artifact Hub](https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/helm-fine-upgrade)](https://artifacthub.io/packages/search?repo=helm-fine-upgrade)

[Back to README](../README.md)

`helm-fine-upgrade` 是一个 Helm 插件，用于更可控地处理 Helm Chart 升级、
Helm Release 状态检查，以及将已有 Kubernetes 资源接管到 Helm Release。

它适合真实集群里的存量系统：Chart、线上资源、values 文件可能已经发生漂移，
一次完整的 `helm upgrade` 风险较高，需要先看清影响范围，再决定如何逐步处理。

## 适用场景

当你遇到下面这些问题时，可以考虑使用本插件：

- 升级前想知道 Chart 会新增、更新、接管或遗留哪些资源。
- 想检查 Helm release storage、当前 Chart 渲染结果、集群运行态是否一致。
- 需要把已有 Kubernetes 资源接管到某个 Helm Release。
- 想生成简化后的 rendered manifest 和 runtime manifest，方便人工 diff。
- 只想对某些工作负载及其关联资源做细粒度 apply。
- 线上镜像版本已经变化，需要把 values.yaml 里的镜像 tag 对齐回来。
- Deployment 的 Pod label / selector 发生变化，需要处理不可变字段迁移。

它不是 Helm、GitOps 控制器或 `helm diff` 的替代品，而是一个辅助工具，重点解决
存量系统迁移、接管、漂移检查和精细化升级中的可控性问题。

## 安装

推荐安装方式：

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
```

安装 hook 会自动从 GitHub Releases 下载当前平台对应的独立二进制包。这个方式不需要
用户安装 Python，也不需要执行 `pip install`，但本机仍然需要安装 `helm` 和
`kubectl`。

卸载：

```bash
helm plugin uninstall fine-upgrade
```

源码模式仍然保留，适合开发者或暂时没有二进制包的平台：

```bash
HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL=1 helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
cd "$(helm env | grep HELM_PLUGINS | awk -F '"' '{print $2}')/helm-fine-upgrade" && pip install -r requirements.txt && cd -
```

Windows 源码模式：

```powershell
$env:HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL = "1"
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
Remove-Item Env:\HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL
```

也可以手动指定某个平台的 release 包安装：

```bash
VERSION=v1.2.0
helm plugin install "https://github.com/DevinZhong/helm-fine-upgrade/releases/download/${VERSION}/helm-fine-upgrade-${VERSION}-linux-amd64.tar.gz"
```

二进制包的更多说明见 [Binary Release](./binary-release.md)。

也可以通过 Artifact Hub 发现本插件：

https://artifacthub.io/

## 基本用法

```bash
helm fine-upgrade [COMMAND] [NAME] [CHART] [flags]
```

查看帮助：

```bash
helm fine-upgrade --help
helm fine-upgrade plan --help
```

## 命令说明

只读命令：

- `plan`：生成升级计划，展示新增、更新、接管、孤儿资源和不可变字段风险。
- `state-check`：检查 Helm release storage、集群运行态，以及可选的当前 Chart
  渲染结果之间是否一致。
- `adopt-plan`：分析集群已有资源是否可以被目标 Release 接管。
- `generate-comparison-file`：生成简化后的 rendered/runtime manifest 文件，方便
  人工比对。
- `show-default-config`：打印默认配置。

会修改文件或集群的命令：

- `apply`：使用 `kubectl apply` 应用选中的 Chart 渲染资源。
- `update-values-image-version`：根据集群中实际运行的 Deployment 镜像版本更新
  values.yaml。
- `update-ownership-metadata`：给已有资源补齐或修复 Helm ownership metadata。
- `rolling-update-pod-labels`：通过临时 Deployment 迁移 Pod label，处理 selector
  不可变场景。

## 推荐工作流

1. 先检查 release 与运行态是否一致：

   ```bash
   helm fine-upgrade state-check my_release . \
       --namespace my_release_namespace \
       --values ./my-values.yaml
   ```

2. 生成升级计划：

   ```bash
   helm fine-upgrade plan my_release . \
       --namespace my_release_namespace \
       --values ./my-values.yaml \
       --output-format json
   ```

3. 生成对比文件，人工检查关键差异：

   ```bash
   helm fine-upgrade generate-comparison-file my_release . \
       --namespace my_release_namespace \
       --values ./my-values.yaml \
       --config ./.my-customized-config.yml
   ```

4. 如果涉及资源接管，先看接管计划：

   ```bash
   helm fine-upgrade adopt-plan my_release . \
       --namespace my_release_namespace \
       --values ./my-values.yaml \
       -l app=my-service
   ```

5. 确认计划和风险后，再执行会修改集群或文件的命令。支持 `--dry-run` 的命令建议先
   dry-run。

## 常用参数

大多数命令支持：

- `--namespace`：Helm Release namespace。
- `--kubeconfig`：kubeconfig 文件路径。
- `--context` / `--kube-context`：Kubernetes context。
- `--timeout`：kubectl 请求超时时间，例如 `30s`。
- `--values`：传给 `helm template` 的 values 文件。
- `--config`：插件配置文件路径。
- `--selector` / `-l`：用于缩小 Deployment 相关流程影响范围的标签选择器。
- `--output-format`：结构化输出格式，支持 `yaml` 和 `json`。
- `--fail-on`：逗号分隔的 summary 字段；只读报告命令中任一指定计数非 0 时
  返回退出码 `2`，方便 CI 拦截。
- `--dry-run`：预览支持 dry-run 的变更命令。
- `--yes`：确认执行会修改集群资源或本地文件的命令。
- `--debug`：打印执行的 Helm/kubectl 命令。

## CI 拦截示例

当升级计划里出现接管、孤儿资源或不可变字段风险时，让流水线失败：

```bash
helm fine-upgrade plan my_release . \
    --namespace my_release_namespace \
    --values ./my-values.yaml \
    --output-format json \
    --fail-on adopt,orphan,immutable_risk
```

当 Helm release storage 和集群运行态发生漂移时，让流水线失败：

```bash
helm fine-upgrade state-check my_release . \
    --namespace my_release_namespace \
    --output-format json \
    --fail-on runtime_missing,runtime_extra,runtime_drift
```

## 安全说明

- 在执行会修改集群的命令前，优先使用 `state-check`、`plan`、`adopt-plan` 和
  `generate-comparison-file`。
- 会修改集群或本地文件的命令默认需要 `--yes`；使用 `--dry-run` 时不需要。
- `apply`、`update-ownership-metadata`、`rolling-update-pod-labels` 会修改集群资源。
- `update-values-image-version` 会修改 `--values` 指定的 values 文件。
- `apply` 使用 `kubectl apply`，不会更新 Helm release storage。如果需要 Helm
  记录和集群状态一致，后续应执行常规 `helm upgrade`。
- `rolling-update-pod-labels` 适合特殊的 selector/label 迁移场景。生产环境使用前，
  建议先在非生产集群验证。
- `adopt-plan` 是只读分析命令；真正修改 ownership metadata 的命令是
  `update-ownership-metadata`。
- 如果资源已经属于其他 Helm Release，不应静默接管，应先确认迁移策略。

## 示例

检查 Helm release storage 与集群运行态：

```bash
helm fine-upgrade state-check my_release . \
    --namespace my_release_namespace \
    --values ./my-values.yaml \
    --config ./.my-customized-config.yml
```

生成 JSON 格式升级计划：

```bash
helm fine-upgrade plan my_release . \
    --namespace my_release_namespace \
    --values ./my-values.yaml \
    --output-format json
```

分析资源接管情况：

```bash
helm fine-upgrade adopt-plan my_release . \
    --namespace my_release_namespace \
    --values ./my-values.yaml \
    -l app=my-service
```

生成对比文件：

```bash
helm fine-upgrade generate-comparison-file my_release . \
    --namespace my_release_namespace \
    --values ./my-values.yaml \
    --config ./.my-customized-config.yml \
    --kubeconfig ~/.kube/my-kubeconfig.yaml \
    --debug
```

## 开发

安装依赖并运行本地检查：

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p "*_tests.py"
python -m py_compile src/main.py src/services/helm_service.py src/services/metadata_service.py src/services/image_service.py src/services/pod_label_service.py src/utils/helm_utils.py src/utils/kube_ops_utils.py src/utils/dict_utils.py src/utils/manifest_utils.py src/utils/shell_utils.py src/utils/output_utils.py
```

GitHub Actions 会在 PR 和推送到 `main` 时执行单元测试和语法检查。

## 贡献

请参考 [CONTRIBUTING.md](../CONTRIBUTING.md)。

## 许可证

[Apache License 2.0](../LICENSE)
