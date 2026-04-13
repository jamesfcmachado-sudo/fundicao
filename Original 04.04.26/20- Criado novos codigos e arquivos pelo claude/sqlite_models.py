"""
Modelos SQLAlchemy para o banco SQLite (fundicao.db).

IMPORTANTE — tabela corrida:
  Não há UNIQUE constraint em (numero_corrida, data_fusao).
  A regra de negócio permite que a mesma corrida apareça várias vezes
  com OFs e séries diferentes. A unicidade é garantida apenas pela
  PRIMARY KEY (id), que é um UUID gerado automaticamente.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    VARCHAR,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────
# Ordem de Fabricação
# ─────────────────────────────────────────────
class OrdemFabricacao(Base):
    __tablename__ = "ordem_fabricacao"

    id                   = Column(String(36), primary_key=True, default=_new_uuid)
    numero_of            = Column(VARCHAR(50),  nullable=False, unique=True)
    numero_nn            = Column(VARCHAR(50))
    nome_cliente         = Column(VARCHAR(200), nullable=False)
    data_abertura_pedido = Column(Date,         nullable=False)
    prazo_entrega_pedido = Column(Date)
    numero_pedido        = Column(VARCHAR(80))
    numero_modelo        = Column(VARCHAR(80))
    descricao_peca       = Column(Text)
    numero_desenho       = Column(VARCHAR(80))
    peso_liquido_kg      = Column(Numeric(14, 4))
    peso_bruto_kg        = Column(Numeric(14, 4))
    liga                 = Column(VARCHAR(120))
    norma                = Column(VARCHAR(120))
    qtd_pecas_pedido     = Column(Integer, nullable=False, default=0)
    qtd_fundida          = Column(Integer, nullable=False, default=0)
    qtd_expedida         = Column(Integer, nullable=False, default=0)
    valor_unitario       = Column(Numeric(18, 6))
    valor_total          = Column(Numeric(18, 2))
    condicao_modelo      = Column(VARCHAR(200))
    observacoes          = Column(Text)
    criado_em            = Column(DateTime, nullable=False, default=datetime.now)
    atualizado_em        = Column(DateTime, nullable=False, default=datetime.now,
                                  onupdate=datetime.now)

    ordens_entrega = relationship(
        "OrdemEntrega", back_populates="ordem_fabricacao",
        cascade="all, delete-orphan",
    )
    certificados = relationship(
        "CertificadoPeca", back_populates="ordem_fabricacao",
        cascade="all, delete-orphan",
    )
    corridas = relationship(
        "Corrida", back_populates="ordem_fabricacao",
    )


# ─────────────────────────────────────────────
# Ordem de Entrega
# ─────────────────────────────────────────────
class OrdemEntrega(Base):
    __tablename__ = "ordem_entrega"

    id                  = Column(String(36), primary_key=True, default=_new_uuid)
    ordem_fabricacao_id = Column(String(36),
                                  ForeignKey("ordem_fabricacao.id", ondelete="CASCADE"),
                                  nullable=False)
    numero_oe           = Column(VARCHAR(80), nullable=False)
    qtd_pecas           = Column(Integer, nullable=False,
                                  default=1)
    data_prevista       = Column(Date)
    observacao          = Column(Text)
    criado_em           = Column(DateTime, nullable=False, default=datetime.now)

    ordem_fabricacao = relationship("OrdemFabricacao", back_populates="ordens_entrega")


# ─────────────────────────────────────────────
# Certificado de Peça
# ─────────────────────────────────────────────
class CertificadoPeca(Base):
    __tablename__ = "certificado_peca"

    id                  = Column(String(36), primary_key=True, default=_new_uuid)
    ordem_fabricacao_id = Column(String(36),
                                  ForeignKey("ordem_fabricacao.id", ondelete="CASCADE"),
                                  nullable=False)
    numero_certificado  = Column(VARCHAR(80), nullable=False)
    qtd_pecas           = Column(Integer, nullable=False, default=1)
    data_emissao        = Column(Date)
    observacao          = Column(Text)
    criado_em           = Column(DateTime, nullable=False, default=datetime.now)

    ordem_fabricacao = relationship("OrdemFabricacao", back_populates="certificados")


# ─────────────────────────────────────────────
# Corrida
# SEM UniqueConstraint em numero_corrida/data_fusao.
# A mesma corrida pode ter várias OFs e séries diferentes.
# Unicidade garantida apenas pela PRIMARY KEY (id = UUID).
# ─────────────────────────────────────────────
class Corrida(Base):
    __tablename__ = "corrida"

    id                      = Column(String(36), primary_key=True, default=_new_uuid)
    data_fusao              = Column(Date,        nullable=False)
    numero_corrida          = Column(VARCHAR(50), nullable=False)
    nome_cliente            = Column(VARCHAR(200), nullable=False)
    ordem_fabricacao_id     = Column(String(36),
                                      ForeignKey("ordem_fabricacao.id", ondelete="SET NULL"))
    numero_ordem_fabricacao = Column(VARCHAR(50))
    qtd_pecas_fundidas      = Column(Integer, nullable=False, default=0)
    serie_pecas_fundidas    = Column(VARCHAR(500))
    liga                    = Column(VARCHAR(120))
    norma                   = Column(VARCHAR(120))
    composicao_quimica_pct  = Column(JSON, nullable=False, default=dict)
    criado_em               = Column(DateTime, nullable=False, default=datetime.now)
    atualizado_em           = Column(DateTime, nullable=False, default=datetime.now,
                                      onupdate=datetime.now)

    ordem_fabricacao = relationship("OrdemFabricacao", back_populates="corridas")
