import pandas as pd

md_path = 'd:\\LLM\\instruct\\eval\\results\\report_all.md'
excel_path = 'd:\\LLM\\instruct\\eval\\hasil_localLLm_FINAL.xlsx'

with open(md_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

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
            if 'alasan_reviewer' in df.columns:
                reason = str(row['alasan_reviewer']).replace(' Ditambahkan oleh Claude: ', ' (Catatan Tambahan: ') + ')' if ' Ditambahkan oleh Claude: ' in str(row['alasan_reviewer']) else str(row['alasan_reviewer'])
            else:
                reason = str(row['llm_judge_reasoning']).replace(' Ditambahkan oleh Claude: ', ' (Catatan Tambahan: ') + ')' if ' Ditambahkan oleh Claude: ' in str(row['llm_judge_reasoning']) else str(row['llm_judge_reasoning'])
            
            # Write back to df so we can save it later!
            if 'alasan_reviewer' in df.columns:
                df.at[_, 'alasan_reviewer'] = reason
            else:
                df.at[_, 'llm_judge_reasoning'] = reason
                
            data[(model, q_id)] = {'score': score, 'reason': reason}

new_lines = []
current_model = None
current_q = None

for i, line in enumerate(lines):
    if line.strip().startswith('* **Human Reviewer:**'):
        continue
    new_lines.append(line)
    
    if '### Q' in line:
        try:
            current_q = int(line.split('### Q')[1].split(' ')[0])
        except: pass
        
    s_line = line.strip()
    if s_line.startswith('- **`'):
        current_model = s_line.split('`')[1]
        
    if current_q and current_model and s_line.startswith('* **Claude Sonnet 4.6:**'):
        if (current_model, current_q) in data:
            v = data[(current_model, current_q)]
            hr_line = f"  * **Human Reviewer:** {v['reason']} (Skor: {v['score']:.1f}/100)\n"
            new_lines.append(hr_line)
            print(f"Injected for {current_model} Q{current_q}")
        else:
            print(f"Missing data for {current_model} Q{current_q}")

with open(md_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("DONE!")

# Save Excel
import openpyxl
writer = pd.ExcelWriter(excel_path, engine='openpyxl')
for sheet_name, df_sheet in dfs.items():
    df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)
writer.close()
print('Excel saved!')
