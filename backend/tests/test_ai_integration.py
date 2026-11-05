"""AI integration tests. No network / API key needed: provider is faked and
Groq HTTP is mocked with httpx.MockTransport."""
import os
os.environ.setdefault('JWT_SECRET', 'test-secret-long-enough-for-local-tests-123456789')
os.environ.setdefault('DATABASE_URL', 'sqlite://')

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.main_state import engine, SessionLocal
from app.db import Base
from app.api import routes
from app.config import get_settings
from app.llm.base import LLMService, LLMError, RawResult
from app.llm.factory import make_recorder
from app.llm.groq import GroqProvider

client = TestClient(app)


class FakeProvider:
    def __init__(self, text="What is the largest driver of the cost increase?", fail=False):
        self.text, self.fail, self.prompts = text, fail, []

    def complete(self, *, model, system, user, json_mode, max_tokens, temperature):
        self.prompts.append(user)
        if self.fail:
            raise LLMError("groq request failed: HTTPStatusError: 401")
        return RawResult(self.text, 100, 20)


@pytest.fixture()
def env(monkeypatch):
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
    provider = FakeProvider()
    svc = LLMService(provider, {"cheap": "m", "strong": "m"}, {"m": (1.0, 2.0)}, make_recorder(SessionLocal))
    keyed = get_settings().model_copy(update={"groq_api_key": "test-key"})
    monkeypatch.setattr(routes, "get_settings", lambda: keyed)
    monkeypatch.setattr(routes, "get_llm", lambda s, f: svc)
    r = client.post('/api/auth/register', json={'email': 'a@example.com', 'password': 'strong-password'})
    h = {'Authorization': f"Bearer {r.json()['access_token']}"}
    sid = client.post('/api/sessions', headers=h, json={'module': 'case', 'case_ref': 'profitability_coffee'}).json()['id']
    return provider, h, sid


def test_turn_uses_llm_and_tracks_tokens(env):
    provider, h, sid = env
    r = client.post(f'/api/sessions/{sid}/turn', headers=h, json={'message': 'I would check costs first.'})
    assert r.status_code == 200, r.text
    assert r.json()['mode'] == 'groq' and r.json()['reply'].startswith('What is the largest')
    u = client.get('/api/usage', headers=h).json()['totals']
    assert (u['calls'], u['input_tokens'], u['output_tokens'], u['failed_calls']) == (1, 100, 20, 0)
    assert u['cost_usd'] == pytest.approx((100 * 1.0 + 20 * 2.0) / 1e6)


def test_second_turn_prompt_contains_history(env):
    provider, h, sid = env
    client.post(f'/api/sessions/{sid}/turn', headers=h, json={'message': 'FIRST-MARKER hypothesis about rent.'})
    client.post(f'/api/sessions/{sid}/turn', headers=h, json={'message': 'Second answer.'})
    assert 'FIRST-MARKER' in provider.prompts[1]


def test_provider_failure_is_safe_recorded_and_retryable(env):
    provider, h, sid = env
    provider.fail = True
    r = client.post(f'/api/sessions/{sid}/turn', headers=h, json={'message': 'My answer.'})
    assert r.status_code == 502
    assert 'test-key' not in r.text and 'HTTPStatusError' not in r.text      # no internals leaked
    s = client.get(f'/api/sessions/{sid}', headers=h).json()
    assert s['state']['turn'] == 0 and s['decisions'] == []                 # turn not half-saved
    assert client.get('/api/usage', headers=h).json()['totals']['failed_calls'] == 1
    provider.fail = False                                                    # retry succeeds
    assert client.post(f'/api/sessions/{sid}/turn', headers=h, json={'message': 'My answer.'}).status_code == 200


def test_empty_llm_reply_is_a_502(env):
    provider, h, sid = env
    provider.text = "   "
    assert client.post(f'/api/sessions/{sid}/turn', headers=h, json={'message': 'x'}).status_code == 502


def test_ai_status_and_probe(env):
    _, h, _ = env
    s = client.get('/api/ai/status', headers=h).json()
    assert s['configured'] is True and 'probe' not in s
    p = client.get('/api/ai/status?probe=true', headers=h).json()['probe']
    assert p['ok'] is True and p['input_tokens'] == 100


def test_ai_endpoints_require_auth():
    assert client.get('/api/usage').status_code == 401
    assert client.get('/api/ai/status').status_code == 401


def test_groq_retries_transient_then_succeeds(monkeypatch):
    monkeypatch.setattr('app.llm.groq.time.sleep', lambda s: None)
    calls = {'n': 0}

    def handler(req):
        calls['n'] += 1
        if calls['n'] == 1:
            return httpx.Response(429, json={'error': 'rate'})
        return httpx.Response(200, json={'choices': [{'message': {'content': 'hi'}}],
                                         'usage': {'prompt_tokens': 7, 'completion_tokens': 2}})
    p = GroqProvider('k', transport=httpx.MockTransport(handler))
    r = p.complete(model='m', system='s', user='u', json_mode=False, max_tokens=5, temperature=0)
    assert (r.text, r.input_tokens, r.output_tokens, calls['n']) == ('hi', 7, 2, 2)


def test_groq_does_not_retry_auth_errors(monkeypatch):
    monkeypatch.setattr('app.llm.groq.time.sleep', lambda s: None)
    calls = {'n': 0}

    def handler(req):
        calls['n'] += 1
        return httpx.Response(401, json={'error': 'bad key'})
    p = GroqProvider('k', transport=httpx.MockTransport(handler))
    with pytest.raises(LLMError):
        p.complete(model='m', system='s', user='u', json_mode=False, max_tokens=5, temperature=0)
    assert calls['n'] == 1
