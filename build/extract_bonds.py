"""从 RibCage 脚本与语言文件提取器官羁绊（tag 效果）数据。"""

import json
import re
from pathlib import Path

PACK = Path("D:/hermes-workspace/ribcage-ws/RibCage/kubejs")
STARTUP = PACK / "startup_scripts/item/organ"
TAG_EFFECT = PACK / "server_scripts/domain/organ/tag_effect"
LANG = PACK / "assets/kubejs/lang/zh_cn.json"
OUT = Path("D:/SelfAgent/work/organ-codex/site/data/bonds.json")

CREATE_RE = re.compile(r"event\.create\('([^']+)'\)(.*)")
TAG_RE = re.compile(r"\.tag\('(kubejs:[a-z_]+)'\)")
STRATEGY_RE = re.compile(r"\.addStrategy\('([a-z_]+)'")
EVENT_CN = {
    "chest_cavity_update": "胸腔变化时",
    "food_eaten": "食用食物时",
    "mob_effect_applicable": "获得状态效果时",
}


def organ_tags():
    mapping = {}
    pattern = re.compile(r"event\.create\('([^']+)'\)(.*?)(?=\n\s*event\.create|\n\s*\}\)|\Z)", re.S)
    for path in sorted(STARTUP.rglob("*.js")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in pattern.finditer(text):
            tags = TAG_RE.findall(m.group(2))
            if tags:
                mapping[m.group(1)] = tags
    return mapping


def tag_effects():
    result = {}
    for path in sorted(TAG_EFFECT.glob("*.js")):
        text = path.read_text(encoding="utf-8", errors="replace")
        tag_m = re.search(r"new TagStrategyModel\('(kubejs:[a-z_]+)'\)", text)
        if not tag_m:
            continue
        tag = tag_m.group(1)
        result[tag] = {
            "events": sorted(set(STRATEGY_RE.findall(text))),
            "source": path.name,
        }
    return result


def main() -> None:
    lang = json.loads(LANG.read_text(encoding="utf-8"))
    names = {}
    thresholds = {}
    for key, value in lang.items():
        m = re.fullmatch(r"tooltips\.kubejs\.tag\.(kubejs:[a-z_]+)", key)
        if m:
            names[m.group(1)] = value
            continue
        m = re.fullmatch(r"tooltips\.kubejs\.overlay\.(kubejs:[a-z_]+)\.(\d+)", key)
        if m:
            thresholds.setdefault(m.group(1), []).append((int(m.group(2)), value))

    by_tag = {}
    for item_id, tags in organ_tags().items():
        for tag in tags:
            by_tag.setdefault(tag, []).append(item_id)

    bonds = []
    for tag, info in sorted(tag_effects().items()):
        organs = sorted(by_tag.get(tag, []))
        if not organs:
            continue
        bonds.append({
            "tag": tag,
            "name": names.get(tag, tag.split(":")[1]),
            "events": [EVENT_CN.get(e, e) for e in info["events"]],
            "thresholds": [
                {"count": count, "text": text}
                for count, text in sorted(thresholds.get(tag, []))
            ],
            "organs": organs,
        })

    bonds.sort(key=lambda b: (b["thresholds"][0]["count"] if b["thresholds"] else 999, b["name"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bonds, ensure_ascii=False, indent=1), encoding="utf-8")
    for bond in bonds:
        print(bond["tag"], bond["name"], len(bond["organs"]), len(bond["thresholds"]), bond["events"])


if __name__ == "__main__":
    main()
