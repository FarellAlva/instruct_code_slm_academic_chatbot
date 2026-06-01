"""Quick debug to find the root cause of HTTP 500 from Ollama."""
import json, urllib.request, urllib.error

OLLAMA_API = "http://localhost:11434"

# Test 1: Simple generation (no context)
print("=== Test 1: Simple generation ===")
payload = json.dumps({
    "model": "gemma2:2b",
    "prompt": "Halo, apa kabar?",
    "stream": False,
    "options": {"temperature": 0.1, "num_predict": 50},
}).encode()

req = urllib.request.Request(
    f"{OLLAMA_API}/api/generate",
    data=payload,
    headers={"Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        result = json.loads(r.read().decode())
        print(f"OK: {result['response'][:100]}")
        print(f"eval_count: {result.get('eval_count')} | eval_duration: {result.get('eval_duration')}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code}: {body[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: With system prompt
print("\n=== Test 2: With system prompt ===")
payload2 = json.dumps({
    "model": "gemma2:2b",
    "system": "Kamu adalah asisten AI.",
    "prompt": "Di mana lokasi Jakarta?",
    "stream": False,
    "options": {"temperature": 0.1, "num_predict": 100},
}).encode()

req2 = urllib.request.Request(
    f"{OLLAMA_API}/api/generate",
    data=payload2,
    headers={"Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req2, timeout=60) as r:
        result = json.loads(r.read().decode())
        print(f"OK: {result['response'][:100]}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code}: {body[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Check if /api/chat works instead
print("\n=== Test 3: /api/chat endpoint ===")
payload3 = json.dumps({
    "model": "gemma2:2b",
    "messages": [
        {"role": "system", "content": "Kamu adalah asisten AI."},
        {"role": "user", "content": "Di mana lokasi Jakarta?"},
    ],
    "stream": False,
    "options": {"temperature": 0.1, "num_predict": 100},
}).encode()

req3 = urllib.request.Request(
    f"{OLLAMA_API}/api/chat",
    data=payload3,
    headers={"Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req3, timeout=60) as r:
        result = json.loads(r.read().decode())
        msg = result.get("message", {})
        print(f"OK: {msg.get('content', '')[:100]}")
        print(f"eval_count: {result.get('eval_count')} | eval_duration: {result.get('eval_duration')}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code}: {body[:500]}")
except Exception as e:
    print(f"Error: {e}")
