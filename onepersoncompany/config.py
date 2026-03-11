from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv_if_present() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv_if_present()


def _as_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    project_name: str = "OnePersonCompany"
    data_dir: Path = Path(os.getenv("OPC_DATA_DIR", "data"))
    host: str = os.getenv("OPC_HOST", "0.0.0.0")
    port: int = int(os.getenv("OPC_PORT", "8100"))
    default_lang: str = os.getenv("OPC_DEFAULT_LANG", "zh")
    llm_enabled: bool = _as_bool(os.getenv("OPC_LLM_ENABLED"), True)
    llm_provider: str = os.getenv("OPC_LLM_PROVIDER", "openai")
    llm_model: str = os.getenv("OPC_LLM_MODEL", "gpt-4.1-mini")
    llm_temperature: float = float(os.getenv("OPC_LLM_TEMPERATURE", "0.3"))
    llm_timeout_sec: int = int(os.getenv("OPC_LLM_TIMEOUT_SEC", "45"))
    llm_read_timeout_sec: int = int(os.getenv("OPC_LLM_READ_TIMEOUT_SEC", str(int(os.getenv("OPC_LLM_TIMEOUT_SEC", "45")))))
    llm_connect_timeout_sec: int = int(os.getenv("OPC_LLM_CONNECT_TIMEOUT_SEC", "10"))
    llm_write_timeout_sec: int = int(os.getenv("OPC_LLM_WRITE_TIMEOUT_SEC", "30"))
    llm_max_retries: int = int(os.getenv("OPC_LLM_MAX_RETRIES", "2"))
    llm_retry_backoff_sec: float = float(os.getenv("OPC_LLM_RETRY_BACKOFF_SEC", "1.5"))
    llm_strict: bool = _as_bool(os.getenv("OPC_LLM_STRICT"), True)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_base_url: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    compat_api_key: str = os.getenv("OPC_COMPAT_API_KEY", "")
    compat_base_url: str = os.getenv("OPC_COMPAT_BASE_URL", "")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    dashscope_base_url: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    moonshot_api_key: str = os.getenv("MOONSHOT_API_KEY", "")
    moonshot_base_url: str = os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
    zhipu_api_key: str = os.getenv("ZHIPU_API_KEY", "")
    zhipu_base_url: str = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")


settings = Settings()
