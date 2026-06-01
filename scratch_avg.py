import pandas as pd

df = pd.read_csv('eval/results/results_raw_20260531_222243.csv')

print("| Model | SemSim | Gemini | Claude | Latency | Tok/s |")
print("|-------|--------|--------|--------|---------|-------|")
for m in ['gemma2:2b', 'qwen3:1.7B', 'llama3.2:1b']:
    sub = df[df['model'] == m]
    ss = sub['semantic_similarity'].mean()
    gj = sub['llm_judge_score'].mean()
    cj = sub['claude_judge_score'].mean()
    lat = sub['latency_s'].mean()
    tps = sub['throughput_tps'].mean()
    
    print(f"| `{m}` | {ss:.4f} | {gj:.1f} | {cj:.1f} | {lat:.2f}s | {tps:.1f} |")
