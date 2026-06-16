from fastapi import HTTPException, Request, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import LegalConsent
from app.schemas import LegalConsentRequest


class LegalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_consents(self, user_id: str) -> list[dict]:
        rows = (
            await self.db.execute(select(LegalConsent).where(LegalConsent.user_id == user_id))
        ).scalars().all()
        return [
            {
                "id": row.id,
                "consent_type": row.consent_type,
                "consented_at": row.consented_at,
                "ip_address": row.ip_address,
            }
            for row in rows
        ]

    async def consent(self, user_id: str, body: LegalConsentRequest, request: Request) -> dict:
        existing = await self._get_consent(user_id, body.consent_type)
        if existing is None:
            self.db.add(
                LegalConsent(
                    user_id=user_id,
                    consent_type=body.consent_type,
                    ip_address=_client_ip(request),
                )
            )
            await self.db.commit()
        return {"ok": True}

    async def require_consent(self, user_id: str, consent_type: str) -> None:
        if await self._get_consent(user_id, consent_type) is not None:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "consent_required",
                "message": "上傳文件前必須先同意著作權聲明",
            },
        )

    async def _get_consent(self, user_id: str, consent_type: str) -> LegalConsent | None:
        return (
            await self.db.execute(
                select(LegalConsent).where(
                    and_(
                        LegalConsent.user_id == user_id,
                        LegalConsent.consent_type == consent_type,
                    )
                )
            )
        ).scalar_one_or_none()


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else None
