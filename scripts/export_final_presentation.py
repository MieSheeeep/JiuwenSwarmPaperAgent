import subprocess
import shutil
from pathlib import Path
import sys

project_dir = Path("projects/group6_defense_ppt169_20261108")
target_docs = Path("docs/第6组项目汇报PPT_终版.pptx")
target_root = Path("第6组项目汇报PPT_终版.pptx")
target_sub = Path("submission/第6组_课程交付材料_20261108/第6组项目汇报PPT.pptx")

cmd = [
    sys.executable,
    "skills/ppt-master/scripts/svg_to_pptx.py",
    str(project_dir),
    "--quick-generate",
    "--with-notes",
    "-t", "fade",
    "-o", str(target_docs)
]

print("Executing ppt-master svg_to_pptx...")
res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
print(res.stdout)
if res.returncode != 0:
    print(res.stderr)
    sys.exit(res.returncode)

# Copy to root and submission
shutil.copy2(target_docs, target_root)
print(f"Copied to {target_root}")

target_sub.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(target_docs, target_sub)
print(f"Copied to {target_sub}")

# Run delivery check
check_cmd = [
    sys.executable,
    "skills/ppt-master/scripts/pptx_delivery_check.py",
    str(target_docs)
]
check_res = subprocess.run(check_cmd, capture_output=True, text=True, encoding="utf-8")
print("Delivery check status:", "PASSED" if check_res.returncode == 0 else "FAILED")
