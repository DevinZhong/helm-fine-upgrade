# helm-fine-upgrade

A way for more controllable upgrading of Helm charts.

## Plugin Manager

To install this plugin, simply run Helm command:

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
```

Before use the plugin, run below command to add python dependences:

```bash
cd "$(helm env | grep HELM_PLUGINS | awk -F'"' '{print $2}')/helm-fine-upgrade" && pip install -r requirements.txt && cd -
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
helm fine-upgrade [ACTION] [NAME] [CHART] [flags]
```

### action

- `generate-comparison-file`: 生成集群当前配置与 chart 配置的对比文件
- `show-default-config`: 打印默认插件配置，可以自行重定向保存
- `update-values-image-version`: 更新 values.yaml 的镜像版本，与集群中的镜像版本进行对齐

### example

Generate simplified Release and cluster runtime Manifests files to the default `./helm-fine-upgrade` directory. (You can then compare them using the vscode editor.)

Using the `--debug` flag allows you to view the executed SHELL commands

```bash
helm fine-upgrade generate-comparison-file \
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
- [ ] 同步集群镜像版本到 values.yaml 文件
- [ ] 接管集群对象到当前 Release
- [ ] Nacos 配置对比
- [ ] 中文文档
- [ ] 英文文档
