# helm-cluster-diff

Generate a Helm release and cluster configuration file that is convenient for comparison.

## Usage

### basic command struct

```bash
helm cluster-diff [ACTION] [NAME] [CHART] [flags]
```

### action

- `generate-comparison-file`

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
- [ ] 中文文档
- [ ] 英文文档
