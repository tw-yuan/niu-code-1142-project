from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.routers import admin as admin_router
from app.routers import auth as auth_router
from app.routers import downloads as downloads_router
from app.routers import events as events_router
from app.routers import history as history_router
from app.routers import tasks as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings = get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.generated_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="AI 課業輔助與作業草稿生成系統",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


app.include_router(auth_router.router)
app.include_router(tasks_router.router)
app.include_router(events_router.router)
app.include_router(downloads_router.router)
app.include_router(history_router.router)
app.include_router(admin_router.router)


_settings = get_settings()
_frontend_dir = Path(_settings.frontend_dist_dir)

if _frontend_dir.exists():
    assets_dir = _frontend_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        target = _frontend_dir / full_path
        if full_path and target.exists() and target.is_file():
            return FileResponse(str(target))
        index = _frontend_dir / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse({"detail": "Frontend not built"}, status_code=404)
else:
    @app.get("/")
    async def root() -> dict:
        return {
            "message": "Backend running. Frontend dist not found.",
            "frontend_dist": str(_frontend_dir),
        }
