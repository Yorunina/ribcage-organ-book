'use strict';

const state = {
  organs: [], scores: {}, cavities: [], invTypes: {}, events: {}, bonds: [], bondTags: new Map(), atlas: { cols: 20, rows: 16, map: {} },
  organById: new Map(),
  filters: { q: '', group: '', rank: '', event: '', score: '' },
  cavityId: 'kubejs:player_17',
  build: {},           // slotIndex -> organId
  selected: null,
  page: 0,
};

const PAGE_SIZE = 60;

const DATA_V = '16';   // 数据/底图版本：重新生成数据或改底图后递增，绕过 CDN 缓存

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

const GROUPS = {
  nature: '自然', ender: '末影', nether: '下界', factory: '工厂', machine: '机械',
  magic: '魔法', food: '食物', infected: '感染', plants: '植物', relics: '遗物',
  rose: '蔷薇', legend: '传说', misc: '其它',
};

/* ---------- § 颜色码 ---------- */
const MC_COLORS = {
  '0': '#000', '1': '#0000aa', '2': '#00aa00', '3': '#00aaaa', '4': '#aa0000',
  '5': '#aa00aa', '6': '#ffaa00', '7': '#aaaaaa', '8': '#555555', '9': '#5555ff',
  a: '#55ff55', b: '#55ffff', c: '#ff5555', d: '#ff55ff', e: '#ffff55', f: '#ffffff',
};

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

function colorize(text) {
  const out = [];
  let style = {};
  const push = (str) => {
    if (!str) return;
    const css = [];
    if (style.color) css.push(`color:${style.color}`);
    if (style.bold) css.push('font-weight:600');
    if (style.italic) css.push('font-style:italic');
    out.push(css.length ? `<span style="${css.join(';')}">${esc(str)}</span>` : esc(str));
  };
  const re = /§([0-9a-fklmnor])/gi;
  let last = 0, m;
  while ((m = re.exec(text))) {
    push(text.slice(last, m.index));
    const c = m[1].toLowerCase();
    if (MC_COLORS[c]) style = { color: MC_COLORS[c] };
    else if (c === 'l') style = { ...style, bold: true };
    else if (c === 'o') style = { ...style, italic: true };
    else if (c === 'r') style = {};
    last = m.index + 2;
  }
  push(text.slice(last));
  return out.join('');
}

function icon(id, size) {
  const pos = state.atlas.map[id];
  if (!pos) return `<i class="ico" style="width:${size}px;height:${size}px"></i>`;
  const scale = state.atlas.cols * size;
  return `<i class="ico" style="width:${size}px;height:${size}px;` +
    `background-size:${scale}px auto;background-position:${-pos[0] * size}px ${-pos[1] * size}px"></i>`;
}

/* ---------- 数据加载 ---------- */
async function boot() {
  const load = (f) => fetch(`./data/${f}?v=${DATA_V}`, { cache: 'no-cache' }).then((r) => r.json());
  const [organs, scores, cavities, invTypes, events, bonds, atlas] = await Promise.all([
    load('organs.json'), load('scores.json'), load('cavities.json'),
    load('inventory_types.json'), load('events.json'), load('bonds.json'), load('atlas.json'),
  ]);
  state.atlas = atlas;
  state.organs = organs;
  state.scores = scores;
  state.cavities = cavities;
  state.invTypes = invTypes;
  state.events = events;
  state.bonds = bonds;
  state.bondTags = new Map();
  bonds.forEach((b) => b.organs.forEach((id) => {
    if (!state.bondTags.has(id)) state.bondTags.set(id, []);
    state.bondTags.get(id).push(b.tag);
  }));
  organs.forEach((o) => state.organById.set(o.id, o));

  initTabs();
  initCodex();
  initBuilder();
  initBonds();
}

function initTabs() {
  $$('.tab').forEach((t) => t.addEventListener('click', () => {
    $$('.tab').forEach((x) => x.setAttribute('aria-selected', String(x === t)));
    $$('.view').forEach((v) => v.classList.toggle('active', v.id === `view-${t.dataset.view}`));
    if (t.dataset.view !== 'codex') $('#detail').classList.remove('open');
  }));
}

