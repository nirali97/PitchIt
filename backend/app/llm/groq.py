import time
import httpx
from .base import LLMError, RawResult

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3


class GroqProvider:
    def __init__(self, api_key: str, transport: httpx.BaseTransport | None = None, timeout: float = 30.0):
        if not api_key:
            raise LLMError("GROQ_API_KEY is not set")
        self._client = httpx.Client(timeout=timeout, transport=transport,
                                    headers={"Authorization": f"Bearer {api_key}"})

    def complete(self, *, model, system, user, json_mode, max_tokens, temperature) -> RawResult:
        body = {"model": model, "max_tokens": max_tokens, "temperature": temperature,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        last: Exception | None = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                r = self._client.post(GROQ_URL, json=body)
                if r.status_code in RETRY_STATUS and attempt < MAX_ATTEMPTS - 1:
                    time.sleep(0.8 * (attempt + 1))
                    continue
                r.raise_for_status()
                d = r.json()
                u = d.get("usage", {})
                return RawResult(d["choices"][0]["message"]["content"],
                                 u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
            except (httpx.TransportError, httpx.TimeoutException) as e:   # network-level: retry
                last = e
                if attempt < MAX_ATTEMPTS - 1:
                    time.sleep(0.8 * (attempt + 1))
                    continue
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
                last = e
                break
        raise LLMError(f"groq request failed: {type(last).__name__}: {str(last)[:150]}") from last
