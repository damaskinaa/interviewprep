import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

KEYCHAIN_SERVICE = "nailit"
SECRET_NAMES = ("OPENAI_API_KEY", "TAVILY_API_KEY")


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
