import re
import pandas as pd

# Load Human Review Data
human_df = pd.read_excel('eval/human_review.xlsx')
human_data = {}
for idx, row in human_df.iterrows():
    no = int(row['no'])
    score = row['score_human_reviewer']
    reason = str(row['alasan_reviewer']).strip()
    human_data[no] = {'score': score, 'reason': reason}

# Load Markdown Report
with open('eval/results/report_20260531_224424.md', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to inject Human Review text in the detail section for each question
# The questions are marked by "### Q01", "### Q02", etc.
def replace_func(match):
    q_str = match.group(1)
    q_num = int(q_str)
    block = match.group(0)
    
    if q_num in human_data:
        hr = human_data[q_num]
        score = hr['score']
        reason = hr['reason']
        # Find where the Claude evaluation for gemma2:2b ends
        # Typically looks like:
        #   * **Claude Sonnet 4.6:** ...
        # (Followed by next model or end of block)
        
        # Regex to find Claude's line inside gemma2:2b's section
        gemma_section = re.search(r'(- \*\*`gemma2:2b`:\*\*.*?(?=\n- \*\*|\Z))', block, re.DOTALL)
        if gemma_section:
            gemma_text = gemma_section.group(1)
            # Find the end of Claude line
            claude_match = re.search(r'(\n\s*\* \*\*Claude Sonnet 4\.6:\*\*.*?)(?=\n\s*\*|\n- \*\*|\Z)', gemma_text, re.DOTALL)
            
            if claude_match:
                claude_text = claude_match.group(1)
                injection = f"{claude_text}\n  * **Human Reviewer:** {reason} (Skor: {score}/100)"
                new_gemma_text = gemma_text.replace(claude_text, injection)
                block = block.replace(gemma_text, new_gemma_text)
                
    return block

# Apply the substitution block by block
# Split content into question blocks and everything else
parts = re.split(r'(### Q(\d+) — [^\n]+[\s\S]*?(?=\n### Q\d+ — |\Z))', content)

new_content = ""
# parts will have: [before_q1, q1_block, '01', empty?, q2_block, '02', empty?]
# wait, re.split with a group will return the whole block as well
# actually, let's use re.sub directly on the whole text
new_content = re.sub(r'### Q(\d+) — [^\n]+[\s\S]*?(?=\n### Q\d+ — |\Z)', replace_func, content)

# Modify Title
new_content = new_content.replace('# Laporan Evaluasi RAG Multi-Model (Paper Aligned)', '# Laporan Evaluasi RAG Keseluruhan (Report All)')
new_content = new_content.replace('**Model yang dievaluasi:**', '**Penilaian Human Review:** Tergabung khusus untuk `gemma2:2b`\n**Model yang dievaluasi:**')

with open('eval/results/report_all.md', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Berhasil membuat report_all.md")
