$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$buildScript = Join-Path $repoRoot "scripts\build-release.py"

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $buildScript
} else {
    & python $buildScript
}

exit $LASTEXITCODE
