"""把需要补全 %s 的器官切成若干批，供并行处理。"""
import json
from pathlib import Path

SITE = Path('D:/SelfAgent/work/organ-codex/site')
OUT = Path('D:/SelfAgent/work/organ-codex/build/batches')
OUT.mkdir(parents=True, exist_ok=True)

organs = {o['id']: o for o in json.load(open(SITE / 'data/organs.json', encoding='utf-8'))}
logic = json.load(open(SITE / 'data/logic.json', encoding='utf-8'))
scores = json.load(open(SITE / 'data/scores.json', encoding='utf-8'))

need = [oid for oid, o in organs.items() if any('%s' in l for l in o['effects'])]
need.sort()

items = []
for oid in need:
    o = organs[oid]
    items.append({
        'id': oid,
        'name': o['name'],
        'effects': o['effects'],
        'logic': [{'event': e['event'], 'fn': e['fn'], 'body': e['body']} for e in logic.get(oid, [])],
    })

N = 4
size = (len(items) + N - 1) // N
for i in range(N):
    chunk = items[i * size:(i + 1) * size]
    if not chunk:
        continue
    path = OUT / f'batch{i + 1}.json'
    json.dump({'scores': scores, 'organs': chunk}, open(path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(path.name, len(chunk), 'organs')
