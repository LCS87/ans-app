# Script de setup do projeto ANS Intelligence (PowerShell)

Write-Host "🚀 Iniciando setup do projeto ANS Intelligence..." -ForegroundColor Cyan

# Verifica se Python está instalado
try {
    $pythonVersion = python --version
    Write-Host "✓ Python encontrado: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Python não encontrado. Instale Python 3.11+" -ForegroundColor Red
    exit 1
}

# Verifica se .env existe
if (-not (Test-Path .env)) {
    Write-Host "⚠ Arquivo .env não encontrado. Criando a partir do .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "✓ Arquivo .env criado. IMPORTANTE: Revise as configurações!" -ForegroundColor Green
}
else {
    Write-Host "✓ Arquivo .env já existe" -ForegroundColor Green
}

# Cria ambiente virtual se não existir
if (-not (Test-Path .venv)) {
    Write-Host "📦 Criando ambiente virtual..." -ForegroundColor Cyan
    python -m venv .venv
    Write-Host "✓ Ambiente virtual criado" -ForegroundColor Green
}
else {
    Write-Host "✓ Ambiente virtual já existe" -ForegroundColor Green
}

# Ativa ambiente virtual
Write-Host "🔧 Ativando ambiente virtual..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

# Instala dependências
Write-Host "📥 Instalando dependências Python..." -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "✓ Dependências instaladas" -ForegroundColor Green

# Verifica se Docker está instalado
try {
    $dockerVersion = docker --version
    Write-Host "✓ Docker encontrado: $dockerVersion" -ForegroundColor Green
    
    # Pergunta se quer subir os containers
    $response = Read-Host "Deseja iniciar os containers Docker (MySQL + Redis)? (s/n)"
    if ($response -eq 's' -or $response -eq 'S') {
        Write-Host "🐳 Iniciando containers Docker..." -ForegroundColor Cyan
        Set-Location docker
        docker-compose up -d
        Set-Location ..
        Write-Host "✓ Containers iniciados" -ForegroundColor Green
        Write-Host "   - MySQL: localhost:3307" -ForegroundColor White
        Write-Host "   - Redis: localhost:6379" -ForegroundColor White
    }
}
catch {
    Write-Host "⚠ Docker não encontrado. Você precisará instalar MySQL e Redis manualmente." -ForegroundColor Yellow
}

# Verifica se Node.js está instalado para o frontend
try {
    $nodeVersion = node --version
    Write-Host "✓ Node.js encontrado: $nodeVersion" -ForegroundColor Green
    
    # Instala dependências do frontend
    if (Test-Path "frontend/vue-app") {
        Write-Host "📦 Instalando dependências do frontend..." -ForegroundColor Cyan
        Set-Location frontend/vue-app
        npm install
        Set-Location ../..
        Write-Host "✓ Dependências do frontend instaladas" -ForegroundColor Green
    }
}
catch {
    Write-Host "⚠ Node.js não encontrado. Frontend não será configurado." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Setup concluído!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Próximos passos:" -ForegroundColor Cyan
Write-Host "   1. Revise o arquivo .env e ajuste as configurações"
Write-Host "   2. Inicie o backend: python -m uvicorn api.main:app --reload"
Write-Host "   3. Inicie o frontend: cd frontend/vue-app; npm run dev"
Write-Host "   4. Acesse: http://localhost:5173"
Write-Host ""
Write-Host "📚 Documentação:" -ForegroundColor Cyan
Write-Host "   - API Docs: http://localhost:8000/api/v1/docs"
Write-Host "   - Guia de Migração: GUIA_MIGRACAO.md"
Write-Host "   - Melhorias: MELHORIAS_RECOMENDADAS.md"
Write-Host ""
