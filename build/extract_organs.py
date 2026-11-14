"""从 RibCage 仓库提取器官图鉴数据，输出静态站用的 JSON。"""
import json
import re
import zipfile
from pathlib import Path

from PIL import Image

PACK = Path('D:/hermes-workspace/ribcage-ws/RibCage')
OUT = Path('D:/SelfAgent/work/organ-codex/site/data')
REPORT = OUT.parent.parent / 'build/organ_validation.json'
OUT.mkdir(parents=True, exist_ok=True)

JS_DIR = PACK / 'kubejs/server_scripts/domain/organ/organ'
ASSET_DIR = PACK / 'kubejs/assets'
TEX_DIR = ASSET_DIR / 'kubejs/textures/item/organs'
MODEL_DIR = ASSET_DIR / 'kubejs/models/item'
SITE_GEN = OUT.parent / 'mc/generated'
LANG = ASSET_DIR / 'kubejs/lang/zh_cn.json'
CLIENT_DIR = PACK / 'kubejs/client_scripts'
INV_DIR = PACK / 'kubejs/data/kubejs/cc_inventory_types'
TYPE_DIR = PACK / 'kubejs/data/kubejs/cc_types'
MODS_DIR = PACK / 'mods'

lang = json.load(open(LANG, encoding='utf-8'))
PREV_ORGANS = {}
prev_path = OUT / 'organs.json'
if prev_path.exists():
    try:
        PREV_ORGANS = {o['id']: o for o in json.load(open(prev_path, encoding='utf-8'))}
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        PREV_ORGANS = {}
MC_LANG = Path('D:/SelfAgent/work/organ-codex/build/mc_zh_cn.json')
mc_lang = json.load(open(MC_LANG, encoding='utf-8')) if MC_LANG.exists() else {}
MOD_ENTITY = {}
for lp in ASSET_DIR.rglob('lang/zh_cn.json'):
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
    tex_index.setdefault(p.stem, []).append(p)
for hits in tex_index.values():
    hits.sort(key=lambda p: (len(p.parts), str(p)))

jar_index = {}
for jar in sorted(MODS_DIR.glob('*.jar')):
    try:
        with zipfile.ZipFile(jar) as archive:
            for name in archive.namelist():
                if name.startswith('assets/'):
                    jar_index.setdefault(name, []).append(jar)
    except (OSError, zipfile.BadZipFile):
        continue


def copy_pack_asset(path):
    asset_rel = path.relative_to(ASSET_DIR)
    rel = Path(*asset_rel.parts[1:]) if asset_rel.parts[0] == 'kubejs' else asset_rel
    out = OUT.parent / 'mc' / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(path.read_bytes())
    return f'mc/{rel.as_posix()}', f'{asset_rel.parts[0]}/assets/{Path(*asset_rel.parts[1:]).as_posix()}'


def copy_jar_asset(jar, asset_name, raw):
    rel = Path(asset_name).relative_to('assets')
    out = SITE_GEN / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    return f'mc/generated/{rel.as_posix()}', f'{jar.name}!{asset_name}'


def jar_bytes(asset_name):
    for jar in jar_index.get(asset_name, []):
        try:
            with zipfile.ZipFile(jar) as archive:
                return jar, archive.read(asset_name)
        except (OSError, KeyError, zipfile.BadZipFile):
            continue
    return None, None


def frame_assets(path):
    frames = [path]
    i = 1
    while True:
        candidate = path.with_name(f'{path.stem}_{i}{path.suffix}')
        if not candidate.exists():
            break
        frames.append(candidate)
        i += 1
    return frames


def pack_texture_info(path):
    urls, sources = [], []
    for frame in frame_assets(path):
        url, source = copy_pack_asset(frame)
        urls.append(url)
        sources.append(source)
    with Image.open(path) as image:
        mode = 'animated' if image.height > image.width else 'raw'
    return {
        'textureUrl': urls[0], 'textureSource': sources[0],
        'textureFiles': urls, 'textureMode': mode,
    }


def asset_ref(ref, default_ns):
    ref = str(ref).split('#', 1)[0]
    if ':' in ref:
        ns, rest = ref.split(':', 1)
    else:
        ns, rest = default_ns, ref
    rest = rest.lstrip('/')
    if not rest.startswith('textures/'):
        rest = 'textures/' + rest
    if not rest.endswith('.png'):
        rest += '.png'
    return ns, rest


