import asyncio

import pytest
from fastapi import HTTPException

from src.engine import providers
from src.routers.simulation import _generate_simulation_json


def _run(**kwargs):
    return asyncio.run(_generate_simulation_json(
        api_key=None,
        mistral_key=None,
        user_config=object(),
        prompt="return json",
        system_instruction="return valid json only",
        max_tokens=256,
        **kwargs,
    ))


@pytest.mark.parametrize(
    ("selected", "resolved_api", "resolved_mistral", "expected_key"),
    [
        ("openai", "openai-key", "", "openai-key"),
        ("groq", "groq-key", "", "groq-key"),
        ("mistral", "", "mistral-key", "mistral-key"),
    ],
)
def test_routes_to_the_selected_provider_and_its_own_key(
    monkeypatch, selected, resolved_api, resolved_mistral, expected_key
):
    calls = []
    monkeypatch.setattr(
        providers,
        "resolve_keys",
        lambda provider, api_key, mistral_key, config: (
            resolved_api, resolved_mistral, None
        ),
    )
    monkeypatch.setattr(providers, "get_model", lambda provider, config: f"{provider}-model")

    def fake_chat(**kwargs):
        calls.append(kwargs)
        return '{"ok": true}'

    monkeypatch.setattr(providers, "chat", fake_chat)
    result = _run(provider=selected)

    assert result == '{"ok": true}'
    assert len(calls) == 1
    assert calls[0]["provider"] == selected
    assert calls[0]["key"] == expected_key
    assert calls[0]["model_override"] == f"{selected}-model"


def test_hybrid_fallback_is_explicit_and_only_uses_its_two_configured_providers(monkeypatch):
    calls = []
    monkeypatch.setattr(
        providers, "resolve_keys", lambda *args: ("gemini-key", "mistral-key", None)
    )
    monkeypatch.setattr(providers, "get_model", lambda provider, config: f"{provider}-model")

    def fake_chat(**kwargs):
        calls.append(kwargs)
        if kwargs["provider"] == "gemini":
            raise RuntimeError("simulated provider outage")
        return '{"fallback": true}'

    monkeypatch.setattr(providers, "chat", fake_chat)
    assert _run(provider="hybrid") == '{"fallback": true}'
    assert [(call["provider"], call["key"]) for call in calls] == [
        ("gemini", "gemini-key"),
        ("mistral", "mistral-key"),
    ]


def test_single_provider_failure_is_reported_without_fallback(monkeypatch):
    calls = []
    monkeypatch.setattr(
        providers, "resolve_keys", lambda *args: ("openai-key", "", None)
    )
    monkeypatch.setattr(providers, "get_model", lambda *args: None)

    def fail_chat(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(providers, "chat", fail_chat)
    with pytest.raises(HTTPException) as exc:
        _run(provider="openai")

    assert exc.value.status_code == 502
    assert len(calls) == 1
    assert "provider unavailable" not in exc.value.detail


def test_rejects_unknown_provider_before_dispatch(monkeypatch):
    monkeypatch.setattr(providers, "chat", lambda **kwargs: pytest.fail("must not dispatch"))
    with pytest.raises(HTTPException) as exc:
        _run(provider="unknown-provider")
    assert exc.value.status_code == 400
