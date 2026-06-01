"""Quick test script for new evaluation components."""
import sys
sys.path.insert(0, '.')

# Test imports
from eval.evaluate import compute_semantic_similarity, diagnose_context, load_dataset
print('All imports OK')

# Test dataset loading
ds = load_dataset()
print(f'Dataset loaded: {len(ds)} questions')

# Test semantic similarity
sim = compute_semantic_similarity(
    'Pradita University terletak di Scientia Business Park Serpong',
    'Lokasi kampus Pradita di Scientia Business Park Summarecon Serpong'
)
print(f'Semantic Similarity test: {sim}')
assert sim > 0.7, f"Expected high similarity, got {sim}"

# Test low similarity
sim_low = compute_semantic_similarity(
    'Harga ayam goreng di pasar tradisional',
    'Jadwal kuliah Informatika semester 2 hari Senin'
)
print(f'Low Similarity test: {sim_low}')
assert sim_low < sim, f"Expected lower similarity for unrelated text, got {sim_low} vs {sim}"

# Test context diagnostics
diag = diagnose_context(
    'Program studi: Informatika. Semester: II. Hari: Senin. Dosen pengampu tertulis: Theresia Herlina, S.Kom., M.T.',
    'Theresia Herlina, S.Kom., M.T. mengajar di program Informatika semester II, antara lain: Interaksi Manusia dan Komputer',
    [{'text': 'test'}]
)
print(f'Context Diagnostics: has_answer={diag["context_has_answer"]}, sim={diag["context_similarity"]}')

# Test empty context
diag_empty = diagnose_context('', 'Some reference', [])
print(f'Empty Context: has_answer={diag_empty["context_has_answer"]}, sim={diag_empty["context_similarity"]}')
assert not diag_empty["context_has_answer"]

print()
print('=' * 40)
print('  ALL TESTS PASSED!')
print('=' * 40)
