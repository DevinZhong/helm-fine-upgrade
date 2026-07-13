#!/usr/bin/env bash
set -euo pipefail

release_name="fine-upgrade-e2e"
namespace="fine-upgrade-e2e"
chart_path="${GITHUB_WORKSPACE:-$(pwd)}/examples/simple-chart"
adoption_chart_path="${GITHUB_WORKSPACE:-$(pwd)}/examples/adoption-chart"
report_dir="${FINE_UPGRADE_REPORT_DIR:-integration-reports}"
mkdir -p "$report_dir"

cleanup() {
  helm uninstall "$release_name" --namespace "$namespace" --wait >/dev/null 2>&1 || true
  kubectl delete namespace "$namespace" --wait=false >/dev/null 2>&1 || true
}
trap cleanup EXIT

assert_json_summary() {
  local file="$1"
  local field="$2"
  local expected="$3"
  python - "$file" "$field" "$expected" <<'PY'
import json
import sys

with open(sys.argv[1], encoding='utf-8') as report_file:
    report = json.load(report_file)
actual = report['summary'][sys.argv[2]]
expected = int(sys.argv[3])
if actual != expected:
    print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
    raise SystemExit(
        f"expected summary.{sys.argv[2]}={expected}, got {actual}")
PY
}

capture_baseline_diagnostics() {
  helm template --is-upgrade --no-hooks --skip-crds "$release_name" "$chart_path" \
    --namespace "$namespace" > "$report_dir/rendered-manifests.yaml"
  kubectl get deployment,service,configmap --namespace "$namespace" -o yaml \
    > "$report_dir/runtime-resources.yaml"
}

expect_fail_on() {
  local field="$1"
  local output_file="$2"
  set +e
  helm fine-upgrade plan "$release_name" "$chart_path" \
    --namespace "$namespace" \
    --output-format json \
    --fail-on "$field" >"$output_file"
  local exit_code=$?
  set -e
  if [ "$exit_code" -ne 2 ]; then
    echo "expected --fail-on $field to exit 2, got $exit_code" >&2
    exit 1
  fi
}

kubectl create namespace "$namespace"

helm upgrade --install "$release_name" "$chart_path" \
  --namespace "$namespace" \
  --wait \
  --timeout 2m

helm fine-upgrade doctor --output-format json > "$report_dir/doctor.json"

# A freshly installed release should agree with its rendered chart and runtime
# state after fields configured in src/config.yml are ignored.
helm fine-upgrade state-check "$release_name" "$chart_path" \
  --namespace "$namespace" \
  --output-format json > "$report_dir/state-clean.json"
if ! assert_json_summary "$report_dir/state-clean.json" runtime_drift 0; then
  capture_baseline_diagnostics
  exit 1
fi

# An out-of-band ConfigMap change must be visible to both state-check and plan.
kubectl patch configmap "${release_name}-config" --namespace "$namespace" \
  --type merge \
  --patch '{"data":{"message":"changed outside Helm"}}'

set +e
helm fine-upgrade state-check "$release_name" "$chart_path" \
  --namespace "$namespace" \
  --output-format json \
  --fail-on runtime_drift > "$report_dir/state-drift.json"
state_check_exit_code=$?
set -e
if [ "$state_check_exit_code" -ne 2 ]; then
  echo "expected state-check --fail-on runtime_drift to exit 2, got $state_check_exit_code" >&2
  exit 1
fi
assert_json_summary "$report_dir/state-drift.json" runtime_drift 1

expect_fail_on update "$report_dir/plan-drift.json"
assert_json_summary "$report_dir/plan-drift.json" update 1

# A pre-existing resource rendered by a chart but not owned by Helm is adoptable.
kubectl create configmap "${release_name}-adoptable" --namespace "$namespace" \
  --from-literal=managed-by=helm-fine-upgrade-integration-test
helm fine-upgrade adopt-plan "$release_name" "$adoption_chart_path" \
  --namespace "$namespace" \
  --output-format json > "$report_dir/adopt-plan.json"
assert_json_summary "$report_dir/adopt-plan.json" adoptable 1

# Mutating commands must not run in non-interactive CI without --yes.
set +e
helm fine-upgrade apply "$release_name" "$chart_path" \
  --namespace "$namespace" > "$report_dir/apply-without-confirmation.log" 2>&1
apply_exit_code=$?
set -e
if [ "$apply_exit_code" -ne 2 ]; then
  echo "expected apply without --yes to exit 2, got $apply_exit_code" >&2
  exit 1
fi

echo "kind integration scenarios passed"
