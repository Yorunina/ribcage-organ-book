# RibCage 器官图鉴 / 构筑器 / 事件推演

No Flesh Within Chest 2 的器官静态站，纯前端（原生 HTML/CSS/JS），无框架、无后端、无外部依赖。

在线地址：https://yorunina.github.io/ribcage-organ-codex/

## 功能

- **图鉴**：浏览 327 个器官；按名称、id、效果文本搜索；按分类 / 稀有度 / 触发事件 / 属性筛选；详情面板还原游戏内 tooltip（含 § 颜色码、分数、获取方式）。
- **构筑**：覆盖 163 种胸腔类型与其槽位布局；点击槽位选器官；实时合计属性；导出 / 导入分享码（JSON → base64url）。
- **事件推演**：伪造事件，按槽位顺序列出响应的器官及其效果文本；伤害类事件给出基于器官分数的近似数值。

## 数据来源与边界

| 数据 | 来源 |
|---|---|
| 器官注册、分数、稀有度、可刷出 | `kubejs/server_scripts/domain/organ/organ/**/*.js` 的 `RegistryOrgan(...)` |
| 器官触发事件 | 同目录 `RegistryOrganStrategy(... .addStrategy/.addOnlyStrategy)` |
| tooltip 文本 | `kubejs/assets/kubejs/lang/zh_cn.json` |
| 胸腔类型 / 槽位 | `kubejs/data/kubejs/cc_types`、`cc_inventory_types` |
| 材质 | `kubejs/assets/kubejs/textures/item/organs/**` |

只能近似、不能精确复现的部分：

- tooltip 中由代码运行期拼出的行、`%s` 数值占位；
- 事件推演的数值：浏览器无法执行 KubeJS 器官策略（那些函数直接调用 Java API），面板数值是按器官分数线性推演的示意值，不等同游戏内结算结果。

## 重新生成数据

```bash
python build/extract_organs.py          # 需要先设置脚本顶部的 PACK 路径
```

脚本会输出 `site/data/*.json`，材质需一并复制到 `site/mc/`（脚本不处理材质拷贝）。

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
