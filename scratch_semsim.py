import re

with open('eval/results/report_20260531_224424.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Ekstrak tabel detail
# Ada bagian '## Detail Per Pertanyaan'
details_part = content.split('## Detail Per Pertanyaan')[1]
lines = details_part.split('\n')

scores = {'gemma2:2b': [], 'qwen3:1.7B': [], 'llama3.2:1b': []}

for line in lines:
    line = line.strip()
    if line.startswith('| `gemma2:2b`') or line.startswith('| `qwen3:1.7B`') or line.startswith('| `llama3.2:1b`'):
        parts = line.split('|')
        if len(parts) >= 7:
            model = parts[1].replace('`', '').strip()
            semsim_str = parts[2].strip()
            try:
                semsim = float(semsim_str)
                if model in scores:
                    scores[model].append(semsim)
            except Exception as e:
                pass

print("SemSim per model di Detail:")
for m in scores:
    data = scores[m]
    if len(data) > 0:
        avg = sum(data) / len(data)
        print(f"{m}: count={len(data)} avg={avg:.4f}")
    else:
        print(f"{m}: NO DATA")
