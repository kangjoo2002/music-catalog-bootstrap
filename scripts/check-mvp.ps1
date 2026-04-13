$ErrorActionPreference = "Stop"

$dataDir = ".catalog-data-check"

if (Test-Path $dataDir) {
    Remove-Item $dataDir -Recurse -Force
}

$first = powershell -ExecutionPolicy Bypass -File .\scripts\run-sample.ps1 -DataDir $dataDir
$second = powershell -ExecutionPolicy Bypass -File .\scripts\run-sample.ps1 -DataDir $dataDir

$firstText = ($first -join [Environment]::NewLine)
$secondText = ($second -join [Environment]::NewLine)

if ($firstText -notmatch "Auto create: 3" -or
    $firstText -notmatch "Auto match: 0" -or
    $firstText -notmatch "Review: 1" -or
    $firstText -notmatch "Failure: 1") {
    throw "첫 실행 결과가 기대와 다릅니다."
}

if ($secondText -notmatch "Auto create: 0" -or
    $secondText -notmatch "Auto match: 3" -or
    $secondText -notmatch "Review: 1" -or
    $secondText -notmatch "Failure: 1") {
    throw "두 번째 실행 결과가 기대와 다릅니다."
}

Write-Host "검증 성공"
Write-Host ""
Write-Host "첫 실행"
Write-Host $firstText
Write-Host ""
Write-Host "두 번째 실행"
Write-Host $secondText
