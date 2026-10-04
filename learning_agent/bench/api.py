"""Minimal OpenAI/Anthropic-compatible chat client for bench runs.

stdlib-only (no requests dependency). Credentials and endpoints come from env:

    Anthropic protocol:  ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN (or ANTHROPIC_API_KEY)
    OpenAI protocol:     OPENAI_BASE_URL + OPENAI_API_KEY

Model selection: --model flag > BENCH_MODEL > ANTHROPIC_MODEL (anthropic) /
OPENAI_MODEL (openai). ``--mock`` replaces the client with a deterministic
offline generator for pipeline tests; mock runs are recorded as such and never
count as evidence.
"""

from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.request

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
RETRYABLE_EXCEPTIONS = (
    urllib.error.URLError,
    TimeoutError,
    ConnectionError,
    http.client.IncompleteRead,
    http.client.RemoteDisconnected,
    OSError,
)


class APIError(RuntimeError):
    pass


def _post_json(url: str, payload: dict, headers: dict[str, str], timeout: float, max_retries: int = 3) -> dict:
    data = json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(max_retries):
        request = urllib.request.Request(url, data=data, method="POST")
        for key, value in headers.items():
            request.add_header(key, value)
        request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            if exc.code in RETRYABLE_STATUS and attempt < max_retries - 1:
                time.sleep(2**attempt * 2)
                last_error = APIError(f"HTTP {exc.code}: {body}")
                continue
            raise APIError(f"HTTP {exc.code}: {body}") from exc
        except RETRYABLE_EXCEPTIONS as exc:
            if attempt < max_retries - 1:
                time.sleep(2**attempt * 2)
                last_error = exc
                continue
            raise APIError(f"connection failed after {max_retries} attempts: {exc}") from exc
    raise APIError(str(last_error))


class AnthropicClient:
    protocol = "anthropic"

    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None, timeout: float = 120.0):
        self.model = model
        self.base_url = (base_url or os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
        self.api_key = api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY") or ""
        self.timeout = timeout
        if not self.api_key:
            raise APIError("missing ANTHROPIC_AUTH_TOKEN / ANTHROPIC_API_KEY in environment")

    def complete(self, system: str | None, user: str, max_tokens: int, temperature: float = 0.0) -> dict:
        payload: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": user}],
        }
        if system:
            payload["system"] = system
        headers = {"x-api-key": self.api_key, "authorization": f"Bearer {self.api_key}", "anthropic-version": "2023-06-01"}
        response = _post_json(f"{self.base_url}/v1/messages", payload, headers, self.timeout)
        try:
            text = "".join(block.get("text", "") for block in response["content"] if block.get("type") == "text")
        except (KeyError, TypeError) as exc:
            raise APIError(f"unexpected anthropic response shape: {str(response)[:300]}") from exc
        usage = response.get("usage", {})
        return {
            "text": text,
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "stop_reason": response.get("stop_reason"),
        }


