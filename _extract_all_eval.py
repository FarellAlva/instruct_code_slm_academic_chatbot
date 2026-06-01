import pandas as pd
df = pd.read_csv('eval/results/results_raw_20260526_013647.csv')
with open('gemini_eval_input_all.txt', 'w', encoding='utf-8') as f:
    for model in df['model'].unique():
        f.write(f'=== MODEL: {model} ===\n')
        for _, row in df[df['model'] == model].iterrows():
            f.write(f'Q{row["question_id"]}: {row["question"]}\n')
            f.write(f'REF: {row["reference_answer"]}\n')
            ans = str(row["answer"]).replace('\n', ' ')
            f.write(f'ANS: {ans}\n')
            f.write('-'*40 + '\n')
