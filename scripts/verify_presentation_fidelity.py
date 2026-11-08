import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open('docs/第6组项目汇报逐页讲稿_终版.md', encoding='utf-8') as f:
    text = f.read()

print("--- AUDITING docs/第6组项目汇报逐页讲稿_终版.md ---")
print(f"Total length: {len(text)} characters")

# Check for banned/suspicious terms
banned = [
    '首创', '自研', '对标', '战队', '空梦轮年', '引擎',
    '已提交PR', '提交了PR', '合入主干', '已录用', '已投稿',
    '例如，', 'Clear Accept', '7.0分', '8.0分', '7.', '8.'
]

for kw in banned:
    matches = [m.start() for m in re.finditer(re.escape(kw), text)]
    if matches:
        print(f"\n[ALERT] Found '{kw}' at {len(matches)} places:")
        for pos in matches[:5]:
            snippet = text[max(0, pos-40):min(len(text), pos+40)].replace('\n', ' ')
            print(f"  --> ...{snippet}...")
    else:
        print(f"[OK] No '{kw}' found.")

print("\n--- CHECKING SLIDE COUNT AND STRUCTURE ---")
slides = re.findall(r'## 第 (\d+) 页[：:]\s*(.+)', text)
print(f"Total slides found: {len(slides)}")
for num, title in slides:
    print(f"  Slide {num:>2}: {title}")
