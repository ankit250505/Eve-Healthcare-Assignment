$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DataDir = Join-Path $ProjectRoot ".postgres-data"
$PasswordFile = Join-Path $ProjectRoot ".postgres-pw"
$Port = "55432"
$Database = "eve_healthcare"
$User = "eve"
$Password = "eve_dev_password"

if (-not (Test-Path $PasswordFile)) {
    Set-Content -Path $PasswordFile -Value $Password -NoNewline
}

if (-not (Test-Path $DataDir)) {
    initdb -D $DataDir -U $User --pwfile $PasswordFile --auth-local trust --auth-host scram-sha-256
}

$Ready = $false
pg_isready -h localhost -p $Port -U $User *> $null
if ($LASTEXITCODE -eq 0) {
    $Ready = $true
}

if (-not $Ready) {
    Start-Process -FilePath postgres -ArgumentList "-D", $DataDir, "-p", $Port -WindowStyle Hidden
    for ($Attempt = 0; $Attempt -lt 10; $Attempt++) {
        Start-Sleep -Seconds 1
        pg_isready -h localhost -p $Port -U $User *> $null
        if ($LASTEXITCODE -eq 0) {
            $Ready = $true
            break
        }
    }
}

if (-not $Ready) {
    throw "PostgreSQL did not become ready on localhost:$Port."
}

$env:PGPASSWORD = $Password
$ExistingDatabase = psql -h localhost -p $Port -U $User -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$Database'"
if ($ExistingDatabase.Trim() -ne "1") {
    createdb -h localhost -p $Port -U $User $Database
}

Write-Host "PostgreSQL is ready on localhost:$Port for database '$Database'."
