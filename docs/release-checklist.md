# Release Checklist

Use this checklist before publishing a stable release.

## Local Checks

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p "*_tests.py"
python -m py_compile src/main.py src/services/helm_service.py src/services/metadata_service.py src/services/image_service.py src/services/pod_label_service.py src/utils/helm_utils.py src/utils/kube_ops_utils.py src/utils/dict_utils.py src/utils/manifest_utils.py src/utils/shell_utils.py src/utils/output_utils.py
```

## CLI Smoke Checks

```bash
python src/main.py --help
python src/main.py plan --help
python src/main.py state-check --help
python src/main.py adopt-plan --help
```

## Documentation Checks

- `plugin.yaml` version matches the release version.
- `CHANGELOG.md` contains the release entry.
- `README.md` examples match supported CLI flags.
- Mutating commands are clearly marked.
- Helm release storage implications are documented.

## Optional Cluster Smoke Test

Use a non-production cluster such as kind or minikube.

1. Install or upgrade a simple Helm chart.
2. Run `helm fine-upgrade state-check`.
3. Run `helm fine-upgrade plan`.
4. Create a manually managed resource rendered by the chart.
5. Run `helm fine-upgrade adopt-plan`.
6. Verify `--output-format json` emits machine-readable JSON.

## Publish

```bash
git status --short
git tag v1.0.0
git push origin main --tags
```

For v1.1.0 and later, pushing a `v*.*.*` tag also triggers the GitHub Release
workflow that builds standalone binary assets.

After publishing, verify plugin installation from GitHub:

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
helm fine-upgrade --help
```
