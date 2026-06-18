# Binary Release

Starting with v1.1.0, GitHub Releases can publish standalone executables built
with PyInstaller.

These binaries bundle Python and the project dependencies, so users do not need
to install Python or run `pip install -r requirements.txt`.

## What Is Included

Each release asset contains:

- `bin/fine-upgrade` or `bin/fine-upgrade.exe`
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

## Usage

Download the archive for your platform from GitHub Releases, extract it, and run:

```bash
./bin/fine-upgrade --help
./bin/fine-upgrade plan my_release . --namespace my_namespace
```

On Windows:

```powershell
.\bin\fine-upgrade.exe --help
```

## Relationship With Helm Plugin Install

The normal Helm plugin installation remains supported:

```bash
helm plugin install https://github.com/DevinZhong/helm-fine-upgrade
```

Binary assets are currently standalone CLI packages. They do not replace the
source-based Helm plugin installation yet.

A future release may add a Helm install hook that automatically downloads the
right binary for the current platform.