def model_candidates(ns, stem):
    candidates = [(MODEL_DIR / f'{stem}_model.json', 'pack'), (MODEL_DIR / f'{stem}.json', 'pack')]
    for path in MODEL_DIR.glob('*.json'):
        if path in (c[0] for c in candidates):
            continue
        try:
            if stem in path.read_text(encoding='utf-8'):
                candidates.append((path, 'pack'))
        except OSError:
            continue
    for model_name in (f'assets/{ns}/models/item/{stem}.json',):
        for jar in jar_index.get(model_name, []):
            candidates.append((jar, model_name))
    return candidates


def model_texture_info(ns, stem):
    for model_path, model_source in model_candidates(ns, stem):
        try:
            if model_source == 'pack':
                data = json.loads(model_path.read_text(encoding='utf-8'))
                model_label = f'kubejs/assets/{model_path.relative_to(ASSET_DIR).as_posix()}'
            else:
                with zipfile.ZipFile(model_path) as archive:
                    data = json.loads(archive.read(model_source).decode('utf-8'))
                model_label = f'{model_path.name}!{model_source}'
        except (OSError, KeyError, json.JSONDecodeError, zipfile.BadZipFile):
            continue
        textures = data.get('textures') or {}
        refs = []
        for key in ('layer0', 'base', '1', 'particle'):
            if textures.get(key):
                refs.append(textures[key])
        refs.extend(value for key, value in sorted(textures.items()) if key not in ('layer0', 'base', '1', 'particle'))
        urls, sources = [], []
        for ref in refs:
            ref_ns, rest = asset_ref(ref, ns)
            asset_name = f'assets/{ref_ns}/{rest}'
            pack_path = ASSET_DIR / ref_ns / rest
            if pack_path.exists():
                for frame in frame_assets(pack_path):
                    url, source = copy_pack_asset(frame)
                    if url not in urls:
                        urls.append(url)
                        sources.append(source)
            else:
                jar, raw = jar_bytes(asset_name)
                if jar is None:
                    continue
                prefix = asset_name[:-4]
                names = [name for name in jar_index
                         if name == asset_name or (name.startswith(prefix + '_') and name.endswith('.png'))]
                for name in sorted(names):
                    frame_jar, frame_raw = jar_bytes(name)
                    if frame_jar is None:
                        continue
                    url, source = copy_jar_asset(frame_jar, name, frame_raw)
                    if url not in urls:
                        urls.append(url)
                        sources.append(source)
        if urls:
            return {
                'textureUrl': urls[0], 'textureSource': f'{model_label} -> {sources[0]}',
                'textureFiles': urls, 'textureMode': 'model',
            }
    return None


def texture_for(organ_path):
    ns, stem = organ_path.split(':', 1)
    hits = tex_index.get(stem, [])
    if hits:
        return pack_texture_info(hits[0])
    model_info = model_texture_info(ns, stem)
    if model_info:
        return model_info
    asset_name = f'assets/{ns}/textures/item/{stem}.png'
    jar, raw = jar_bytes(asset_name)
    if jar is not None:
        urls, sources = [], []
        prefix = f'assets/{ns}/textures/item/{stem}'
        for name in sorted(jar_index):
            if name == asset_name or (name.startswith(prefix + '_') and name.endswith('.png')):
                frame_jar, frame_raw = jar_bytes(name)
                if frame_jar is not None:
                    url, source = copy_jar_asset(frame_jar, name, frame_raw)
                    urls.append(url)
                    sources.append(source)
        return {
            'textureUrl': urls[0], 'textureSource': sources[0],
            'textureFiles': urls, 'textureMode': 'raw',
        }
    return None

# ---------- 激活效果与二级悬浮提示 ----------
CONST_KEYS = {}
key_word = CLIENT_DIR / 'const/key_word.js'
if key_word.exists():
    for m in re.finditer(r"const\s+(\w+)\s*=\s*Text\.translatable\('([^']+)'", key_word.read_text(encoding='utf-8')):
        CONST_KEYS[m.group(1)] = m.group(2)

def hover_marker(const_name):
    key = CONST_KEYS.get(const_name)
    if not key:
        return None
    label = lang.get(key, const_name)
    details = []
    stem = key.rsplit('.', 2)[0]
    i = 1
    while True:
        v = lang.get(f'{stem}.{i}')
        if v is None:
            break
        details.append(v)
        i += 1
    if not details and key.startswith('tooltips.organ_score.'):
        score_key = key[len('tooltips.organ_score.'):]
        desc = lang.get(f'tooltips.organ_score.hover.{score_key}')
        if desc:
            details = [desc]
    if not details:
        return None
    return {'label': label, 'details': details}

