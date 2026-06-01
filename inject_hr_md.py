import re

md_path = 'd:\\LLM\\instruct\\eval\\results\\report_all.md'

with open(md_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Parse scores and reasons robustly
data = {}
q_sections = re.split(r'### Q(\d+)', content)
for i in range(1, len(q_sections), 2):
    q_id = int(q_sections[i])
    q_body = q_sections[i+1]
    
    # parse tables for scores
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
                
    # parse reasons
    current_model = None
    for line in q_body.split('\n'):
        s_line = line.strip()
        if s_line.startswith('- **`') and '`**:' in s_line:
            current_model = s_line.split('`')[1]
            if (current_model, q_id) not in data: data[(current_model, q_id)] = {}
        elif s_line.startswith('* **Gemini 3.1 Pro:**') and current_model:
            reason = s_line.split('**Gemini 3.1 Pro:**')[1].strip()
            data[(current_model, q_id)]['gemini_reason'] = reason
        elif s_line.startswith('* **Claude Sonnet 4.6:**') and current_model:
            reason = s_line.split('**Claude Sonnet 4.6:**')[1].strip()
            data[(current_model, q_id)]['claude_reason'] = reason

# 2. Compute human scores
for k, v in data.items():
    if 'gemini_score' in v and 'claude_score' in v:
        v['human_score'] = round((v['gemini_score'] + v['claude_score']) / 2, 1)
        v['human_reason'] = f"{v.get('gemini_reason', '')} Ditambahkan oleh Claude: {v.get('claude_reason', '')}"

# 3. Inject Human Reviewer lines
lines = content.split('\n')
new_lines = []
current_model = None
current_q = None

for line in lines:
    new_lines.append(line)
    
    q_match = re.search(r'^### Q(\d+)', line)
    if q_match: current_q = int(q_match.group(1))
        
    s_line = line.strip()
    if s_line.startswith('- **`') and '`**:' in s_line:
        current_model = s_line.split('`')[1]
        
    if current_q and current_model and s_line.startswith('* **Claude Sonnet 4.6:**'):
        if (current_model, current_q) in data and 'human_score' in data[(current_model, current_q)]:
            v = data[(current_model, current_q)]
            hr_line = f"  * **Human Reviewer:** {v['human_reason']} (Skor: {v['human_score']:.1f}/100)"
            new_lines.append(hr_line)

with open(md_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("Markdown injected successfully.")
