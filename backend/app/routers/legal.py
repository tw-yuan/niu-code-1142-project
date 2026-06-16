from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.tables import User
from app.schemas import LegalConsentRequest
from app.services.audit_service import AuditService
from app.services.legal_service import LegalService

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/consents")
async def list_consents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LegalService(db).list_consents(current_user.id)


@router.post("/consent")
async def consent(
    body: LegalConsentRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await LegalService(db).consent(current_user.id, body, request)
    await AuditService(db).log(
        "legal.consent",
        user_id=current_user.id,
        resource=f"legal_consent:{body.consent_type}",
        request=request,
        detail={"consent_type": body.consent_type},
    )
    return result
