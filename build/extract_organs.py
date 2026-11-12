"""从 RibCage 仓库提取器官图鉴数据，输出静态站用的 JSON。"""
import json
import re
from pathlib import Path

PACK = Path('D:/hermes-workspace/ribcage-ws/RibCage')
OUT = Path('D:/SelfAgent/work/organ-codex/site/data')
OUT.mkdir(parents=True, exist_ok=True)

JS_DIR = PACK / 'kubejs/server_scripts/domain/organ/organ'
TEX_DIR = PACK / 'kubejs/assets/kubejs/textures/item/organs'
LANG = PACK / 'kubejs/assets/kubejs/lang/zh_cn.json'
INV_DIR = PACK / 'kubejs/data/kubejs/cc_inventory_types'
TYPE_DIR = PACK / 'kubejs/data/kubejs/cc_types'

lang = json.load(open(LANG, encoding='utf-8'))
MC_LANG = Path('D:/SelfAgent/work/organ-codex/build/mc_zh_cn.json')
mc_lang = json.load(open(MC_LANG, encoding='utf-8')) if MC_LANG.exists() else {}
# 全包 lang 汇总：mod 生物名（entity.<ns>.<stem>）
MOD_ENTITY = {}
for lp in (PACK / 'kubejs/assets').rglob('lang/zh_cn.json'):
    try:
        d = json.load(open(lp, encoding='utf-8'))
    except Exception:
        continue
    for k, v in d.items():
        if k.startswith('entity.') and k.count('.') == 2:
            MOD_ENTITY.setdefault(k.split('.', 2)[2], v)

# ---------- 事件中文名 ----------
EVENT_NAMES = {
    'item_right_clicked': '右键物品', 'item_left_clicked': '左键物品',
    'entity_do_damage': '造成伤害', 'chest_cavity_update': '胸腔更新',
    'food_eaten': '进食', 'block_broken': '破坏方块',
    'entity_be_hurt': '受到伤害', 'player_enchant': '附魔',
    'entity_loot': '实体掉落', 'chest_loot': '箱子战利品',
    'entity_tick': '每 tick', 'iss_player_spell_cast': '施法',
    'entity_kill': '击杀', 'entity_be_interacted': '被交互',
    'entity_interact': '交互', 'block_right_clicked': '右键方块',
    'organ_add_status_effect': '添加状态效果', 'exposure_frame_added': '曝光取景',
    'entity_fall': '摔落', 'villager_update_special_prices': '村民价格更新',
    'shield_block': '盾牌格挡', 'player_dodge': '闪避',
    'entity_death': '死亡', 'key_active': '主动技能',
    'organ_take_off': '摘除器官', 'organ_take_on': '装上器官',
}

# ---------- 材质索引 ----------
tex_index = {}
for p in TEX_DIR.rglob('*.png'):
    key = p.stem
    tex_index.setdefault(key, []).append(p)
for k, v in tex_index.items():
    v.sort(key=lambda p: (len(p.parts), str(p)))

def texture_for(organ_path):
    stem = organ_path.split(':')[-1]
    hits = tex_index.get(stem)
    if not hits:
        return None
    rel = hits[0].relative_to(PACK / 'kubejs/assets/kubejs')
    return 'mc/' + rel.as_posix()

# ---------- 解析器官注册 ----------
def chain_of(text, start):
    """从 start 位置读到第一个不以 . 开头的行，返回该语句文本"""
    end = len(text)
    pos = start
    lines = text[start:].split('\n')
    consumed = 0
    for line in lines:
        stripped = line.strip()
        if consumed > 0 and stripped and not stripped.startswith('.') and not stripped.startswith('//'):
            break
        consumed += len(line) + 1
        pos = start + consumed
    return text[start:pos]

organs = {}
for js in sorted(JS_DIR.rglob('*.js')):
    src = js.read_text(encoding='utf-8')
    for m in re.finditer(r"RegistryOrgan\(\s*'([^']+)'\s*\)", src):
        oid = m.group(1)
        chain = chain_of(src, m.end() - 1)
        rec = organs.setdefault(oid, {'id': oid, 'scores': {}, 'rank': 0, 'canSpawn': False, 'events': []})
        for sm in re.finditer(r"\.addScore\(\s*'([^']+)'\s*,\s*(-?[\d.]+)\s*\)", chain):
            rec['scores'][sm.group(1)] = float(sm.group(2))
        rm = re.search(r"\.setRank\(\s*(-?\d+)\s*\)", chain)
        if rm:
            rec['rank'] = int(rm.group(1))
        if re.search(r"\.setCanSpawn\(\s*true\s*\)", chain):
            rec['canSpawn'] = True

