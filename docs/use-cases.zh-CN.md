# 使用场景

这份文档说明 `helm-fine-upgrade` 适合处理哪些问题，以及每类问题应该从哪个命令
开始。这个插件的目标是在真正修改集群之前，先把 Helm 变更风险看清楚。

## 升级前风险评估

当你准备升级某个 release，想先知道 chart 会新增、更新、接管或遗留哪些资源时，
使用 `plan`。

```bash
helm fine-upgrade plan my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --output-format json
```

在 CI 中，可以在出现接管、孤儿资源或不可变字段风险时让任务失败：

```bash
helm fine-upgrade plan my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --output-format json \
    --fail-on adopt,orphan,immutable_risk
```

常用 summary 字段：

- `create`：chart 渲染出来但当前还不存在的资源。
- `update`：当前已存在，但和 chart 渲染结果不同的资源。
- `adopt`：chart 中存在、集群中也存在，但当前 release 尚未管理的资源。
- `orphan`：当前 release 管理，但本次 chart 渲染结果里已经没有的资源。
- `immutable_risk`：可能涉及不可变字段变更的资源，例如 Deployment selector。

## 运行态漂移检查

当你怀疑有人手工改过集群，或者 Helm release storage 和线上资源不一致时，使用
`state-check`。

```bash
helm fine-upgrade state-check my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --output-format json
```

在 CI 中，可以在 release storage 和运行态发生漂移时让任务失败：

```bash
helm fine-upgrade state-check my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --output-format json \
    --fail-on runtime_missing,runtime_extra,runtime_drift
```

常用 summary 字段：

- `runtime_missing`：release 记录里有，但集群中缺失的资源。
- `runtime_extra`：集群中存在，但 release 记录里缺失的资源。
- `runtime_drift`：release 和集群中都存在，但忽略无关字段后内容仍不一致的资源。
- `chart_create`、`chart_update`、`chart_delete`：release storage 与当前 chart
  渲染结果之间的差异。

## 存量资源接管

当 chart 需要管理集群中已经存在的资源时，先使用 `adopt-plan` 看接管关系，不要直接
修改 ownership metadata。

```bash
helm fine-upgrade adopt-plan my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --output-format yaml
```

如果发现资源已经属于其他 release，可以让 CI 失败：

```bash
helm fine-upgrade adopt-plan my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --output-format json \
    --fail-on conflict
```

确认符合预期后，先预览 metadata 变更：

```bash
helm fine-upgrade update-ownership-metadata my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --dry-run
```

人工确认后再执行：

```bash
helm fine-upgrade update-ownership-metadata my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --yes
```

## Selector 或 Label 迁移

当 Deployment selector 或 Pod label 需要变化时，Kubernetes 某些字段无法原地更新，
应先检查风险。

```bash
helm fine-upgrade plan my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --selector app=my-service \
    --fail-on immutable_risk
```

如果确实需要做受控迁移，先 dry-run：

```bash
helm fine-upgrade rolling-update-pod-labels my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --selector app=my-service \
    --dry-run
```

在非生产环境验证后，再执行实际变更：

```bash
helm fine-upgrade rolling-update-pod-labels my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --selector app=my-service \
    --yes
```
