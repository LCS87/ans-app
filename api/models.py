"""Pydantic models para validação e serialização."""
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class OperadoraBase(BaseModel):
    """Modelo base de operadora."""
    registro_ans: str = Field(..., description="Registro ANS da operadora")
    cnpj: str = Field(..., description="CNPJ da operadora")
    razao_social: str = Field(..., description="Razão social")
    nome_fantasia: Optional[str] = Field(None, description="Nome fantasia")
    modalidade: Optional[str] = Field(None, description="Modalidade da operadora")


class OperadoraResponse(OperadoraBase):
    """Resposta de operadora com score de busca."""
    score: Optional[int] = Field(None, description="Score de relevância na busca")


class PaginationMetadata(BaseModel):
    """Metadados de paginação."""
    page: int = Field(..., ge=1, description="Página atual")
    limit: int = Field(..., ge=1, le=200, description="Itens por página")
    total: int = Field(..., ge=0, description="Total de itens")
    pages: int = Field(..., ge=0, description="Total de páginas")


class OperadorasSearchResponse(BaseModel):
    """Resposta paginada de busca de operadoras."""
    query: str = Field(..., description="Query de busca")
    results: List[OperadoraResponse]
    metadata: PaginationMetadata


class GastoOperadora(BaseModel):
    """Modelo de gasto por operadora."""
    posicao: int = Field(..., ge=1, description="Posição no ranking")
    registro_ans: str
    razao_social: str
    valor_total: float = Field(..., description="Valor total em reais")
    
    @validator('valor_total')
    def validate_valor(cls, v):
        if v < 0:
            raise ValueError('Valor não pode ser negativo')
        return round(v, 2)


class AnalyticsGastosResponse(BaseModel):
    """Resposta de analytics de gastos."""
    periodo: str = Field(..., description="Período da análise (ex: 2024)")
    top: int = Field(..., description="Quantidade de operadoras no ranking")
    total_geral: float = Field(..., description="Soma total dos gastos")
    ranking: List[GastoOperadora]


class HealthCheckResponse(BaseModel):
    """Resposta de health check."""
    status: str = Field(..., description="Status geral (ok/degraded/down)")
    version: str
    database: str = Field(..., description="Status do banco de dados")
    cache: Optional[str] = Field(None, description="Status do cache")
    uptime_seconds: float


class ErrorResponse(BaseModel):
    """Resposta de erro padronizada."""
    error: str = Field(..., description="Tipo do erro")
    message: str = Field(..., description="Mensagem descritiva")
    details: Optional[dict] = Field(None, description="Detalhes adicionais")
