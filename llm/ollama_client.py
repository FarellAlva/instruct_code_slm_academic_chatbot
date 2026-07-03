"""
llm/ollama_client.py — Thin client for the local Ollama OpenAI-compatible API.
"""

import json
import re
import requests
from typing import Generator, List, Dict, Any, Optional

from config import (
    OLLAMA_API_URL,
    OLLAMA_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TOP_P,
    SYSTEM_PROMPT,
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


# ─── Message building helpers ──────────────────────────────────────────────────

def build_messages(
    user_query:  str,
    context:     str,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    """
    Assemble the message list for the chat completion call.

    Order:
      1. system prompt (with injected context)
      2. previous turns from chat history
      3. current user message
    """
    system_content = SYSTEM_PROMPT
    if context.strip():
        system_content += f"\n\n===== RELEVANT CONTEXT =====\n{context}\n============================="

    messages = [{"role": "system", "content": system_content}]

    if chat_history:
        messages.extend(chat_history)

    messages.append({"role": "user", "content": user_query})
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
) -> str:
    """
    Send a single chat completion request to Ollama and return the full reply.

    Raises:
        requests.HTTPError  — if Ollama returns 4xx/5xx
        requests.Timeout    — if Ollama does not respond in time
    """
    messages = build_messages(user_query, context, chat_history)

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
    return _strip_think(raw_content)


# ─── Streaming call ────────────────────────────────────────────────────────────

def stream_chat_with_context(
    user_query:   str,
    context:      str = "",
    chat_history: Optional[List[Dict[str, str]]] = None,
    model:        str  = DEFAULT_MODEL,
    temperature:  float = DEFAULT_TEMPERATURE,
    max_tokens:   int   = DEFAULT_MAX_TOKENS,
    top_p:        float = DEFAULT_TOP_P,
) -> Generator[str, None, None]:
    """
    Yield response tokens as they arrive (SSE / JSON-lines stream).
    Suitable for displaying responses word-by-word in Streamlit.
    """
    messages = build_messages(user_query, context, chat_history)

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
                # Strip "data: " prefix if present (SSE format)
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

        yield from _stream_strip_think(_raw_tokens())


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
