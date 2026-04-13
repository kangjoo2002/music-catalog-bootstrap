$ErrorActionPreference = "Stop"

$dataDir = ".catalog-data"
$outputFile = "out\sample-target.sql"

& "$PSScriptRoot\run-cli.ps1" export-sql .\fixtures\sample-target.properties $outputFile $dataDir
exit $LASTEXITCODE
