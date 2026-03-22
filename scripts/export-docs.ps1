param(
    [string]$TargetPath = "..\modlink-studio.github.io"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$distPath = Join-Path $repoRoot "vpdocs/.vitepress/dist"
$targetRepoPath = Join-Path $repoRoot $TargetPath
$resolvedTargetRepoPath = (Resolve-Path -LiteralPath $targetRepoPath).Path

if (-not (Test-Path -LiteralPath (Join-Path $resolvedTargetRepoPath ".git"))) {
    throw "Target path is not a git repository: $resolvedTargetRepoPath"
}

Push-Location $repoRoot
try {
    npm run docs:pdoc:build
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    npm run docs:vp:build
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    Get-ChildItem -LiteralPath $resolvedTargetRepoPath -Force |
        Where-Object { $_.Name -ne ".git" } |
        Remove-Item -Recurse -Force

    Copy-Item -LiteralPath (Join-Path $distPath "*") -Destination $resolvedTargetRepoPath -Recurse -Force

    Write-Host "Docs exported to $resolvedTargetRepoPath"
}
finally {
    Pop-Location
}
