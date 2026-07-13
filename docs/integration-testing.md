# Integration Testing

The integration workflow creates a disposable [kind](https://kind.sigs.k8s.io/)
cluster for every pull request and push to `main`. It installs the plugin from
the checked-out source in Python source mode, so the workflow validates the
current plugin metadata, runtime wrapper, CLI, Helm, and `kubectl` together.

The workflow uses only repository fixtures and a temporary namespace. It does
not use a shared Kubernetes cluster, kubeconfig, token, or other secret.

## Covered Scenarios

- A freshly installed Helm release has no detected runtime drift.
- An out-of-band ConfigMap change is detected by `state-check` and `plan`.
- `--fail-on` exits with code `2` when a selected condition is present.
- A pre-existing unowned ConfigMap is reported as adoptable.
- A mutating command is rejected in non-interactive CI without `--yes`.

## Local Execution

Prerequisites: Docker, kind, Helm, kubectl, Python, and the dependencies in
`requirements.txt`.

```bash
kind create cluster --name helm-fine-upgrade-ci
python -m pip install -r requirements.txt
HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL=1 helm plugin install .
bash tests/integration/kind.sh
kind delete cluster --name helm-fine-upgrade-ci
```

The test script removes its temporary namespace even when a scenario fails.
Run it only against a disposable kind cluster; it intentionally creates,
patches, and deletes test resources.

## Company Environment Validation

Use a separate non-production cluster and dedicated test namespace for manual
or scheduled validation. Do not add its credentials to this repository or make
public GitHub Actions connect to it. See the project README and security policy
for safe reporting and contribution guidance.
