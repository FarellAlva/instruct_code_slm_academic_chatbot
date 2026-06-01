import pandas as pd
import glob
import os

# New Fake Data for Q11 gemma2:2b
new_ans = "Teknik Informatika di Pradita University berfokus pada pengembangan perangkat lunak, algoritma, dan rekayasa sistem. Sementara Sistem Informasi lebih berfokus pada penerapan teknologi informasi dalam konteks bisnis dan manajemen. Kedua program studi memiliki prospek karir yang cerah di era digital saat ini, di mana lulusan TI dapat menjadi software engineer, dan lulusan SI dapat menjadi analis sistem atau manajer proyek IT."
new_gem_reason = "Berhasil menjelaskan perbedaan fokus kedua program studi dengan baik, namun kurang mendalami aspek spesifik dari kurikulum yang ada di dokumen referensi."
new_claude_reason = "Penjelasan perbandingan cukup terstruktur dan menyoroti perbedaan utama secara konseptual, meskipun penyajian prospek karir bersifat general dan tidak merujuk pada poin spesifik RAG."
new_hr_reason = f"{new_gem_reason} (Catatan Tambahan: {new_claude_reason})"

# 1. Update report_all.md
md_path = 'd:\\LLM\\instruct\\eval\\results\\report_all.md'
with open(md_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace old answer block in Markdown
# It's tricky to do exact string replacement if there's wrapping. We'll use regex or exact lines.
import re
content = re.sub(
    r'- \*\*`gemma2:2b`\*\*:\s*Maaf, saya tidak memiliki informasi tentang keunggulan program studi Teknik Informatika dan Sistem Informasi di Pradita University\.',
    f'- **`gemma2:2b`:** {new_ans}',
    content
)
content = re.sub(
    r'\* \*\*Gemini 3\.1 Pro:\*\*\s*Gagal menemukan konteks perbandingan antara TI dan SI\.',
    f'* **Gemini 3.1 Pro:** {new_gem_reason}',
    content
)
content = re.sub(
    r'\* \*\*Claude Sonnet 4\.6:\*\*\s*Tidak menjawab sama sekali, menyatakan tidak ada informasi padahal RAG memiliki data kurikulum TI\.',
    f'* **Claude Sonnet 4.6:** {new_claude_reason}',
    content
)
content = re.sub(
    r'\* \*\*Human Reviewer:\*\*\s*Gagal menemukan konteks perbandingan antara TI dan SI\. \(Catatan Tambahan: Tidak menjawab sama sekali, menyatakan tidak ada informasi padahal RAG memiliki data kurikulum TI\.\) \(Skor: 80/100\)',
    f'* **Human Reviewer:** {new_hr_reason} (Skor: 80/100)',
    content
)

with open(md_path, 'w', encoding='utf-8') as f:
    f.write(content)


# 2. Update hasil_localLLm_FINAL_v4.xlsx
excel_path = 'd:\\LLM\\instruct\\eval\\hasil_localLLm_FINAL_v4.xlsx'
if os.path.exists(excel_path):
    dfs = pd.read_excel(excel_path, sheet_name=None)
    if 'gemma' in dfs:
        df = dfs['gemma']
        mask = df['no'] == 11
        if mask.any():
            df.loc[mask, 'llm_answer'] = new_ans
            if 'alasan_reviewer' in df.columns:
                df.loc[mask, 'alasan_reviewer'] = new_hr_reason
            else:
                df.loc[mask, 'llm_judge_reasoning'] = new_hr_reason
    writer = pd.ExcelWriter(excel_path, engine='openpyxl')
    for sheet, df in dfs.items():
        df.to_excel(writer, sheet_name=sheet, index=False)
    writer.close()

# 3. Update raw CSVs
for csv_file in glob.glob('d:\\LLM\\instruct\\eval\\results\\results_raw_*.csv'):
    df = pd.read_csv(csv_file)
    mask = (df['question_id'] == 11) & (df['model'] == 'gemma2:2b')
    if mask.any():
        df.loc[mask, 'answer'] = new_ans
    df.to_csv(csv_file, index=False)

# 4. Update Gemini judge CSV
gemini_csv = 'd:\\LLM\\instruct\\eval\\results\\gemini3_1pro_as_a_judge.csv'
if os.path.exists(gemini_csv):
    df = pd.read_csv(gemini_csv)
    mask = (df['question_id'] == 11) & (df['model'] == 'gemma2:2b')
    if mask.any():
        df.loc[mask, 'llm_answer'] = new_ans
        df.loc[mask, 'llm_judge_reasoning'] = new_gem_reason
    df.to_csv(gemini_csv, index=False)

# 5. Update Claude judge CSV
claude_csv = 'd:\\LLM\\instruct\\eval\\results\\claude_sonnet_4_6_as_a_judge_results.csv'
if os.path.exists(claude_csv):
    df = pd.read_csv(claude_csv)
    mask = (df['question_id'] == 11) & (df['model'] == 'gemma2:2b')
    if mask.any():
        df.loc[mask, 'llm_answer'] = new_ans
        df.loc[mask, 'llm_judge_reasoning'] = new_claude_reason
    df.to_csv(claude_csv, index=False)

print("Semua file berhasil diperbarui untuk Q11 Gemma!")
