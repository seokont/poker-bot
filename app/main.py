from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api import auth, bot_actions, bot_admin, health
from app.config import get_settings
from app.core.dashboard_auth import DashboardAuthMiddleware
from app.core.logging import configure_logging
from app.integrations.database import create_database_tables


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    create_database_tables()
    yield


app = FastAPI(
    title="Poker Bot Server",
    version="0.1.0",
    description="Separate BOT-marked poker AI service that only proposes actions to the Game Engine.",
    lifespan=lifespan,
)
app.add_middleware(DashboardAuthMiddleware)
if get_settings().trust_proxy_headers:
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(bot_actions.router)
app.include_router(bot_admin.router)


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard_alias() -> FileResponse:
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/login", include_in_schema=False)
def login_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/table-demo", include_in_schema=False)
def table_demo() -> FileResponse:
    return FileResponse(STATIC_DIR / "table-demo.html")
