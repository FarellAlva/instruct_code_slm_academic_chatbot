import pandas as pd
df = pd.read_csv('eval/results/results_raw_20260523_114434.csv')
with open('gemini_eval_input.txt', 'w', encoding='utf-8') as f:
    for _, row in df[df['model'] == 'qwen3:1.7B'].iterrows():
        f.write(f'Q{row["question_id"]}: {row["question"]}\n')
        f.write(f'REF: {row["reference_answer"]}\n')
        ans = str(row["answer"]).replace('\n', ' ')
        f.write(f'ANS: {ans}\n')
        f.write('-'*40 + '\n')
