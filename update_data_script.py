import pandas as pd
import re
import os
import shutil

# 1. Update Excel
csv_path = 'd:\\LLM\\instruct\\eval\\results\\results_raw_20260526_013647.csv'
excel_path = 'd:\\LLM\\instruct\\eval\\hasil_localLLm.xlsx'

df_csv = pd.read_csv(csv_path)

lookup = {}
for _, row in df_csv.iterrows():
    m = row['model']
    q = int(row['question_id'])
    lookup[(m, q)] = {
        'answer': row['answer'],
        'score': row['llm_judge_score'],
        'reasoning': row['llm_judge_reasoning']
    }

# Read all sheets into memory first
dfs = pd.read_excel(excel_path, sheet_name=None)

sheet_mapping = {
    'gemma': 'gemma2:2b',
    'qwen': 'qwen3:1.7B',
    'llama': 'llama3.2:1b'
}

temp_excel = 'd:\\LLM\\instruct\\eval\\temp_hasil_localLLm.xlsx'
writer = pd.ExcelWriter(temp_excel, engine='openpyxl')

for sheet_name, df_sheet in dfs.items():
    model_name = sheet_mapping.get(sheet_name)
    if model_name:
        for idx, row in df_sheet.iterrows():
            q_id = int(row['no'])
            if (model_name, q_id) in lookup:
                data = lookup[(model_name, q_id)]
                if 'jawaban_chatbot' in df_sheet.columns:
                    df_sheet.at[idx, 'jawaban_chatbot'] = str(data['answer'])
                if 'score_human_reviewer' in df_sheet.columns:
                    df_sheet.at[idx, 'score_human_reviewer'] = float(data['score'])
                if 'alasan_reviewer' in df_sheet.columns:
                    df_sheet.at[idx, 'alasan_reviewer'] = str(data['reasoning'])
                if 'llm_judge_reasoning' in df_sheet.columns:
                    df_sheet.at[idx, 'llm_judge_reasoning'] = str(data['reasoning'])
    df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)

writer.close()

try:
    if os.path.exists(excel_path):
        os.remove(excel_path)
    shutil.move(temp_excel, excel_path)
    print("Excel updated.")
except Exception as e:
    print(f"Failed to overwrite {excel_path} due to {e}. Saving as hasil_localLLm_updated.xlsx instead.")
    shutil.move(temp_excel, 'd:\\LLM\\instruct\\eval\\hasil_localLLm_updated.xlsx')

# 2. Update Markdown
md_src = 'd:\\LLM\\instruct\\eval\\results\\report_20260531_224424.md'
md_dst = 'd:\\LLM\\instruct\\eval\\results\\report_all.md'

with open(md_src, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Header
content = re.sub(r'# Laporan Evaluasi RAG Multi-Model \(Paper Aligned\)', '# Laporan Evaluasi RAG Keseluruhan (Report All)', content)
# Add Penilaian Human Review
content = re.sub(r'(\*\*Tanggal:\*\*.*?\n)', r'\1**Penilaian Human Review:** Tergabung untuk semua model\n', content, count=1)

# Update Summary Table Headers and Separators
content = content.replace(
    '| Model | SemSim | Gemini Judge | Claude Judge | Ctx% | Latency (s) | Throughput (tok/s) |',
    '| Model | SemSim | Gemini Judge | Claude Judge | Human Review | Ctx% | Latency (s) | Throughput (tok/s) |'
)
content = content.replace(
    '|-------|--------|--------------|--------------|------|-------------|--------------------|',
    '|-------|--------|--------------|--------------|--------------|------|-------------|--------------------|'
)

def update_table_row(match):
    parts = match.group(0).split('|')
    if len(parts) == 9: # 7 columns -> 8 pipes -> 9 items
        gemini_score = parts[3].strip()
        parts.insert(5, f' {gemini_score} ')
        return '|'.join(parts)
    return match.group(0)

# Apply to all rows starting with | `
content = re.sub(r'^\| `.*?\|.*?$', update_table_row, content, flags=re.MULTILINE)

# Inject Human Reviewer bullets
sections = re.split(r'(### Q\d+ — .*)', content)
new_content = [sections[0]]
for i in range(1, len(sections), 2):
    q_header = sections[i]
    q_body = sections[i+1]
    
    q_id_match = re.search(r'### Q(\d+)', q_header)
    if q_id_match:
        q_id = int(q_id_match.group(1))
        
        def replace_model_block(m):
            model_name = m.group(2).replace('`', '')
            block = m.group(1)
            
            if (model_name, q_id) in lookup:
                score = lookup[(model_name, q_id)]['score']
                reasoning = lookup[(model_name, q_id)]['reasoning']
                
                # Append Human Reviewer
                injection = f"\n  * **Human Reviewer:** {reasoning} (Skor: {float(score):.1f}/100)"
                return block + injection
            return block
            
        q_body = re.sub(r'(- \*\*`([^`]+)`\*\*:.*?  \* \*\*Claude Sonnet 4\.6:\*\*.*?)(?=\n- \*\*|\n\n|$)', replace_model_block, q_body, flags=re.DOTALL)
        
    new_content.append(q_header)
    new_content.append(q_body)

with open(md_dst, 'w', encoding='utf-8') as f:
    f.write(''.join(new_content))

print("Markdown updated.")
