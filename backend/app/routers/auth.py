from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_current_user_optional, get_db, rate_limit
from app.models.tables import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService, clear_refresh_cookie, issue_tokens
from app.services.cost_service import quota_status

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    svc = AuthService(db)
    user = await svc.register(body)
    access_token = issue_tokens(response, user)
    await AuditService(db).log("auth.register", user_id=user.id, request=request)
    return TokenResponse(access_token=access_token, user=await _user_out(db, user))


@router.post("/login", response_model=TokenResponse, dependencies=[rate_limit("auth_login", 10, 900)])
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    svc = AuthService(db)
    user = await svc.login(body)
    access_token = issue_tokens(response, user)
    await AuditService(db).log("auth.login", user_id=user.id, request=request)
    return TokenResponse(access_token=access_token, user=await _user_out(db, user))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")
    svc = AuthService(db)
    user = await svc.user_from_refresh_token(refresh_token)
    access_token = issue_tokens(response, user)
    await AuditService(db).log("auth.refresh", user_id=user.id, request=request)
    return TokenResponse(access_token=access_token, user=await _user_out(db, user))


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    clear_refresh_cookie(response)
    if current_user:
        await AuditService(db).log("auth.logout", user_id=current_user.id, request=request)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _user_out(db, current_user)


async def _user_out(db: AsyncSession, user: User) -> UserOut:
    data = UserOut.model_validate(user).model_dump()
    data.update(await quota_status(db, user))
    return UserOut(**data)
