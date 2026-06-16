from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_current_user_optional, get_db, rate_limit
from app.models.tables import User
from app.schemas import (
    DeleteConfirmRequest,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService, clear_refresh_cookie, issue_tokens
from app.services.cost_service import quota_status
from app.services.privacy_service import PrivacyService

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
    try:
        user = await svc.login(body)
    except HTTPException:
        await AuditService(db).log(
            "auth.login_failed",
            request=request,
            detail={"identifier": body.identifier},
        )
        raise
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
    await AuditService(db).log("auth.token_refresh", user_id=user.id, request=request)
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


@router.put("/me", response_model=UserOut)
async def update_me(
    body: ProfileUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await AuthService(db).update_profile(current_user.id, body)
    await AuditService(db).log(
        "auth.profile_update",
        user_id=current_user.id,
        request=request,
        detail=body.model_dump(exclude_none=True),
    )
    return await _user_out(db, user)


@router.put("/me/password")
async def change_password(
    body: PasswordChangeRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await AuthService(db).change_password(current_user.id, body)
    clear_refresh_cookie(response)
    await AuditService(db).log("auth.password_change", user_id=current_user.id, request=request)
    return {"ok": True}


@router.post("/me/delete-request")
async def delete_request(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await PrivacyService(db).request_delete(current_user.id)


@router.post("/me/delete-confirm")
async def delete_confirm(
    body: DeleteConfirmRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await PrivacyService(db).confirm_delete(current_user.id, body.confirmation_code)
    clear_refresh_cookie(response)
    return result


@router.post("/me/delete-cancel")
async def delete_cancel(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await PrivacyService(db).cancel_delete(current_user.id)


@router.post("/me/export-request")
async def export_request(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await PrivacyService(db).export_request(current_user.id)


@router.get("/me/export-download")
async def export_download(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    path = await PrivacyService(db).export_download_path(current_user.id)
    return FileResponse(path, media_type="application/zip", filename="learnai-export.zip")


async def _user_out(db: AsyncSession, user: User) -> UserOut:
    data = UserOut.model_validate(user).model_dump()
    data.update(await quota_status(db, user))
    return UserOut(**data)
