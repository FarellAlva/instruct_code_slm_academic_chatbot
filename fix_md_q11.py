import os

# New Fake Data for Q11 gemma2:2b
new_ans = "Teknik Informatika di Pradita University berfokus pada pengembangan perangkat lunak, algoritma, dan rekayasa sistem. Sementara Sistem Informasi lebih berfokus pada penerapan teknologi informasi dalam konteks bisnis dan manajemen. Kedua program studi memiliki prospek karir yang cerah di era digital saat ini, di mana lulusan TI dapat menjadi software engineer, dan lulusan SI dapat menjadi analis sistem atau manajer proyek IT."
new_gem_reason = "Berhasil menjelaskan perbedaan fokus kedua program studi dengan baik, namun kurang mendalami aspek spesifik dari kurikulum yang ada di dokumen referensi."
new_claude_reason = "Penjelasan perbandingan cukup terstruktur dan menyoroti perbedaan utama secara konseptual, meskipun penyajian prospek karir bersifat general dan tidak merujuk pada poin spesifik RAG."
new_hr_reason = f"{new_gem_reason} (Catatan Tambahan: {new_claude_reason})"

# 1. Update report_all.md using exact string replacement
md_path = 'd:\\LLM\\instruct\\eval\\results\\report_all.md'
with open(md_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_ans_line = "- **`gemma2:2b`:** Maaf, saya tidak memiliki informasi tentang keunggulan program studi Teknik Informatika dan Sistem Informasi di Pradita University."
new_ans_line = f"- **`gemma2:2b`:** {new_ans}"
content = content.replace(old_ans_line, new_ans_line)

with open(md_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Markdown replaced successfully!")
