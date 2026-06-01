"""
llm/ollama_client.py — Thin client for the local Ollama OpenAI-compatible API.
"""

import json
import requests
from typing import Generator, List, Dict, Any, Optional

from config import (
    OLLAMA_API_URL,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TOP_P,
    SYSTEM_PROMPT,
)


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

    return data["choices"][0]["message"]["content"]


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
        for line in response.iter_lines():
            if not line:
                continue
            # Strip "data: " prefix if present (SSE format)
            raw = line.decode("utf-8")
            if raw.startswith("data: "):
                raw = raw[6:]
            if raw == "[DONE]":
                break
            try:
                chunk = json.loads(raw)
                delta = chunk["choices"][0]["delta"]
                token = delta.get("content", "")
                if token:
                    yield token
            except (json.JSONDecodeError, KeyError):
                continue


def check_ollama_connection(model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Quick health check — returns a dict with 'ok' bool and 'message'.
    """
    try:
        resp = requests.get(f"http://localhost:11434/api/tags", timeout=5)
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
            "message": "❌ Cannot connect to Ollama at localhost:11434. Is it running?",
            "models":  [],
        }
    except Exception as e:
        return {"ok": False, "message": str(e), "models": []}
