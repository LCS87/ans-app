# Script para rodar testes

param(
    [string]$Type = "all",
    [switch]$Coverage
)

Write-Host "🧪 Executando testes..." -ForegroundColor Cyan

# Ativa ambiente virtual
if (Test-Path .venv\Scripts\Activate.ps1) {
    & .\.venv\Scripts\Activate.ps1
}

# Define comando base
$command = "pytest"

# Adiciona filtros baseado no tipo
switch ($Type) {
    "smoke" {
        $command += " -m smoke"
        Write-Host "📋 Rodando testes smoke..." -ForegroundColor Yellow
    }
    "integration" {
        $command += " -m integration"
        Write-Host "📋 Rodando testes de integração..." -ForegroundColor Yellow
    }
    "unit" {
        $command += " -m 'not integration and not smoke'"
        Write-Host "📋 Rodando testes unitários..." -ForegroundColor Yellow
    }
    default {
        Write-Host "📋 Rodando todos os testes..." -ForegroundColor Yellow
    }
}

# Adiciona cobertura se solicitado
if ($Coverage) {
    $command += " --cov=api --cov-report=html --cov-report=term"
    Write-Host "📊 Gerando relatório de cobertura..." -ForegroundColor Yellow
}

# Executa testes
Write-Host "Comando: $command" -ForegroundColor Gray
Invoke-Expression $command

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Testes concluídos com sucesso!" -ForegroundColor Green
    
    if ($Coverage) {
        Write-Host "📊 Relatório de cobertura: htmlcov/index.html" -ForegroundColor Cyan
    }
}
else {
    Write-Host ""
    Write-Host "❌ Alguns testes falharam" -ForegroundColor Red
    exit 1
}
