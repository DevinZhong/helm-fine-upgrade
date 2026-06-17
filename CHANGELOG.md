# Changelog

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