/* ---------- 图鉴 ---------- */
function initCodex() {
  const groups = [...new Set(state.organs.map((o) => o.group))].sort(
    (a, b) => (Object.keys(GROUPS).indexOf(a) + 1 || 99) - (Object.keys(GROUPS).indexOf(b) + 1 || 99) || a.localeCompare(b));
  $('#groups').innerHTML = groups.map((g) =>
    `<button class="chip" data-g="${g}" aria-pressed="false">${GROUPS[g] || g}</button>`).join('');
  $('#groups').addEventListener('click', (e) => {
    const b = e.target.closest('.chip');
    if (!b) return;
    const on = b.getAttribute('aria-pressed') === 'true';
    $$('#groups .chip').forEach((x) => x.setAttribute('aria-pressed', 'false'));
    b.setAttribute('aria-pressed', String(!on));
    state.filters.group = on ? '' : b.dataset.g;
    resetPage();
  });

  const ranks = [...new Set(state.organs.map((o) => o.rank))].sort((a, b) => a - b);
  $('#ranks').innerHTML = ranks.map((r) =>
    `<button class="chip" data-r="${r}" aria-pressed="false">R${r}</button>`).join('');
  $('#ranks').addEventListener('click', (e) => {
    const b = e.target.closest('.chip');
    if (!b) return;
    const on = b.getAttribute('aria-pressed') === 'true';
    $$('#ranks .chip').forEach((x) => x.setAttribute('aria-pressed', 'false'));
    b.setAttribute('aria-pressed', String(!on));
    state.filters.rank = on ? '' : b.dataset.r;
    resetPage();
  });

  const evs = Object.entries(state.events).sort((a, b) => b[1].organs.length - a[1].organs.length);
  $('#eventFilter').innerHTML = '<option value="">全部</option>' +
    evs.map(([k, v]) => `<option value="${k}">${esc(v.name)} · ${v.organs.length}</option>`).join('');
  $('#eventFilter').addEventListener('change', (e) => {
    state.filters.event = e.target.value;
    resetPage();
  });

  const scoreIds = [...new Set(state.organs.flatMap((o) => Object.keys(o.scores)))].sort();
  $('#scoreFilter').innerHTML = '<option value="">全部</option>' +
    scoreIds.map((s) => `<option value="${s}">${esc(state.scores[s]?.name || s)}</option>`).join('');
  $('#scoreFilter').addEventListener('change', (e) => {
    state.filters.score = e.target.value;
    renderGrid();
  });

  $('#q').addEventListener('input', (e) => {
    state.filters.q = e.target.value.trim().toLowerCase();
    resetPage();
  });
  $('#grid').addEventListener('click', (e) => {
    const c = e.target.closest('.card');
    if (c) showDetail(c.dataset.id);
  });
  $('#pagePrev').addEventListener('click', () => changePage(-1));
  $('#pageNext').addEventListener('click', () => changePage(1));
  renderGrid();
}

function resetPage() {
  state.page = 0;
  renderGrid();
}

function changePage(delta) {
  const totalPages = Math.max(1, Math.ceil(matched().length / PAGE_SIZE));
  const next = Math.max(0, Math.min(totalPages - 1, state.page + delta));
  if (next === state.page) return;
  state.page = next;
  renderGrid();
  document.querySelector('#grid')?.focus({ preventScroll: true });
}

function matched() {
  const f = state.filters;
  return state.organs.filter((o) => {
    if (f.group && o.group !== f.group) return false;
    if (f.rank !== '' && String(o.rank) !== f.rank) return false;
    if (f.event && !o.events.some((e) => e.event === f.event)) return false;
    if (f.score && !(f.score in o.scores)) return false;
    if (f.q) {
      const hay = (o.name + ' ' + o.path + ' ' + o.effects.join(' ') + ' ' + o.flavor.join(' ')).toLowerCase();
      if (!hay.includes(f.q)) return false;
    }
    return true;
  });
}

function renderGrid() {
  const list = matched();
  $('#count').textContent = `${list.length} 个器官`;
  $('#pageText').textContent = '滚动浏览';
  $('#pagePrev').disabled = true;
  $('#pageNext').disabled = true;
  const html = list.map((o) => `
    <button class="card" data-id="${o.id}">
      ${icon(o.id, 32)}
      <span><span class="n">${esc(o.name)}</span><span class="g">${GROUPS[o.group] || o.group} · R${o.rank}</span></span>
    </button>`).join('');
  $('#grid').innerHTML = html || '<p class="hint">没有匹配的器官。</p>';
}

