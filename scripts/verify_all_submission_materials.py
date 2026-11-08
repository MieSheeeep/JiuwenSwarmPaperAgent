from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import re

D = Path("submission/第6组_课程交付材料_20261108")
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def check_docx(filename):
    p = D / filename
    with ZipFile(p) as z:
        root = ET.fromstring(z.read("word/document.xml"))
        full_text = "".join(root.itertext())
    
    print(f"\nChecking {filename} ({len(full_text)} chars)...")
    required_terms = [
        'AgentRail', 'valid_at', 'observed_at', '29 项', '13 项', '8 项',
        '未提交上游 PR', '未验证', '金若曦', '洪豊幀', '黄炜杰', '黄俊翔', '王智洋'
    ]
    for term in required_terms:
        assert term in full_text, f"Missing term: {term}"
    
    # Check no 19-test obsolete claim
    assert not re.search(r'19\s*[项个].{0,8}(?:测试|检查)', full_text), "Found obsolete 19-test claim!"
    print("  -> PASSED: All required terms present, zero obsolete claims!")

for name in ['第6组系统使用说明书.docx', '第6组课程报告.docx']:
    check_docx(name)

# Check PPT
ppt_p = D / '第6组项目汇报PPT.pptx'
with ZipFile(ppt_p) as z:
    slides_xml = [n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]
    assert len(slides_xml) == 16, f"Expected 16 slides, got {len(slides_xml)}"
    full_ppt_text = ""
    for name in slides_xml:
        root = ET.fromstring(z.read(name))
        full_ppt_text += "".join(root.itertext()) + "\n"
    notes_xml = [n for n in z.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml', n)]
    assert len(notes_xml) == 16, f"Expected 16 notes, got {len(notes_xml)}"
    for name in notes_xml:
        root = ET.fromstring(z.read(name))
        full_ppt_text += "".join(root.itertext()) + "\n"

print(f"\nChecking 第6组项目汇报PPT.pptx (16 slides, 16 notes)...")
assert not re.search(r'19\s*[项个].{0,8}(?:测试|检查)', full_ppt_text), "Found obsolete 19-test claim in PPT!"
for term in ['AgentRail', 'valid_at', 'observed_at', '29 项', '13 项', '8 项', '未提交上游 PR', '金若曦', '洪豊幀', '黄炜杰', '黄俊翔', '王智洋']:
    assert term in full_ppt_text, f"Missing term in PPT: {term}"
print("  -> PASSED: All required terms present in PPT, zero obsolete claims!")
print("\nALL VERIFICATIONS PASSED 100%!")
