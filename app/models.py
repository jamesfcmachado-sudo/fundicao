import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class OrdemFabricacao(Base):
    __tablename__ = "ordem_fabricacao"
    __table_args__ = {"schema": "fabricacao"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
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
    qtd_pecas_pedido: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    qtd_fundida: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    qtd_expedida: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    valor_unitario: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    valor_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    condicao_modelo: Mapped[str | None] = mapped_column(String(200))
    observacoes: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    ordens_entrega: Mapped[list["OrdemEntrega"]] = relationship(
        back_populates="ordem_fabricacao", cascade="all, delete-orphan"
    )
    certificados: Mapped[list["CertificadoPeca"]] = relationship(
        back_populates="ordem_fabricacao", cascade="all, delete-orphan"
    )
    corridas: Mapped[list["Corrida"]] = relationship(back_populates="ordem_fabricacao")


class OrdemEntrega(Base):
    __tablename__ = "ordem_entrega"
    __table_args__ = {"schema": "fabricacao"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    ordem_fabricacao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fabricacao.ordem_fabricacao.id", ondelete="CASCADE"),
        nullable=False,
    )
    numero_oe: Mapped[str] = mapped_column(String(80), nullable=False)
    qtd_pecas: Mapped[int] = mapped_column(Integer, nullable=False)
    data_prevista: Mapped[date | None] = mapped_column(Date)
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    ordem_fabricacao: Mapped["OrdemFabricacao"] = relationship(back_populates="ordens_entrega")


class CertificadoPeca(Base):
    __tablename__ = "certificado_peca"
    __table_args__ = {"schema": "fabricacao"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    ordem_fabricacao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fabricacao.ordem_fabricacao.id", ondelete="CASCADE"),
        nullable=False,
    )
    numero_certificado: Mapped[str] = mapped_column(String(80), nullable=False)
    qtd_pecas: Mapped[int] = mapped_column(Integer, nullable=False)
    data_emissao: Mapped[date | None] = mapped_column(Date)
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    ordem_fabricacao: Mapped["OrdemFabricacao"] = relationship(back_populates="certificados")


class Corrida(Base):
    __tablename__ = "corrida"
    __table_args__ = {"schema": "corridas"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    data_fusao: Mapped[date] = mapped_column(Date, nullable=False)
    numero_corrida: Mapped[str] = mapped_column(String(50), nullable=False)
    nome_cliente: Mapped[str] = mapped_column(String(200), nullable=False)
    ordem_fabricacao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fabricacao.ordem_fabricacao.id", ondelete="SET NULL"),
    )
    numero_ordem_fabricacao: Mapped[str | None] = mapped_column(String(50))
    qtd_pecas_fundidas: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    serie_pecas_fundidas: Mapped[str | None] = mapped_column(String(500))
    liga: Mapped[str | None] = mapped_column(String(120))
    norma: Mapped[str | None] = mapped_column(String(120))
    composicao_quimica_pct: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    ordem_fabricacao: Mapped["OrdemFabricacao | None"] = relationship(back_populates="corridas")


class LogEvento(Base):
    """Somente leitura na aplicação — registros gerados por triggers no banco."""

    __tablename__ = "log_evento"
    __table_args__ = {"schema": "auditoria"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    schema_name: Mapped[str] = mapped_column(Text, nullable=False)
    table_name: Mapped[str] = mapped_column(Text, nullable=False)
    operacao: Mapped[str] = mapped_column(String(1), nullable=False)
    registro_id: Mapped[str | None] = mapped_column(Text)
    usuario_db: Mapped[str] = mapped_column(Text, nullable=False)
    usuario_app: Mapped[str | None] = mapped_column(Text)
    dados_antigos: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    dados_novos: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