function showDetail(id) {
  const o = state.organById.get(id);
  if (!o) return;
  const boxes = $('#detail');
  const scoreRows = Object.entries(o.scores).map(([k, v]) => {
    const s = state.scores[k] || {};
    return `<div class="score-row"><span class="muted" title="${esc(s.desc || '')}">${esc(s.name || k)}</span><b>${v > 0 ? '+' : ''}${v}</b></div>`;
  }).join('');
  const evTags = o.events.map((e) =>
    `<span class="tag">${esc(state.events[e.event]?.name || e.event)}${e.mode === 'only' ? ' · 仅' : ''}</span>`).join('');
  boxes.innerHTML = `
    <button class="close" aria-label="关闭">✕</button>
    <div class="detail-head">${icon(o.id, 40)}<h2 class="mc-name">${esc(o.name)}</h2></div>
    <div class="mc-id">${esc(o.id)}</div>
    ${o.flavor.map((t) => `<div class="mc-line flavor">${colorize(t)}</div>`).join('')}
    ${o.effects.length ? `<div class="mc-sep"></div>${(o.effectsResolved || o.effects).map((t) => `<div class="mc-line">${colorize(t)}</div>`).join('')}` : ''}
    ${o.slotEffects?.length ? `<div class="mc-sep"></div><div class="mc-line muted">槽位效果</div>${o.slotEffects.map((t) => `<div class="mc-line">${esc(t)}</div>`).join('')}` : ''}
    ${scoreRows ? `<div class="mc-sep"></div>${scoreRows}` : ''}
    ${o.obtain ? `<div class="mc-sep"></div><div class="mc-line muted">${colorize(o.obtain)}</div>` : ''}
    ${evTags ? `<div class="tagline">${evTags}</div>` : ''}
    <div class="mc-sep"></div>
    <div class="hint">分类 ${GROUPS[o.group] || o.group} · 稀有度 R${o.rank}${o.canSpawn ? ' · 可自然刷出' : ''}</div>
  `;
  boxes.querySelector('.close').addEventListener('click', () => boxes.classList.remove('open'));
  boxes.classList.add('open');
}

/* ---------- 羁绊 ---------- */
function initBonds() {
  const el = $('#bonds');
  $('#bondCount').textContent = `${state.bonds.length} 组羁绊`;
  el.innerHTML = state.bonds.map((b) => {
    const steps = b.thresholds.length
      ? b.thresholds.map((t) =>
          `<li><span class="step-n">${t.count} 件</span><span class="step-t">${esc(t.text.replace(/^（\d+）/, ''))}</span></li>`).join('')
      : '<li><span class="step-t muted">该羁绊暂无文字说明</span></li>';
    const organs = b.organs.map((id) =>
      `<button class="bond-organ" data-id="${id}" title="${esc(state.organById.get(id)?.name || id)}">${icon(id, 24)}</button>`).join('');
    return `<article class="bond">
      <div class="bond-head">
        <h3>${esc(b.name)}</h3>
        <span class="bond-tag">${esc(b.tag)}</span>
        <span class="bond-count">${b.organs.length} 件器官</span>
      </div>
      <div class="bond-events">触发：${b.events.map(esc).join(' · ')}</div>
      <ul class="bond-steps">${steps}</ul>
      <div class="bond-organs">${organs}</div>
    </article>`;
  }).join('');

  el.addEventListener('click', (e) => {
    const btn = e.target.closest('.bond-organ');
    if (!btn) return;
    const id = btn.dataset.id;
    const tab = $$('.tab').find((t) => t.dataset.view === 'codex');
    if (tab) tab.click();
    showDetail(id);
  });
}

/* ---------- 构筑 ---------- */
function cavity() {
  return state.invTypes[state.cavityId] || state.invTypes['kubejs:player_17'] ||
    state.invTypes[Object.keys(state.invTypes)[0]];
}

function invTypeFor() {
  return cavity();
}

