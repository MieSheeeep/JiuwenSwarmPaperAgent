import os
from pathlib import Path

p = Path(r"C:\Users\15pro\.codex\sessions")
for f in p.rglob("*01a12945*"):
    print(f, f.stat().st_size, f.stat().st_mtime)
