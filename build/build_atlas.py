"""把器官材质打包成一张图集，减少页面请求数。"""
import json
from pathlib import Path
from PIL import Image

SITE = Path('D:/SelfAgent/work/organ-codex/site')
organs = json.load(open(SITE / 'data/organs.json', encoding='utf-8'))
COLS = 20
CELL = 16

items = [(o['id'], o['texture']) for o in organs if o.get('texture')]
rows = (len(items) + COLS - 1) // COLS
atlas = Image.new('RGBA', (COLS * CELL, rows * CELL), (0, 0, 0, 0))
index = {'cols': COLS, 'cell': CELL, 'rows': rows, 'map': {}}

for i, (oid, tex) in enumerate(items):
    p = SITE / tex
    if not p.exists():
        continue
    im = Image.open(p).convert('RGBA')
    if im.width != CELL:
        im = im.resize((CELL, CELL), Image.Resampling.NEAREST)
    elif im.height != CELL:
        im = im.crop((0, 0, CELL, CELL))   # 动画贴图取首帧
    c, r = i % COLS, i // COLS
    atlas.alpha_composite(im, (c * CELL, r * CELL))
    index['map'][oid] = [c, r]

atlas.save(SITE / 'mc/atlas.png', optimize=True)
json.dump(index, open(SITE / 'data/atlas.json', 'w', encoding='utf-8'), separators=(',', ':'))
print('atlas', atlas.size, 'entries', len(index['map']))
