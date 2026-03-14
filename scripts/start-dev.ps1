# Script para iniciar ambiente de desenvolvimento

Write-Host "🚀 Iniciando ambiente de desenvolvimento ANS Intelligence..." -ForegroundColor Cyan

# Verifica se .env existe
if (-not (Test-Path .env)) {
    Write-Host "❌ Arquivo .env não encontrado. Execute setup.ps1 primeiro." -ForegroundColor Red
    exit 1
}

# Ativa ambiente virtual
if (Test-Path .venv\Scripts\Activate.ps1) {
    Write-Host "🔧 Ativando ambiente virtual..." -ForegroundColor Cyan
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "⚠ Ambiente virtual não encontrado. Execute setup.ps1 primeiro." -ForegroundColor Yellow
}

# Verifica se containers estão rodando
Write-Host "🐳 Verificando containers Docker..." -ForegroundColor Cyan
$mysqlRunning = docker ps --filter "name=mysql" --filter "status=running" -q
$redisRunning = docker ps --filter "name=redis" --filter "status=running" -q

if (-not $mysqlRunning -or -not $redisRunning) {
    Write-Host "⚠ Containers não estão rodando. Iniciando..." -ForegroundColor Yellow
    Set-Location docker
    docker-compose up -d
    Set-Location ..
    Write-Host "⏳ Aguardando containers iniciarem (10s)..." -ForegroundColor Cyan
    Start-Sleep -Seconds 10
}

Write-Host "✓ Containers rodando" -ForegroundColor Green

# Inicia backend em background
Write-Host "🔥 Iniciando backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000}"

# Aguarda backend iniciar
Write-Host "⏳ Aguardando backend iniciar (5s)..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Verifica se backend está respondendo
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "✓ Backend iniciado: http://localhost:8000" -ForegroundColor Green
    Write-Host "✓ API Docs: http://localhost:8000/api/v1/docs" -ForegroundColor Green
} catch {
    Write-Host "⚠ Backend pode não ter iniciado corretamente" -ForegroundColor Yellow
}

# Inicia frontend
Write-Host "🎨 Iniciando frontend..." -ForegroundColor Cyan
Set-Location frontend/vue-app
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {npm run dev}"
Set-Location ../..

Write-Host ""
Write-Host "✅ Ambiente de desenvolvimento iniciado!" -ForegroundColor Green
Write-Host ""
Write-Host "📍 URLs:" -ForegroundColor Cyan
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "   Backend: http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs: http://localhost:8000/api/v1/docs" -ForegroundColor White
Write-Host "   MySQL: localhost:3307" -ForegroundColor White
Write-Host "   Redis: localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "💡 Dica: Use Ctrl+C nas janelas para parar os serviços" -ForegroundColor Yellow
Write-Host ""
