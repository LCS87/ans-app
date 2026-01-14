Param(
    [int]$Port = 8002
)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvPython = Join-Path $ProjectRoot ".\.venv\Scripts\python.exe"
$LogDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $LogDir "uvicorn_$timestamp.log"

# Check if port in use
$connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($connection) {
    Write-Host "Port $Port is in use. Aborting."
    exit 1
}

Write-Host "Starting uvicorn on port $Port, logs -> $logFile"
Start-Process -FilePath $VenvPython -ArgumentList "-m","uvicorn","api.main:app","--host","127.0.0.1","--port",$Port -WorkingDirectory $ProjectRoot -RedirectStandardOutput $logFile -RedirectStandardError $logFile -NoNewWindow -PassThru

Write-Host "Uvicorn started."