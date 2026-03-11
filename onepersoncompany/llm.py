from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

import httpx

from .config import settings
from .logging_setup import get_logger

logger = get_logger("onepersoncompany.llm")


class LLMClient:
    def __init__(self) -> None:
        if settings.llm_provider == "anthropic":
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required when OPC_LLM_PROVIDER=anthropic")
            return
        self._resolve_openai_like_credentials()

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if settings.llm_provider in {"openai", "openai_compatible", "deepseek", "dashscope", "moonshot", "zhipu"}:
            return self._generate_openai_like(system_prompt, user_prompt)
        if settings.llm_provider == "anthropic":
            return self._generate_anthropic(system_prompt, user_prompt)
        raise ValueError(
            "Unsupported OPC_LLM_PROVIDER. Use one of: "
            "openai, anthropic, openai_compatible, deepseek, dashscope, moonshot, zhipu."
        )

    def _resolve_openai_like_credentials(self) -> Tuple[str, str]:
        provider = settings.llm_provider
        if provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when OPC_LLM_PROVIDER=openai")
            return settings.openai_base_url, settings.openai_api_key
        if provider == "openai_compatible":
            if not settings.compat_api_key or not settings.compat_base_url:
                raise ValueError(
                    "OPC_COMPAT_API_KEY and OPC_COMPAT_BASE_URL are required when "
                    "OPC_LLM_PROVIDER=openai_compatible"
                )
            return settings.compat_base_url, settings.compat_api_key
        if provider == "deepseek":
            if not settings.deepseek_api_key:
                raise ValueError("DEEPSEEK_API_KEY is required when OPC_LLM_PROVIDER=deepseek")
            return settings.deepseek_base_url, settings.deepseek_api_key
        if provider == "dashscope":
            if not settings.dashscope_api_key:
                raise ValueError("DASHSCOPE_API_KEY is required when OPC_LLM_PROVIDER=dashscope")
            return settings.dashscope_base_url, settings.dashscope_api_key
        if provider == "moonshot":
            if not settings.moonshot_api_key:
                raise ValueError("MOONSHOT_API_KEY is required when OPC_LLM_PROVIDER=moonshot")
            return settings.moonshot_base_url, settings.moonshot_api_key
        if provider == "zhipu":
            if not settings.zhipu_api_key:
                raise ValueError("ZHIPU_API_KEY is required when OPC_LLM_PROVIDER=zhipu")
            return settings.zhipu_base_url, settings.zhipu_api_key
        raise ValueError(
            "Unsupported openai-like provider. Use one of: openai, openai_compatible, deepseek, "
            "dashscope, moonshot, zhipu."
        )

    def _build_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            timeout=settings.llm_timeout_sec,
            connect=settings.llm_connect_timeout_sec,
            read=settings.llm_read_timeout_sec,
            write=settings.llm_write_timeout_sec,
        )

    @staticmethod
    def _should_retry_status(code: int) -> bool:
        return code in {408, 409, 425, 429, 500, 502, 503, 504}

    def _post_with_retries(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        last_error: Optional[Exception] = None
        timeout = self._build_timeout()

        for attempt in range(settings.llm_max_retries + 1):
            try:
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(url, json=payload, headers=headers)

                if self._should_retry_status(response.status_code) and attempt < settings.llm_max_retries:
                    delay = settings.llm_retry_backoff_sec * (attempt + 1)
                    logger.warning(
                        "LLM temporary status=%s attempt=%s/%s retry_in=%.1fs",
                        response.status_code,
                        attempt + 1,
                        settings.llm_max_retries + 1,
                        delay,
                    )
                    time.sleep(delay)
                    continue

                response.raise_for_status()
                return response.json()

            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.RemoteProtocolError, httpx.NetworkError) as exc:
                last_error = exc
                if attempt >= settings.llm_max_retries:
                    break
                delay = settings.llm_retry_backoff_sec * (attempt + 1)
                logger.warning(
                    "LLM network timeout attempt=%s/%s retry_in=%.1fs error=%s",
                    attempt + 1,
                    settings.llm_max_retries + 1,
                    delay,
                    exc,
                )
                time.sleep(delay)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if attempt >= settings.llm_max_retries or not self._should_retry_status(exc.response.status_code):
                    raise
                delay = settings.llm_retry_backoff_sec * (attempt + 1)
                logger.warning(
                    "LLM retryable HTTP error status=%s attempt=%s/%s retry_in=%.1fs",
                    exc.response.status_code,
                    attempt + 1,
                    settings.llm_max_retries + 1,
                    delay,
                )
                time.sleep(delay)

        if last_error is None:
            raise RuntimeError("LLM request failed without detailed error")
        raise last_error

    def _generate_openai_like(self, system_prompt: str, user_prompt: str) -> str:
        base_url, api_key = self._resolve_openai_like_credentials()
        url = base_url.rstrip("/") + "/chat/completions"
        payload: Dict[str, Any] = {
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        data = self._post_with_retries(url=url, payload=payload, headers=headers)
        return data["choices"][0]["message"]["content"].strip()

    def _generate_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        url = settings.anthropic_base_url.rstrip("/") + "/v1/messages"
        payload: Dict[str, Any] = {
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "max_tokens": 1400,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        data = self._post_with_retries(url=url, payload=payload, headers=headers)
        blocks = data.get("content", [])
        texts = [block.get("text", "") for block in blocks if block.get("type") == "text"]
        return "\n".join([item for item in texts if item]).strip()
