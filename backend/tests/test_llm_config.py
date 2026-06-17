import json

from app.config import settings
from app.models.tables import AdminConfig
from app.services.admin_service import AdminService
from app.services.llm_config import default_llm_config


def test_default_llm_config_uses_feature_specific_provider(monkeypatch):
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://default.example/v1")
    monkeypatch.setattr(settings, "LLM_API_KEY", "default-key")
    monkeypatch.setattr(settings, "LLM_CHAT_BASE_URL", "https://chat.example/v1")
    monkeypatch.setattr(settings, "LLM_CHAT_API_KEY", "chat-key")
    monkeypatch.setattr(settings, "LLM_VISION_BASE_URL", "")
    monkeypatch.setattr(settings, "LLM_VISION_API_KEY", "")
    monkeypatch.setattr(settings, "LLM_EMBED_BASE_URL", "https://embed.example/v1")
    monkeypatch.setattr(settings, "LLM_EMBED_API_KEY", "")

    config = default_llm_config()

    assert config["chat"]["base_url"] == "https://chat.example/v1"
    assert config["chat"]["api_key"] == "chat-key"
    assert config["vision"]["base_url"] == "https://default.example/v1"
    assert config["vision"]["api_key"] == "default-key"
    assert config["embedding"]["base_url"] == "https://embed.example/v1"
    assert config["embedding"]["api_key"] == "default-key"


async def test_reset_llm_config_removes_db_override(monkeypatch):
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://default.example/v1")
    monkeypatch.setattr(settings, "LLM_API_KEY", "default-key")
    monkeypatch.setattr(settings, "LLM_CHAT_BASE_URL", "")
    monkeypatch.setattr(settings, "LLM_CHAT_API_KEY", "")

    db = FakeSession(
        AdminConfig(
            key="llm_config",
            value=json.dumps(
                {
                    "chat": {
                        "base_url": "https://old.example/v1",
                        "api_key": "old-key",
                        "model": "old-model",
                    }
                }
            ),
        )
    )

    config = await AdminService(db).reset_llm_config(actor_id="admin-id")

    assert db.row is None
    assert db.commit_count == 2
    assert db.added[0].action == "admin.config_reset"
    assert config["chat"]["base_url"] == "https://default.example/v1"
    assert config["chat"]["api_key"] == "********"


class FakeExecuteResult:
    def __init__(self, row):
        self.row = row

    def scalar_one_or_none(self):
        return self.row


class FakeSession:
    def __init__(self, row):
        self.row = row
        self.added = []
        self.commit_count = 0

    async def execute(self, _statement):
        return FakeExecuteResult(self.row)

    async def delete(self, row):
        if row is self.row:
            self.row = None

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commit_count += 1
