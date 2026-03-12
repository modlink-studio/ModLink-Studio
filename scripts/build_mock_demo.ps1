param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pyprojectPath = Join-Path $repoRoot "pyproject.toml"
$distRoot = Join-Path $repoRoot "dist"
$buildRoot = Join-Path $repoRoot "build"
$releaseRoot = Join-Path $repoRoot "release"
$specPath = Join-Path $repoRoot "packaging\\mock_demo.spec"
$pyInstallerPath = Join-Path $repoRoot ".venv\\Scripts\\pyinstaller.exe"
$appName = "OpenBCIGanglionUI-MockDemo"
$releaseName = "$appName-$Version-windows"
$releaseDir = Join-Path $releaseRoot $releaseName
$zipPath = Join-Path $releaseRoot "$releaseName.zip"
$notesPath = Join-Path $releaseDir "README.txt"

if ([string]::IsNullOrWhiteSpace($Version)) {
    $versionLine = Select-String -Path $pyprojectPath -Pattern '^version = "(.+)"$' | Select-Object -First 1
    if (-not $versionLine) {
        throw "Could not determine project version from $pyprojectPath"
    }
    $Version = $versionLine.Matches[0].Groups[1].Value
    $releaseName = "$appName-$Version-windows"
    $releaseDir = Join-Path $releaseRoot $releaseName
    $zipPath = Join-Path $releaseRoot "$releaseName.zip"
    $notesPath = Join-Path $releaseDir "README.txt"
}

if (Test-Path (Join-Path $distRoot $appName)) {
    Remove-Item -Recurse -Force (Join-Path $distRoot $appName)
}

if (Test-Path (Join-Path $buildRoot $appName)) {
    Remove-Item -Recurse -Force (Join-Path $buildRoot $appName)
}

if (Test-Path $releaseDir) {
    Remove-Item -Recurse -Force $releaseDir
}

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

if (-not (Test-Path $pyInstallerPath)) {
    throw "PyInstaller executable not found at $pyInstallerPath"
}

& $pyInstallerPath --noconfirm --clean $specPath
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

New-Item -ItemType Directory -Path $releaseDir | Out-Null
Copy-Item -Recurse -Force (Join-Path $distRoot $appName) $releaseDir
Copy-Item -Force (Join-Path $repoRoot "README.md") $releaseDir

@"
OpenBCI Ganglion UI Mock Demo

This package bundles the mock-data demo build.

Run:
  OpenBCIGanglionUI-MockDemo\OpenBCIGanglionUI-MockDemo.exe

Notes:
  - This build uses the mock backend included in the app.
  - It is intended for UI demonstration and workflow walkthroughs.
  - Recorded files are written under the configured save directory.
"@ | Set-Content -Path $notesPath -Encoding UTF8

Compress-Archive -Path $releaseDir -DestinationPath $zipPath

Write-Host "Built release package:"
Write-Host "  $zipPath"
