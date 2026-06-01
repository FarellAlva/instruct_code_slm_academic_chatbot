import pandas as pd
import re

md_dst = 'd:\\LLM\\instruct\\eval\\results\\report_all.md'
csv_path = 'd:\\LLM\\instruct\\eval\\results\\results_raw_20260526_013647.csv'

df_csv = pd.read_csv(csv_path)

lookup = {}
for _, row in df_csv.iterrows():
    m = row['model']
    q = int(row['question_id'])
    lookup[(m, q)] = {
        'score': row['llm_judge_score'],
        'reasoning': row['llm_judge_reasoning']
    }

models = ['gemma2:2b', 'qwen3:1.7B', 'llama3.2:1b']

with open(md_dst, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
current_q = None
current_model = None
matches = 0

for i, line in enumerate(lines):
    new_lines.append(line)
    
    q_match = re.search(r'^### Q(\d+)', line)
    if q_match:
        current_q = int(q_match.group(1))
        
    s_line = line.strip()
    
    # Robust model matching
    for m in models:
        if f"`{m}`:**" in s_line or f"**{m}**:" in s_line:
            current_model = m
            #print(f"L{i} Matched model {m} for Q {current_q}")
            break
            
    if current_q and current_model and "Claude Sonnet 4.6:**" in s_line:
        # Check if we already appended here
        if i + 1 < len(lines) and 'Human Reviewer:' in lines[i+1]:
            continue
            
        if (current_model, current_q) in lookup:
            score = lookup[(current_model, current_q)]['score']
            reasoning = lookup[(current_model, current_q)]['reasoning']
            # Using same indentation as Gemini/Claude (2 spaces)
            hr_line = f"  * **Human Reviewer:** {reasoning} (Skor: {float(score):.1f}/100)\n"
            new_lines.append(hr_line)
            matches += 1

with open(md_dst, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Markdown updated. {matches} blocks injected.")
