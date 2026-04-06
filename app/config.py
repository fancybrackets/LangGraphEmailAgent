from dataclasses import dataclass
import os


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Step 13 Model Panel API")
    privacy_mode: bool = _as_bool(os.getenv("PRIVACY_MODE"), True)
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    default_model: str = os.getenv("DEFAULT_MODEL", "qwen2.5:7b")
    imap_host: str | None = os.getenv("IMAP_HOST")
    imap_user: str | None = os.getenv("IMAP_USER")
    imap_password: str | None = os.getenv("IMAP_PASSWORD")
    imap_folder: str = os.getenv("IMAP_FOLDER", "INBOX")
    imap_sent_folder: str = os.getenv("IMAP_SENT_FOLDER", "Sent")


settings = Settings()
