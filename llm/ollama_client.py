"""
llm/ollama_client.py — Thin client for the local Ollama OpenAI-compatible API.
"""

import json
import re
import secrets
import requests
from typing import Generator, List, Dict, Any, Optional

from config import (
    OLLAMA_API_URL,
    OLLAMA_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TOP_P,
    DEFAULT_NUM_CTX,
    MAX_INPUT_CHARS,
    MAX_HISTORY_TURNS,
    MAX_HISTORY_TOKENS,
    estimate_tokens,
    SYSTEM_PROMPT,
)
from rag.sanitize import sanitize_user_input, sanitize_context_chunk
from rag.output_guard import (
    guard_output,
    detect_system_prompt_leak,
    STANDARD_REFUSAL,
)


# ─── Thinking-block stripper ──────────────────────────────────────────────────
# Some models (gemma4, qwen3, deepseek-r1) prefix answers with <think>…</think>.
# These tags must be removed before sending text to Streamlit so the UI
# never shows a blank placeholder.

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _strip_think(text: str) -> str:
    """Remove <think>…</think> blocks and trim surrounding whitespace."""
    return _THINK_BLOCK_RE.sub("", text).strip()


def _stream_strip_think(tokens: Generator[str, None, None]) -> Generator[str, None, None]:
    """
    Filter <think>…</think> blocks out of a token stream.

    Strategy: buffer tokens until we can confirm we are outside a think block,
    then yield them.  Works correctly when tags are split across chunk boundaries.
    """
    buffer = ""
    inside_think = False

    for token in tokens:
        buffer += token

        while True:
            if inside_think:
                # Look for closing tag
                end = buffer.lower().find("</think>")
                if end == -1:
                    # Still inside — consume whole buffer and wait for more
                    break
                # Found end of think block — discard up to and including </think>
                buffer = buffer[end + len("</think>"):]
                inside_think = False
            else:
                # Look for opening tag
                start = buffer.lower().find("<think>")
                if start == -1:
                    # No opening tag — yield everything except last 6 chars
                    # (to guard against split "<think" at buffer boundary)
                    safe = buffer[:-6] if len(buffer) > 6 else ""
                    if safe:
                        yield safe
                        buffer = buffer[len(safe):]
                    break
                else:
                    # Yield everything before the opening tag
                    if start > 0:
                        yield buffer[:start]
                    buffer = buffer[start + len("<think>"):]
                    inside_think = True

    # Flush remaining buffer (outside any think block)
    if buffer and not inside_think:
        cleaned = _strip_think(buffer)  # final safety pass
        if cleaned:
            yield cleaned


def _stream_guard_leak(
    tokens: Generator[str, None, None],
    context: str = "",
) -> Generator[str, None, None]:
    """
    Defense-in-depth streaming filter:
    Monitors the incoming token stream for canary phrases or system leakage snippets.
    If detected, immediately halts leakage and emits standard refusal.
    """
    buffer = ""
    for token in tokens:
        buffer += token
        if detect_system_prompt_leak(buffer):
            yield f"\n\n{STANDARD_REFUSAL}"
            return
        yield token


# ─── Message building helpers ──────────────────────────────────────────────────

