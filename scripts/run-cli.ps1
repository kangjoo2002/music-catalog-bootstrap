param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$srcDir = Join-Path $repoRoot "src"
if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
    $env:PYTHONPATH = $srcDir
} else {
    $env:PYTHONPATH = "$srcDir;$($env:PYTHONPATH)"
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m music_catalog_bootstrap @CliArgs
    exit $LASTEXITCODE
}

& python -m music_catalog_bootstrap @CliArgs
exit $LASTEXITCODE
