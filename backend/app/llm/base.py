"""Provider-agnostic LLM layer: model tiering, JSON validation w/ one repair retry,
response cache for deterministic calls, token/latency/cost tracking."""
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol, Type
from pydantic import BaseModel, ValidationError


class LLMError(Exception):
    pass


@dataclass
class RawResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class Provider(Protocol):
    def complete(self, *, model: str, system: str, user: str, json_mode: bool,
                 max_tokens: int, temperature: float) -> RawResult: ...


@dataclass
class LLMRequest:
    task: str
    system: str
    user: str
    tier: str = "cheap"                    # "cheap" | "strong" -> mapped via config, never hardcoded
    schema: Type[BaseModel] | None = None  # if set: output must validate
    prompt_version: str = "v1"
    max_tokens: int = 800
    temperature: float = 0.0
    user_id: int | None = None
    use_cache: bool = True


@dataclass
class LLMResult:
    text: str
    parsed: BaseModel | None
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float
    cached: bool = False


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.M)


def extract_json(text: str) -> dict:
    t = _FENCE.sub("", text.strip())
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        s, e = t.find("{"), t.rfind("}")
        if s != -1 and e > s:
            return json.loads(t[s:e + 1])
        raise


@dataclass
class LLMService:
    provider: Provider
    models: dict[str, str]                                   # tier -> model id
    pricing: dict[str, tuple[float, float]] = field(default_factory=dict)  # $/1M tokens (in, out)
    recorder: Callable[[dict], None] | None = None
    _cache: dict[str, LLMResult] = field(default_factory=dict)

    def _cost(self, model: str, i: int, o: int) -> float:
        pi, po = self.pricing.get(model, (0.0, 0.0))
        return (i * pi + o * po) / 1_000_000

    def _key(self, model: str, r: LLMRequest) -> str:
        return hashlib.sha256(json.dumps([model, r.prompt_version, r.system, r.user]).encode()).hexdigest()

    def run(self, r: LLMRequest) -> LLMResult:
        if r.tier not in self.models:
            raise LLMError(f"unknown tier {r.tier!r}")
        model = self.models[r.tier]
        cacheable = r.use_cache and r.temperature == 0
        key = self._key(model, r)
        if cacheable and key in self._cache:
            hit = self._cache[key]
            res = LLMResult(hit.text, hit.parsed, model, 0, 0, 0, 0.0, cached=True)
            self._record(r, res)
            return res

        t0 = time.perf_counter()
        tin = tout = 0
        user = r.user
        parsed = None
        text = ""
        for attempt in range(2 if r.schema else 1):
            try:
                raw = self.provider.complete(model=model, system=r.system, user=user,
                                             json_mode=r.schema is not None,
                                             max_tokens=r.max_tokens, temperature=r.temperature)
            except LLMError:
                self._record(r, LLMResult("", None, model, tin, tout,
                                          int((time.perf_counter() - t0) * 1000), 0.0), failed=True)
                raise
            tin += raw.input_tokens
            tout += raw.output_tokens
            text = raw.text
            if not r.schema:
                break
            try:
                parsed = r.schema.model_validate(extract_json(text))
                break
            except (json.JSONDecodeError, ValidationError) as e:
                if attempt == 1:
                    self._record(r, LLMResult(text, None, model, tin, tout,
                                              int((time.perf_counter() - t0) * 1000), self._cost(model, tin, tout)),
                                 failed=True)
                    raise LLMError(f"{r.task}: invalid structured output after retry: {str(e)[:200]}") from e
                user = r.user + f"\n\nYour previous output was invalid ({str(e)[:200]}). Return ONLY valid JSON matching the schema."
        res = LLMResult(text, parsed, model, tin, tout, int((time.perf_counter() - t0) * 1000),
                        self._cost(model, tin, tout))
        if cacheable:
            self._cache[key] = res
        self._record(r, res)
        return res

    def _record(self, r: LLMRequest, res: LLMResult, failed: bool = False):
        if self.recorder:
            self.recorder(dict(user_id=r.user_id, task=r.task + (":failed" if failed else ""), model=res.model,
                               prompt_version=r.prompt_version, input_tokens=res.input_tokens,
                               output_tokens=res.output_tokens, latency_ms=res.latency_ms,
                               cost_usd=res.cost_usd, cached=int(res.cached)))
