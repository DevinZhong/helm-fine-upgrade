$ErrorActionPreference = "Stop"

$PluginDir = if ($env:HELM_PLUGIN_DIR) {
    $env:HELM_PLUGIN_DIR
} else {
    Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
}

$Binary = Join-Path $PluginDir "bin/fine-upgrade.exe"
if (Test-Path -LiteralPath $Binary) {
    & $Binary @args
    exit $LASTEXITCODE
}

$Main = Join-Path $PluginDir "src/main.py"
$Python = Get-Command python -ErrorAction SilentlyContinue
if ($Python) {
    & $Python.Source $Main @args
    exit $LASTEXITCODE
}

Write-Error "fine-upgrade binary was not found and Python is not available. Run the install hook again or reinstall the plugin from GitHub Releases."
exit 1
