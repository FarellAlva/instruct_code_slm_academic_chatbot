import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(path='chroma_db', settings=Settings(anonymized_telemetry=False))
col = client.get_collection('pradita_knowledge')

# Test $contains
print("=== Test $contains 'theresia' ===")
try:
    r = col.get(limit=5, include=['metadatas'], where={"dosen_names": {"$contains": "theresia"}})
    print(f"Found: {len(r['ids'])}")
except Exception as e:
    print(f"Error: {e}")

# Test $eq exact match
print("\n=== Test $eq exact ===")
try:
    r = col.get(limit=5, include=['metadatas'], where={"dosen_names": {"$eq": "theresia herlina, s.kom., m.t"}})
    print(f"Found: {len(r['ids'])}")
except Exception as e:
    print(f"Error: {e}")

# Check what operators are supported
print("\n=== Sample of all dosen_names in DB ===")
all_data = col.get(limit=600, include=['metadatas'])
dosen_set = set()
for m in all_data['metadatas']:
    dn = m.get('dosen_names', '')
    if dn:
        dosen_set.add(dn)
print(f"Unique dosen_names values: {len(dosen_set)}")
for dn in list(dosen_set)[:5]:
    print(f"  '{dn}'")
