$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$specPath = Join-Path $repoRoot "packaging\app.spec"
$pyInstaller = Join-Path $repoRoot ".venv\Scripts\pyinstaller.exe"
$distPath = Join-Path $repoRoot "release"
$buildPath = Join-Path $repoRoot "build\pyinstaller"

if (-not (Test-Path $pyInstaller)) {
    throw "PyInstaller executable not found at $pyInstaller"
}

if (Test-Path $distPath) {
    Remove-Item -Recurse -Force $distPath
}

if (Test-Path $buildPath) {
    Remove-Item -Recurse -Force $buildPath
}

& $pyInstaller `
    --noconfirm `
    --clean `
    --distpath $distPath `
    --workpath $buildPath `
    $specPath

Write-Host ""
Write-Host "Build complete:"
Write-Host "  $distPath\OpenBCIGanglionUI\OpenBCIGanglionUI.exe"
