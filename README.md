# RibCage Organ Book / 构筑器

No Flesh Within Chest 2 的器官静态站，纯前端（原生 HTML/CSS/JS），无框架、无后端、无外部依赖。

在线地址：https://yorunina.github.io/ribcage-organ-book/

## 功能

- **图鉴**：浏览 327 个器官；按名称、id、效果文本搜索；按分类 / 稀有度 / 触发事件 / 属性筛选；详情面板还原游戏内 tooltip（含 § 颜色码、分数、获取方式）。
- **构筑**：覆盖 163 种胸腔类型与其槽位布局；点击槽位选器官；实时合计属性；导出 / 导入分享码（JSON → base64url）。

## 数据来源与边界

| 数据 | 来源 |
|---|---|
| 器官注册、分数、稀有度、可刷出 | `kubejs/server_scripts/domain/organ/organ/**/*.js` 的 `RegistryOrgan(...)` |
| 器官触发事件 | 同目录 `RegistryOrganStrategy(... .addStrategy/.addOnlyStrategy)` |
| tooltip 文本 | `kubejs/assets/kubejs/lang/zh_cn.json` |
| 胸腔类型 / 槽位 / GUI 底图 | `kubejs/data/kubejs/cc_types`、`cc_inventory_types`；底图取自 `kubejs/assets/kubejs/textures/gui/chest_cavity` |
| 材质 | `kubejs/assets/kubejs/textures/item/organs/**` |

tooltip 里的 `%s` 运行时占位符已按器官策略函数补齐：能定位到常量（概率、时长、系数、分数名）的直接填值，
逻辑复杂的改写成一句逻辑描述；原始行保留在 `effects`，补齐行在 `effectsResolved`。

只能近似、不能精确复现的部分：

- tooltip 中由代码运行期拼出的行、`%s` 数值占位；

## 重新生成数据

```bash
python build/extract_organs.py          # 需要先设置脚本顶部的 PACK 路径
```

```bash
python build/build_atlas.py             # 把所有器官材质打成一张图集 site/mc/atlas.png
```

材质以图集形式提供：319 个 16×16 器官图标合成单张 320×256 PNG，页面用背景定位显示，只需一次请求。

胸腔 GUI 底图随提取脚本一起复制到 `site/mc/gui/`。槽位坐标与底图是 1:1 的 GUI 像素，槽位内格 16×16，构筑页按同一比例缩放底图与槽位。

## 本地预览

```bash
cd site && python -m http.server 8765
```

## 结构

```
site/
  index.html   style.css   app.js
  data/        organs.json scores.json cavities.json inventory_types.json events.json
  mc/          器官材质（原始 16×16，pixelated 渲染）
build/extract_organs.py
```
