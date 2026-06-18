# Changelog

## 1.0.0

### Added

- Publish the first stable command set for Helm fine-grained upgrade,
  release-state inspection, and resource adoption workflows.
- Add release documentation, contribution guidance, and a v1.0 release
  checklist.

## 0.9.0

### Added

- Add `--output-format yaml|json` for structured report commands.
- Add GitHub Actions CI for unit tests and Python compilation checks.
- Document local development checks in the README.

## 0.8.0

### Added

- Replace the single `action` positional parser with argparse subcommands.
- Add Kubernetes connection flags for supported commands: `--namespace`,
  `--kubeconfig`, `--context`, and `--timeout`.
- Propagate Kubernetes connection flags to Helm and kubectl command execution.
- Add explicit `--debug` handling for subcommands.

### Removed

- Remove the legacy shell-based command runner.

### Fixed

- Make CLI help work without importing command-specific optional dependencies.

## 0.7.0

### Added

- Add the `adopt-plan` action to analyze Helm ownership metadata before
  adopting existing cluster resources.
- Report resources as `managed`, `adoptable`, `needs_metadata_update`,
  `conflict`, or `missing`.
- Include kubectl annotation and label command previews for resources that can
  be adopted or repaired.

## 0.6.0

### Added

- Add the `state-check` action to compare Helm release storage with live cluster
  resources.
- When a chart is provided, compare the current chart render with Helm release
  storage to expose pending creates, updates, and deletes.
- Add structured summaries for runtime missing resources, runtime extras,
  runtime drift, chart creates, chart updates, and chart deletes.

## 0.5.0

### Added

- Add the `plan` action to generate a structured upgrade plan before mutating
  live cluster resources.
- Report per-resource statuses for `create`, `update`, `unchanged`, `adopt`,
  and `orphan`.
- Detect common immutable-field risks for Deployment, StatefulSet, DaemonSet,
  Service, and PersistentVolumeClaim resources.
- Reuse selector-aware related-resource discovery when building plans.

## 0.4.0

### Added

- Add standard-library unit tests for selector parsing, ignored-field cleanup,
  related manifest discovery, image version parsing, hash-suffixed resource
  matching, and Deployment readiness checks.
- Document safety notes for mutating actions and the current `kubectl apply`
  behavior.

### Changed

- Build Helm and kubectl calls as argument lists for safer path and argument
  handling.
- Default Helm namespace lookup to `default` when Helm does not provide
  `HELM_NAMESPACE`.
- Expand common runtime resource discovery to include StatefulSet, DaemonSet,
  Job, Ingress, and NetworkPolicy.
- Make selector parsing tolerate whitespace and trailing separators.

### Fixed

- Skip empty YAML documents emitted by `helm template`.
- Avoid failures when `image_version_fields` is missing or empty.
- Support image tags for multiple containers and digest-style images.
- Remove the `startupProbe.initialDelaySeconds` assumption from Deployment
  apply checks.
- Replace shell-pipeline Deployment readiness checks with YAML status parsing.
- Fix the Deployment readiness retry counter.
