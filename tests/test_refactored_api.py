"""Testes para API refatorada."""
import pytest
from fastapi.testclient import TestClient

from api.main_refactored import app

client = TestClient(app)


class TestHealthCheck:
    """Testes de health check."""
    
    def test_health_check_returns_ok(self):
        """Health check deve retornar status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["ok", "degraded"]
        assert "version" in data
        assert "uptime_seconds" in data
    
    def test_health_check_has_components(self):
        """Health check deve incluir status de componentes."""
        response = client.get("/health")
        data = response.json()
        
        assert "database" in data
        assert "cache" in data


class TestOperadorasEndpoints:
    """Testes de endpoints de operadoras."""
    
    def test_search_operadoras_success(self):
        """Busca de operadoras deve retornar resultados."""
        response = client.get("/api/v1/operadoras?q=amil&page=1&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "metadata" in data
        assert data["query"] == "amil"
    
    def test_search_operadoras_pagination(self):
        """Busca deve incluir metadados de paginação."""
        response = client.get("/api/v1/operadoras?q=saude&page=1&limit=5")
        data = response.json()
        
        metadata = data["metadata"]
        assert metadata["page"] == 1
        assert metadata["limit"] == 5
        assert "total" in metadata
        assert "pages" in metadata
    
    def test_search_operadoras_empty_query(self):
        """Busca com query vazia deve retornar erro."""
        response = client.get("/api/v1/operadoras?q=&page=1")
        assert response.status_code == 422  # Validation error
    
    def test_search_operadoras_invalid_page(self):
        """Busca com página inválida deve retornar erro."""
        response = client.get("/api/v1/operadoras?q=test&page=0")
        assert response.status_code == 422
    
    def test_search_operadoras_limit_bounds(self):
        """Busca deve respeitar limites de paginação."""
        # Limite muito alto
        response = client.get("/api/v1/operadoras?q=test&limit=300")
        assert response.status_code == 422
        
        # Limite válido
        response = client.get("/api/v1/operadoras?q=test&limit=50")
        assert response.status_code == 200


class TestAnalyticsEndpoints:
    """Testes de endpoints de analytics."""
    
    def test_get_ranking_gastos_success(self):
        """Ranking de gastos deve retornar dados."""
        response = client.get("/api/v1/analytics/gastos?periodo=2024&top=10")
        
        # Pode retornar 200 ou 404 dependendo se dados existem
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "periodo" in data
            assert "top" in data
            assert "ranking" in data
            assert "total_geral" in data
    
    def test_get_ranking_gastos_custom_top(self):
        """Ranking deve aceitar parâmetro top customizado."""
        response = client.get("/api/v1/analytics/gastos?periodo=2024&top=5")
        
        if response.status_code == 200:
            data = response.json()
            assert data["top"] == 5
    
    def test_get_ranking_gastos_invalid_top(self):
        """Ranking com top inválido deve retornar erro."""
        response = client.get("/api/v1/analytics/gastos?top=0")
        assert response.status_code == 422
        
        response = client.get("/api/v1/analytics/gastos?top=200")
        assert response.status_code == 422


class TestLegacyEndpoints:
    """Testes de endpoints legados (deprecated)."""
    
    def test_legacy_search_still_works(self):
        """Endpoint legado /search deve continuar funcionando."""
        response = client.get("/search?query=test&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "query" in data
        assert "results" in data
    
    def test_legacy_top_10_still_works(self):
        """Endpoint legado /analytics/top-10 deve continuar funcionando."""
        response = client.get("/analytics/top-10")
        assert response.status_code in [200, 404]


class TestErrorHandling:
    """Testes de tratamento de erros."""
    
    def test_404_returns_error_response(self):
        """Rota inexistente deve retornar erro padronizado."""
        response = client.get("/api/v1/nao-existe")
        assert response.status_code == 404
    
    def test_validation_error_returns_422(self):
        """Erro de validação deve retornar 422."""
        response = client.get("/api/v1/operadoras")  # Missing required 'q'
        assert response.status_code == 422


class TestDocumentation:
    """Testes de documentação."""
    
    def test_openapi_schema_available(self):
        """Schema OpenAPI deve estar disponível."""
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
    
    def test_swagger_ui_available(self):
        """Swagger UI deve estar disponível."""
        response = client.get("/api/v1/docs")
        assert response.status_code == 200
    
    def test_redoc_available(self):
        """ReDoc deve estar disponível."""
        response = client.get("/api/v1/redoc")
        assert response.status_code == 200


@pytest.mark.integration
class TestIntegration:
    """Testes de integração."""
    
    def test_full_search_flow(self):
        """Fluxo completo de busca."""
        # 1. Busca inicial
        response = client.get("/api/v1/operadoras?q=bradesco&page=1&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        results = data["results"]
        
        if results:
            # 2. Busca detalhes de uma operadora
            registro_ans = results[0]["registro_ans"]
            response = client.get(f"/api/v1/operadoras/{registro_ans}")
            
            # Pode não encontrar se registro não for exato
            assert response.status_code in [200, 404]
