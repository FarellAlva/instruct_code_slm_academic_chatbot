import re

md_path = 'd:\\LLM\\instruct\\eval\\results\\report_all.md'
with open(md_path, 'r', encoding='utf-8') as f:
    content = f.read()

data = {}
q_sections = re.split(r'### Q(\d+)', content)
for i in range(1, len(q_sections), 2):
    q_id = int(q_sections[i])
    q_body = q_sections[i+1]
    
    for line in q_body.split('\n'):
        if line.startswith('| `'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 5:
                model = parts[1].replace('`', '')
                gemini = float(parts[3])
                claude = float(parts[4])
                if (model, q_id) not in data: data[(model, q_id)] = {}
                data[(model, q_id)]['gemini_score'] = gemini
                data[(model, q_id)]['claude_score'] = claude

for m in ['gemma2:2b', 'qwen3:1.7B', 'llama3.2:1b']:
    scores = [int(round((data[(m, q)]['gemini_score'] + data[(m, q)]['claude_score']) / 2)) for q in range(1, 16) if (m, q) in data]
    print(f"{m} natural average (int per Q): {sum(scores) / len(scores):.1f}")
