import re
import pandas as pd

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

with open(md_dst, 'r', encoding='utf-8') as f:
    content = f.read()

# The injection failed before, let's fix it.
# We will split by "### Q"
sections = re.split(r'(### Q\d+ — .*)', content)
new_content = [sections[0]]
for i in range(1, len(sections), 2):
    q_header = sections[i]
    q_body = sections[i+1]
    
    q_id_match = re.search(r'### Q(\d+)', q_header)
    if q_id_match:
        q_id = int(q_id_match.group(1))
        
        # Split by `- **` to process each model block
        model_blocks = re.split(r'(- \*\*`.*?`\*\*.*?(?=\n- \*\*`|\n\n\n|$))', q_body, flags=re.DOTALL)
        # re.split keeps the delimiter and the rest alternating, but since we capture everything in the delimiter...
        # Wait, a better way is to use finditer and replace.
        
        def inject_hr(m):
            model_name = m.group(1)
            block = m.group(0)
            if (model_name, q_id) in lookup:
                score = lookup[(model_name, q_id)]['score']
                reasoning = lookup[(model_name, q_id)]['reasoning']
                # If Human Reviewer is already there, don't append again (just in case)
                if "Human Reviewer" not in block:
                    return block + f"\n  * **Human Reviewer:** {reasoning} (Skor: {float(score):.1f}/100)\n"
            return block
            
        q_body = re.sub(r'- \*\*`(.*?)`\*\*:.*?(?=\n- \*\*`|\n\n\n|\n\n---)', inject_hr, q_body, flags=re.DOTALL)
        
    new_content.append(q_header)
    new_content.append(q_body)

with open(md_dst, 'w', encoding='utf-8') as f:
    f.write(''.join(new_content))

print("Markdown updated with Human Review.")
