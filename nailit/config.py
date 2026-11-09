import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

KEYCHAIN_SERVICE = "nailit"
SECRET_NAMES = ("OPENAI_API_KEY", "OPENAI_TTS_API_KEY", "TAVILY_API_KEY")


def keychain_secret(name: str) -> str:
    """Read a secret from the macOS Keychain (service "nailit", account = name)."""
    if sys.platform != "darwin":
        return ""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", name, "-w"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def load_secrets(env_file: Path | None = None) -> None:
    """Keychain first, then .env / existing environment as fallback."""
    load_dotenv(env_file or Path.cwd() / ".env")
    for name in SECRET_NAMES:
        value = keychain_secret(name)
        if value:
            os.environ[name] = value


def _price_pair(value: str) -> tuple[float, float]:
    parts = [p.strip() for p in (value or "").split(",")]
    try:
        return float(parts[0]), float(parts[1])
    except (IndexError, ValueError):
        return 0.0, 0.0


def llm_settings() -> dict:
    """Base URL, two models (fast, strong) and USD prices per 1M tokens, from the environment."""
    fast = os.getenv("NAILIT_MODEL_FAST") or os.getenv("OPENAI_MODEL_FAST") or "gpt-4o-mini"
    strong = os.getenv("NAILIT_MODEL_STRONG") or os.getenv("OPENAI_MODEL_STRATEGY") or "gpt-4o"
    return {
        "base_url": os.getenv("OPENAI_BASE_URL") or "",
        "model_fast": fast,
        "model_strong": strong,
        "prices": {
            "fast": _price_pair(os.getenv("NAILIT_PRICE_FAST", "0.15,0.60")),
            "strong": _price_pair(os.getenv("NAILIT_PRICE_STRONG", "2.50,10.00")),
        },
    }