function initBuilder() {
  const list = Object.values(state.invTypes)
    .sort((a, b) => b.slots.length - a.slots.length || a.id.localeCompare(b.id));
  const opts = list.map((t) =>
    `<option value="${t.id}">${esc(t.name)}${t.usedBy.length ? ` · 用于 ${t.usedBy.length} 种胸腔` : ' · 未被使用'}</option>`).join('');
  $('#cavitySelect').innerHTML = opts;

  // 其余底图等首屏稳定后再预取，避免和当前底图抢带宽
  setTimeout(() => {
    Object.values(state.invTypes).forEach((t) => {
      if (t.bg) new Image().src = `./${t.bg}?v=${DATA_V}`;
    });
  }, 2500);
  $('#cavitySelect').value = state.cavityId;
  $('#cavitySelect').addEventListener('change', (e) => {
    state.cavityId = e.target.value;
    state.build = {};
    renderSlots();
  });

  $('#fillDefault').addEventListener('click', () => {
    const c = cavity();
    state.build = {};
    c.defaultOrgans.forEach((d) => {
      if (state.organById.has(d.item)) state.build[d.pos] = d.item;
    });
    renderSlots();
  });
  $('#clearBuild').addEventListener('click', () => { state.build = {}; renderSlots(); });
  $('#exportBtn').addEventListener('click', () => {
    const payload = { c: state.cavityId, s: state.build };
    $('#share').value = b64urlEncode(JSON.stringify(payload));
  });
  $('#importBtn').addEventListener('click', () => {
    try {
      const raw = $('#share').value.trim();
      const data = JSON.parse(b64urlDecode(raw));
      if (!state.invTypes[data.c]) throw new Error('未知槽位布局');
      state.cavityId = data.c;
      $('#cavitySelect').value = data.c;
      state.build = {};
      Object.entries(data.s || {}).forEach(([k, v]) => {
        if (state.organById.has(v)) state.build[k] = v;
      });
      renderSlots();
    } catch (err) {
      $('#share').value = '分享码无效：' + err.message;
    }
  });

  $('#pickList').addEventListener('click', (e) => {
    const c = e.target.closest('.card');
    if (!c) return;
    state.build[state.pickSlot] = c.dataset.id;
    closePicker();
    renderSlots();
  });
  $('#pickQ').addEventListener('input', renderPickList);
  $('#pickClear').addEventListener('click', () => {
    delete state.build[state.pickSlot];
    closePicker();
    renderSlots();
  });
  $('#picker').addEventListener('click', (e) => {
    if (e.target.id === 'picker') closePicker();
  });
  renderSlots();
}

