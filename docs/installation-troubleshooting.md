# Installation And Troubleshooting

This guide collects installation notes for Helm 3, Helm 4, binary packages, and
common platform issues.

## Recommended Install

Helm 3:

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
```

Helm 4:

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade --verify=false
```

Helm 4 introduced plugin source verification. The GitHub source install path is
not currently published with Helm plugin provenance metadata, so Helm 4 users
need `--verify=false`. This does not disable the plugin's own binary download
logic; it only skips Helm's plugin source verification step.

## Requirements

- `helm` must be installed and available in `PATH`.
- `kubectl` must be installed and available in `PATH` for commands that inspect
  or mutate cluster resources.
- Kubernetes credentials must be configured for the target cluster.
- The install hook needs network access to GitHub Releases unless source mode is
  explicitly requested.

## What The Install Hook Does

When installed from the source repository, Helm first downloads the repository
into the local plugin directory. The plugin install hook then:

1. Detects the current operating system and CPU architecture.
2. Selects the matching GitHub Release asset.
3. Downloads the binary plugin package for that platform.
4. Copies `bin/fine-upgrade` or `bin/fine-upgrade.exe` into the installed plugin
   directory.

The downloaded executable bundles Python and Python dependencies, but still
calls external `helm` and `kubectl` commands.

## Source Mode

Use source mode for development or for platforms without a published binary
package:

```bash
HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL=1 helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
cd "$(helm env | grep HELM_PLUGINS | awk -F '"' '{print $2}')/helm-fine-upgrade"
python -m pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
$env:HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL = "1"
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade --verify=false
Remove-Item Env:\HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL
```

## Common Issues

### Helm 4: plugin source does not support verification

Error:

```text
plugin source does not support verification. Use --verify=false to skip verification
```

Use:

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade --verify=false
```

### Windows local path install fails with symlink privilege

Error:

```text
symlink ... A required privilege is not held by the client
```

This can happen when installing from a local directory on Windows because Helm's
local development install mode may create a symlink. Prefer installing from the
GitHub URL, or enable Windows Developer Mode / run a shell with the required
privilege when doing local plugin development.

### Binary download fails during install

Check:

- The machine can access `https://github.com/DevinZhong/helm-fine-upgrade`.
- The release tag in `plugin.yaml` exists.
- Your platform has a published release asset.
- `curl` or `wget` is available on Linux/macOS.
- PowerShell can run `Invoke-WebRequest` on Windows.

### linux-arm64 install is not supported yet

Linux ARM64 binaries are not published yet. Use source mode, or build a native
binary package for the platform.

### helm or kubectl is not found

Run:

```bash
helm version
kubectl version --client
```

Install the missing command and make sure it is available in `PATH`.

### PowerShell execution policy blocks scripts

The plugin uses `powershell.exe -ExecutionPolicy Bypass -File ...` for hook and
runtime scripts. If your environment still blocks script execution, review local
security policy or install from the release asset manually.

## Manual Release Asset Install

Manual release asset installation avoids the source install hook:

```bash
VERSION=v1.6.0
helm plugin install "https://github.com/DevinZhong/helm-fine-upgrade/releases/download/${VERSION}/helm-fine-upgrade-${VERSION}-linux-amd64.tar.gz"
```

Windows:

```powershell
$Version = "v1.6.0"
helm plugin install "https://github.com/DevinZhong/helm-fine-upgrade/releases/download/$Version/helm-fine-upgrade-$Version-windows-amd64.tar.gz"
```
