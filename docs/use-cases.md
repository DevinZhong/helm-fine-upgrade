# Use Cases

This guide shows when `helm-fine-upgrade` is useful and which command to start
with. The plugin is meant to make risky Helm changes visible before you mutate a
cluster.

## Upgrade Risk Review

Use this when you are about to upgrade a release and want to know what the chart
will create, update, adopt, or leave behind.

```bash
helm fine-upgrade plan my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --output-format json
```

For CI, fail the job when the plan contains resource adoption, orphaned release
resources, or immutable-field risk:

```bash
helm fine-upgrade plan my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --output-format json \
    --fail-on adopt,orphan,immutable_risk
```

Useful summary fields:

- `create`: resources rendered by the chart that do not exist yet.
- `update`: resources that exist but differ from the rendered chart.
- `adopt`: resources rendered by the chart that already exist in the cluster
  but are not tracked by the release.
- `orphan`: resources tracked by the release but no longer rendered by the
  chart.
- `immutable_risk`: resources with possible immutable-field changes, such as a
  Deployment selector change.

## Runtime Drift Check

Use this when you suspect the live cluster no longer matches Helm release
storage, for example after manual `kubectl` changes.

```bash
helm fine-upgrade state-check my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --output-format json
```

For CI, fail when release storage and live resources drift:

```bash
helm fine-upgrade state-check my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --output-format json \
    --fail-on runtime_missing,runtime_extra,runtime_drift
```

Useful summary fields:

- `runtime_missing`: resources recorded in the release but missing from the
  cluster.
- `runtime_extra`: live resources associated with the release but missing from
  release storage.
- `runtime_drift`: resources that exist in both places but differ after ignored
  fields are removed.
- `chart_create`, `chart_update`, `chart_delete`: changes between release
  storage and the current chart render.

## Existing Resource Adoption

Use this when a chart should manage resources that already exist in the cluster.
Start with an adoption report before modifying ownership metadata.

```bash
helm fine-upgrade adopt-plan my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --output-format yaml
```

Fail CI when resources are already owned by another release:

```bash
helm fine-upgrade adopt-plan my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --output-format json \
    --fail-on conflict
```

If the report is expected, preview metadata changes:

```bash
helm fine-upgrade update-ownership-metadata my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --dry-run
```

Apply them only after review:

```bash
helm fine-upgrade update-ownership-metadata my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --yes
```

## Selector Or Label Migration

Use this when a Deployment selector or Pod label needs to change. Kubernetes
does not allow some selector fields to be updated in place, so inspect the risk
first.

```bash
helm fine-upgrade plan my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --selector app=my-service \
    --fail-on immutable_risk
```

If a controlled label migration is required, preview the rolling workflow:

```bash
helm fine-upgrade rolling-update-pod-labels my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --selector app=my-service \
    --dry-run
```

Run the mutating command only after validating the plan in a non-production
environment:

```bash
helm fine-upgrade rolling-update-pod-labels my_release ./chart \
    --namespace my_namespace \
    --values ./values.yaml \
    --selector app=my-service \
    --yes
```
