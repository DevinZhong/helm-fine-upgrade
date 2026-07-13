# Examples

This directory contains Helm chart fixtures and a GitHub Actions workflow
snippet for trying `helm-fine-upgrade` commands.

## Example Chart

The chart in `simple-chart/` renders a Deployment, Service, and ConfigMap. Use it
as a safe local fixture for command syntax and report-shape checks.

Render with Helm:

```bash
helm template demo ./examples/simple-chart --namespace demo
```

Generate an upgrade plan:

```bash
helm fine-upgrade plan demo ./examples/simple-chart \
    --namespace demo \
    --values ./examples/simple-chart/values.yaml \
    --output-format json
```

Use the same plan as a CI gate:

```bash
helm fine-upgrade plan demo ./examples/simple-chart \
    --namespace demo \
    --values ./examples/simple-chart/values.yaml \
    --output-format json \
    --fail-on adopt,orphan,immutable_risk
```

Check runtime drift:

```bash
helm fine-upgrade state-check demo ./examples/simple-chart \
    --namespace demo \
    --values ./examples/simple-chart/values.yaml \
    --output-format json \
    --fail-on runtime_missing,runtime_extra,runtime_drift
```

## CI Workflow

`ci/github-actions.yml` shows where to install the plugin and run report gates in
a GitHub Actions workflow. Replace `my_release`, `my_namespace`, and chart paths
with your real release settings before using it in a repository.

## Adoption Fixture

`adoption-chart/` renders one ConfigMap. The integration test creates that
ConfigMap before Helm owns it, then verifies that `adopt-plan` reports it as
adoptable. It is intended for disposable test clusters only.
