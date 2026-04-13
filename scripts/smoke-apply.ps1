param(
    [ValidateSet("postgresql", "mysql")]
    [string]$Engine = "postgresql",
    [switch]$Cleanup
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Resolve-PythonCommand() {
    foreach ($candidate in @("python", "python3")) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            return $candidate
        }
    }
    throw "Required command not found: python or python3"
}

function Invoke-CommandQuietly([string[]]$Command) {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $Command[0] @($Command[1..($Command.Length - 1)]) *> $null
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    return $exitCode
}

Require-Command "docker"
$pythonCommand = Resolve-PythonCommand
$srcDir = Join-Path $root "src"
$pathSeparator = [IO.Path]::PathSeparator
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$srcDir$pathSeparator$($env:PYTHONPATH)"
}
else {
    $env:PYTHONPATH = $srcDir
}

if ((Invoke-CommandQuietly @("docker", "info")) -ne 0) {
    throw "Docker daemon is not available. Start Docker Desktop and try again."
}

if ($Engine -eq "postgresql") {
    $composeFile = Join-Path $root "examples\direct-apply\postgresql\docker-compose.yml"
    $profile = Join-Path $root "fixtures\sample-target-postgres-apply.properties"
    $env:MCB_PG_PASSWORD = "bootstrap"
    $dataDir = ".catalog-data-apply-postgres"
    $verifyCommand = @(
        "docker", "compose", "-f", $composeFile, "exec", "-T", "db",
        "psql", "--username", "bootstrap", "--dbname", "music_app",
        "-c", "select count(*) as artist_count from service_artists; select count(*) as release_count from service_releases;"
    )
}
else {
    $composeFile = Join-Path $root "examples\direct-apply\mysql\docker-compose.yml"
    $profile = Join-Path $root "fixtures\sample-target-mysql-apply.properties"
    $env:MCB_MYSQL_PASSWORD = "bootstrap"
    $dataDir = ".catalog-data-apply-mysql"
    $verifyCommand = @(
        "docker", "compose", "-f", $composeFile, "exec", "-T", "db",
        "mysql", "--host=127.0.0.1", "--user=bootstrap", "--password=bootstrap", "music_app",
        "-e", "select count(*) as artist_count from service_artists; select count(*) as release_count from service_releases;"
    )
}

try {
    if (Test-Path $dataDir) {
        Remove-Item -Recurse -Force $dataDir
    }
    & docker compose -f $composeFile up -d --wait
    & $pythonCommand -m music_catalog_bootstrap bootstrap fixtures\sample_releases.csv $profile --data-dir $dataDir --apply
    $verifyExecutable = $verifyCommand[0]
    $verifyArguments = $verifyCommand[1..($verifyCommand.Length - 1)]
    & $verifyExecutable @verifyArguments
}
finally {
    if ($Cleanup -and (Test-Path $dataDir)) {
        Remove-Item -Recurse -Force $dataDir
    }
    if ($Cleanup) {
        & docker compose -f $composeFile down -v
    }
}