function b64urlEncode(s) {
  return btoa(unescape(encodeURIComponent(s))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function b64urlDecode(s) {
  const p = s.replace(/-/g, '+').replace(/_/g, '/');
  return decodeURIComponent(escape(atob(p + '='.repeat((4 - (p.length % 4)) % 4))));
}

function renderSlots() {
  const it = cavity();
  const grid = $('#slotgrid');
  if (!it || !it.slots.length) {
    grid.innerHTML = '<p class="hint">该胸腔类型没有槽位数据。</p>';
    $('#cavityHint').textContent = '';
    renderTotals();
    return;
  }
  const slots = it.slots;
  const bgW = (it.size && it.size.x) || (Math.max(...slots.map((s) => s.x)) + 18);
  const bgH = (it.size && it.size.y) || (Math.max(...slots.map((s) => s.y)) + 18);
  const k = Math.min(2, 620 / bgW);
  const size = Math.round(16 * k);          // 槽位内格 16×16，与 GUI 底图一一对应
  grid.style.position = 'relative';
  grid.style.width = `${Math.round(bgW * k)}px`;
  grid.style.height = `${Math.round(bgH * k)}px`;
  if (it.bg) {
    grid.classList.add('has-bg');
    grid.style.backgroundImage = `url("./${it.bg}?v=${DATA_V}")`;
    grid.style.backgroundSize =
      `${Math.round((it.texW || bgW) * k)}px ${Math.round((it.texH || bgH) * k)}px`;
    grid.style.backgroundPosition = '0 0';
  } else {
    grid.classList.remove('has-bg');
    grid.style.backgroundImage = '';
  }

  grid.innerHTML = slots.map((s, i) => {
    const organId = state.build[i];
    const o = organId ? state.organById.get(organId) : null;
    const style = `left:${Math.round(s.x * k)}px;top:${Math.round(s.y * k)}px;width:${size}px;height:${size}px`;
    return `<div class="slot ${o ? '' : 'empty'}" data-i="${i}" style="${style}" title="${o ? esc(o.name) : '空槽位'}">
      ${o ? icon(o.id, size) : ''}
      ${s.type ? `<span class="st">${esc(s.type.split('_')[0])}</span>` : ''}
    </div>`;
  }).join('');

  grid.onclick = (e) => {
    const el = e.target.closest('.slot');
    if (!el) return;
    openPicker(Number(el.dataset.i));
  };
  const users = it.usedBy.length ? ` · 用于 ${it.usedBy.length} 种胸腔` : ' · 未被任何胸腔类型使用';
  $('#cavityHint').textContent = `${it.name}${users}${it.defaultOrgans.length ? ` · 默认 ${it.defaultOrgans.length} 件器官` : ''}`;
  renderTotals();
}

function renderTotals() {
  const c = cavity();
  const acc = {};
  (c.baseScores || []).forEach((s) => {
    acc[s.id] = (acc[s.id] || 0) + Number(s.value);
  });
  Object.values(state.build).forEach((id) => {
    const o = state.organById.get(id);
    if (!o) return;
    Object.entries(o.scores).forEach(([k, v]) => { acc[k] = (acc[k] || 0) + v; });
  });
  const rows = Object.entries(acc)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .map(([k, v]) => `<div class="total-row"><span class="muted">${esc(state.scores[k]?.name || k)}</span><span>${v > 0 ? '+' : ''}${round(v)}</span></div>`)
    .join('');
  const filled = Object.keys(state.build).length;
  $('#totals').innerHTML = (filled ? `<div class="total-row"><span class="muted">已放器官</span><span>${filled}</span></div>` : '') +
    (rows || '<span class="hint">尚未放入器官</span>');
  renderSpecial();
  renderBondEffects();
}

function placedOrgans() {
  const seen = new Set();
  return Object.values(state.build).map((id) => state.organById.get(id))
    .filter((o) => o && !seen.has(o.id) && seen.add(o.id));
}

function renderSpecial() {
  const lines = [];
  placedOrgans().forEach((o) => {
    const fx = (o.effectsResolved && o.effectsResolved.length ? o.effectsResolved : o.effects) || [];
    if (!fx.length) return;
    const text = fx.map((t) => t.trim()).filter(Boolean).join('<br>');
    lines.push(`<div class="fx-row"><span class="fx-name">${esc(o.name)}</span><span class="fx-text">${colorize(text)}</span></div>`);
  });
  $('#special').innerHTML = lines.length ? lines.join('') : '<span class="hint">所选器官没有特殊效果</span>';
}

function renderBondEffects() {
  const counts = {};
  placedOrgans().forEach((o) => {
    (state.bondTags.get(o.id) || []).forEach((tag) => { counts[tag] = (counts[tag] || 0) + 1; });
  });
  const blocks = [];
  state.bonds.forEach((b) => {
    const n = counts[b.tag] || 0;
    if (!n) return;
    const hit = b.thresholds.filter((t) => n >= t.count);
    if (!hit.length) return;
    const steps = hit.map((t) => `<li><span class="step-n">${t.count} 件</span><span class="step-t">${esc(t.text.replace(/^（\d+）/, ''))}</span></li>`).join('');
    blocks.push(`<div class="fx-row"><div class="fx-name">${esc(b.name)} · ${n} 件</div><ul class="bond-steps">${steps}</ul></div>`);
  });
  $('#bondfx').innerHTML = blocks.length ? blocks.join('') : '<span class="hint">尚未触发羁绊</span>';
}

const round = (v) => Math.round(v * 100) / 100;

let pickSlot = null;
function openPicker(i) {
  state.pickSlot = i;
  pickSlot = i;
  $('#pickQ').value = '';
  renderPickList();
  $('#picker').classList.add('open');
  $('#pickQ').focus();
}
function closePicker() {
  $('#picker').classList.remove('open');
  state.pickSlot = null;
}
function renderPickList() {
  const q = $('#pickQ').value.trim().toLowerCase();
  const list = state.organs.filter((o) => !q ||
    (o.name + o.path).toLowerCase().includes(q)).slice(0, 120);
  $('#pickList').innerHTML = list.map((o) => `
    <button class="card" data-id="${o.id}">
      ${icon(o.id, 26)}
      <span><span class="n">${esc(o.name)}</span><span class="g">${GROUPS[o.group] || o.group}</span></span>
    </button>`).join('');
}

boot();
