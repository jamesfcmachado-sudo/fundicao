from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.routers import ordens


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


class AuditUserMiddleware(BaseHTTPMiddleware):
    """Lê X-Audit-User e grava em request.state (usado em get_db → set_config no PostgreSQL)."""

    async def dispatch(self, request: Request, call_next):
        raw = request.headers.get("x-audit-user")
        request.state.audit_user = raw.strip() if raw else None
        return await call_next(request)


app = FastAPI(
    title="API Fundição",
    description="FastAPI + SQLAlchemy — banco `fundicao` (esquemas fabricacao, corridas, auditoria).",
    lifespan=lifespan,
)
app.add_middleware(AuditUserMiddleware)
app.include_router(ordens.router)


@app.get("/health")
def health():
    return {"status": "ok"}
