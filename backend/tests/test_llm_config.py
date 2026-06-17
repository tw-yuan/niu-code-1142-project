from app.config import settings
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
