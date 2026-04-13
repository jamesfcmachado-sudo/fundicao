from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrdemFabricacaoBase(BaseModel):
    numero_of: str
    numero_nn: str | None = None
    nome_cliente: str
    data_abertura_pedido: date
    prazo_entrega_pedido: date | None = None
    numero_pedido: str | None = None
    numero_modelo: str | None = None
    descricao_peca: str | None = None
    numero_desenho: str | None = None
    peso_liquido_kg: Decimal | None = None
    peso_bruto_kg: Decimal | None = None
    liga: str | None = None
    norma: str | None = None
    qtd_pecas_pedido: int = 0
    qtd_fundida: int = 0
    qtd_expedida: int = 0
    valor_unitario: Decimal | None = None
    valor_total: Decimal | None = None
    condicao_modelo: str | None = None
    observacoes: str | None = None


class OrdemFabricacaoCreate(OrdemFabricacaoBase):
    pass


class OrdemFabricacaoRead(OrdemFabricacaoBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    criado_em: datetime
    atualizado_em: datetime


class OrdemEntregaCreate(BaseModel):
    numero_oe: str
    qtd_pecas: int = Field(gt=0)
    data_prevista: date | None = None
    observacao: str | None = None


class OrdemEntregaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ordem_fabricacao_id: UUID
    numero_oe: str
    qtd_pecas: int
    data_prevista: date | None
    observacao: str | None
    criado_em: datetime


class CertificadoPecaCreate(BaseModel):
    numero_certificado: str
    qtd_pecas: int = Field(gt=0)
    data_emissao: date | None = None
    observacao: str | None = None


class CertificadoPecaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ordem_fabricacao_id: UUID
    numero_certificado: str
    qtd_pecas: int
    data_emissao: date | None
    observacao: str | None
    criado_em: datetime


class CorridaCreate(BaseModel):
    data_fusao: date
    numero_corrida: str
    nome_cliente: str
    ordem_fabricacao_id: UUID | None = None
    numero_ordem_fabricacao: str | None = None
    qtd_pecas_fundidas: int = 0
    serie_pecas_fundidas: str | None = None
    liga: str | None = None
    norma: str | None = None
    composicao_quimica_pct: dict[str, Any] = Field(default_factory=dict)


class CorridaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    data_fusao: date
    numero_corrida: str
    nome_cliente: str
    ordem_fabricacao_id: UUID | None
    numero_ordem_fabricacao: str | None
    qtd_pecas_fundidas: int
    serie_pecas_fundidas: str | None
    liga: str | None
    norma: str | None
    composicao_quimica_pct: dict[str, Any]
    criado_em: datetime
    atualizado_em: datetime
