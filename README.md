# helm-fine-upgrade

A way for more controllable upgrading of Helm charts.

`helm-fine-upgrade` helps teams inspect, adopt, and upgrade existing Kubernetes
resources with finer control than a full `helm upgrade`. It is especially useful
for legacy clusters where runtime resources, Helm charts, and values files may
have drifted from each other.

## Plugin Manager

To install this plugin, simply run Helm command:

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
```

Before use the plugin, run below command to add python dependences:

```bash
cd "$(helm env | grep HELM_PLUGINS | awk -F '"' '{print $2}')/helm-fine-upgrade" && pip install -r requirements.txt && cd -
```

To uninstall, run:

```bash
helm plugin uninstall fine-upgrade
```

## Usage

Run this command to view the help document:

```bash
helm fine-upgrade --help
```

### Plugin Basic Command Structure

```bash
helm fine-upgrade [COMMAND] [NAME] [CHART] [flags]
```

### Plugin Action

- `adopt-plan`: 分析 chart 渲染资源和集群已有资源的接管关系，并输出接管命令预览
- `state-check`: 检查 Helm release 记录、集群运行态和当前 chart 之间的一致性
- `plan`: 生成升级计划，展示新增、更新、接管、孤儿资源和不可变字段风险
- `generate-comparison-file`: 生成集群当前配置与 chart 配置的对比文件
- `apply`: 根据 chart 渲染结果应用资源，可配合选择器控制影响范围
- `show-default-config`: 打印默认插件配置，可以自行重定向保存
- `update-values-image-version`: 更新 values.yaml 的镜像版本，与集群中的镜像版本进行对齐
- `update-ownership-metadata`: 更新 API 对象的元数据信息，使 Helm 可以接管相关对象的更新维护（用于接管其他 chart 或者其他方式创建的对象）
- `rolling-update-pod-labels`: 滚动更新 pod 的标签。（Deployment 指定 Pod 的标签后，无法更新 Pod 的标签，此动作用于处理此类情况）

### Safety Notes

- Prefer `plan` and `generate-comparison-file` before running mutating actions.
- Use `--dry-run` where supported to review the commands or manifests first.
- `apply`, `update-ownership-metadata`, and `rolling-update-pod-labels` may change
  live cluster resources.
- `apply` uses `kubectl apply` and does not update Helm release storage. Run a
  regular Helm upgrade afterward when you need Helm release state to match the
  cluster state.

### Kubernetes Connection Flags

Most commands support these flags:

- `--namespace`: Helm release namespace
- `--kubeconfig`: kubeconfig file path
- `--context`: Kubernetes context
- `--timeout`: kubectl request timeout, for example `30s`

### Examples

Generate simplified helm rendered manifests and cluster runtime manifests files to the default `./helm-fine-upgrade` directory. (You can then compare them using the vscode editor.)

Using the `--debug` flag allows you to view the executed SHELL commands

```bash
# Execute `generate-comparison-file` action in debug mode in chart root directory.
# Release name is `my_release` and release namespace is `my_release_namespace`.
# Specify values in a YAML file `./my-values.yaml`.
# Specify the plugin configuration file path as `./.my-customized-config.yml`.
helm fine-upgrade generate-comparison-file \
    my_release . \
    --namespace my_release_namespace \
    --values ./my-values.yaml \
    --config ./.my-customized-config.yml \
    --kubeconfig ~/.kube/my-kubeconfig.yaml \
    --debug
```

Generate a structured upgrade plan:

```bash
helm fine-upgrade plan \
    my_release . \
    --namespace my_release_namespace \
    --values ./my-values.yaml \
    --config ./.my-customized-config.yml
```

Check whether Helm release storage, live cluster resources, and the current chart
are still aligned:

```bash
helm fine-upgrade state-check \
    my_release . \
    --namespace my_release_namespace \
    --values ./my-values.yaml \
    --config ./.my-customized-config.yml
```

Analyze which existing resources can be adopted by the release:

```bash
helm fine-upgrade adopt-plan \
    my_release . \
    --namespace my_release_namespace \
    --values ./my-values.yaml \
    -l app=my-service
```

## TODO

- [x] 实现初版基础对比功能
- [x] 接入 Helm 插件机制
- [x] 补充初始化说明
- [x] 配置文件输出
- [x] 同步集群镜像版本到 values.yaml 文件
- [x] 接管集群对象到当前 Release
- [ ] ~~Nacos 配置对比~~
- [ ] 中文文档
- [ ] 英文文档
- [x] 实现平滑更新 Pod 标签
- [ ] 通过选择器过滤对比范围
- [ ] 通过选择器手动更新对象

## Contributing

- We follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) to submit code.
- If you have any good ideas or bugs or suggestions, please feel free to submit an issue.
- Talk is cheap. Welcome to submit your valuable pull request.

## License

[Apache License 2.0](./LICENSE)
