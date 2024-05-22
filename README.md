# helm-cluster-diff

Generate a Helm release and cluster configuration file that is convenient for comparison.

## Plugin Manager

To install this plugin, simply run Helm command:

```bash
helm plugin install https://github.com/DevinZhong/helm-cluster-diff
```

Before use the plugin, run below command to add python dependences:

```bash
cd "$(helm env | grep HELM_PLUGINS | awk -F'"' '{print $2}')/helm-cluster-diff" && pip install -r requirements.txt && cd -
```

To uninstall, run:

```bash
helm plugin uninstall cluster-diff
```

## Usage

Run this command to view the help document:

```bash
helm cluster-diff --help
```

### Plugin Basic Command Structure

```bash
helm cluster-diff [ACTION] [NAME] [CHART] [flags]
```

### action

- `generate-comparison-file`: 生成集群当前配置与 chart 配置的对比文件
- `show-default-config`: 打印默认插件配置，可以自行重定向保存

### example

Generate simplified Release and cluster runtime Manifests files to the default ./helm-cluster-diff directory. (You can then compare them using the vscode editor.)

Using the `--debug` flag allows you to view the executed SHELL commands

```bash
helm cluster-diff generate-comparison-file \
    smart100-test . \
    --namespace smart100-test \
    --values ./values.yaml \
    --kubeconfig ~/.kube/smart100-kubeconfig.yaml \
    --debug
```

## TODO

- [x] 实现初版基础对比功能
- [x] 接入 Helm 插件机制
- [x] 补充初始化说明
- [x] 配置文件输出
- [ ] 中文文档
- [ ] 英文文档
