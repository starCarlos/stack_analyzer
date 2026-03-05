from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from typing import Any

from app.llm import cache


def _endpoint() -> str:
    base = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    style = os.getenv("LLM_API_STYLE", "chat_completions").lower()
    return f"{base}/responses" if style == "responses" else f"{base}/chat/completions"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.getenv('LLM_API_KEY', '').strip()}",
        "Content-Type": "application/json",
    }


def _cache_key(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _default_system_prompt() -> str:
    return os.getenv(
        "LLM_SYSTEM_PROMPT",
        "你是严谨的A股投研分析助手。请输出简洁、结构化、可执行的结论；若要求JSON则仅输出JSON。",
    )


def _build_messages(prompt: str | None, system: str | None, messages: list[dict] | None) -> list[dict]:
    if messages:
        return messages
    out: list[dict] = []
    out.append({"role": "system", "content": system or _default_system_prompt()})
    out.append({"role": "user", "content": prompt or ""})
    return out


def _post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url=url, data=data, headers=_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_content_chat(raw: dict[str, Any]) -> str:
    return raw.get("choices", [{}])[0].get("message", {}).get("content", "")


def _extract_content_responses(raw: dict[str, Any]) -> str:
    if isinstance(raw.get("output_text"), str):
        return raw["output_text"]
    chunks: list[str] = []
    for item in raw.get("output", []) or []:
        for c in item.get("content", []) or []:
            if c.get("type") in {"output_text", "text"} and c.get("text"):
                chunks.append(c["text"])
    return "\n".join(chunks).strip()


def _to_responses_input(messages: list[dict]) -> tuple[str, list[dict]]:
    instructions_parts: list[str] = []
    input_items: list[dict] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            text = "\n".join([str(x.get("text", "")) if isinstance(x, dict) else str(x) for x in content])
        else:
            text = str(content)
        if role == "system":
            instructions_parts.append(text)
            continue
        input_items.append(
            {
                "role": role if role in {"user", "assistant"} else "user",
                "content": [{"type": "input_text", "text": text}],
            }
        )
    if not input_items:
        input_items = [{"role": "user", "content": [{"type": "input_text", "text": ""}]}]
    instructions = "\n".join([x for x in instructions_parts if x]).strip() or _default_system_prompt()
    return instructions, input_items


def _normalize_responses_format(response_format: dict[str, Any]) -> dict[str, Any]:
    """
    兼容不同网关对 Responses `text.format` 的字段要求。
    - 传入 chat-completions 风格:
      {"type":"json_schema","json_schema":{"name":"x","schema":{...},"strict":true}}
    - 转成 responses 常见风格:
      {"type":"json_schema","name":"x","schema":{...},"strict":true}
    """
    rf_type = response_format.get("type")
    if rf_type == "json_schema" and isinstance(response_format.get("json_schema"), dict):
        js = response_format["json_schema"]
        return {
            "type": "json_schema",
            "name": js.get("name", "response"),
            "schema": js.get("schema", {}),
            "strict": bool(js.get("strict", True)),
        }
    return response_format


def chat(
    prompt: str | None = None,
    *,
    system: str | None = None,
    messages: list[dict] | None = None,
    response_format: dict[str, Any] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: int | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "error": "LLM_API_KEY is empty", "content": "", "source": "no_key"}

    style = os.getenv("LLM_API_STYLE", "chat_completions").lower()
    messages_final = _build_messages(prompt, system, messages)
    payload: dict[str, Any] = {
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")) if temperature is None else temperature,
    }
    if style == "responses":
        instructions, input_items = _to_responses_input(messages_final)
        payload["instructions"] = instructions
        payload["input"] = input_items
    else:
        payload["messages"] = messages_final
    if max_tokens is not None:
        if style == "responses":
            payload["max_output_tokens"] = max_tokens
        else:
            payload["max_tokens"] = max_tokens
    if response_format is not None:
        if style == "responses":
            payload["text"] = {"format": _normalize_responses_format(response_format)}
        else:
            payload["response_format"] = response_format

    key = _cache_key(payload)
    if use_cache:
        hit = cache.get(key)
        if hit:
            return dict(hit)

    timeout = int(os.getenv("LLM_TIMEOUT", "60")) if timeout is None else int(timeout)
    try:
        raw = _post_json(_endpoint(), payload, timeout=timeout)
        content = _extract_content_responses(raw) if style == "responses" else _extract_content_chat(raw)
        result = {
            "ok": True,
            "content": content,
            "raw": raw,
            "model": payload["model"],
            "source": f"remote:{style}",
        }
        if use_cache:
            cache.set_(key, result)
        return result
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:  # noqa: BLE001
            detail = str(exc)
        return {"ok": False, "error": f"http_error:{exc.code}", "detail": detail, "content": "", "source": "error"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "content": "", "source": "error"}


def chat_json(
    prompt: str,
    *,
    system: str | None = None,
    json_schema: dict[str, Any] | None = None,
    schema_name: str = "response",
    strict: bool = True,
    use_cache: bool = True,
) -> dict[str, Any]:
    style = os.getenv("LLM_API_STYLE", "chat_completions").lower()
    if json_schema:
        rf = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": json_schema, "strict": strict},
        }
    else:
        rf = {"type": "json_object"}

    retry = int(os.getenv("LLM_JSON_RETRY", "1"))
    max_out = int(os.getenv("LLM_JSON_MAX_TOKENS", "220"))
    timeout_override = int(os.getenv("LLM_JSON_TIMEOUT", os.getenv("LLM_TIMEOUT", "60")))

    def _call(fmt: dict[str, Any] | None, sys_prompt: str | None, cache_flag: bool) -> dict[str, Any]:
        return chat(
            prompt,
            system=sys_prompt,
            response_format=fmt,
            max_tokens=max_out,
            timeout=timeout_override,
            use_cache=cache_flag,
        )

    # 1) 优先 response_format（严格）
    resp = _call(rf, system, use_cache)
    # 2) responses 网关常见不支持 format，或超时，降级到纯文本 JSON
    if (not resp.get("ok")) and style == "responses":
        fallback_system = (system or _default_system_prompt()) + "\n只输出一个合法JSON对象，不要输出任何解释文本。"
        resp = _call(None, fallback_system, False)
    # 3) 再次重试（可配置次数）
    attempts = 0
    while (not resp.get("ok")) and attempts < retry:
        attempts += 1
        fallback_system = (system or _default_system_prompt()) + "\n仅返回JSON对象，字段必须完整，内容尽量简短。"
        resp = _call(None, fallback_system, False)
    if not resp.get("ok"):
        return resp
    text = resp.get("content", "").strip()
    try:
        parsed = json.loads(text) if text else {}
        resp["parsed"] = parsed
        return resp
    except Exception as exc:  # noqa: BLE001
        resp["ok"] = False
        resp["error"] = f"json_parse_error:{exc}"
        return resp
