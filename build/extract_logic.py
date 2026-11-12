"""提取每个器官的策略函数源码，供 tooltip 的 %s 占位符解析/描述生成使用。"""
import json
import re
from pathlib import Path

PACK = Path('D:/hermes-workspace/ribcage-ws/RibCage')
JS_DIR = PACK / 'kubejs/server_scripts/domain/organ/organ'
OUT = Path('D:/SelfAgent/work/organ-codex/site/data/logic.json')


def function_bodies(src):
    """粗切 function 声明体：靠花括号计数。"""
    out = {}
    for m in re.finditer(r'function\s+(\w+)\s*\(([^)]*)\)\s*\{', src):
        name = m.group(1)
        i = m.end()
        depth = 1
        while i < len(src) and depth:
            c = src[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            i += 1
        out[name] = src[m.end():i - 1].strip()
    return out


strategy_re = re.compile(
    r"RegistryOrganStrategy\(\s*new\s+OrganStrategyModel\(\s*'([^']+)'\s*\)(.*?)\)\s*\n\)", re.S)

logic = {}
for js in sorted(JS_DIR.rglob('*.js')):
    src = js.read_text(encoding='utf-8')
    bodies = function_bodies(src)
    for m in strategy_re.finditer(src):
        oid, body = m.group(1), m.group(2)
        entries = logic.setdefault(oid, [])
        for em in re.finditer(r"\.add(Only)?Strategy\(\s*'([^']+)'\s*,\s*(\w+)", body):
            fn = em.group(3)
            if fn not in bodies:
                continue
            entries.append({
                'event': em.group(2),
                'mode': 'only' if em.group(1) else 'all',
                'fn': fn,
                'file': js.relative_to(JS_DIR).as_posix(),
                'body': bodies[fn],
            })

json.dump(logic, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
organs = json.load(open(OUT.parent / 'organs.json', encoding='utf-8'))
need = [o for o in organs if any('%s' in line for line in o['effects'])]
print('logic entries', len(logic), '| organs needing %s work', len(need),
      '| of which have logic', sum(1 for o in need if o['id'] in logic))
print('sample body:', list(logic.values())[0][0]['body'][:200].replace('\n', ' '))
