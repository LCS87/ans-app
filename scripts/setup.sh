#!/bin/bash
# Script de setup do projeto ANS Intelligence

set -e

echo "🚀 Iniciando setup do projeto ANS Intelligence..."

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verifica se Python está instalado
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python não encontrado. Instale Python 3.11+${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python encontrado: $(python --version)${NC}"

# Verifica se .env existe
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ Arquivo .env não encontrado. Criando a partir do .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ Arquivo .env criado. IMPORTANTE: Revise as configurações!${NC}"
else
    echo -e "${GREEN}✓ Arquivo .env já existe${NC}"
fi

# Cria ambiente virtual se não existir
if [ ! -d ".venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python -m venv .venv
    echo -e "${GREEN}✓ Ambiente virtual criado${NC}"
else
    echo -e "${GREEN}✓ Ambiente virtual já existe${NC}"
fi

# Ativa ambiente virtual
echo "🔧 Ativando ambiente virtual..."
source .venv/bin/activate || source .venv/Scripts/activate

# Instala dependências
echo "📥 Instalando dependências Python..."
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✓ Dependências instaladas${NC}"

# Verifica se Docker está instalado
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker encontrado: $(docker --version)${NC}"
    
    # Pergunta se quer subir os containers
    read -p "Deseja iniciar os containers Docker (MySQL + Redis)? (s/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        echo "🐳 Iniciando containers Docker..."
        cd docker
        docker-compose up -d
        cd ..
        echo -e "${GREEN}✓ Containers iniciados${NC}"
        echo "   - MySQL: localhost:3307"
        echo "   - Redis: localhost:6379"
    fi
else
    echo -e "${YELLOW}⚠ Docker não encontrado. Você precisará instalar MySQL e Redis manualmente.${NC}"
fi

# Verifica se Node.js está instalado para o frontend
if command -v node &> /dev/null; then
    echo -e "${GREEN}✓ Node.js encontrado: $(node --version)${NC}"
    
    # Instala dependências do frontend
    if [ -d "frontend/vue-app" ]; then
        echo "📦 Instalando dependências do frontend..."
        cd frontend/vue-app
        npm install
        cd ../..
        echo -e "${GREEN}✓ Dependências do frontend instaladas${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Node.js não encontrado. Frontend não será configurado.${NC}"
fi

echo ""
echo -e "${GREEN}✅ Setup concluído!${NC}"
echo ""
echo "📝 Próximos passos:"
echo "   1. Revise o arquivo .env e ajuste as configurações"
echo "   2. Inicie o backend: python -m uvicorn api.main:app --reload"
echo "   3. Inicie o frontend: cd frontend/vue-app && npm run dev"
echo "   4. Acesse: http://localhost:5173"
echo ""
echo "📚 Documentação:"
echo "   - API Docs: http://localhost:8000/api/v1/docs"
echo "   - Guia de Migração: GUIA_MIGRACAO.md"
echo "   - Melhorias: MELHORIAS_RECOMENDADAS.md"
echo ""
