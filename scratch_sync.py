import re
import pandas as pd
import json

def parse_report(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    details_part = content.split('## Detail Per Pertanyaan')[1]
    # Split by questions
    questions = re.split(r'### Q\d+ — ', details_part)[1:]
    
    parsed_data = []
    
    for q_idx, q_text in enumerate(questions):
        q_id = q_idx + 1 # 1 to 15
        
        # Extract table data
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
        
        # Extract reasoning
        eval_part = re.split(r'\*\*Jawaban model & Evaluasi LLM Judge', q_text)
        if len(eval_part) > 1:
            eval_text = eval_part[1]
            
            # We can split by `- **`
            model_blocks = re.split(r'\n- \*\*(.*?)\*\*:', eval_text)[1:]
            
            for i in range(0, len(model_blocks), 2):
                model_name = model_blocks[i].replace('`', '').strip()
                block_content = model_blocks[i+1]
                
                # Extract Gemini reasoning
                gem_match = re.search(r'\*\*Gemini 3\.1 Pro:\*\* (.*?)(?=\n\s*\* \*\*Claude|$)', block_content, re.DOTALL)
                claude_match = re.search(r'\*\*Claude Sonnet 4\.6:\*\* (.*?)(?=\n- \*\*|\n$|$)', block_content, re.DOTALL)
                
                gem_reasoning = gem_match.group(1).strip() if gem_match else ""
                claude_reasoning = claude_match.group(1).strip() if claude_match else ""
                
                if model_name in model_scores:
                    model_scores[model_name]['gemini_reasoning'] = gem_reasoning
                    model_scores[model_name]['claude_reasoning'] = claude_reasoning
        
        for model, data in model_scores.items():
            parsed_data.append({
                'question_id': q_id,
                'model': model,
                **data
            })
            
    return parsed_data

parsed = parse_report('eval/results/report_20260531_224424.md')
print(f"Extracted {len(parsed)} records.")
for i in range(3):
    print(json.dumps(parsed[i], indent=2))
