$ErrorActionPreference = "Stop"

$dataDir = ".catalog-data"
& "$PSScriptRoot\run-cli.ps1" plan .\fixtures\sample-target.properties $dataDir
exit $LASTEXITCODE