# ---------- 解析策略（事件触发） ----------
strategy_re = re.compile(r"RegistryOrganStrategy\(\s*new\s+OrganStrategyModel\(\s*'([^']+)'\s*\)(.*?)\)\s*\n\)", re.S)
for js in sorted(JS_DIR.rglob('*.js')):
    src = js.read_text(encoding='utf-8')
    for m in strategy_re.finditer(src):
        oid, body = m.group(1), m.group(2)
        rec = organs.setdefault(oid, {'id': oid, 'scores': {}, 'rank': 0, 'canSpawn': False, 'events': []})
        for em in re.finditer(r"\.add(Only)?Strategy\(\s*'([^']+)'", body):
            mode = 'only' if em.group(1) else 'all'
            ev = em.group(2)
            if ev in ('chest_cavity_update', 'organ_take_off', 'organ_take_on'):
                continue  # 装备期回调，不算可触发效果
            rec['events'].append({'event': ev, 'mode': mode})
        rec['events'] = [dict(t) for t in {tuple(sorted(e.items())) for e in rec['events']}]

# ---------- 名称与 tooltip ----------
def lang_get(k, default=None):
    return lang.get(k, default)

out_organs = []
for oid, rec in organs.items():
    path = oid.split(':')[-1]
    name = lang_get(f'item.kubejs.{path}', path)
    obtain = lang_get(f'gui.chestcavity.organ_holo.obtain.{oid}', '')
    flavor, effects = [], []
    i = 1
    while True:
        v = lang_get(f'tooltips.kubejs.{path}.default.{i}')
        if v is None:
            break
        flavor.append(v)
        i += 1
    i = 1
    while True:
        v = lang_get(f'tooltips.kubejs.{path}.alt.{i}')
        if v is None:
            break
        effects.append(v)
        i += 1
    group = 'misc'
    for js in JS_DIR.rglob(f'{path}.js'):
        rel = js.relative_to(JS_DIR).parts
        group = rel[0] if len(rel) > 1 else 'misc'
        break
    out_organs.append({
        'id': oid,
        'path': path,
        'name': name,
        'group': group,
        'texture': texture_for(oid),
        'rank': rec['rank'],
        'canSpawn': rec['canSpawn'],
        'scores': rec['scores'],
        'events': rec['events'],
        'obtain': obtain,
        'flavor': flavor,
        'effects': effects,
    })

out_organs.sort(key=lambda o: (o['group'], o['id']))

# ---------- 分数表 ----------
scores = {}
for k, v in lang.items():
    if k.startswith('tooltips.organ_score.hover.'):
        sid = k[len('tooltips.organ_score.hover.'):]
        scores.setdefault(sid, {})['desc'] = v
    elif k.startswith('tooltips.organ_score.') and not k.startswith('tooltips.organ_score.hover.'):
        sid = k[len('tooltips.organ_score.'):]
        scores.setdefault(sid, {})['name'] = v

# ---------- 胸腔类型与槽位 ----------
BUNDLE_TEX = PACK / 'kubejs/assets'
GUI_OUT = OUT.parent / 'mc/gui'

def resolve_bg(tex):
    """把 kubejs:textures/gui/x.png 解析成包内文件，并复制到站点的 mc/gui/"""
    if not tex or ':' not in tex:
        return ''
    ns, rest = tex.split(':', 1)
    src = BUNDLE_TEX / ns / rest
    if not src.exists():
        alt = Path('D:/hermes-workspace/ribcage-ws/chestcavity/src/main/resources/assets') / ns / rest
        if not alt.exists():
            alt = Path('D:/hermes-workspace/ribcage-ws/chestcavity/src/main/resources/assets/chestcavity/textures/gui') / Path(rest).name
        src = alt if alt.exists() else src
    if not src.exists():
        return ''
    GUI_OUT.mkdir(parents=True, exist_ok=True)
    dst = GUI_OUT / f'{ns}_{src.stem}.png'
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        dst.write_bytes(src.read_bytes())
    try:
        from PIL import Image
        w, h = Image.open(dst).size
    except Exception:
        w = h = 0
    return f'mc/gui/{dst.name}', w, h