def resolve_tooltip_expr(expr):
    expr = expr.strip()
    marker = hover_marker(expr)
    if marker:
        return marker['label'], marker
    if expr in CONST_KEYS:
        return lang.get(CONST_KEYS[expr], expr), None
    m = re.search(r"Text\.translatable\('([^']+)'(.*)\)", expr)
    if not m:
        return expr, None
    key, args = m.group(1), m.group(2)
    text = lang.get(key, key)
    values = []
    for a in re.findall(r"Text\.gold\('([^']*)'\)|Text\.yellow\('([^']*)'\)|\b([A-Z]\w*Hover)\b", args):
        literal = a[0] or a[1]
        if literal:
            values.append(literal)
        else:
            hm = hover_marker(a[2])
            if hm:
                values.append(f"[[{hm['label']}|{'\\n'.join(hm['details'])}]]")
            else:
                values.append(lang.get(CONST_KEYS.get(a[2], ''), a[2]))
    for value in values:
        text = text.replace('%s', value, 1)
    return text, None

def activation_for(oid):
    result = []
    for js in sorted((CLIENT_DIR / 'tooltips/organ').glob('*.js')):
        active = False
        for line in js.read_text(encoding='utf-8').splitlines():
            m = re.search(r"new MultiStateTooltip\('([^']+)'", line)
            if m:
                active = m.group(1) == oid
                continue
            if active and re.match(r'\s*\)\s*$', line):
                active = False
            if active:
                m = re.search(r'\.addCtrl\((.*)\)', line)
                if not m:
                    continue
                text, hover = resolve_tooltip_expr(m.group(1))
                if text.startswith('RelicsOrganScoreTooltips'):
                    text = '遗物属性激活效果（游戏内按遗物属性展开）'
                    hover = None
                result.append({'text': text, 'hover': hover})
    return result

# ---------- 解析器官注册 ----------
def new_record(oid):
    return {'id': oid, 'scores': {}, 'rank': 0, 'canSpawn': False, 'events': [],
            'sourceFile': None, 'sourceGroup': None, 'sourceFiles': []}


def chain_of(text, start):
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
source_warnings = []
for js in sorted(JS_DIR.rglob('*.js')):
    src = js.read_text(encoding='utf-8')
    source_file = js.relative_to(JS_DIR).as_posix()
    source_group = Path(source_file).parts[0]
    for m in re.finditer(r"RegistryOrgan\(\s*'([^']+)'\s*\)", src):
        oid = m.group(1)
        if oid == 'kubejs:test':
            continue
        chain = chain_of(src, m.end() - 1)
        rec = organs.setdefault(oid, new_record(oid))
        if source_file not in rec['sourceFiles']:
            rec['sourceFiles'].append(source_file)
        if rec['sourceFile'] and rec['sourceFile'] != source_file:
            source_warnings.append(f'{oid}: multiple registration files: {rec["sourceFile"]}, {source_file}')
        else:
            rec['sourceFile'] = source_file
            rec['sourceGroup'] = source_group
        for sm in re.finditer(r"\.addScore\(\s*'([^']+)'\s*,\s*(-?[\d.]+)\s*\)", chain):
            rec['scores'][sm.group(1)] = float(sm.group(2))
        rm = re.search(r"\.setRank\(\s*(-?\d+)\s*\)", chain)
        if rm:
            rec['rank'] = int(rm.group(1))
        if re.search(r"\.setCanSpawn\(\s*true\s*\)", chain):
            rec['canSpawn'] = True

# ---------- 动态器官注册 ----------
giant_js = JS_DIR / 'nature/giant_organs.js'
if giant_js.exists():
    source_file = giant_js.relative_to(JS_DIR).as_posix()
    for line in giant_js.read_text(encoding='utf-8').splitlines():
        m = re.match(r"\s*(\w+):\s*(\[.*\]),?\s*$", line)
        if not m:
            continue
        oid = 'kubejs:giant_' + m.group(1)
        scores = {
            score: float(value)
            for score, value in re.findall(r"\['([^']+)',\s*(-?[\d.]+)\]", m.group(2))
        }
        rec = organs.setdefault(oid, new_record(oid))
        rec.update({'scores': scores, 'sourceFile': source_file, 'sourceGroup': 'nature'})
        rec['sourceFiles'] = [source_file]

