import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
log_file = r'C:\Users\15pro\.codex\sessions\2026\11\06\rollout-2026-11-06T09-46-58-01a12945-7b7a-7132-a545-f4894bd11261_01a1ae89-a5c5-7c31-b9da-f46e70d13db6.jsonl'

with open(log_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx in range(max(0, len(lines)-150), len(lines)):
    line = lines[idx]
    try:
        data = json.loads(line)
        ev_type = data.get('type')
        payload = data.get('payload', {})
        role = payload.get('role')
        content = payload.get('content', '')
        if isinstance(content, list):
            text_parts = []
            for p in content:
                if isinstance(p, dict):
                    if p.get('type') == 'text':
                        text_parts.append(p.get('text', ''))
                    elif 'text' in p:
                        text_parts.append(p.get('text', ''))
            content = '\n'.join(text_parts)
        if role or ev_type in ['user_message', 'assistant_message']:
            print(f'=== [{idx}] {role or ev_type} ===')
            print(str(content).strip()[:400])
        elif 'name' in payload:
            name = payload.get('name')
            inp = str(payload.get('input', payload.get('arguments', '')))[:200]
            print(f'--- [{idx}] Tool {name}: {inp} ---')
    except Exception as e:
        pass
