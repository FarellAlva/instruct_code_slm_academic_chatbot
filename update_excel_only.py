import re
import pandas as pd
import openpyxl

md_path = 'd:\\LLM\\instruct\\eval\\results\\report_all.md'
excel_path = 'd:\\LLM\\instruct\\eval\\hasil_localLLm_updated.xlsx'
final_excel_path = 'd:\\LLM\\instruct\\eval\\hasil_localLLm_FINAL.xlsx'

with open(md_path, 'r', encoding='utf-8') as f:
    content = f.read()

# We already updated the markdown successfully in the previous run, so let's parse the newly generated human scores
data = {}
lines = content.split('\n')
current_q = None
current_model = None

for i, line in enumerate(lines):
    q_match = re.search(r'^### Q(\d+)', line)
    if q_match:
        current_q = int(q_match.group(1))
        
    s_line = line.strip()
    if s_line.startswith('- **`') and '`**:' in s_line:
        current_model = s_line.split('`')[1]
        if (current_model, current_q) not in data:
            data[(current_model, current_q)] = {}
            
    elif s_line.startswith('* **Human Reviewer:**') and current_model:
        # Example: * **Human Reviewer:** Kombinasi penilaian: ... (Skor: 87.5/100)
        try:
            reason_part = s_line.split('**Human Reviewer:**')[1].strip()
            score_part = reason_part.split('(Skor: ')[-1].replace('/100)', '').strip()
            reason = reason_part.rsplit('(Skor:', 1)[0].strip()
            
            data[(current_model, current_q)]['human_score'] = float(score_part)
            data[(current_model, current_q)]['human_reason'] = reason
        except Exception as e:
            print(f"Error parsing line: {s_line} - {e}")

# Update Excel File
sheet_mapping = {
    'gemma': 'gemma2:2b',
    'qwen': 'qwen3:1.7B',
    'llama': 'llama3.2:1b'
}

dfs = pd.read_excel(excel_path, sheet_name=None)
writer = pd.ExcelWriter(final_excel_path, engine='openpyxl')

for sheet_name, df_sheet in dfs.items():
    model_name = sheet_mapping.get(sheet_name)
    if model_name:
        for idx, row in df_sheet.iterrows():
            q_id = int(row['no'])
            if (model_name, q_id) in data:
                v = data[(model_name, q_id)]
                if 'human_score' in v:
                    if 'score_human_reviewer' in df_sheet.columns:
                        df_sheet.at[idx, 'score_human_reviewer'] = v['human_score']
                    if 'alasan_reviewer' in df_sheet.columns:
                        df_sheet.at[idx, 'alasan_reviewer'] = v['human_reason']
    df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)

writer.close()
print("Excel updated and saved to hasil_localLLm_FINAL.xlsx")
