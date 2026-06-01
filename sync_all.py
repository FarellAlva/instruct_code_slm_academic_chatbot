import re
import pandas as pd
import json

def parse_report(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    details_part = content.split('## Detail Per Pertanyaan')[1]
    questions = re.split(r'### Q\d+ — ', details_part)[1:]
    
    parsed_data = {}
    
    for q_idx, q_text in enumerate(questions):
        q_id = q_idx + 1
        
        table_match = re.search(r'\|\s*Model\s*\|[\s\S]*?(?=\n\n|\n\*\*Jawaban)', q_text)
        if not table_match:
            continue
        table_lines = table_match.group(0).strip().split('\n')
        
        model_scores = {}
        for line in table_lines:
            if line.startswith('| `'):
                parts = line.split('|')
                model = parts[1].replace('`', '').strip()
                semsim = float(parts[2].strip())
                gemini = float(parts[3].strip())
                claude = float(parts[4].strip())
                model_scores[model] = {'semsim': semsim, 'gemini': gemini, 'claude': claude}
        
        eval_part = re.split(r'\*\*Jawaban model & Evaluasi LLM Judge', q_text)
        if len(eval_part) > 1:
            eval_text = eval_part[1]
            
            # Use regex to find each model section carefully
            # Find all model headers like "- **`model`:**"
            model_matches = list(re.finditer(r'- \*\*(.*?)\*\*:', eval_text))
            
            for i in range(len(model_matches)):
                model_name = model_matches[i].group(1).replace('`', '').strip()
                start_idx = model_matches[i].end()
                end_idx = model_matches[i+1].start() if i+1 < len(model_matches) else len(eval_text)
                
                block_content = eval_text[start_idx:end_idx]
                
                gem_match = re.search(r'\*\*Gemini 3\.1 Pro:\*\*\s*(.*?)(?=\n\s*\* \*\*Claude|$)', block_content, re.DOTALL)
                claude_match = re.search(r'\*\*Claude Sonnet 4\.6:\*\*\s*(.*?)(?=\n- \*\*|\n$|$)', block_content, re.DOTALL)
                
                gem_reasoning = gem_match.group(1).strip() if gem_match else ""
                claude_reasoning = claude_match.group(1).strip() if claude_match else ""
                
                if model_name in model_scores:
                    model_scores[model_name]['gemini_reasoning'] = gem_reasoning
                    model_scores[model_name]['claude_reasoning'] = claude_reasoning
        
        for model, data in model_scores.items():
            parsed_data[(q_id, model)] = data
            
    return parsed_data

parsed = parse_report('eval/results/report_20260531_224424.md')
print(f"Extracted {len(parsed)} records from MD.")

def update_csv(filename, columns_map):
    df = pd.read_csv(filename)
    updated = 0
    for idx, row in df.iterrows():
        q_id = int(row['question_id'])
        model = row['model']
        if (q_id, model) in parsed:
            data = parsed[(q_id, model)]
            if 'semantic_similarity' in columns_map:
                df.at[idx, 'semantic_similarity'] = data['semsim']
            if 'llm_judge_score' in columns_map:
                df.at[idx, 'llm_judge_score'] = data['gemini']
            if 'llm_judge_reasoning' in columns_map:
                df.at[idx, 'llm_judge_reasoning'] = data.get('gemini_reasoning', '')
            if 'claude_judge_score' in columns_map:
                df.at[idx, 'claude_judge_score'] = data['claude']
            if 'claude_judge_reasoning' in columns_map:
                df.at[idx, 'claude_judge_reasoning'] = data.get('claude_reasoning', '')
            updated += 1
    df.to_csv(filename, index=False)
    print(f"Updated {updated} records in {filename}")

# Update the files
update_csv('eval/results/results_raw_20260531_222243.csv', 
          ['semantic_similarity', 'llm_judge_score', 'llm_judge_reasoning', 'claude_judge_score', 'claude_judge_reasoning'])

update_csv('eval/results/gemini3_1pro_as_a_judge.csv', 
          ['semantic_similarity', 'llm_judge_score', 'llm_judge_reasoning'])

update_csv('eval/results/claude_sonnet_4_6_as_a_judge_results.csv', 
          ['semantic_similarity', 'claude_judge_score', 'claude_judge_reasoning', 'llm_judge_score', 'llm_judge_reasoning'])

# Generate summary
df_raw = pd.read_csv('eval/results/results_raw_20260531_222243.csv')
summary = []
for m in df_raw['model'].unique():
    sub = df_raw[df_raw['model'] == m]
    summary.append({
        'model': m,
        'semantic_similarity': sub['semantic_similarity'].mean(),
        'llm_judge_score': sub['llm_judge_score'].mean(),
        'claude_judge_score': sub['claude_judge_score'].mean(),
        'context_has_answer': sub['context_has_answer'].mean(),
        'context_similarity': sub['context_similarity'].mean(),
        'latency_s': sub['latency_s'].mean(),
        'throughput_tps': sub['throughput_tps'].mean()
    })

pd.DataFrame(summary).to_csv('eval/results/results_summary_20260531_222243.csv', index=False)
print("Updated results_summary_20260531_222243.csv")
