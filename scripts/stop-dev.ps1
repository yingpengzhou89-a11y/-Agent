$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $root 'logs'

foreach ($service in 'backend', 'frontend') {
    $pidFile = Join-Path $logDir "$service.pid"
    if (Test-Path -LiteralPath $pidFile) {
        $processId = [int](Get-Content -LiteralPath $pidFile -Raw)
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $processId -Force
            Write-Host "已停止 $service（PID $processId）。"
        }
        Remove-Item -LiteralPath $pidFile -Force
    }
}

Push-Location $root
try {
    docker compose stop postgres
} finally {
    Pop-Location
}
