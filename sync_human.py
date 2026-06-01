import pandas as pd

# Baca data raw yang sudah sinkron
raw_df = pd.read_csv('eval/results/results_raw_20260531_222243.csv')

# Baca human_review
human_df = pd.read_excel('eval/human_review.xlsx')

updated_count = 0
for idx, row in human_df.iterrows():
    model = row['model']
    no = row['no']
    
    # Cari di raw_df
    match = raw_df[(raw_df['model'] == model) & (raw_df['question_id'] == no)]
    
    if not match.empty:
        # Gunakan Gemini (llm_judge) sebagai human review karena alasan awalnya dari sana
        new_score = match['llm_judge_score'].values[0]
        new_reason = match['llm_judge_reasoning'].values[0]
        
        human_df.at[idx, 'score_human_reviewer'] = new_score
        human_df.at[idx, 'alasan_reviewer'] = new_reason
        updated_count += 1

# Simpan kembali ke Excel
human_df.to_excel('eval/human_review.xlsx', index=False)

print(f"Berhasil mengupdate {updated_count} baris di human_review.xlsx")