inv_types = {}
for p in sorted(INV_DIR.glob('*.json')):
    d = json.load(open(p, encoding='utf-8'))
    size = d.get('backgroundSize') or {'x': 176, 'y': 166}
    bg_path, bg_w, bg_h = resolve_bg(d.get('backgroundTexture', '')) or ('', 0, 0)
    inv_types['kubejs:' + p.stem] = {
        'id': 'kubejs:' + p.stem,
        'slots': d.get('slotDefinitions', []),
        'bg': bg_path,
        'texW': bg_w,
        'texH': bg_h,
        'size': size,
        'playerInv': d.get('playerInventoryPosition') or {'x': 0, 'y': 0},
    }

SPECIAL_CAVITY = {
    'player': '玩家', 'functional_entity': '功能实体', 'default': '默认',
    'rel:с': '', 'relics': '遗物', 'relics_awakening': '遗物·觉醒',
}
CAVITY_GROUPS = {
    'animals': '动物', 'biomancy': '生物术', 'ender': '末影', 'golem': '傀儡',
    'nether': '下界', 'relics': '遗物', 'undead': '亡灵', 'base': '基础',
}
cavities = []
for p in sorted(TYPE_DIR.rglob('*.json')):
    d = json.load(open(p, encoding='utf-8'))
    cid = 'kubejs:' + p.stem
    cname = (SPECIAL_CAVITY.get(p.stem)
             or mc_lang.get(f'entity.minecraft.{p.stem}')
             or MOD_ENTITY.get(p.stem)
             or lang_get(f'entity.minecraft.{p.stem}')
             or lang_get(f'entity.kubejs.{p.stem}')
             or p.stem)
    cavities.append({
        'id': cid,
        'name': cname,
        'group': CAVITY_GROUPS.get(p.parent.name if p.parent != TYPE_DIR else 'base',
                                    p.parent.name if p.parent != TYPE_DIR else 'base'),
        'inventoryType': d.get('inventoryType'),
        'baseOrganScores': d.get('baseOrganScores') or [],
        'defaultOrgans': [{'pos': e['position'], 'item': e['item']} for e in d.get('defaultChestCavity', [])],
    })
cavities.sort(key=lambda c: (c['group'], c['id']))

# 用 cc_types 回填槽位布局的名称、默认器官与基础分数（构筑页以槽位布局为单位）
by_inv = {}
for c in cavities:
    by_inv.setdefault(c['inventoryType'], []).append(c)
for iid, it in inv_types.items():
    users = by_inv.get(iid, [])
    it['usedBy'] = [c['id'] for c in users]
    rep = users[0] if users else None
    it['defaultOrgans'] = rep['defaultOrgans'] if rep else []
    it['baseScores'] = rep['baseOrganScores'] if rep else []
    stem = iid.split(':')[-1]
    label = (mc_lang.get(f'entity.minecraft.{stem}') or MOD_ENTITY.get(stem) or stem)
    if rep and rep['name'] and rep['name'] != stem:
        label = rep['name']
    it['name'] = f"{label} · {len(it['slots'])} 格"

events = {}
for o in out_organs:
    for e in o['events']:
        events.setdefault(e['event'], []).append(o['id'])
events_out = {k: {'name': EVENT_NAMES.get(k, k), 'organs': sorted(v)} for k, v in sorted(events.items())}

json.dump(out_organs, open(OUT / 'organs.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(scores, open(OUT / 'scores.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(cavities, open(OUT / 'cavities.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(inv_types, open(OUT / 'inventory_types.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(events_out, open(OUT / 'events.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

print('organs', len(out_organs),
      '| with texture', sum(1 for o in out_organs if o['texture']),
      '| with effects', sum(1 for o in out_organs if o['effects']),
      '| with events', sum(1 for o in out_organs if o['events']))
print('scores', len(scores), 'cavities', len(cavities), 'inv types', len(inv_types), 'events', len(events_out))
print('sample:', json.dumps(out_organs[0], ensure_ascii=False)[:300])
