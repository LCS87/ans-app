"""Pydantic models para validação e serialização."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import re


class OperadoraBase(BaseModel):
    """Modelo base de operadora."""

    registro_ans: str = Field(
        ..., min_length=6, max_length=6, description="Registro ANS"
    )
    cnpj: str = Field(..., min_length=14, max_length=14, description="CNPJ")
    razao_social: str = Field(..., min_length=1, description="Razão social")
    nome_fantasia: Optional[str] = Field(None, description="Nome fantasia")
    modalidade: Optional[str] = Field(None, description="Modalidade")

    @field_validator("registro_ans")
    @classmethod
    def validate_registro(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("registro_ans deve conter apenas números")
        return v

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj(cls, v: str) -> str:
        if not re.match(r"^\d{14}$", v):
            raise ValueError("CNPJ deve ter 14 dígitos numéricos")
        return v


class OperadoraResponse(OperadoraBase):
    """Resposta de operadora com score de busca."""

    score: Optional[int] = Field(None, ge=0, le=100, description="Score 0-100")
    uf: Optional[str] = Field(None, description="UF da sede (CADOP)")
    regiao_comercializacao: Optional[str] = Field(
        None, description="Região de comercialização (CADOP)"
    )


class PaginationMetadata(BaseModel):
    """Metadados de paginação."""

    page: int = Field(..., ge=1)
    limit: int = Field(..., ge=1, le=200)
    total: int = Field(..., ge=0)
    pages: int = Field(..., ge=0)


class OperadorasSearchResponse(BaseModel):
    """Resposta paginada de busca."""

    query: str
    results: List[OperadoraResponse]
    metadata: PaginationMetadata


class GastoOperadora(BaseModel):
    """Gasto por operadora."""

    posicao: int = Field(..., ge=1)
    registro_ans: str
    razao_social: str
    valor_total: float = Field(..., ge=0)

    @field_validator("valor_total")
    @classmethod
    def validate_valor(cls, v: float) -> float:
        return round(v, 2)


class AnalyticsGastosResponse(BaseModel):
    """Resposta do endpoint de ranking de gastos."""

    periodo: str = Field(..., description="Período da análise (ano)")
    top: int = Field(..., description="Quantidade de operadoras no ranking")
    total_geral: float = Field(..., description="Total geral de gastos do período")
    total_operadoras: int = Field(
        ..., description="Total de operadoras com gastos no período"
    )
    ranking: List[GastoOperadora] = Field(..., description="Ranking de operadoras")


class HealthCheckResponse(BaseModel):
    """Health check."""

    status: str = Field(..., pattern=r"^(ok|degraded|down)$")
    version: str
    database: str
    cache: Optional[str] = None
    uptime_seconds: float = Field(..., ge=0)


class ErrorResponse(BaseModel):
    """Erro padronizado."""

    error: str
    message: str
    details: Optional[dict] = None
