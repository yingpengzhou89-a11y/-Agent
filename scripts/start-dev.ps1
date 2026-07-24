param(
    [switch]$NoFrontend,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $root 'logs'
$backendLog = Join-Path $logDir 'backend.log'
$backendErrorLog = Join-Path $logDir 'backend.error.log'
$frontendLog = Join-Path $logDir 'frontend.log'
$frontendErrorLog = Join-Path $logDir 'frontend.error.log'

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-ListeningPort([int]$Port) {
    return $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

try {
    docker compose up -d postgres | Out-Host
} catch {
    throw 'Unable to start PostgreSQL. Start Docker Desktop and run this script again.'
}

for ($attempt = 1; $attempt -le 30; $attempt++) {
    docker compose exec -T postgres pg_isready -U interview -d interview_copilot *> $null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 1
    if ($attempt -eq 30) { throw 'PostgreSQL was not ready within 30 seconds. Run: docker compose logs postgres' }
}

$pythonExe = ((conda run --no-capture-output -n Agent python -c "import sys; print(sys.executable)") |
    Select-Object -Last 1).Trim()
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw 'Conda environment Agent was not found. Create it with: conda create --name Agent python=3.13'
}

Push-Location (Join-Path $root 'backend')
try {
    & $pythonExe -m alembic upgrade head
} finally {
    Pop-Location
}

if (-not (Test-ListeningPort 18000)) {
    $backend = Start-Process -FilePath $pythonExe -WorkingDirectory (Join-Path $root 'backend') -WindowStyle Hidden `
        -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--reload', '--port', '18000') `
        -RedirectStandardOutput $backendLog -RedirectStandardError $backendErrorLog -PassThru
    Set-Content -LiteralPath (Join-Path $logDir 'backend.pid') -Value $backend.Id
}

if (-not $NoFrontend -and -not (Test-ListeningPort 5173)) {
    $npm = (Get-Command npm.cmd -ErrorAction Stop).Source
    $frontend = Start-Process -FilePath $npm -WorkingDirectory (Join-Path $root 'frontend') -WindowStyle Hidden `
        -ArgumentList @('run', 'dev') -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErrorLog -PassThru
    Set-Content -LiteralPath (Join-Path $logDir 'frontend.pid') -Value $frontend.Id
}

Write-Host 'Interview Copilot Agent is running.' -ForegroundColor Green
Write-Host 'Frontend: http://localhost:5173'
Write-Host 'Backend:  http://127.0.0.1:18000/docs'
Write-Host "Logs: $logDir"

if (-not $NoBrowser) {
    Start-Process 'http://localhost:5173'
}