class OpenAIClient:
    protocol = "openai"

    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None, timeout: float = 120.0):
        self.model = model
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or ""
        self.timeout = timeout
        if not self.api_key:
            raise APIError("missing OPENAI_API_KEY in environment")

    def complete(self, system: str | None, user: str, max_tokens: int, temperature: float = 0.0) -> dict:
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
        payload = {"model": self.model, "max_tokens": max_tokens, "temperature": temperature, "messages": messages}
        headers = {"authorization": f"Bearer {self.api_key}"}
        response = _post_json(f"{self.base_url}/chat/completions", payload, headers, self.timeout)
        try:
            choice = response["choices"][0]
            text = choice["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise APIError(f"unexpected openai response shape: {str(response)[:300]}") from exc
        usage = response.get("usage", {})
        return {
            "text": text,
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "stop_reason": choice.get("finish_reason"),
        }


class MockClient:
    """Deterministic offline client for pipeline wiring tests. NOT evidence.

    Recognizes the frozen bench prompts and answers each stage with valid JSON
    so runner→judge→report can be exercised without network. Teaching answers
    are clearly marked as mock; all judge scores are constant on purpose so a
    mock report can never look like a real advantage claim.
    """

    protocol = "mock"

    def __init__(self, model: str = "mock-model", **_kwargs):
        self.model = model

    def complete(self, system: str | None, user: str, max_tokens: int, temperature: float = 0.0) -> dict:
        from learning_agent.bench.prompts import (
            JUDGE_SYSTEM_PROMPT_V1,
            LEARNER_DIAG_SYSTEM_PROMPT_V1,
            LEARNER_POSTTEST_SYSTEM_PROMPT_V1,
            POST_TEST_JUDGE_SYSTEM_PROMPT_V1,
        )

        if system == JUDGE_SYSTEM_PROMPT_V1:
            units = [
                {"id": "E1", "text": "mock: diagnostic statement", "addresses_gap": True},
                {"id": "E2", "text": "mock: targeted explanation", "addresses_gap": True},
                {"id": "E3", "text": "mock: generic filler", "addresses_gap": False},
            ]
            text = json.dumps(
                {
                    "correctness": 4, "diagnostic_precision": 4, "explanation_relevance": 4,
                    "cognitive_load": 4, "hint_quality": 4, "misconception_handling": 4,
                    "transfer_quality": 4, "diagnosis_found": "mock diagnosis",
                    "units": units, "notes": "mock judge output (pipeline test only)",
                },
                ensure_ascii=False,
            )
        elif system == LEARNER_DIAG_SYSTEM_PROMPT_V1:
            text = "mock learner: 我现在的理解是……（诊断问题回答，流水线测试占位）"
        elif system == LEARNER_POSTTEST_SYSTEM_PROMPT_V1:
            tiers = ["isomorphic", "near_transfer", "far_transfer"]
            answers = [
                {"tier": tier, "answer": f"mock learner answer for {tier}"} for tier in tiers if tier in user
            ]
            text = json.dumps({"answers": answers}, ensure_ascii=False)
        elif system == POST_TEST_JUDGE_SYSTEM_PROMPT_V1:
            tiers = {
                tier: {"correct": 1, "reason": "mock grading"} for tier in ("isomorphic", "near_transfer", "far_transfer") if tier in user
            }
            text = json.dumps(
                {"tiers": tiers, "misconception_corrected": True, "notes": "mock post-test grading"},
                ensure_ascii=False,
            )
        else:
            text = (
                "（mock 输出，仅用于流水线验证，不构成证据）\n"
                "先确认卡点——你的问题属于诊断环节要处理的内容。\n"
                "第一步，回顾定义；第二步，用一个例子说明；第三步，请你用自己的话复述一遍？\n"
                "常见误区：把结论当定义用。变式：换一个场景再试一次。"
            )
        return {
            "text": text,
            "input_tokens": len(user) // 4,
            "output_tokens": len(text) // 4,
            "stop_reason": "end_turn",
        }


def detect_provider() -> str:
    if os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    raise APIError(
        "no API credentials found; set ANTHROPIC_AUTH_TOKEN/ANTHROPIC_API_KEY or OPENAI_API_KEY, "
        "or use --mock for offline pipeline testing"
    )


def default_model(provider: str) -> str | None:
    if os.environ.get("BENCH_MODEL"):
        return os.environ["BENCH_MODEL"]
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_MODEL")
    if provider == "openai":
        return os.environ.get("OPENAI_MODEL")
    return "mock-model"


def make_client(provider: str, model: str | None, timeout: float = 120.0, mock: bool = False):
    if mock:
        return MockClient()
    if provider == "anthropic":
        return AnthropicClient(model=model or default_model("anthropic") or "", timeout=timeout)
    if provider == "openai":
        return OpenAIClient(model=model or default_model("openai") or "", timeout=timeout)
    if provider == "mock":
        return MockClient()
    raise APIError(f"unknown provider {provider!r}; expected anthropic | openai | mock")
