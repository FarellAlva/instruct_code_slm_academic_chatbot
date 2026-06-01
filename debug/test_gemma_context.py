"""Test generation with actual context from RAG for Gemma2:2b."""
import sys, os, json, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.retriever import retrieve_context
from config import SYSTEM_PROMPT

OLLAMA_API = "http://localhost:11434"

# Retrieve actual context
q = "Di mana lokasi kampus Pradita University?"
ret = retrieve_context(q, top_k=6)
context = ret["context"]

print("=== Context retrieved ===")
print(context[:300])
print(f"Total context length: {len(context)}")

full_prompt = (
    f"KONTEKS:\n{context}\n\n"
    f"PERTANYAAN: {q}\n\n"
    "Jawab berdasarkan konteks di atas."
)

# Test /api/generate with system prompt
print("\n=== Test /api/generate ===")
payload = json.dumps({
    "model": "gemma2:2b",
    "system": SYSTEM_PROMPT,
    "prompt": full_prompt,
    "stream": False,
    "options": {
        "temperature": 0.1,
        "num_predict": 512,
        "top_p": 0.9,
    },
}).encode()

req = urllib.request.Request(
    f"{OLLAMA_API}/api/generate",
    data=payload,
    headers={"Content-Type": "application/json"},
)

try:
    with urllib.request.urlopen(req, timeout=90) as resp:
        r = json.loads(resp.read().decode())
        print("SUCCESS generate!")
        print(r["response"][:300])
except urllib.error.HTTPError as e:
    print(f"Failed generate: HTTP {e.code}")
    print(e.read().decode()[:500])
except Exception as e:
    print(f"Failed generate: {e}")

# Test /api/chat as an alternative
print("\n=== Test /api/chat ===")
payload_chat = json.dumps({
    "model": "gemma2:2b",
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": full_prompt}
    ],
    "stream": False,
    "options": {
        "temperature": 0.1,
        "num_predict": 512,
        "top_p": 0.9,
    },
}).encode()

req_chat = urllib.request.Request(
    f"{OLLAMA_API}/api/chat",
    data=payload_chat,
    headers={"Content-Type": "application/json"},
)

try:
    with urllib.request.urlopen(req_chat, timeout=90) as resp:
        r = json.loads(resp.read().decode())
        print("SUCCESS chat!")
        print(r["message"]["content"][:300])
except urllib.error.HTTPError as e:
    print(f"Failed chat: HTTP {e.code}")
    print(e.read().decode()[:500])
except Exception as e:
    print(f"Failed chat: {e}")
