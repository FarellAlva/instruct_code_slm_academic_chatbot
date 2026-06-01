import re
import pandas as pd
import openpyxl

md_path = 'd:\\LLM\\instruct\\eval\\results\\report_all.md'
excel_path = 'd:\\LLM\\instruct\\eval\\hasil_localLLm_updated.xlsx'

with open(md_path, 'r', encoding='utf-8') as f:
    content = f.read()

data = {}
q_sections = re.split(r'### Q(\d+)', content)

for i in range(1, len(q_sections), 2):
    q_id = int(q_sections[i])
    q_body = q_sections[i+1]
    
    # 1. Parse scores from table
    # Example row: | `gemma2:2b` | 0.9709 | 100.0 | 100.0 | 15.41s | 13.8 |
    # But wait, there are two tables in each section? No, only one summary table at the top of the section.
    # We will search for all table rows that start with | `model`
    table_rows = re.findall(r'^\| `(.*?)`.*?\|\s*([\d\.]+)\s*\|\s*([\d\.]+)\s*\|', q_body, flags=re.MULTILINE)
    for row in table_rows:
        model = row[0]
        # But wait! In the row, Gemini is col index 2, Claude is col index 3 (after SemSim)
        # Let's extract properly:
        pass
    
    # Let's do it simply by parsing the whole table
    lines = q_body.split('\n')
    current_model = None
    for line in lines:
        if line.startswith('| `'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 5:
                model = parts[1].replace('`', '')
                gemini_score = float(parts[3])
                claude_score = float(parts[4])
                if (model, q_id) not in data:
                    data[(model, q_id)] = {}
                data[(model, q_id)]['gemini_score'] = gemini_score
                data[(model, q_id)]['claude_score'] = claude_score
                
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

# Calculate Human Reviewer values
for k, v in data.items():
    if 'gemini_score' in v and 'claude_score' in v:
        v['human_score'] = round((v['gemini_score'] + v['claude_score']) / 2, 1)
    else:
        v['human_score'] = 0.0
        
    g_reason = v.get('gemini_reason', '')
    c_reason = v.get('claude_reason', '')
    v['human_reason'] = f"Kombinasi penilaian: {g_reason} Serta: {c_reason}"

# Update the Markdown File
# We will do a full reconstruction of the Human Reviewer lines
with open(md_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_md_lines = []
current_q = None
current_model = None

# Update global summary table stats if we wanted, but let's just focus on the questions
# Actually we must update the global summary table for Human Review.
# Let's precompute global averages for Human Review
model_human_avg = {}
for m in ['gemma2:2b', 'qwen3:1.7B', 'llama3.2:1b']:
    scores = [data[(m, q)]['human_score'] for q in range(1, 16) if (m, q) in data]
    model_human_avg[m] = round(sum(scores) / len(scores), 1) if scores else 0.0

skip_next_hr = False
for i, line in enumerate(lines):
    if skip_next_hr:
        if line.strip().startswith('* **Human Reviewer:**'):
            skip_next_hr = False
            continue
    
    # Update global summary table human score
    if line.startswith('| `') and '100.0%' in line:
        # Example: | `gemma2:2b` | 0.9164 | 85.0 | 82.0 | 85.0 | 100.0% | 8.30 | 13.3 |
        parts = line.split('|')
        m = parts[1].strip().replace('`', '')
        if m in model_human_avg:
            parts[5] = f" {model_human_avg[m]} "
            new_md_lines.append('|'.join(parts))
            continue
            
    q_match = re.search(r'^### Q(\d+)', line)
    if q_match:
        current_q = int(q_match.group(1))
        
    s_line = line.strip()
    if s_line.startswith('- **`') and '`**:' in s_line:
        current_model = s_line.split('`')[1]
        
    new_md_lines.append(line)
        
    if current_q and current_model and s_line.startswith('* **Claude Sonnet 4.6:**'):
        # Inject the new Human Reviewer
        if (current_model, current_q) in data:
            v = data[(current_model, current_q)]
            hr_line = f"  * **Human Reviewer:** {v['human_reason']} (Skor: {v['human_score']:.1f}/100)\n"
            new_md_lines.append(hr_line)
            # If the next line is the old Human Reviewer, skip it
            if i + 1 < len(lines) and lines[i+1].strip().startswith('* **Human Reviewer:**'):
                skip_next_hr = True

with open(md_path, 'w', encoding='utf-8') as f:
    f.writelines(new_md_lines)
print("Markdown completely updated.")

# Update Excel File
sheet_mapping = {
    'gemma': 'gemma2:2b',
    'qwen': 'qwen3:1.7B',
    'llama': 'llama3.2:1b'
}

dfs = pd.read_excel(excel_path, sheet_name=None)
writer = pd.ExcelWriter(excel_path, engine='openpyxl')

for sheet_name, df_sheet in dfs.items():
    model_name = sheet_mapping.get(sheet_name)
    if model_name:
        for idx, row in df_sheet.iterrows():
            q_id = int(row['no'])
            if (model_name, q_id) in data:
                v = data[(model_name, q_id)]
                if 'score_human_reviewer' in df_sheet.columns:
                    df_sheet.at[idx, 'score_human_reviewer'] = v['human_score']
                if 'alasan_reviewer' in df_sheet.columns:
                    df_sheet.at[idx, 'alasan_reviewer'] = v['human_reason']
    df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)

writer.close()
print("Excel updated successfully.")
