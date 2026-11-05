"""Thin, validated wrapper around the official Groq SDK.

- chat_text(): plain text reply.
- chat_json(): structured reply validated against a Pydantic model, with one repair attempt.
Every SDK error is converted into LLMError with a message that is safe to show users.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import TypeVar

import groq
from pydantic import BaseModel, ValidationError

from app.config import get_settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

# Groq docs: gpt-oss models support response_format json_schema; others only json_object.
JSON_SCHEMA_MODEL_PREFIXES = ("openai/gpt-oss-",)


class LLMError(RuntimeError):
    """Groq call failed or produced unusable output (message is safe to show users)."""


class MissingCredentialError(LLMError):
    pass


class _RetryableOutput(Exception):
    """Groq rejected the generation because it did not match JSON/schema — worth one retry."""


@dataclass
class LLMUsage:
    groq_calls: int = 0
    groq_prompt_tokens: int = 0
    groq_completion_tokens: int = 0

    def add(self, resp) -> None:
        self.groq_calls += 1
        if u := getattr(resp, "usage", None):
            self.groq_prompt_tokens += u.prompt_tokens or 0
            self.groq_completion_tokens += u.completion_tokens or 0

    def as_dict(self) -> dict:
        return asdict(self)


def get_client() -> groq.Groq:
    s = get_settings()
    if s.groq_api_key is None or not s.groq_api_key.get_secret_value().strip():
        raise MissingCredentialError(
            "GROQ_API_KEY is missing. Copy backend/.env.example to backend/.env and add your key."
        )
    return groq.Groq(
        api_key=s.groq_api_key.get_secret_value(), timeout=s.groq_timeout_s, max_retries=s.groq_max_retries
    )


def _create(client: groq.Groq, **kwargs):
    model = kwargs.get("model", "")
    if model.startswith("openai/gpt-oss-"):
        kwargs.setdefault("reasoning_effort", "low")  # keep hidden reasoning (and token use) small
    try:
        return client.chat.completions.create(**kwargs)
    except groq.AuthenticationError as e:
        raise LLMError("Groq rejected the API key (401). Check GROQ_API_KEY in backend/.env.") from e
    except groq.RateLimitError as e:
        raise LLMError(
            "Groq rate/token limit reached (429) after retries. Wait a bit, or check "
            "console.groq.com/settings/limits."
        ) from e
    except groq.NotFoundError as e:
        raise LLMError(f"Groq model '{model}' not found. Run: python -m scripts.groq_ping --list-models") from e
    except groq.BadRequestError as e:
        text = str(e).lower()
        if "json" in text or "schema" in text:
            raise _RetryableOutput(str(e)[:300]) from e
        raise LLMError(f"Groq rejected the request (400): {str(e)[:200]}") from e
    except groq.APITimeoutError as e:  # subclass of APIConnectionError → must come first
        raise LLMError("Groq request timed out.") from e
    except groq.APIConnectionError as e:
        raise LLMError("Could not reach Groq (network error).") from e
    except groq.APIStatusError as e:
        raise LLMError(f"Groq API error {e.status_code}.") from e


def chat_text(
    user: str,
    *,
    system: str = "You are a concise assistant.",
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 400,
    client: groq.Groq | None = None,
) -> tuple[str, LLMUsage]:
    client, usage = client or get_client(), LLMUsage()
    resp = _create(
        client,
        model=model or get_settings().groq_model,
        temperature=temperature,
        max_completion_tokens=max_tokens,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    usage.add(resp)
    return (resp.choices[0].message.content or "").strip(), usage


def response_format_for(schema: type[BaseModel], model: str) -> dict:
    if model.startswith(JSON_SCHEMA_MODEL_PREFIXES):
        return {"type": "json_schema", "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()}}
    return {"type": "json_object"}


def chat_json(
    schema: type[T],
    *,
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 2000,
    attempts: int = 2,
    client: groq.Groq | None = None,
) -> tuple[T, LLMUsage]:
    """Structured call: JSON → Pydantic validation → one repair attempt → LLMError."""
    client, usage = client or get_client(), LLMUsage()
    model = model or get_settings().groq_model
    messages = [
        {
            "role": "system",
            "content": f"{system}\n\nRespond ONLY with a JSON object matching this JSON Schema:\n"
            f"{json.dumps(schema.model_json_schema())}",
        },
        {"role": "user", "content": user},
    ]
    last_err = ""
    for attempt in range(1, attempts + 1):
        try:
            resp = _create(
                client,
                model=model,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_tokens,
                response_format=response_format_for(schema, model),
            )
        except _RetryableOutput as e:
            last_err = str(e)
            log.warning("Groq JSON generation rejected (attempt %d/%d)", attempt, attempts)
            continue
        usage.add(resp)
        content = resp.choices[0].message.content or ""
        try:
            return schema.model_validate_json(content), usage
        except ValidationError as e:
            last_err = str(e)[:800]
            log.warning("Groq output failed %s validation (attempt %d/%d)", schema.__name__, attempt, attempts)
            messages += [
                {"role": "assistant", "content": content[:4000]},
                {"role": "user", "content": f"That JSON failed validation:\n{last_err}\nReturn a corrected JSON object only."},
            ]
    raise LLMError(f"Model output did not match {schema.__name__} after {attempts} attempts.")
