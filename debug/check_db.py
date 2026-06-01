import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(path='chroma_db', settings=Settings(anonymized_telemetry=False))
col = client.get_collection('pradita_knowledge')
print(f'Total docs: {col.count()}')
sample = col.get(limit=5, include=['documents', 'metadatas'])
for d, m in zip(sample['documents'], sample['metadatas']):
    print(f'---\nSource: {m["source"]}, Page: {m["page"]}')
    print(d[:400])
