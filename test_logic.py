lines = [
    '### Q01  Informasi Kampus [Sederhana]',
    '- **`gemma2:2b`:** Kampus Pradita',
    '  * **Gemini 3.1 Pro:** Sangat lengkap',
    '  * **Claude Sonnet 4.6:** Akurat 100%'
]
current_q = None
current_model = None
for line in lines:
    if '### Q' in line:
        current_q = int(line.split('### Q')[1].split(' ')[0])
    s_line = line.strip()
    if s_line.startswith('- **`') and '`**:' in s_line:
        current_model = s_line.split('`')[1]
    
    print(f"[{line}] -> q={current_q}, model={current_model}")
    if current_q and current_model and s_line.startswith('* **Claude Sonnet 4.6:**'):
        print('INJECTED', current_model, current_q)
