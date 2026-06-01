import re
import pandas as pd
import openpyxl

md_path = 'd:\\LLM\\instruct\\eval\\results\\report_all.md'
excel_path = 'd:\\LLM\\instruct\\eval\\hasil_localLLm_updated.xlsx'
final_excel_path = 'd:\\LLM\\instruct\\eval\\hasil_localLLm_FINAL.xlsx'

with open(md_path, 'r', encoding='utf-8') as f:
    content = f.read()

data = {}

# 1. First parse the scores and reasons robustly
q_sections = re.split(r'### Q(\d+)', content)
for i in range(1, len(q_sections), 2):
    q_id = int(q_sections[i])
    q_body = q_sections[i+1]
    
    # parse tables for scores
    # | `model` | semsim | gemini | claude |
    for line in q_body.split('\n'):
        if line.startswith('| `'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 5:
                model = parts[1].replace('`', '')
                gemini = float(parts[3])
                claude = float(parts[4])
                if (model, q_id) not in data:
                    data[(model, q_id)] = {}
                data[(model, q_id)]['gemini_score'] = gemini
                data[(model, q_id)]['claude_score'] = claude
                
    # parse reasons
    lines = q_body.split('\n')
    current_model = None
    for line in lines:
        s_line = line.strip()
        if s_line.startswith('- **`') and '`**:' in s_line:
            current_model = s_line.split('`')[1]
            if (current_model, q_id) not in data:
                data[(current_model, q_id)] = {}
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
        # Combined reasoning
        v['human_reason'] = f"{v.get('gemini_reason', '')} (Catatan Tambahan: {v.get('claude_reason', '')})"

# 3. Rebuild markdown line by line
with open(md_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_md = []
current_q = None
current_model = None

# Averages for global table
model_human_avg = {}
for m in ['gemma2:2b', 'qwen3:1.7B', 'llama3.2:1b']:
    scores = [data[(m, q)]['human_score'] for q in range(1, 16) if (m, q) in data and 'human_score' in data[(m, q)]]
    model_human_avg[m] = round(sum(scores) / len(scores), 1) if scores else 0.0

for i, line in enumerate(lines):
    # Strip existing Human Reviewer completely (don't append to new_md)
    if line.strip().startswith('* **Human Reviewer:**'):
        continue
        
    # Update table
    if line.startswith('| `'):
        parts = line.split('|')
        m = parts[1].strip().replace('`', '')
        if m in model_human_avg and len(parts) >= 6:
            parts[5] = f" {model_human_avg[m]} "
            new_md.append('|'.join(parts))
            continue
            
    q_match = re.search(r'^### Q(\d+)', line)
    if q_match:
        current_q = int(q_match.group(1))
        
    s_line = line.strip()
    if s_line.startswith('- **`') and '`**:' in s_line:
        current_model = s_line.split('`')[1]
        
    new_md.append(line)
    
    # Inject after Claude
    if current_q and current_model and s_line.startswith('* **Claude Sonnet 4.6:**'):
        if (current_model, current_q) in data and 'human_score' in data[(current_model, current_q)]:
            v = data[(current_model, current_q)]
            hr_line = f"  * **Human Reviewer:** {v['human_reason']} (Skor: {v['human_score']:.1f}/100)\n"
            new_md.append(hr_line)

with open(md_path, 'w', encoding='utf-8') as f:
    f.writelines(new_md)
print("Markdown updated line by line successfully.")