# ---------- 解析策略（事件触发） ----------
strategy_re = re.compile(r"RegistryOrganStrategy\(\s*new\s+OrganStrategyModel\(\s*'([^']+)'\s*\)(.*?)\)\s*\n\)", re.S)
for js in sorted(JS_DIR.rglob('*.js')):
    src = js.read_text(encoding='utf-8')
    for m in strategy_re.finditer(src):
        oid, body = m.group(1), m.group(2)
        rec = organs.setdefault(oid, new_record(oid))
        for em in re.finditer(r"\.add(Only)?Strategy\(\s*'([^']+)'", body):
            mode = 'only' if em.group(1) else 'all'
            ev = em.group(2)
            if ev in ('chest_cavity_update', 'organ_take_off', 'organ_take_on'):
                continue
            rec['events'].append({'event': ev, 'mode': mode})
        rec['events'] = [dict(t) for t in {tuple(sorted(e.items())) for e in rec['events']}]

# ---------- 名称与 tooltip ----------
def lang_get(k, default=None):
    return lang.get(k, default)

out_organs = []
validation_warnings = list(source_warnings)
validation_errors = []
placeholder_organs = []
known_groups = {'nature', 'ender', 'nether', 'factory', 'machine', 'magic', 'food', 'infected', 'plants', 'relics', 'rose', 'legend'}

for oid, rec in organs.items():
    ns, path = oid.split(':', 1)
    name_key = f'item.{ns}.{path}'
    name = lang_get(name_key, path)
    obtain_key = f'gui.chestcavity.organ_holo.obtain.{oid}'
    obtain = lang_get(obtain_key, '')
    flavor, flavor_keys, effects, effect_keys = [], [], [], []
    i = 1
    while True:
        key = f'tooltips.kubejs.{path}.default.{i}'
        v = lang_get(key)
        if v is None and path.startswith('giant_'):
            key = f'tooltips.kubejs.giant_organ.default.{i}'
            v = lang_get(key)
        if v is None:
            break
        flavor.append(v)
        flavor_keys.append(key)
        i += 1
    i = 1
    while True:
        key = f'tooltips.kubejs.{path}.alt.{i}'
        v = lang_get(key)
        if v is None:
            break
        effects.append(v)
        effect_keys.append(key)
        i += 1
    if ns == 'kubejs' and name_key not in lang:
        validation_warnings.append(f'{oid}: missing lang key {name_key}')
    raw_tooltip = flavor + effects
    raw_placeholders = sum(text.count('%s') for text in raw_tooltip)
    if raw_placeholders:
        placeholder_organs.append(oid)
    source_file = rec.get('sourceFile')
    source_group = rec.get('sourceGroup')
    if not source_file:
        validation_errors.append(f'{oid}: no RegistryOrgan source file')
        group = 'unknown'
    elif source_group not in known_groups:
        validation_errors.append(f'{oid}: unknown source group {source_group!r} from {source_file}')
        group = 'unknown'
    else:
        group = source_group
    texture_info = texture_for(oid)
    if not texture_info:
        validation_warnings.append(f'{oid}: no direct texture or model texture found')
        texture_info = {'textureUrl': None, 'textureSource': None, 'textureFiles': [], 'textureMode': None}
    else:
        for texture_url in texture_info['textureFiles']:
            if not (OUT.parent / texture_url).exists():
                validation_errors.append(f'{oid}: copied texture missing at {texture_url}')
    item = {
        'id': oid,
        'path': path,
        'name': name,
        'group': group,
        'sourceFile': source_file,
        'sourceGroup': source_group,
        'sourceFiles': rec.get('sourceFiles', []),
        'nameKey': name_key,
        'obtainKey': obtain_key,
        'tooltipKeys': flavor_keys + effect_keys,
        'placeholderCount': raw_placeholders,
        'texture': texture_info['textureUrl'],
        **texture_info,
        'rank': rec['rank'],
        'canSpawn': rec['canSpawn'],
        'scores': rec['scores'],
        'events': rec['events'],
        'obtain': obtain,
        'flavor': flavor,
        'effects': effects,
        'activationEffects': activation_for(oid),
        'slotEffects': [],
    }
    previous = PREV_ORGANS.get(oid, {}).get('effectsResolved')
    if isinstance(previous, list) and len(previous) == len(effects):
        item['effectsResolved'] = previous
    resolved_tooltip = item.get('effectsResolved', effects)
    if any('%s' in text for text in resolved_tooltip):
        validation_warnings.append(f'{oid}: unresolved tooltip placeholder remains after extraction')
    out_organs.append(item)

out_organs.sort(key=lambda o: (-o['rank'], o['group'], o['id']))

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

