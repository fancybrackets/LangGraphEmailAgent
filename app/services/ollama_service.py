import re
import subprocess

import requests

from app.config import settings


_active_model: str | None = settings.default_model

_MODEL_CATALOG: list[dict[str, str]] = [
    {
        "name": "llama3.2:1b",
        "label": "Llama 3.2 1B",
        "notes": "En hafif secenek, M1 icin hizli baslangic",
    },
    {
        "name": "llama3.2:3b",
        "label": "Llama 3.2 3B",
        "notes": "Daha iyi kalite, hala hafif",
    },
    {
        "name": "qwen2.5:3b",
        "label": "Qwen 2.5 3B",
        "notes": "TR/EN karmasi islerde dengeli",
    },
    {
        "name": "qwen2.5:0.5b",
        "label": "Qwen 2.5 0.5B",
        "notes": "Cok hafif ve hizli; temel tool-calling denemeleri icin",
    },
    {
        "name": "qwen2.5:1.5b",
        "label": "Qwen 2.5 1.5B",
        "notes": "Hafif ve daha tutarli; tool-calling icin iyi denge",
    },
    {
        "name": "qwen2.5-coder:0.5b",
        "label": "Qwen 2.5 Coder 0.5B",
        "notes": "Kod odakli hafif model; tool-calling denemelerine uygun",
    },
    {
        "name": "qwen2.5-coder:1.5b",
        "label": "Qwen 2.5 Coder 1.5B",
        "notes": "Kod + arac kullanimi senaryolari icin daha guclu hafif secenek",
    },
    {
        "name": "gemma3:4b-it-qat",
        "label": "Gemma 3 4B IT (QAT)",
        "notes": "Google Gemma 3 4B instruction modeli",
    },
    {
        "name": "gemma3:4b",
        "label": "Gemma 3 4B (Default)",
        "notes": "Gemma 3 4B varsayilan etiket (yedek secenek)",
    },
]


def ollama_reachable() -> bool:
    try:
        response = requests.get(settings.ollama_base_url, timeout=2)
        return response.status_code < 500
    except requests.RequestException:
        return False


def _run_ollama(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ollama", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def list_models() -> list[dict[str, str | None]]:
    result = _run_ollama(["list"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ollama list failed.")

    lines = [line.rstrip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return []

    parsed: list[dict[str, str | None]] = []
    for line in lines[1:]:
        # Split by 2+ spaces to preserve values like "986 MB" and "4 hours ago".
        cols = re.split(r"\s{2,}", line.strip())
        if not cols:
            continue

        name = cols[0] if len(cols) >= 1 else None
        size = cols[2] if len(cols) >= 3 else None
        modified = cols[3] if len(cols) >= 4 else None

        if not name:
            continue
        parsed.append({"name": name, "size": size, "modified": modified})
    return parsed


def pull_model(model_name: str) -> str:
    if not is_catalog_model(model_name):
        raise RuntimeError(f"Model catalog disi: {model_name}")

    result = _run_ollama(["pull", model_name])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Failed to pull model: {model_name}")
    return result.stdout.strip() or f"Model pulled: {model_name}"


def delete_model(model_name: str) -> str:
    global _active_model

    result = _run_ollama(["rm", model_name])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Failed to delete model: {model_name}")
    if _active_model == model_name:
        _active_model = None
    return result.stdout.strip() or f"Model deleted: {model_name}"


def get_active_model() -> str | None:
    return _active_model


def set_active_model(model_name: str) -> str:
    global _active_model

    installed = {row["name"] for row in list_models() if row.get("name")}
    if model_name not in installed:
        raise RuntimeError(f"Model is not installed: {model_name}")

    _active_model = model_name
    return _active_model


def get_model_catalog() -> list[dict[str, str]]:
    return _MODEL_CATALOG


def is_catalog_model(model_name: str) -> bool:
    return any(item["name"] == model_name for item in _MODEL_CATALOG)
