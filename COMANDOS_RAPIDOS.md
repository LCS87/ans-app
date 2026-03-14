# ⚡ Comandos Rápidos

Referência rápida de comandos para o projeto ANS Intelligence.

## 🚀 Setup Inicial

```powershell
# Windows - Setup completo
.\scripts\setup.ps1

# Linux/Mac - Setup completo
chmod +x scripts/setup.sh && ./scripts/setup.sh
```

## 🔧 Desenvolvimento

### Iniciar Tudo (Automático)

```powershell
# Windows
.\scripts\start-dev.ps1
```
siar Manualmente

```bash
# 1. Ativar ambiente virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 2. Iniciar containers
cd docker && docker-compose up -d && cd ..

# 3. Backend (Terminal 1)
python -m uvicorn api.main:app --reload

# 4. Frontend (Terminal 2)
cd frontend/vue-app && npm run dev
```

## 🐳 Docker

```bash
# Iniciar containers
cd docker && docker-compose up -d

# Parar containers
docker-compose down

# Ver logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
docker-compose logs -f redis

# Reiniciar um serviço
docker-compose restart backend

# Rebuild
docker-compose up -d --build
```

## 🧪 Testes

```powershell
# Todos os testes
pytest

# Com cobertura
pytest --cov=api --cov-report=html

# Apenas smoke tests
pytest -m smoke

# Apenas integration tests
pytest -m integration

# Testes específicos
pytest tests/test_refactored_api.py -v

# Com script (Windows)
.\scripts\test.ps1
.\scripts\test.ps1 -Coverage
.\scripts\test.ps1 -Type smoke
```

## 📦 Dependências

```bash
# Instalar/Atualizar dependências Python
pip install -r requirements.txt

# Instalar dependências frontend
cd frontend/vue-app && npm install

# Adicionar nova dependência
pip install nome-pacote
pip freeze > requirements.txt
```

## 🔍 Verificações

```bash
# Health check
curl http://localhost:8000/health

# Testar endpoint de busca
curl "http://localhost:8000/api/v1/operadoras?q=amil&page=1&limit=10"

# Testar analytics
curl "http://localhost:8000/api/v1/analytics/gastos?periodo=2024&top=10"

# Verificar containers
docker ps

# Verificar logs do backend
docker-compose logs backend --tail=50
```

## 🗄️ Banco de Dados

```bash
# Conectar ao MySQL
docker exec -it ans-mysql mysql -u user -p ans_db

# Backup
docker exec ans-mysql mysqldump -u user -p ans_db > backup.sql

# Restore
docker exec -i ans-mysql mysql -u user -p ans_db < backup.sql

# Ver tabelas
docker exec -it ans-mysql mysql -u user -p -e "USE ans_db; SHOW TABLES;"
```

## 🔴 Redis

```bash
# Conectar ao Redis
docker exec -it ans-redis redis-cli

# Comandos Redis úteis
PING                    # Testar conexão
KEYS ans:*             # Ver todas as chaves
GET ans:key            # Ver valor de uma chave
FLUSHALL               # Limpar todo o cache (cuidado!)
INFO                   # Informações do servidor
```

## 📝 Git

```bash
# Criar branch
git checkout -b feature/minha-feature

# Commit
git add .
git commit -m "feat: adiciona nova funcionalidade"

# Push
git push origin feature/minha-feature

# Atualizar branch
git checkout main
git pull upstream main
git checkout feature/minha-feature
git rebase main
```

## 🔧 Troubleshooting

```bash
# Limpar cache Python
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Recriar ambiente virtual
rm -rf .venv
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Limpar containers Docker
docker-compose down -v
docker system prune -a

# Verificar portas em uso (Windows)
netstat -ano | findstr :8000
netstat -ano | findstr :5173
netstat -ano | findstr :3307
netstat -ano | findstr :6379

# Matar processo por porta (Windows)
# Encontre o PID com netstat acima, depois:
taskkill /PID <PID> /F
```

## 📊 Monitoramento

```bash
# Ver uso de recursos dos containers
docker stats

# Ver logs em tempo real
docker-compose logs -f

# Ver apenas erros
docker-compose logs | grep -i error

# Exportar logs
docker-compose logs > logs.txt
```

## 🌐 URLs Importantes

```
Frontend:        http://localhost:5173
Backend:         http://localhost:8000
API Docs:        http://localhost:8000/api/v1/docs
ReDoc:           http://localhost:8000/api/v1/redoc
Health Check:    http://localhost:8000/health
MySQL:           localhost:3307
Redis:           localhost:6379
```

## 📚 Documentação

```bash
# Abrir documentação da API
start http://localhost:8000/api/v1/docs  # Windows
open http://localhost:8000/api/v1/docs   # Mac
xdg-open http://localhost:8000/api/v1/docs  # Linux

# Ver estrutura do projeto
tree -L 3 -I 'node_modules|__pycache__|.venv'
```

## 🔐 Segurança

```bash
# Gerar nova SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Verificar variáveis de ambiente
cat .env  # Linux/Mac
type .env  # Windows

# Verificar se .env está no .gitignore
git check-ignore .env
```

## 🚀 Deploy

```bash
# Build para produção (frontend)
cd frontend/vue-app
npm run build

# Testar build localmente
npm run preview

# Build Docker para produção
docker-compose -f docker-compose.yml build

# Deploy
docker-compose -f docker-compose.yml up -d
```

## 📈 Performance

```bash
# Analisar tamanho do bundle (frontend)
cd frontend/vue-app
npm run build -- --report

# Ver queries lentas do MySQL
docker exec -it ans-mysql mysql -u root -p -e "SHOW FULL PROCESSLIST;"

# Monitorar Redis
docker exec -it ans-redis redis-cli MONITOR
```

## 🧹 Limpeza

```bash
# Limpar logs antigos
rm *.log *.txt

# Limpar cache Redis
docker exec -it ans-redis redis-cli FLUSHALL

# Limpar dados de teste
rm -rf etl/data/processed/*
rm -rf etl/data/interim/*

# Limpar node_modules
cd frontend/vue-app && rm -rf node_modules && npm install
```

## 💡 Dicas

```bash
# Alias úteis (adicione ao seu .bashrc ou .zshrc)
alias ans-start="cd ~/ans-intelligence-app && .\scripts\start-dev.ps1"
alias ans-test="cd ~/ans-intelligence-app && pytest"
alias ans-logs="cd ~/ans-intelligence-app/docker && docker-compose logs -f"

# Variáveis de ambiente temporárias
export DEBUG=true
export LOG_LEVEL=DEBUG

# Ver todas as rotas da API
python -c "from api.main import app; print([r.path for r in app.routes])"
```

## 🆘 Ajuda Rápida

```bash
# Ver ajuda do uvicorn
uvicorn --help

# Ver ajuda do pytest
pytest --help

# Ver ajuda do docker-compose
docker-compose --help

# Ver versões instaladas
python --version
node --version
docker --version
docker-compose --version
```

---

**Dica:** Salve este arquivo nos favoritos do seu navegador ou crie um alias para abri-lo rapidamente!
