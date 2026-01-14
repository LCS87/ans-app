Param(
    [int]$Port = 8002,
    [int]$MaxRestarts = 0, # 0 = infinito
    [int]$BackoffSeconds = 5
)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvPython = Join-Path $ProjectRoot ".\.venv\Scripts\python.exe"
$LogDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$restartCount = 0
while ($true) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $logFile = Join-Path $LogDir "uvicorn_monitor_$timestamp.log"

    Write-Host "Starting uvicorn on port $Port, logs -> $logFile"

    # Execute Uvicorn in foreground and redirect output to log file
    & $VenvPython -m uvicorn api.main:app --host 127.0.0.1 --port $Port *> $logFile 2>&1
    $exitCode = $LASTEXITCODE

    Write-Host "Process exited with code $exitCode"
    $restartCount += 1

    if ($MaxRestarts -ne 0 -and $restartCount -ge $MaxRestarts) {
        Write-Host "Máximo de reinícios ($MaxRestarts) alcançado. Saindo."
        break
    }

    Write-Host "Aguardando $BackoffSeconds segundos antes de reiniciar..."
    Start-Sleep -Seconds $BackoffSeconds
}
