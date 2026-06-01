import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(path='chroma_db', settings=Settings(anonymized_telemetry=False))
col = client.get_collection('pradita_knowledge')
print(f'Total docs: {col.count()}')

# Check a jadwal entry
sample = col.get(limit=3, include=['documents', 'metadatas'], where={"doc_type": {"$eq": "jadwal"}})
for d, m in zip(sample['documents'], sample['metadatas']):
    print(f'\n--- Metadata: {m}')
    print(f'Text preview: {d[:150]}...')

# Test a filtered query
print("\n\n=== Test: dosen_names contains 'theresia' ===")
filtered = col.get(include=['documents', 'metadatas'], where={"dosen_names": {"$contains": "theresia"}})
print(f"Found {len(filtered['documents'])} chunks")
for d, m in zip(filtered['documents'][:3], filtered['metadatas'][:3]):
    print(f"  -> {m.get('mata_kuliah', '?')} | {m.get('prodi', '?')} | dosen: {m.get('dosen_names', '?')}")
