from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import UPLOAD_DIR, GENERATED_FILE_DIR
from app.database import init_db
from app.routers import auth, tasks, history, admin

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_FILE_DIR.mkdir(parents=True, exist_ok=True)
    await init_db()
    yield


app = FastAPI(
    title="AI 課業輔助系統",
    description="AI 課業輔助與作業草稿生成系統 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(history.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve frontend static files (built React app)
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        file = FRONTEND_DIR / full_path
        if file.exists() and file.is_file():
            return FileResponse(file)
        return FileResponse(FRONTEND_DIR / "index.html")
