# Contributing

Thanks for improving `helm-fine-upgrade`.

## Development Setup

```bash
python -m pip install -r requirements.txt
```

Run tests:

```bash
python -m unittest discover -s tests -p "*_tests.py"
```

Run syntax checks:

```bash
python -m py_compile src/main.py src/services/helm_service.py src/services/metadata_service.py src/services/image_service.py src/services/pod_label_service.py src/utils/helm_utils.py src/utils/kube_ops_utils.py src/utils/dict_utils.py src/utils/manifest_utils.py src/utils/shell_utils.py src/utils/output_utils.py
```

## Pull Requests

- Keep changes focused.
- Add or update tests for behavior changes.
- Prefer read-only planning/reporting behavior before adding mutating behavior.
- Document new commands, flags, and safety implications in `README.md`.
- Update `CHANGELOG.md` for user-visible changes.

## Commit Style

Use Conventional Commits where possible:

```text
feat: add upgrade plan output
fix: handle missing helm namespace
docs: update release checklist
test: cover adoption conflict handling
```

## Safety Guidelines

- Treat live Kubernetes mutations as high risk.
- Prefer `--dry-run` support for mutating commands.
- Keep Helm release storage implications explicit in documentation.
- Do not silently take ownership of resources that belong to another Helm
  release.
