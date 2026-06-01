import re

md_path = 'd:\\LLM\\instruct\\eval\\results\\report_all.md'
with open(md_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    s_line = line.strip()
    if s_line.startswith('* **Claude Sonnet 4.6:**'):
        print(f"Found Claude at {i}: {s_line}")
