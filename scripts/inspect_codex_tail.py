import json
from pathlib import Path

p = Path(r"C:\Users\15pro\.codex\sessions\2026\11\06\rollout-2026-11-06T09-46-58-01a12945-7b7a-7132-a545-f4894bd11261_01a1ae89-a5c5-7c31-b9da-f46e70d13db6.jsonl")

# Read the last 200KB of the file
size = p.stat().st_size
with open(p, "rb") as f:
    f.seek(max(0, size - 200000))
    lines = f.readlines()

print(f"Total lines in tail: {len(lines)}")
for line in lines[-30:]:
    try:
        obj = json.loads(line.decode('utf-8', errors='ignore'))
        t = obj.get("type", "")
        role = obj.get("role", "")
        # print concise summary
        content = str(obj.get("content", ""))[:120].replace("\n", " ")
        msg = obj.get("message", {})
        if isinstance(msg, dict):
            m_role = msg.get("role", "")
            m_content = str(msg.get("content", ""))[:120].replace("\n", " ")
            print(f"[{t}] role={role}/{m_role}: {m_content}")
        else:
            print(f"[{t}] role={role}: {content}")
    except Exception as e:
        print("err:", e)
