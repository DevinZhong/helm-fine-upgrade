# helm-fine-upgrade

[中文文档](./docs/README.zh-CN.md)

A Helm plugin for controlled upgrades, release-state inspection, and adoption of
existing Kubernetes resources.

`helm-fine-upgrade` is designed for real clusters where Helm charts, live
resources, and values files may have drifted over time. It helps you inspect
upgrade impact, compare Helm release storage with runtime state, adopt existing
resources into a release, and apply carefully selected rendered manifests.

## When To Use It

Use this plugin when you need to:

- Preview what a chart upgrade would create, update, adopt, or leave orphaned.
- Check whether Helm release storage, the current chart, and live resources are
  still aligned.
- Adopt existing Kubernetes resources into a Helm release.
- Compare simplified rendered manifests with simplified runtime manifests.
- Perform a carefully scoped apply for selected workloads and related resources.
- Align values files with the image tags already running in the cluster.
- Migrate Deployment Pod labels when immutable selector fields are involved.

This project does not replace Helm, GitOps controllers, or `helm diff`. It is a
companion tool for messy migration and upgrade situations where you need a clear
plan before changing live cluster resources.

## Install

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
```

Install Python dependencies:

```bash
cd "$(helm env | grep HELM_PLUGINS | awk -F '"' '{print $2}')/helm-fine-upgrade" && pip install -r requirements.txt && cd -
```

Uninstall:

```bash
helm plugin uninstall fine-upgrade
```

## Usage

```bash
helm fine-upgrade [COMMAND] [NAME] [CHART] [flags]
```

View help:

```bash
helm fine-upgrade --help
helm fine-upgrade plan --help
```

## Commands

Read-only commands:

- `plan`: Generate an upgrade plan with creates, updates, adoptions, orphans,
  and immutable-field risks.
- `state-check`: Compare Helm release storage, live cluster resources, and
  optionally the current chart render.
- `adopt-plan`: Analyze whether existing cluster resources can be adopted by the
  target release.
- `generate-comparison-file`: Write simplified rendered and runtime manifests
  for manual diffing.
- `show-default-config`: Print the default ignore-field and image-field config.

Mutating commands:

- `apply`: Apply selected rendered manifests with `kubectl apply`.
- `update-values-image-version`: Update values.yaml image tags from live
  Deployment images.
- `update-ownership-metadata`: Add or repair Helm ownership metadata on
  existing resources.
- `rolling-update-pod-labels`: Migrate Deployment Pod labels by creating a
  temporary Deployment and switching traffic.

## Recommended Workflow

1. Check release and runtime state:

   ```bash
   helm fine-upgrade state-check my_release . \
       --namespace my_release_namespace \
       --values ./my-values.yaml
   ```

2. Generate an upgrade plan:

   ```bash
   helm fine-upgrade plan my_release . \
       --namespace my_release_namespace \
       --values ./my-values.yaml \
       --output-format json
   ```

3. Generate comparison files for manual review:

   ```bash
   helm fine-upgrade generate-comparison-file my_release . \
       --namespace my_release_namespace \
       --values ./my-values.yaml \
       --config ./.my-customized-config.yml
   ```

4. If the chart needs to adopt existing resources, inspect adoption first:

   ```bash
   helm fine-upgrade adopt-plan my_release . \
       --namespace my_release_namespace \
       --values ./my-values.yaml \
       -l app=my-service
   ```

5. Use mutating commands only after reviewing the plan and, where supported,
   `--dry-run`.

## Common Flags

Most commands support:

- `--namespace`: Helm release namespace.
- `--kubeconfig`: kubeconfig file path.
- `--context` / `--kube-context`: Kubernetes context.
- `--timeout`: kubectl request timeout, for example `30s`.
- `--values`: values file passed to `helm template`.
- `--config`: plugin config file path.
- `--selector` / `-l`: label selector used to scope Deployment-oriented flows.
- `--output-format`: `yaml` or `json` for structured report commands.
- `--dry-run`: preview supported mutating actions.
- `--debug`: print Helm and kubectl commands.

## Safety Notes

- Prefer `state-check`, `plan`, `adopt-plan`, and `generate-comparison-file`
  before running mutating commands.
- `apply`, `update-ownership-metadata`, and `rolling-update-pod-labels` may
  change live cluster resources.
- `apply` uses `kubectl apply` and does not update Helm release storage. Run a
  regular `helm upgrade` afterward when Helm release state must match runtime
  state.
- `rolling-update-pod-labels` is intended for special selector/label migration
  cases. Test it in a non-production environment before using it on critical
  workloads.
- `adopt-plan` is read-only. `update-ownership-metadata` performs the ownership
  metadata changes.

## Examples

State check in YAML:

```bash
helm fine-upgrade state-check my_release . \
    --namespace my_release_namespace \
    --values ./my-values.yaml \
    --config ./.my-customized-config.yml
```

Plan in JSON:

```bash
helm fine-upgrade plan my_release . \
    --namespace my_release_namespace \
    --values ./my-values.yaml \
    --output-format json
```

Adoption analysis:

```bash
helm fine-upgrade adopt-plan my_release . \
    --namespace my_release_namespace \
    --values ./my-values.yaml \
    -l app=my-service
```

Comparison files:

```bash
helm fine-upgrade generate-comparison-file my_release . \
    --namespace my_release_namespace \
    --values ./my-values.yaml \
    --config ./.my-customized-config.yml \
    --kubeconfig ~/.kube/my-kubeconfig.yaml \
    --debug
```

## Development

Install dependencies and run local checks:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p "*_tests.py"
python -m py_compile src/main.py src/services/helm_service.py src/services/metadata_service.py src/services/image_service.py src/services/pod_label_service.py src/utils/helm_utils.py src/utils/kube_ops_utils.py src/utils/dict_utils.py src/utils/manifest_utils.py src/utils/shell_utils.py src/utils/output_utils.py
```

GitHub Actions runs the same unit-test and compile checks on pull requests and
pushes to `main`.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

[Apache License 2.0](./LICENSE)
