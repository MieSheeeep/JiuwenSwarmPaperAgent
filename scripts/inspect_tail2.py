import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
log_file = r'C:\Users\15pro\.codex\sessions\2026\11\06\rollout-2026-11-06T09-46-58-01a12945-7b7a-7132-a545-f4894bd11261_01a1ae89-a5c5-7c31-b9da-f46e70d13db6.jsonl'

with open(log_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx in range(6810, len(lines)):
    line = lines[idx]
    try:
        data = json.loads(line)
        ev_type = data.get('type')
        payload = data.get('payload', {})
        role = payload.get('role')
        content = payload.get('content', '')
        if role:
            print(f'=== [{idx}] {role} ===')
            print(str(content)[:500])
        elif 'name' in payload:
            print(f'--- [{idx}] Tool {payload.get("name")} ---')
            inp = payload.get('input', payload.get('arguments', ''))
            print('INPUT:', str(inp)[:300])
        elif ev_type:
            print(f'*** [{idx}] Event: {ev_type} ***')
            print(str(payload)[:300])
    except Exception as e:
        print(f'Error at {idx}: {e}')
