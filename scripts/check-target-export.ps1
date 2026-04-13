$ErrorActionPreference = "Stop"

$dataDir = ".catalog-data-target-check"
$outputFile = "out\target-check.sql"

if (Test-Path $dataDir) {
    Remove-Item $dataDir -Recurse -Force
}

if (Test-Path $outputFile) {
    Remove-Item $outputFile -Force
}

$importText = powershell -ExecutionPolicy Bypass -File .\scripts\run-sample.ps1 -DataDir $dataDir
$planText = powershell -ExecutionPolicy Bypass -File .\scripts\run-cli.ps1 plan .\fixtures\sample-target.properties $dataDir
$exportText = powershell -ExecutionPolicy Bypass -File .\scripts\run-cli.ps1 export-sql .\fixtures\sample-target.properties $outputFile $dataDir

$importOutput = ($importText -join [Environment]::NewLine)
$planOutput = ($planText -join [Environment]::NewLine)
$exportOutput = ($exportText -join [Environment]::NewLine)

if ($planOutput -notmatch "Canonical artists: 3" -or
    $planOutput -notmatch "Canonical releases: 3" -or
    $planOutput -notmatch "Latest review: 1" -or
    $planOutput -notmatch "Latest failure: 1") {
    throw "계획 결과가 기대와 다릅니다."
}

if (-not (Test-Path $outputFile)) {
    throw "SQL 파일이 생성되지 않았습니다."
}

$sqlText = Get-Content $outputFile -Raw
if ($sqlText -notmatch 'INSERT IGNORE INTO `service_artists`' -or
    $sqlText -notmatch 'INSERT IGNORE INTO `service_releases`') {
    throw "SQL 내용이 기대와 다릅니다."
}

Write-Host "검증 성공"
Write-Host ""
Write-Host "입력 결과"
Write-Host $importOutput
Write-Host ""
Write-Host "계획 결과"
Write-Host $planOutput
Write-Host ""
Write-Host "내보내기 결과"
Write-Host $exportOutput
