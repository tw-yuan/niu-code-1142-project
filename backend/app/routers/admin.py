from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.session import Session
from app.models.system_setting import SystemSetting
from app.models.system_setting_history import SystemSettingHistory
from app.services.ai_service import DEFAULT_SYSTEM_PROMPT, test_api_connection, get_ai_config
from app.utils.security import mask_secret

router = APIRouter(prefix="/api/admin", tags=["admin"])

DEFAULT_SETTINGS = {
    "api_base_url": {"label": "API Base URL", "secret": False},
    "api_key": {"label": "API Key", "secret": True},
    "model_name": {"label": "模型名稱", "secret": False},
    "temperature": {"label": "Temperature", "secret": False},
    "max_tokens": {"label": "Max Tokens", "secret": False},
    "system_prompt": {"label": "系統提示詞", "secret": False},
    "max_file_size_mb": {"label": "檔案大小限制 (MB)", "secret": False},
}


class SettingItem(BaseModel):
    key: str
    label: str
    value: str
    is_secret: bool


class UpdateSettingsRequest(BaseModel):
    settings: dict[str, str]


@router.get("/settings", response_model=list[SettingItem])
async def get_settings(
    session: Session = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    items = []
    for key, meta in DEFAULT_SETTINGS.items():
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()

        if setting:
            value = setting.value
        elif key == "system_prompt":
            value = DEFAULT_SYSTEM_PROMPT
        else:
            value = ""
        display_value = mask_secret(value) if meta["secret"] and value else value

        items.append(SettingItem(
            key=key,
            label=meta["label"],
            value=display_value,
            is_secret=meta["secret"],
        ))
    return items


@router.put("/settings")
async def update_settings(
    req: UpdateSettingsRequest,
    session: Session = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    updated_keys = []
    for key, new_value in req.settings.items():
        if key not in DEFAULT_SETTINGS:
            continue

        meta = DEFAULT_SETTINGS[key]
        if meta["secret"] and new_value and "*" in new_value:
            continue

        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()

        old_value = setting.value if setting else ""

        if setting:
            setting.value = new_value
            setting.is_secret = meta["secret"]
            setting.updated_by = session.user_id
        else:
            setting = SystemSetting(
                key=key,
                value=new_value,
                is_secret=meta["secret"],
                updated_by=session.user_id,
            )
            db.add(setting)
            await db.flush()

        history = SystemSettingHistory(
            setting_id=setting.id,
            key=key,
            old_value=mask_secret(old_value) if meta["secret"] else old_value,
            new_value=mask_secret(new_value) if meta["secret"] else new_value,
            updated_by=session.user_id,
        )
        db.add(history)
        updated_keys.append(key)

    await db.commit()
    return {"success": True, "updated": updated_keys}


@router.post("/test-api")
async def test_api(
    session: Session = Depends(require_admin),
):
    config = await get_ai_config()
    success, message = await test_api_connection(config)
    return {"success": success, "message": message}


@router.get("/settings/history")
async def get_settings_history(
    session: Session = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SystemSettingHistory).order_by(SystemSettingHistory.updated_at.desc()).limit(50)
    )
    items = result.scalars().all()
    return [
        {
            "id": h.id,
            "key": h.key,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "updated_at": h.updated_at.isoformat(),
        }
        for h in items
    ]
