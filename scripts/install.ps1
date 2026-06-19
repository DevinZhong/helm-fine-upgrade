param(
    [switch]$Update
)

$ErrorActionPreference = "Stop"

$PluginDir = if ($env:HELM_PLUGIN_DIR) {
    $env:HELM_PLUGIN_DIR
} else {
    Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
}

if ($env:HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL -eq "1") {
    Write-Host "Skipping fine-upgrade binary download because HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL=1"
    exit 0
}

$Version = $env:HELM_FINE_UPGRADE_BINARY_VERSION
if (-not $Version) {
    $PluginYaml = Get-Content -LiteralPath (Join-Path $PluginDir "plugin.yaml")
    $VersionLine = $PluginYaml | Where-Object { $_ -match "^version:" } | Select-Object -First 1
    $Version = ($VersionLine -split ":", 2)[1].Trim()
    $Version = $Version.Trim("'")
    $Version = $Version.Trim('"')
}

$Tag = "v$Version"
$Asset = "windows-amd64"
$Url = "https://github.com/DevinZhong/helm-fine-upgrade/releases/download/$Tag/helm-fine-upgrade-$Tag-$Asset.tar.gz"
$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("helm-fine-upgrade-" + [System.Guid]::NewGuid().ToString("N"))
$Archive = Join-Path $TempDir "package.tar.gz"
$ExtractDir = Join-Path $TempDir "extract"

New-Item -ItemType Directory -Force -Path $TempDir, $ExtractDir | Out-Null

try {
    Write-Host "Downloading fine-upgrade $Tag binary package for $Asset"
    Invoke-WebRequest -Uri $Url -OutFile $Archive
    tar -xzf $Archive -C $ExtractDir

    $PackageDir = Join-Path $ExtractDir "helm-fine-upgrade-$Tag-$Asset"
    $Binary = Join-Path $PackageDir "bin/fine-upgrade.exe"
    if (-not (Test-Path -LiteralPath $Binary)) {
        throw "Downloaded package does not contain bin/fine-upgrade.exe."
    }

    $BinDir = Join-Path $PluginDir "bin"
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    Copy-Item -LiteralPath $Binary -Destination (Join-Path $BinDir "fine-upgrade.exe") -Force
    Write-Host "Installed fine-upgrade binary: $(Join-Path $BinDir "fine-upgrade.exe")"
} finally {
    if (Test-Path -LiteralPath $TempDir) {
        Remove-Item -LiteralPath $TempDir -Recurse -Force
    }
}
