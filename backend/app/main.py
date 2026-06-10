from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import admin, auth, documents, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env == "production":
        if settings.app_secret_key == "change-me-in-production":
            raise RuntimeError("APP_SECRET_KEY must be changed in production")
        if settings.shared_login_password == "student123":
            raise RuntimeError("SHARED_LOGIN_PASSWORD must be changed in production")
        if settings.admin_login_password == "admin123":
            raise RuntimeError("ADMIN_LOGIN_PASSWORD must be changed in production")
    await init_db()
    yield


app = FastAPI(title="學業輔助系統", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(sessions.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
