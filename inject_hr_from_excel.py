import re

md_path = 'd:\\LLM\\instruct\\eval\\results\\report_all.md'

with open(md_path, 'r', encoding='utf-8') as f:
    content = f.read()

# I will find all Claude Sonnet lines and just append Human Reviewer after them!
# Format in markdown: * **Claude Sonnet 4.6:** <text>

# Wait, I need to know the model and q_id to get the right data!
# But actually, I already updated Excel with the correct data. Let's just read Excel to get the Human Reviewer values!
import pandas as pd
excel_path = 'd:\\LLM\\instruct\\eval\\hasil_localLLm_FINAL.xlsx'

dfs = pd.read_excel(excel_path, sheet_name=None)
sheet_mapping = {
    'gemma': 'gemma2:2b',
    'qwen': 'qwen3:1.7B',
    'llama': 'llama3.2:1b'
}

data = {}
for sheet, df in dfs.items():
    model = sheet_mapping.get(sheet)
    if model:
        for _, row in df.iterrows():
            q_id = int(row['no'])
            score = float(row['score_human_reviewer'])
            reason = str(row['alasan_reviewer'])
            data[(model, q_id)] = {'score': score, 'reason': reason}

# Now, we go through the markdown line by line.
lines = content.split('\n')
new_lines = []
current_model = None
current_q = None

for line in lines:
    new_lines.append(line)
    
    q_match = re.search(r'^### Q(\d+)', line)
    if q_match:
        current_q = int(q_match.group(1))
        
    s_line = line.strip()
    if s_line.startswith('- **`') and '`**:' in s_line:
        current_model = s_line.split('`')[1]
        
    # Inject after Claude
    if current_q and current_model and s_line.startswith('* **Claude Sonnet 4.6:**'):
        if (current_model, current_q) in data:
            v = data[(current_model, current_q)]
            hr_line = f"  * **Human Reviewer:** {v['reason']} (Skor: {v['score']:.1f}/100)"
            new_lines.append(hr_line)
            # Reset so we don't inject multiple times if there are multiple Claude lines? There shouldn't be.

with open(md_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("Markdown fully injected!")
