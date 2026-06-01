import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rag.retriever import retrieve_context
from llm.ollama_client import stream_chat_with_context
from config import SYSTEM_PROMPT

print("=== TEST RAG: Harga ===")
r = retrieve_context("harga pradita unversity berapa", top_k=4)

print("\n--- RAG Context ---")
for chunk in r["chunks"]:
    print(f"Source: {chunk['source']} | Score: {chunk.get('rerank_score', 0)}")
    print(chunk["text"])
    print("-" * 50)


print("\n--- LLM Response ---")
response = ""
for token in stream_chat_with_context("harga pradita unversity berapa", r["context"], [], "qwen2.5:3b", 0.1, 800):
   response += token
   print(token, end="", flush=True)

print("\n")
