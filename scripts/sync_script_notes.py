import re
import sys
sys.path.insert(0, ".")
from scripts.build_unified_master_presentation import NOTES_DATA

script_path = "docs/第6组项目汇报逐页讲稿_终版.md"
with open(script_path, "r", encoding="utf-8") as f:
    text = f.read()

# Split by slide
slides = re.split(r'(?m)^## 第(\d+)页\s*(.*?)$', text)
# slides[0] is header
header = slides[0].strip()

new_content = [header + "\n\n"]
for i in range(1, len(slides), 3):
    num = int(slides[i])
    title = slides[i+1].strip()
    body = slides[i+2]
    
    # Extract page content
    page_content_match = re.search(r'(?s)### 页面内容\s*\n(.*?)(?=### 讲稿|\Z)', body)
    page_content = page_content_match.group(1).strip() if page_content_match else ""
    
    notes = NOTES_DATA.get(num, "").strip()
    
    slide_text = f"## 第{num}页 {title}\n\n"
    if page_content:
        slide_text += f"### 页面内容\n\n{page_content}\n\n"
    
    # Parse notes into subheadings
    timing_m = re.search(r'⏱️【建议用时】\s*\n([^\n]+)', notes)
    timing = timing_m.group(1).strip() if timing_m else ""
    
    speech_m = re.search(r'🎙️【逐字答辩讲稿】\s*\n(.*?)(?=🔄【换页过渡语】|\Z)', notes, re.DOTALL)
    speech = speech_m.group(1).strip() if speech_m else ""
    
    trans_m = re.search(r'🔄【换页过渡语】\s*\n(.*?)(?=💡【评委可能提问与应答预案】|\Z)', notes, re.DOTALL)
    trans = trans_m.group(1).strip() if trans_m else ""
    
    qa_m = re.search(r'💡【评委可能提问与应答预案】\s*\n(.*?)(?=\Z)', notes, re.DOTALL)
    qa = qa_m.group(1).strip() if qa_m else ""
    
    slide_text += f"### 【建议用时】\n{timing}\n\n"
    slide_text += f"### 【逐字答辩讲稿】\n{speech}\n\n"
    slide_text += f"### 【换页过渡语】\n{trans}\n\n"
    slide_text += f"### 【评委可能提问与应答预案】\n{qa}\n\n---\n\n"
    
    new_content.append(slide_text)

full_output = "".join(new_content)
with open(script_path, "w", encoding="utf-8") as f:
    f.write(full_output)

print(f"[OK] Updated {script_path} with 16 comprehensive slides and 4-part notes!")
