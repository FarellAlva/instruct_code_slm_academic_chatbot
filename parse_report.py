import re

md_path = 'd:\\LLM\\instruct\\eval\\results\\report_all.md'
with open(md_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Parse the table blocks to get Gemini and Claude scores per question
# Table format: | `gemma2:2b` | 0.9709 | 100.0 | 100.0 | 15.41s | 13.8 |
data = {} # (model, q_id) -> {'gemini_score': float, 'claude_score': float, 'gemini_reason': str, 'claude_reason': str}

q_sections = re.split(r'### Q(\d+)', content)
for i in range(1, len(q_sections), 2):
    q_id = int(q_sections[i])
    q_body = q_sections[i+1]
    
    # 1. Parse scores from the table in this section
    # The table comes after "**Hasil per model:**"
    table_match = re.search(r'\| Model \|.*?\|Tok/s \|\n\|--.*?--\|\n(.*?)\n\n', q_body, re.DOTALL)
    if table_match:
        table_rows = table_match.group(1).strip().split('\n')
        for row in table_rows:
            cols = [c.strip() for c in row.split('|') if c.strip()]
            if len(cols) >= 4 and '`' in cols[0]:
                model = cols[0].replace('`', '')
                gemini_score = float(cols[2])
                claude_score = float(cols[3])
                data[(model, q_id)] = {'gemini_score': gemini_score, 'claude_score': claude_score}
                
    # 2. Parse reasonings
    # Format:
    # - **`model`:** ...
    #   * **Gemini 3.1 Pro:** <reason>
    #   * **Claude Sonnet 4.6:** <reason>
    
    lines = q_body.split('\n')
    current_model = None
    for line in lines:
        s_line = line.strip()
        if s_line.startswith('- **`') and '`**:' in s_line:
            current_model = s_line.split('`')[1]
        elif s_line.startswith('* **Gemini 3.1 Pro:**') and current_model:
            reason = s_line.split('**Gemini 3.1 Pro:**')[1].strip()
            data[(current_model, q_id)]['gemini_reason'] = reason
        elif s_line.startswith('* **Claude Sonnet 4.6:**') and current_model:
            reason = s_line.split('**Claude Sonnet 4.6:**')[1].strip()
            data[(current_model, q_id)]['claude_reason'] = reason

# Print first few to verify
for k in list(data.keys())[:3]:
    print(k, data[k])