def build_messages(
    user_query:  str,
    context:     str = "",
    chat_history: Optional[List[Dict[str, str]]] = None,
    max_history_turns: int = MAX_HISTORY_TURNS,
    max_history_tokens: Optional[int] = None,
    num_ctx: Optional[int] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    delimiter_token: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Assemble the message list for the chat completion call following Fase 2 Target Prompt Template.

    Order:
      1. system prompt (rules only, NO injected context)
      2. previous turns from chat history (bounded by turns & dynamic token budget)
      3. current user message with request-scoped random delimiter:
         <konteks_{token}>
         {sanitized_context}
         </konteks_{token}>
         <pertanyaan_user_{token}>
         {sanitized_user_query}
         </pertanyaan_user_{token}>
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Compute effective history token budget dynamically based on Context Window
    if max_history_tokens is not None:
        effective_max_history = max_history_tokens
    elif num_ctx is not None:
        sys_tokens = estimate_tokens(SYSTEM_PROMPT)
        ctx_tokens = estimate_tokens(context) if context else 0
        query_tokens = estimate_tokens(user_query)
        safety_margin = 150
        reserved = sys_tokens + ctx_tokens + query_tokens + max_tokens + safety_margin
        effective_max_history = max(0, num_ctx - reserved)
    else:
        effective_max_history = MAX_HISTORY_TOKENS

    if chat_history:
        # Take at most the last max_history_turns
        recent = list(chat_history[-max_history_turns:])
        # Trim oldest turns if total history tokens exceed dynamic budget
        total_tokens = sum(estimate_tokens(m.get("content", "")) for m in recent)
        while recent and total_tokens > effective_max_history:
            dropped = recent.pop(0)
            total_tokens -= estimate_tokens(dropped.get("content", ""))
        messages.extend(recent)

    # Generate request-scoped delimiter token
    b = delimiter_token or secrets.token_hex(4)

    # Sanitize user query
    clean_query, is_suspicious, reasons = sanitize_user_input(user_query, max_chars=MAX_INPUT_CHARS)
    if is_suspicious:
        print(f"[SECURITY] Flagged suspicious prompt injection in user query: {reasons}")

    parts = []
    if context and context.strip():
        clean_ctx, ctx_suspicious, ctx_reasons = sanitize_context_chunk(context)
        if ctx_suspicious:
            print(f"[SECURITY] Flagged suspicious pattern in context chunk: {ctx_reasons}")
        parts.append(f"<konteks_{b}>\n{clean_ctx}\n</konteks_{b}>")

    parts.append(f"<pertanyaan_user_{b}>\n{clean_query}\n</pertanyaan_user_{b}>")
    user_content = "\n\n".join(parts)

    messages.append({"role": "user", "content": user_content})
    return messages


# ─── Synchronous (non-streaming) call ─────────────────────────────────────────

def chat_with_context(
    user_query:   str,
    context:      str = "",
    chat_history: Optional[List[Dict[str, str]]] = None,
    model:        str  = DEFAULT_MODEL,
    temperature:  float = DEFAULT_TEMPERATURE,
    max_tokens:   int   = DEFAULT_MAX_TOKENS,
    top_p:        float = DEFAULT_TOP_P,
    num_ctx:      int   = DEFAULT_NUM_CTX,
    use_native_api: bool = True,
    delimiter_token: Optional[str] = None,
) -> str:
    """
    Send a single chat completion request to Ollama and return the guarded reply.
    Uses native /api/chat with explicit options (num_ctx) with fallback to /v1.
    """
    messages = build_messages(
        user_query,
        context,
        chat_history,
        num_ctx=num_ctx,
        max_tokens=max_tokens,
        delimiter_token=delimiter_token,
    )

    raw_content = ""
    if use_native_api:
        try:
            payload = {
                "model":       model,
                "messages":    messages,
                "stream":      False,
                "options": {
                    "temperature": temperature,
                    "top_p":       top_p,
                    "num_predict": max_tokens,
                    "num_ctx":     num_ctx,
                },
            }
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            raw_content = data.get("message", {}).get("content", "")
        except Exception as exc:
            print(f"[OllamaClient] Native /api/chat failed ({exc}). Falling back to /v1...")
            raw_content = ""

    if not raw_content:
        # Fallback to OpenAI-compatible /v1 endpoint
        payload = {
            "model":       model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
            "top_p":       top_p,
            "stream":      False,
        }

        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        raw_content = data["choices"][0]["message"]["content"]

    cleaned = _strip_think(raw_content)
    return guard_output(cleaned, context=context)


# ─── Streaming call ────────────────────────────────────────────────────────────

def stream_chat_with_context(
    user_query:   str,
    context:      str = "",
    chat_history: Optional[List[Dict[str, str]]] = None,
    model:        str  = DEFAULT_MODEL,
    temperature:  float = DEFAULT_TEMPERATURE,
    max_tokens:   int   = DEFAULT_MAX_TOKENS,
    top_p:        float = DEFAULT_TOP_P,
    num_ctx:      int   = DEFAULT_NUM_CTX,
    use_native_api: bool = True,
    delimiter_token: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Yield response tokens as they arrive.
    Uses native /api/chat stream with explicit num_ctx options, falling back to /v1 SSE stream.
    Includes defense-in-depth leak detection during streaming.
    """
    messages = build_messages(
        user_query,
        context,
        chat_history,
        num_ctx=num_ctx,
        max_tokens=max_tokens,
        delimiter_token=delimiter_token,
    )

    if use_native_api:
        try:
            payload = {
                "model":       model,
                "messages":    messages,
                "stream":      True,
                "options": {
                    "temperature": temperature,
                    "top_p":       top_p,
                    "num_predict": max_tokens,
                    "num_ctx":     num_ctx,
                },
            }
            with requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=120,
                stream=True,
            ) as response:
                response.raise_for_status()

                def _raw_native_tokens() -> Generator[str, None, None]:
                    for line in response.iter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line.decode("utf-8"))
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                yield token
                        except (json.JSONDecodeError, KeyError):
                            continue

                yield from _stream_guard_leak(_stream_strip_think(_raw_native_tokens()), context=context)
                return
        except Exception as exc:
            print(f"[OllamaClient] Native streaming failed ({exc}). Falling back to /v1...")

    # Fallback to /v1 SSE streaming
    payload = {
        "model":       model,
        "messages":    messages,
        "temperature": temperature,
        "max_tokens":  max_tokens,
        "top_p":       top_p,
        "stream":      True,
    }

    with requests.post(
        OLLAMA_API_URL,
        json=payload,
        timeout=120,
        stream=True,
    ) as response:
        response.raise_for_status()

        def _raw_tokens() -> Generator[str, None, None]:
            for line in response.iter_lines():
                if not line:
                    continue
                raw = line.decode("utf-8")
                if raw.startswith("data: "):
                    raw = raw[6:]
                if raw == "[DONE]":
                    return
                try:
                    chunk = json.loads(raw)
                    delta = chunk["choices"][0]["delta"]
                    token = delta.get("content", "")
                    if token:
                        yield token
                except (json.JSONDecodeError, KeyError):
                    continue

        yield from _stream_guard_leak(_stream_strip_think(_raw_tokens()), context=context)


def check_ollama_connection(model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Quick health check — returns a dict with 'ok' bool and 'message'.
    """
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        tags = resp.json().get("models", [])
        model_names = [m.get("name", "") for m in tags]
        available   = any(model in n for n in model_names)
        return {
            "ok":      True,
            "message": f"Ollama is running. Requested model '{model}' "
                       + ("found ✅" if available else "NOT found ⚠️"),
            "models":  model_names,
        }
    except requests.exceptions.ConnectionError:
        return {
            "ok":      False,
            "message": f"❌ Cannot connect to Ollama at {OLLAMA_BASE_URL}. Is it running?",
            "models":  [],
        }
    except Exception as e:
        return {"ok": False, "message": str(e), "models": []}
