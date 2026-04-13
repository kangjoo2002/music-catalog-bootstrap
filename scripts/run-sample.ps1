param(
    [string]$InputFile = "fixtures/sample_releases.csv",
    [string]$DataDir = ".catalog-data"
)

$ErrorActionPreference = "Stop"
& "$PSScriptRoot\run-cli.ps1" import $InputFile $DataDir
exit $LASTEXITCODE
