"""合并四批 tooltip 补齐结果，校验数字来源，写回 organs.json。"""
import json
import re
from pathlib import Path

BASE = Path('D:/SelfAgent/work/organ-codex')
SITE = BASE / 'site'
organs = json.load(open(SITE / 'data/organs.json', encoding='utf-8'))
logic = json.load(open(SITE / 'data/logic.json', encoding='utf-8'))
by_id = {o['id']: o for o in organs}

merged, problems, flagged = {}, [], []
NUM = re.compile(r'\d+(?:\.\d+)?')

for i in range(1, 5):
    p = BASE / f'build/batches/out{i}.json'
    data = json.load(open(p, encoding='utf-8'))
    for oid, lines in data.items():
        if oid not in by_id:
            problems.append(f'{oid}: 器官不存在')
            continue
        o = by_id[oid]
        bodies = ' '.join(e['body'] for e in logic.get(oid, []))
        for k, text in lines.items():
            idx = int(k) - 1
            if not (0 <= idx < len(o['effects'])):
                problems.append(f'{oid}: 行号 {k} 越界')
                continue
            if '%s' in text:
                problems.append(f'{oid}#{k}: 仍含 %s')
                continue
            orig = o['effects'][idx]
            src_nums = set(NUM.findall(orig) + NUM.findall(bodies))
            for n in NUM.findall(text):
                if n not in src_nums:
                    flagged.append((oid, k, n, text.strip()[:80]))
            merged.setdefault(oid, {})[k] = text

# 写回：effectsResolved 覆盖 effects 中对应行
for o in organs:
    m = merged.get(o['id'])
    if not m:
        continue
    resolved = []
    for i, line in enumerate(o['effects'], start=1):
        resolved.append(m.get(str(i), line))
    o['effectsResolved'] = resolved

json.dump(organs, open(SITE / 'data/organs.json', 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))

print('merged organs:', len(merged), 'lines:', sum(len(v) for v in merged.values()))
print('problems:', len(problems))
for p in problems[:10]:
    print('  !', p)
print('numbers not traceable to source:', len(flagged))
for f in flagged[:25]:
    print('  ?', f[0], '#' + f[1], '数字', f[2], '|', f[3])
