# Binary Release

Starting with v1.2.0, installing the source repository downloads the matching
Helm-installable binary plugin package from GitHub Releases. The release assets
are built with PyInstaller.

These binaries bundle Python and the project dependencies, so users do not need
to install Python or run `pip install -r requirements.txt`.

## What Is Included

Each release asset contains:

- `bin/fine-upgrade` or `bin/fine-upgrade.exe`
- `plugin.yaml`
- `README.md`
- `CHANGELOG.md`
- `LICENSE`
- `docs/`

The executable still calls external `helm` and `kubectl` commands, so the target
machine must have Helm, kubectl, and Kubernetes credentials configured.

## Supported Assets

The release workflow builds:

- `linux-amd64`
- `darwin-amd64`
- `darwin-arm64`
- `windows-amd64`

Linux ARM64 is not built yet because PyInstaller generally needs to build on the
target platform. It can be added later with a native runner or an emulated build
setup.

## Install

Recommended:

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
```

The install hook detects the current platform and downloads the matching release
asset.

Manual installation from a release asset is also supported:

```bash
VERSION=v1.2.0
helm plugin install "https://github.com/DevinZhong/helm-fine-upgrade/releases/download/${VERSION}/helm-fine-upgrade-${VERSION}-linux-amd64.tar.gz"
```

On Windows:

```powershell
$Version = "v1.2.0"
helm plugin install "https://github.com/DevinZhong/helm-fine-upgrade/releases/download/$Version/helm-fine-upgrade-$Version-windows-amd64.tar.gz"
```

After installation:

```bash
helm fine-upgrade --help
helm fine-upgrade plan my_release . --namespace my_namespace
```

## Relationship With Helm Plugin Install

The normal Helm plugin install command is the recommended installation path for
end users:

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
```

It installs the source repository first, then the install hook downloads the
matching binary package into `bin/`.

Source mode remains supported for development or unsupported platforms:

```bash
HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL=1 helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
cd "$(helm env | grep HELM_PLUGINS | awk -F '"' '{print $2}')/helm-fine-upgrade" && pip install -r requirements.txt && cd -
```

## Distribution Channels

The canonical download channel is GitHub Releases. The release asset URL can be
used directly with `helm plugin install`.

For discovery, the project can also be listed on Artifact Hub as a Helm plugin
repository later. Artifact Hub improves visibility, but the release assets should
remain the source of truth for downloadable packages.