INVENTORY_LABELS = {
    'medium_aquatic': '水生胸腔', 'medium_ender': '末影胸腔',
    'medium_golem': '傀儡胸腔', 'medium_nether': '下界胸腔',
    'medium_terra': '自然胸腔', 'medium_undead': '亡灵胸腔',
    'medium_vita': '血肉胸腔', 'small_aquatic': '小型水生胸腔',
    'small_ender': '小型末影胸腔', 'small_golem': '小型傀儡胸腔',
    'small_nether': '小型下界胸腔', 'small_terra': '小型自然胸腔',
    'small_undead': '小型亡灵胸腔', 'small_vita': '小型血肉胸腔',
    'large_golem': '大型傀儡胸腔',
}

CAVITY_LABELS = {
    'aquatic': '水生', 'default': '默认', 'ender': '末影', 'factory': '工厂',
    'functional_entity': '功能实体', 'gula': '暴食', 'large_golem': '大型傀儡',
    'plant': '植物', 'relics': '遗物', 'relics_awakening': '遗物·觉醒',
    'revolution_machine': '革命机器', 'rose': '玫瑰',
    'transdimensional_mechanized': '跨维度机械', 'transdimensional_plant': '跨维度植物',
    'transdimensional_relics': '跨维度遗物', 'transdimensional_rose': '跨维度玫瑰',
    'player_17': '玩家·17格', 'player_21': '玩家·21格', 'player_25': '玩家·25格',
    'player_27': '玩家·27格',
}

def cavity_label(stem, fallback=''):
    return (lang_get(f'tooltips.kubejs.hover.{stem}_type.0')
            or CAVITY_LABELS.get(stem)
            or fallback
            or stem)

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
    cname = cavity_label(p.stem, SPECIAL_CAVITY.get(p.stem)
                         or mc_lang.get(f'entity.minecraft.{p.stem}')
                         or MOD_ENTITY.get(p.stem)
                         or lang_get(f'entity.minecraft.{p.stem}')
                         or lang_get(f'entity.kubejs.{p.stem}'))
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
    label = INVENTORY_LABELS.get(stem) or cavity_label(stem, mc_lang.get(f'entity.minecraft.{stem}') or MOD_ENTITY.get(stem))
    it['name'] = f"{label} · {len(it['slots'])} 格"

events = {}
for o in out_organs:
    for e in o['events']:
        events.setdefault(e['event'], []).append(o['id'])
events_out = {k: {'name': EVENT_NAMES.get(k, k), 'organs': sorted(v)} for k, v in sorted(events.items())}
slot_types = {}
for key, value in lang.items():
    match = re.fullmatch(r'slot_type\.chestcavity\.([^.]*)\.(name|desc)', key)
    if match:
        slot_types.setdefault(match.group(1), {})[match.group(2)] = value.strip()

json.dump(out_organs, open(OUT / 'organs.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(scores, open(OUT / 'scores.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(cavities, open(OUT / 'cavities.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(inv_types, open(OUT / 'inventory_types.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(slot_types, open(OUT / 'slot_types.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(events_out, open(OUT / 'events.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

print('organs', len(out_organs),
      '| with texture', sum(1 for o in out_organs if o['texture']),
      '| with effects', sum(1 for o in out_organs if o['effects']),
      '| with events', sum(1 for o in out_organs if o['events']))
print('scores', len(scores), 'cavities', len(cavities), 'inv types', len(inv_types), 'events', len(events_out))
print('textures', sum(1 for o in out_organs if o['textureUrl']),
      '| raw', sum(1 for o in out_organs if o['textureMode'] == 'raw'),
      '| model', sum(1 for o in out_organs if o['textureMode'] == 'model'),
      '| missing', sum(1 for o in out_organs if not o['textureUrl']))
print('tooltip placeholders', len(placeholder_organs), 'organs', sum(o['placeholderCount'] for o in out_organs))
validation = {
    'organs': len(out_organs),
    'warnings': validation_warnings,
    'errors': validation_errors,
    'counts': {
        'withTexture': sum(1 for o in out_organs if o['textureUrl']),
        'missingTexture': sum(1 for o in out_organs if not o['textureUrl']),
        'withSource': sum(1 for o in out_organs if o['sourceFile']),
        'withTooltipKeys': sum(1 for o in out_organs if o['tooltipKeys']),
        'placeholderCount': sum(o['placeholderCount'] for o in out_organs),
        'placeholderOrganCount': len(placeholder_organs),
    },
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding='utf-8')
for message in validation_warnings:
    print('WARNING:', message)
for message in validation_errors:
    print('ERROR:', message)
if validation_errors:
    raise SystemExit(1)
print('validation', REPORT, 'warnings', len(validation_warnings), 'errors', len(validation_errors))
print('sample:', json.dumps(out_organs[0], ensure_ascii=False)[:300])
