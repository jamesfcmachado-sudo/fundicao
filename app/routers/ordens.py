from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OrdemFabricacao
from app.schemas import OrdemFabricacaoCreate, OrdemFabricacaoRead

router = APIRouter(prefix="/ordens-fabricacao", tags=["Ordens de fabricação"])


@router.get("", response_model=list[OrdemFabricacaoRead])
def listar_ordens(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)) -> list[OrdemFabricacao]:
    stmt = select(OrdemFabricacao).order_by(OrdemFabricacao.criado_em.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/{of_id}", response_model=OrdemFabricacaoRead)
def obter_ordem(of_id: UUID, db: Session = Depends(get_db)) -> OrdemFabricacao:
    of = db.get(OrdemFabricacao, of_id)
    if not of:
        raise HTTPException(status_code=404, detail="Ordem de fabricação não encontrada")
    return of


@router.post("", response_model=OrdemFabricacaoRead, status_code=201)
def criar_ordem(payload: OrdemFabricacaoCreate, db: Session = Depends(get_db)) -> OrdemFabricacao:
    of = OrdemFabricacao(**payload.model_dump())
    db.add(of)
    db.flush()
    db.refresh(of)
    return of
