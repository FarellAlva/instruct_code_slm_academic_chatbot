import re
import pandas as pd

with open('eval/results/report_20260531_224424.md', 'r', encoding='utf-8') as f:
    content = f.read()

details_part = content.split('## Detail Per Pertanyaan')[1]
questions = re.split(r'### Q(\d+) — [^\n]+', details_part)[1:] # [q1_num, q1_text, q2_num, q2_text...]

human_data = {}
for i in range(0, len(questions), 2):
    q_num = int(questions[i])
    q_text = questions[i+1]
    
    # Cari bagian gemma2:2b
    gemma_block = re.search(r'- \*\*`gemma2:2b`:\*\*.*?(?=\n- \*\*`|\Z)', q_text, re.DOTALL)
    if gemma_block:
        text = gemma_block.group(0)
        # Cari skor dari tabel
        # Tabel
        table_lines = re.search(r'\|\s*Model\s*\|.*?(?=\n\n|\n\*\*Jawaban)', q_text, re.DOTALL)
        score = 0
        if table_lines:
            for line in table_lines.group(0).split('\n'):
                if '`gemma2:2b`' in line:
                    parts = line.split('|')
                    if len(parts) > 3:
                        score = float(parts[3].strip()) # Gemini score
        
        # Cari Gemini reasoning
        gem_match = re.search(r'\*\*Gemini 3\.1 Pro:\*\*\s*(.*?)(?=\n\s*\* \*\*Claude|\Z)', text, re.DOTALL)
        if gem_match:
            reason = gem_match.group(1).strip()
            human_data[q_num] = {'score': score, 'reason': reason}

# 1. Update human_review.xlsx
df = pd.read_excel('eval/human_review.xlsx')
for idx, row in df.iterrows():
    no = int(row['no'])
    if no in human_data:
        df.at[idx, 'score_human_reviewer'] = human_data[no]['score']
        df.at[idx, 'alasan_reviewer'] = human_data[no]['reason']
df.to_excel('eval/human_review.xlsx', index=False)
print("Updated human_review.xlsx successfully.")

# 2. Build report_all.md again
def replace_func(match):
    q_str = match.group(1)
    q_num = int(q_str)
    block = match.group(0)
    
    if q_num in human_data:
        hr = human_data[q_num]
        score = hr['score']
        reason = hr['reason']
        
        gemma_section = re.search(r'(- \*\*`gemma2:2b`:\*\*.*?(?=\n- \*\*|\Z))', block, re.DOTALL)
        if gemma_section:
            gemma_text = gemma_section.group(1)
            claude_match = re.search(r'(\n\s*\* \*\*Claude Sonnet 4\.6:\*\*.*?)(?=\n\s*\*|\n- \*\*|\Z)', gemma_text, re.DOTALL)
            
            if claude_match:
                claude_text = claude_match.group(1)
                injection = f"{claude_text}\n  * **Human Reviewer:** {reason} (Skor: {score}/100)"
                new_gemma_text = gemma_text.replace(claude_text, injection)
                block = block.replace(gemma_text, new_gemma_text)
                
    return block

new_content = re.sub(r'### Q(\d+) — [^\n]+[\s\S]*?(?=\n### Q\d+ — |\Z)', replace_func, content)
new_content = new_content.replace('# Laporan Evaluasi RAG Multi-Model (Paper Aligned)', '# Laporan Evaluasi RAG Keseluruhan (Report All)')
new_content = new_content.replace('**Model yang dievaluasi:**', '**Penilaian Human Review:** Tergabung khusus untuk `gemma2:2b`\n**Model yang dievaluasi:**')

with open('eval/results/report_all.md', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Built report_all.md successfully.")
