"""Prove the three caches in this repo actually fire.

1. LLM prompt-prefix cache: chat_create sends prompt_cache_key + breakpoints.
2. Auth TTL cache: a second authenticate() does not hit Postgres.
3. Bus topology TTL cache: a second _all_stops() does not re-query.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import authenticator  # noqa: E402
import bus_function  # noqa: E402
import llm  # noqa: E402
import metrics  # noqa: E402


def fake_chat_response(
    content="ok",
    *,
    prompt_tokens=100,
    completion_tokens=5,
    cached_tokens=0,
):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            prompt_tokens_details=SimpleNamespace(cached_tokens=cached_tokens),
        ),
    )


def fake_openai_client(create_fn):
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create_fn))
    )


def _load_executor():
    existing = sys.modules.get("unihelp_executor")
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(
        "unihelp_executor",
        _HERE / "executor.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["unihelp_executor"] = module
    spec.loader.exec_module(module)
    return module


class TestLlmPromptCache:
    def test_cached_system_message_marks_prefix_cacheable(self):
        message = llm.cached_system_message("You are the executor.")

        assert message["role"] == "system"
        part = message["content"][0]
        assert part["type"] == "text"
        assert part["text"] == "You are the executor."
        assert part["cache_control"] == {"type": "ephemeral"}
        assert part["prompt_cache_breakpoint"] == {"mode": "explicit"}

    def test_identity_message_is_plain_so_it_does_not_bust_the_prefix(self):
        message = llm.identity_message(
            {"role": "student", "name": "Ada"},
            label="Authenticated user",
        )

        assert message["role"] == "system"
        assert isinstance(message["content"], str)
        assert "Ada" in message["content"]
        assert "cache_control" not in message

    def test_chat_create_sends_prompt_cache_key_and_breakpoints(
        self, monkeypatch
    ):
        captured = {}

        def fake_create(**kwargs):
            captured.update(kwargs)
            return fake_chat_response(cached_tokens=80)

        monkeypatch.setattr(llm, "get_client", lambda: fake_openai_client(fake_create))

        llm.chat_create(
            cache_key="executor",
            messages=[
                llm.cached_system_message("stable prefix"),
                {"role": "user", "content": "combine these results"},
            ],
            tools=[{"type": "function", "function": {"name": "lookup"}}],
        )

        assert captured["prompt_cache_key"] == "executor"
        prefix = captured["messages"][0]["content"][0]
        assert prefix["cache_control"] == {"type": "ephemeral"}
        assert prefix["prompt_cache_breakpoint"] == {"mode": "explicit"}
        assert captured["tools"][-1]["cache_control"] == {"type": "ephemeral"}
        from config import LLM_MODEL

        assert captured["model"] == LLM_MODEL

    def test_gateway_cache_hit_is_recorded_in_metrics(self, monkeypatch):
        def fake_create(**kwargs):
            return fake_chat_response(
                prompt_tokens=200,
                completion_tokens=10,
                cached_tokens=160,
            )

        monkeypatch.setattr(llm, "get_client", lambda: fake_openai_client(fake_create))
        metrics.reset()

        with metrics.request_scope(
            user_name="Ada",
            user_role="student",
            roll_number="2501CS00",
            query="dinner and bus",
        ):
            llm.chat_create(
                cache_key="executor",
                messages=[llm.cached_system_message("stable prefix")],
            )

        snap = metrics.snapshot()
        assert snap["totals"]["cached_tokens"] == 160
        call = snap["requests"][0]["llm_calls"][0]
        assert call["cache_key"] == "executor"
        assert call["cached_tokens"] == 160


class TestExecutorUsesPromptCache:
    def test_multi_task_synthesis_sends_executor_cache_fields(
        self, monkeypatch
    ):
        captured = {}

        def fake_create(**kwargs):
            captured.update(kwargs)
            return fake_chat_response(content="dinner and bus combined")

        monkeypatch.setattr(llm, "get_client", lambda: fake_openai_client(fake_create))

        executor_mod = _load_executor()
        ex = executor_mod.Executor()
        order = []

        def stub(name):
            def _call(request, user_metadata):
                order.append(name)
                return f"{name}:{request}"

            return _call

        ex._agent_map = {name: stub(name) for name in list(ex._agent_map)}

        result = ex.execute(
            "dinner and bus",
            {
                "tasks": [
                    {"agent": "mess", "request": "Kalam dinner"},
                    {"agent": "bus", "request": "Bus 02 schedule"},
                ]
            },
            {"role": "student", "name": "Ada", "roll_number": "2501CS00"},
        )

        assert result == "dinner and bus combined"
        assert order == ["mess", "bus"]
        assert captured["prompt_cache_key"] == "executor"
        part = captured["messages"][0]["content"][0]
        assert part["text"] == executor_mod.Executor.SYSTEM_PROMPT
        assert part["cache_control"] == {"type": "ephemeral"}
        assert part["prompt_cache_breakpoint"] == {"mode": "explicit"}
        assert "mess:Kalam dinner" in captured["messages"][1]["content"]


class TestAuthTtlCache:
    @pytest.fixture(autouse=True)
    def _clear_auth_cache(self):
        authenticator.invalidate_auth_cache()
        yield
        authenticator.invalidate_auth_cache()

    def _patch_db(self, monkeypatch, row):
        calls = {"count": 0}

        class FakeCursor:
            def execute(self, sql, params=None):
                calls["count"] += 1

            def fetchone(self):
                return row

            def close(self):
                pass

        class FakeConn:
            def cursor(self):
                return FakeCursor()

            def close(self):
                pass

        monkeypatch.setattr(authenticator, "_get_connection", lambda: FakeConn())
        return calls

    def test_second_authenticate_is_a_cache_hit(self, monkeypatch):
        calls = self._patch_db(
            monkeypatch,
            ("key-ada", "student", "Ada", "2501CS00"),
        )

        first = authenticator.authenticate("key-ada")
        second = authenticator.authenticate("key-ada")

        assert first == {
            "role": "student",
            "name": "Ada",
            "roll_number": "2501CS00",
        }
        assert second == first
        assert calls["count"] == 1

    def test_miss_is_cached_so_typos_do_not_hammer_the_db(self, monkeypatch):
        calls = self._patch_db(monkeypatch, None)

        assert authenticator.authenticate("nope") is None
        assert authenticator.authenticate("nope") is None
        assert calls["count"] == 1

    def test_expired_entry_hits_the_db_again(self, monkeypatch):
        now = {"t": 1_000.0}
        monkeypatch.setattr(authenticator.time, "time", lambda: now["t"])
        calls = self._patch_db(
            monkeypatch,
            ("key-ada", "student", "Ada", "2501CS00"),
        )

        authenticator.authenticate("key-ada")
        assert calls["count"] == 1

        now["t"] = 1_000.0 + authenticator._CACHE_TTL_SECONDS + 1
        authenticator.authenticate("key-ada")
        assert calls["count"] == 2

    def test_invalidate_forces_a_fresh_lookup(self, monkeypatch):
        calls = self._patch_db(
            monkeypatch,
            ("key-ada", "student", "Ada", "2501CS00"),
        )

        authenticator.authenticate("key-ada")
        authenticator.invalidate_auth_cache("key-ada")
        authenticator.authenticate("key-ada")
        assert calls["count"] == 2


class TestBusTopologyCache:
    @pytest.fixture(autouse=True)
    def _clear_topology_cache(self):
        bus_function._invalidate_topology_cache()
        yield
        bus_function._invalidate_topology_cache()

    def test_second_all_stops_call_does_not_query_again(self, monkeypatch):
        fetches = []

        def fake_fetch(query, params=()):
            fetches.append(query)
            return [{"s": "Gate 1"}, {"s": "Kalam"}]

        monkeypatch.setattr(bus_function, "_fetch", fake_fetch)

        first = bus_function._all_stops()
        second = bus_function._all_stops()

        assert first == ["Gate 1", "Kalam"]
        assert second == first
        assert len(fetches) == 1

    def test_invalidate_makes_the_next_call_recompute(self, monkeypatch):
        fetches = []

        def fake_fetch(query, params=()):
            fetches.append(query)
            return [{"s": "Gate 1"}]

        monkeypatch.setattr(bus_function, "_fetch", fake_fetch)

        bus_function._all_stops()
        bus_function._invalidate_topology_cache()
        bus_function._all_stops()
        assert len(fetches) == 2

    def test_expired_topology_entry_recomputes(self, monkeypatch):
        now = {"t": 1_000.0}
        monkeypatch.setattr(bus_function.time, "time", lambda: now["t"])
        fetches = []

        def fake_fetch(query, params=()):
            fetches.append(query)
            return [{"s": "Gate 1"}]

        monkeypatch.setattr(bus_function, "_fetch", fake_fetch)

        bus_function._all_stops()
        assert len(fetches) == 1

        now["t"] = 1_000.0 + bus_function._TOPOLOGY_CACHE_TTL_SECONDS + 1
        bus_function._all_stops()
        assert len(fetches) == 2
