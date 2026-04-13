"""Modelos ORM para SQLite (fundicao.db) — OFs, OE, certificados e corridas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class OrdemFabricacao(Base):
    __tablename__ = "ordem_fabricacao"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    numero_of: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    numero_nn: Mapped[str | None] = mapped_column(String(50))
    nome_cliente: Mapped[str] = mapped_column(String(200), nullable=False)
    data_abertura_pedido: Mapped[date] = mapped_column(Date, nullable=False)
    prazo_entrega_pedido: Mapped[date | None] = mapped_column(Date)
    numero_pedido: Mapped[str | None] = mapped_column(String(80))
    numero_modelo: Mapped[str | None] = mapped_column(String(80))
    descricao_peca: Mapped[str | None] = mapped_column(Text)
    numero_desenho: Mapped[str | None] = mapped_column(String(80))
    peso_liquido_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    peso_bruto_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    liga: Mapped[str | None] = mapped_column(String(120))
    norma: Mapped[str | None] = mapped_column(String(120))
    qtd_pecas_pedido: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qtd_fundida: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qtd_expedida: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valor_unitario: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    valor_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    condicao_modelo: Mapped[str | None] = mapped_column(String(200))
    observacoes: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now().astimezone())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now().astimezone())

    ordens_entrega: Mapped[list["OrdemEntrega"]] = relationship(
        back_populates="ordem_fabricacao", cascade="all, delete-orphan"
    )
    certificados: Mapped[list["CertificadoPeca"]] = relationship(
        back_populates="ordem_fabricacao", cascade="all, delete-orphan"
    )
    corridas: Mapped[list["Corrida"]] = relationship(back_populates="ordem_fabricacao")


class OrdemEntrega(Base):
    __tablename__ = "ordem_entrega"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ordem_fabricacao_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ordem_fabricacao.id", ondelete="CASCADE"), nullable=False
    )
    numero_oe: Mapped[str] = mapped_column(String(80), nullable=False)
    qtd_pecas: Mapped[int] = mapped_column(Integer, nullable=False)
    data_prevista: Mapped[date | None] = mapped_column(Date)
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now().astimezone())

    ordem_fabricacao: Mapped["OrdemFabricacao"] = relationship(back_populates="ordens_entrega")


class CertificadoPeca(Base):
    __tablename__ = "certificado_peca"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ordem_fabricacao_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ordem_fabricacao.id", ondelete="CASCADE"), nullable=False
    )
    numero_certificado: Mapped[str] = mapped_column(String(80), nullable=False)
    qtd_pecas: Mapped[int] = mapped_column(Integer, nullable=False)
    data_emissao: Mapped[date | None] = mapped_column(Date)
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now().astimezone())

    ordem_fabricacao: Mapped["OrdemFabricacao"] = relationship(back_populates="certificados")


class Corrida(Base):
    __tablename__ = "corrida"
    __table_args__ = (UniqueConstraint("numero_corrida", "data_fusao", name="uq_corrida_numero_data"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    data_fusao: Mapped[date] = mapped_column(Date, nullable=False)
    numero_corrida: Mapped[str] = mapped_column(String(50), nullable=False)
    nome_cliente: Mapped[str] = mapped_column(String(200), nullable=False)
    ordem_fabricacao_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ordem_fabricacao.id", ondelete="SET NULL")
    )
    numero_ordem_fabricacao: Mapped[str | None] = mapped_column(String(50))
    qtd_pecas_fundidas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    serie_pecas_fundidas: Mapped[str | None] = mapped_column(String(500))
    liga: Mapped[str | None] = mapped_column(String(120))
    norma: Mapped[str | None] = mapped_column(String(120))
    composicao_quimica_pct: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=lambda: {}
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now().astimezone())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now().astimezone())

    ordem_fabricacao: Mapped["OrdemFabricacao | None"] = relationship(back_populates="corridas")
