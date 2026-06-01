import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rag.retriever import retrieve_context
from llm.ollama_client import stream_chat_with_context

print("=== TEST 4: Siapa itu eng handri? ===")
prompt = "siapa itu eng handri"
r = retrieve_context(prompt, top_k=4)

print("\n--- RAG Context ---")
print(r["context"][:800])

print("\n--- LLM Response ---")
response = ""
for token in stream_chat_with_context(prompt, r["context"], [], "qwen2.5:3b", 0.1, 200):
   response += token
   print(token, end="", flush=True)

print("\n")
