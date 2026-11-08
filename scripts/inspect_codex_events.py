import json
from pathlib import Path

p = Path(r"C:\Users\15pro\.codex\sessions\2026\11\06\rollout-2026-11-06T09-46-58-01a12945-7b7a-7132-a545-f4894bd11261_01a1ae89-a5c5-7c31-b9da-f46e70d13db6.jsonl")

size = p.stat().st_size
with open(p, "rb") as f:
    f.seek(max(0, size - 150000))
    lines = f.readlines()

for i, line in enumerate(lines[-20:]):
    try:
        obj = json.loads(line.decode('utf-8', errors='ignore'))
        payload = obj.get("payload", {})
        item = payload.get("item", {})
        call = payload.get("call", {})
        msg = payload.get("message", "")
        # print useful fields
        txt = json.dumps(obj, ensure_ascii=False)
        print(f"--- Event {i} (len {len(txt)}) ---")
        if "command" in txt or "thought" in txt or "content" in txt or "text" in txt:
            # print up to 300 chars
            print(txt[:300])
    except Exception as e:
        print(e)
