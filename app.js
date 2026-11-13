'use strict';

const state = {
  organs: [], scores: {}, cavities: [], invTypes: {}, events: {}, bonds: [], bondTags: new Map(),
  atlas: { cols: 20, rows: 16, map: {} },
  organById: new Map(),
  filters: { q: '', group: '', rank: '', event: '', score: '' },
  cavityId: 'kubejs:player_17',
  build: {},
  selected: null,
  pickSlot: null,
};

const DATA_V = '24';
const GROUPS = {
  nature: '自然', ender: '末影', nether: '下界', factory: '工厂', machine: '机械',
  magic: '魔法', food: '食物', infected: '感染', plants: '植物', relics: '遗物',
  rose: '玫瑰', legend: '传说', misc: '其它',
};
const MC_COLORS = {
  '0': '#000', '1': '#0000aa', '2': '#00aa00', '3': '#00aaaa', '4': '#aa0000',
  '5': '#aa00aa', '6': '#ffaa00', '7': '#aaaaaa', '8': '#555555', '9': '#5555ff',
  a: '#55ff55', b: '#55ffff', c: '#ff5555', d: '#ff55ff', e: '#ffff55', f: '#ffffff',
};

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const round = (v) => Math.round(v * 100) / 100;

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

/* ---------- boot ---------- */
async function boot() {
  const load = (f) => fetch(`./data/${f}?v=${DATA_V}`, { cache: 'no-cache' }).then((r) => r.json());
  const [organs, scores, cavities, invTypes, events, bonds, atlas] = await Promise.all([
    load('organs.json'), load('scores.json'), load('cavities.json'),
    load('inventory_types.json'), load('events.json'), load('bonds.json'), load('atlas.json'),
  ]);
  Object.assign(state, { atlas, organs, scores, cavities, invTypes, events, bonds });
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
  initShell();
}

function initTabs() {
  $$('.tab').forEach((t) => t.addEventListener('click', () => {
    $$('.tab').forEach((x) => x.setAttribute('aria-selected', String(x === t)));
    $$('.view').forEach((v) => v.classList.toggle('active', v.id === `view-${t.dataset.view}`));
    closeDrawers();
    window.scrollTo({ top: 0, behavior: 'auto' });
  }));
}

/* ---------- shell / drawers ---------- */
function closeDrawers() {
  $('#detail').classList.remove('open');
  $('#filters').classList.remove('open');
  $('#scrim').classList.remove('on');
}

function initShell() {
  $('#scrim').addEventListener('click', closeDrawers);
  initTooltip();
  $('#toggleFilters').addEventListener('click', () => {
    $('#filters').classList.add('open');
    $('#scrim').classList.add('on');
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== $('#q') && $('#view-codex').classList.contains('active')) {
      e.preventDefault();
      $('#q').focus();
    }
    if (e.key === 'Escape') closeDrawers();
  });
}

function initTooltip() {
  const tip = document.createElement('div');
  tip.className = 'tip';
  document.body.appendChild(tip);

  const show = (term) => {
    const text = term.dataset.tip;
    if (!text) return;
    tip.innerHTML = text.split('\n').map(colorize).join('<br>');
    tip.classList.add('on');
    const r = term.getBoundingClientRect();
    const box = tip.getBoundingClientRect();
    let left = r.left;
    if (left + box.width > window.innerWidth - 12) left = window.innerWidth - box.width - 12;
    let top = r.top - box.height - 8;
    if (top < 64) top = r.bottom + 8;
    tip.style.left = `${Math.max(12, left)}px`;
    tip.style.top = `${top}px`;
  };
  const hide = () => tip.classList.remove('on');

  document.addEventListener('mouseover', (e) => {
    const term = e.target.closest?.('.hover-term');
    if (term) show(term); else hide();
  });
  document.addEventListener('focusin', (e) => {
    const term = e.target.closest?.('.hover-term');
    if (term) show(term); else hide();
  });
  document.addEventListener('scroll', hide, true);
  $('#detail').addEventListener('scroll', hide);
}

/* ---------- codex ---------- */
function initCodex() {
  const groups = [...new Set(state.organs.map((o) => o.group))].sort(
    (a, b) => (Object.keys(GROUPS).indexOf(a) + 1 || 99) - (Object.keys(GROUPS).indexOf(b) + 1 || 99) || a.localeCompare(b));
  $('#groups').innerHTML = groups.map((g) =>
    `<button class="chip" data-g="${g}" aria-pressed="false">${GROUPS[g] || g}</button>`).join('');

  const ranks = [...new Set(state.organs.map((o) => o.rank))].sort((a, b) => a - b);
  $('#ranks').innerHTML = ranks.map((r) =>
    `<button class="chip" data-r="${r}" aria-pressed="false">阶级 ${r}</button>`).join('');

  const evs = Object.entries(state.events).sort((a, b) => b[1].organs.length - a[1].organs.length);
  $('#eventFilter').innerHTML = '<option value="">全部事件</option>' +
    evs.map(([k, v]) => `<option value="${k}">${esc(v.name)} · ${v.organs.length}</option>`).join('');

  const scoreIds = [...new Set(state.organs.flatMap((o) => Object.keys(o.scores)))].sort();
  $('#scoreFilter').innerHTML = '<option value="">全部属性</option>' +
    scoreIds.map((s) => `<option value="${s}">${esc(state.scores[s]?.name || s)}</option>`).join('');

  const chips = (sel, key) => {
    $(sel).addEventListener('click', (e) => {
      const b = e.target.closest('.chip');
      if (!b) return;
      const on = b.getAttribute('aria-pressed') === 'true';
      $$(`${sel} .chip`).forEach((x) => x.setAttribute('aria-pressed', 'false'));
      b.setAttribute('aria-pressed', String(!on));
      state.filters[key] = on ? '' : (b.dataset.g ?? b.dataset.r);
      renderGrid();
    });
  };
  chips('#groups', 'group');
  chips('#ranks', 'rank');

  $('#eventFilter').addEventListener('change', (e) => { state.filters.event = e.target.value; renderGrid(); });
  $('#scoreFilter').addEventListener('change', (e) => { state.filters.score = e.target.value; renderGrid(); });
  $('#q').addEventListener('input', (e) => { state.filters.q = e.target.value.trim().toLowerCase(); renderGrid(); });

  $('#resetFilters').addEventListener('click', () => {
    state.filters = { q: '', group: '', rank: '', event: '', score: '' };
    $('#q').value = '';
    $('#eventFilter').value = '';
    $('#scoreFilter').value = '';
    $$('.chip').forEach((c) => c.setAttribute('aria-pressed', 'false'));
    renderGrid();
  });

  $('#grid').addEventListener('click', (e) => {
    const c = e.target.closest('.card');
    if (c) showDetail(c.dataset.id);
  });

  renderGrid();
}

function matched() {
  const f = state.filters;
  return [...state.organs].filter((o) => {
    if (f.group && o.group !== f.group) return false;
    if (f.rank !== '' && String(o.rank) !== f.rank) return false;
    if (f.event && !o.events.some((e) => e.event === f.event)) return false;
    if (f.score && !(f.score in o.scores)) return false;
    if (f.q) {
      const hay = (o.name + ' ' + o.path + ' ' + o.effects.join(' ') + ' ' + o.flavor.join(' ')).toLowerCase();
      if (!hay.includes(f.q)) return false;
    }
    return true;
  }).sort((a, b) => b.rank - a.rank || a.name.localeCompare(b.name, 'zh-CN'));
}

function renderGrid() {
  const list = matched();
  $('#count').textContent = list.length;
  if (!list.length) {
    $('#grid').innerHTML = '<p class="hint">没有匹配的器官，试试放宽筛选条件。</p>';
    return;
  }

  const groups = new Map();
  list.forEach((o) => {
    if (!groups.has(o.group)) groups.set(o.group, []);
    groups.get(o.group).push(o);
  });
  const order = [...groups.entries()].sort((a, b) => b[1].length - a[1].length
    || (GROUPS[a[0]] || a[0]).localeCompare(GROUPS[b[0]] || b[0], 'zh-CN'));

  $('#grid').innerHTML = order.map(([group, items]) => `
    <section class="group-block">
      <div class="group-head">
        <h3>${GROUPS[group] || group}</h3>
        <span class="group-count">${items.length}</span>
      </div>
      <div class="cardgrid">${items.map((o) => `
        <button class="card rank-${o.rank} ${o.id === state.selected ? 'sel' : ''}" data-id="${o.id}">
          ${icon(o.id, 30)}
          <span class="card-body">
            <span class="n">${esc(o.name)}</span>
            <span class="g"><i class="rank-dot"></i>${GROUPS[o.group] || o.group}</span>
          </span>
        </button>`).join('')}</div>
    </section>`).join('');
}

/* ---------- detail ---------- */
function showDetail(id) {
  const o = state.organById.get(id);
  if (!o) return;
  state.selected = id;
  $$('#grid .card').forEach((c) => c.classList.toggle('sel', c.dataset.id === id));

  const scoreRows = Object.entries(o.scores).map(([k, v]) => {
    const s = state.scores[k] || {};
    return `<div class="score-row"><span title="${esc(s.desc || '')}">${esc(s.name || k)}</span><b>${v > 0 ? '+' : ''}${v}</b></div>`;
  }).join('');

  const effects = (o.effectsResolved && o.effectsResolved.length ? o.effectsResolved : o.effects) || [];
  const evTags = o.events.map((e) =>
    `<span class="tag">${esc(state.events[e.event]?.name || e.event)}${e.mode === 'only' ? ' · 仅' : ''}</span>`).join('');
  const activation = (o.activationEffects || []).map((entry) =>
    `<p class="mc-line activation-line">${renderRich(entry.text)}</p>`).join('');

  $('#detailBody').innerHTML = `
    <div class="d-head">
      <button class="d-close" id="detailClose" aria-label="关闭">✕</button>
      <div class="d-title">
        ${icon(o.id, 42)}
        <div>
          <h2 class="d-name">${esc(o.name)}</h2>
          <div class="d-id">${esc(o.id)}</div>
        </div>
      </div>
      <div class="d-tags">
        <span class="tag r${o.rank}">R${o.rank}</span>
        <span class="tag">${GROUPS[o.group] || o.group}</span>
        ${o.canSpawn ? '<span class="tag">可自然刷出</span>' : ''}
      </div>
    </div>
    ${o.flavor.length ? `<section class="d-sec"><h4>描述</h4>${o.flavor.map((t) => `<p class="d-flavor">${colorize(t)}</p>`).join('')}</section>` : ''}
    ${effects.length ? `<section class="d-sec"><h4>特殊效果</h4>${effects.map((t) => `<p class="mc-line">${colorize(t)}</p>`).join('')}</section>` : ''}
    ${activation ? `<section class="d-sec"><h4>槽位激活效果</h4>${activation}</section>` : ''}
    ${o.slotEffects?.length ? `<section class="d-sec"><h4>槽位效果</h4>${o.slotEffects.map((t) => `<p class="slot-fx">${esc(t)}</p>`).join('')}</section>` : ''}
    ${scoreRows ? `<section class="d-sec"><h4>基础属性</h4>${scoreRows}</section>` : ''}
    ${o.obtain ? `<section class="d-sec"><h4>获取方式</h4><p class="d-obtain">${colorize(o.obtain)}</p></section>` : ''}
    ${evTags ? `<section class="d-sec"><h4>触发事件</h4><div class="event-chips">${evTags}</div></section>` : ''}
  `;
  $('#detailClose')?.addEventListener('click', () => {
    $('#detail').classList.remove('open');
    $('#scrim').classList.remove('on');
  });
  $('#detail').classList.add('has-sel');
  $('#detail').scrollTop = 0;

  if (window.matchMedia('(max-width:1180px)').matches) {
    $('#detail').classList.add('open');
    $('#scrim').classList.add('on');
  }
}

function renderRich(text) {
  return colorize(text).replace(/\[\[([^|]+)\|([^\]]*)\]\]/g, (_, label, details) => {
    const plain = details.replace(/\\n/g, '\n');
    return `<span class="hover-term" tabindex="0" data-tip="${esc(plain)}">${esc(label)}</span>`;
  });
}

/* ---------- bonds ---------- */
function initBonds() {
  $('#bondCount').textContent = `${state.bonds.length} 组 · 按胸腔内标签件数生效`;
  $('#bonds').innerHTML = state.bonds.map((b) => {
    const steps = b.thresholds.length
      ? b.thresholds.map((t) =>
          `<li><span class="step-n">${t.count} 件</span><span class="step-t">${esc(t.text.replace(/^（\d+）/, ''))}</span></li>`).join('')
      : '<li><span class="step-t muted">该羁绊暂无文字说明</span></li>';
    const organs = b.organs.map((id) =>
      `<button class="bond-organ" data-id="${id}" title="${esc(state.organById.get(id)?.name || id)}">${icon(id, 22)}</button>`).join('');
    return `<article class="bond">
      <div class="bond-head">
        <h3>${esc(b.name)}</h3>
        <span class="bond-tag">${esc(b.tag)}</span>
        <span class="bond-count">${b.organs.length} 件</span>
      </div>
      <div class="bond-events">触发：${b.events.map(esc).join(' · ')}</div>
      <ul class="bond-steps">${steps}</ul>
      <div class="bond-organs">${organs}</div>
    </article>`;
  }).join('');

  $('#bonds').addEventListener('click', (e) => {
    const btn = e.target.closest('.bond-organ');
    if (!btn) return;
    $$('.tab').find((t) => t.dataset.view === 'codex')?.click();
    showDetail(btn.dataset.id);
  });
}

/* ---------- builder ---------- */
const cavity = () => state.invTypes[state.cavityId] || state.invTypes['kubejs:player_17'] ||
  state.invTypes[Object.keys(state.invTypes)[0]];

const dragState = { active: false, moved: false, suppressClick: false, source: null, id: null, slot: null, x: 0, y: 0, ghost: null, pointerType: '', move: null, up: null };

function initBuilder() {
  const list = Object.values(state.invTypes).sort((a, b) => b.slots.length - a.slots.length || a.id.localeCompare(b.id));
  $('#cavitySelect').innerHTML = list.map((t) => `<option value="${t.id}">${esc(t.name)}${t.usedBy.length ? ` · ${t.usedBy.length} 种胸腔` : ''}</option>`).join('');
  $('#cavitySelect').value = state.cavityId;
  $('#cavitySelect').addEventListener('change', (e) => { state.cavityId = e.target.value; state.build = {}; renderSlots(); });
  $('#fillDefault').addEventListener('click', () => { state.build = {}; cavity().defaultOrgans.forEach((d) => { if (state.organById.has(d.item)) state.build[d.pos] = d.item; }); renderSlots(); });
  $('#clearBuild').addEventListener('click', () => { state.build = {}; renderSlots(); });
  $('#exportBtn').addEventListener('click', () => { $('#share').value = b64urlEncode(JSON.stringify({ c: state.cavityId, s: state.build })); });
  $('#importBtn').addEventListener('click', () => {
    try {
      const data = JSON.parse(b64urlDecode($('#share').value.trim()));
      if (!state.invTypes[data.c]) throw new Error('未知槽位布局');
      state.cavityId = data.c; $('#cavitySelect').value = data.c; state.build = {};
      Object.entries(data.s || {}).forEach(([k, v]) => { if (state.organById.has(v)) state.build[k] = v; });
      renderSlots();
    } catch (err) { $('#share').value = '分享码无效：' + err.message; }
  });
  initLibrary();
  $('#pickList').addEventListener('click', (e) => { const c = e.target.closest('.card'); if (!c) return; state.build[state.pickSlot] = c.dataset.id; closePicker(); renderSlots(); });
  $('#pickQ').addEventListener('input', renderPickList);
  $('#pickClear').addEventListener('click', () => { delete state.build[state.pickSlot]; closePicker(); renderSlots(); });
  $('#picker').addEventListener('click', (e) => { if (e.target.id === 'picker') closePicker(); });
  renderSlots();
}

function initLibrary() {
  const groups = [...new Set(state.organs.map((o) => o.group))].sort((a, b) => (GROUPS[a] || a).localeCompare(GROUPS[b] || b, 'zh-CN'));
  $('#libraryGroup').innerHTML += groups.map((g) => `<option value="${esc(g)}">${esc(GROUPS[g] || g)}</option>`).join('');
  $('#libraryQ').addEventListener('input', renderLibrary);
  $('#libraryGroup').addEventListener('change', renderLibrary);
  $('#libraryRank').addEventListener('change', renderLibrary);
  $('#libraryList').addEventListener('pointerdown', onDragStart);
  $('#libraryList').addEventListener('click', (e) => {
    if (dragState.moved || dragState.suppressClick) { dragState.suppressClick = false; return; }
    const card = e.target.closest('.library-card');
    if (!card) return;
    const first = cavity().slots.findIndex((_, i) => !state.build[i]);
    if (first >= 0) { state.build[first] = card.dataset.id; renderSlots(); }
  });
  renderLibrary();
}

function renderLibrary() {
  const q = $('#libraryQ').value.trim().toLowerCase();
  const group = $('#libraryGroup').value;
  const order = $('#libraryRank').value;
  const list = state.organs.filter((o) => (!group || o.group === group) && (!q || `${o.name} ${o.id} ${o.path}`.toLowerCase().includes(q)))
    .sort((a, b) => (order === 'asc' ? a.rank - b.rank : b.rank - a.rank) || a.name.localeCompare(b.name, 'zh-CN'));
  $('#libraryCount').textContent = list.length;
  $('#libraryList').innerHTML = list.map((o) => `<button class="library-card rank-${o.rank}" data-id="${esc(o.id)}" type="button">${icon(o.id, 28)}<span class="library-card-body"><b>${esc(o.name)}</b><small><i class="rank-dot"></i>${esc(GROUPS[o.group] || o.group)}</small></span></button>`).join('');
}

function onDragStart(e) {
  const card = e.target.closest('.library-card');
  if (!card || e.button !== 0) return;
  beginDrag(e, 'library', card.dataset.id, null, card);
}

function beginDrag(e, source, id, slot, element) {
  dragState.active = true; dragState.moved = false; dragState.source = source; dragState.id = id; dragState.slot = slot; dragState.x = e.clientX; dragState.y = e.clientY; dragState.pointerType = e.pointerType || 'mouse';
  element.classList.add('drag-armed');
  const move = (ev) => onDragMove(ev, element);
  const up = (ev) => onDragEnd(ev, element, move, up);
  dragState.move = move; dragState.up = up;
  document.addEventListener('pointermove', move);
  document.addEventListener('pointerup', up, { once: true });
  document.addEventListener('pointercancel', up, { once: true });
}

function onDragMove(e, element) {
  const dx = e.clientX - dragState.x;
  const dy = e.clientY - dragState.y;
  const dist = Math.hypot(dx, dy);
  if (!dragState.moved && dragState.pointerType === 'touch' && dragState.source === 'library' && Math.abs(dy) > 8 && Math.abs(dy) > Math.abs(dx) * 1.15) {
    cancelDragForScroll(element);
    return;
  }
  const threshold = dragState.pointerType === 'touch' ? 12 : 5;
  if (!dragState.moved && dist <= threshold) return;
  if (!dragState.moved) {
    dragState.moved = true; element.classList.add('dragging');
    dragState.ghost = document.createElement('div'); dragState.ghost.className = 'drag-ghost'; dragState.ghost.innerHTML = icon(dragState.id, 34); document.body.appendChild(dragState.ghost);
  }
  dragState.ghost.style.transform = `translate(${e.clientX + 14}px,${e.clientY + 14}px)`;
  clearDropStates();
  const target = document.elementFromPoint(e.clientX, e.clientY)?.closest('.slot');
  if (target) target.classList.add('drop-target');
  if (dragState.source === 'slot' && document.elementFromPoint(e.clientX, e.clientY)?.closest('#removeZone')) $('#removeZone').classList.add('hot');
}

function cancelDragForScroll(element) {
  if (dragState.move) document.removeEventListener('pointermove', dragState.move);
  if (dragState.up) {
    document.removeEventListener('pointerup', dragState.up);
    document.removeEventListener('pointercancel', dragState.up);
  }
  if (dragState.ghost) dragState.ghost.remove();
  clearDropStates();
  element?.classList.remove('drag-armed', 'dragging');
  dragState.suppressClick = true;
  dragState.active = false; dragState.moved = false; dragState.source = null; dragState.id = null; dragState.slot = null; dragState.pointerType = ''; dragState.move = null; dragState.up = null;
}

function onDragEnd(e, element, move, up) {
  document.removeEventListener('pointermove', move);
  document.removeEventListener('pointercancel', up);
  clearDropStates();
  element.classList.remove('drag-armed', 'dragging');
  const moved = dragState.moved;
  const source = dragState.source;
  const from = dragState.slot;
  const target = document.elementFromPoint(e.clientX, e.clientY)?.closest('.slot');
  const remove = document.elementFromPoint(e.clientX, e.clientY)?.closest('#removeZone');
  if (dragState.ghost) dragState.ghost.remove();
  if (moved) {
    dragState.suppressClick = true;
    if (remove || (source === 'slot' && !target)) {
      if (source === 'slot') delete state.build[from];
    } else if (target) {
      const to = Number(target.dataset.i);
      if (source === 'slot') { const old = state.build[to]; state.build[to] = dragState.id; if (old) state.build[from] = old; else delete state.build[from]; }
      else state.build[to] = dragState.id;
    }
    renderSlots();
  }
  dragState.active = false; dragState.moved = false; dragState.source = null; dragState.id = null; dragState.slot = null; dragState.pointerType = ''; dragState.move = null; dragState.up = null;
}

function clearDropStates() { $$('.slot.drop-target').forEach((x) => x.classList.remove('drop-target')); $('#removeZone').classList.remove('hot'); }

const b64urlEncode = (s) => btoa(unescape(encodeURIComponent(s))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const b64urlDecode = (s) => { const p = s.replace(/-/g, '+').replace(/_/g, '/'); return decodeURIComponent(escape(atob(p + '='.repeat((4 - (p.length % 4)) % 4)))); };

function renderSlots() {
  const it = cavity(); const grid = $('#slotgrid');
  if (!it || !it.slots.length) { grid.innerHTML = '<p class="hint">该胸腔类型没有槽位数据。</p>'; $('#cavityHint').textContent = ''; renderTotals(); return; }
  const slots = it.slots; const bgW = (it.size && it.size.x) || (Math.max(...slots.map((s) => s.x)) + 18); const bgH = (it.size && it.size.y) || (Math.max(...slots.map((s) => s.y)) + 18); const k = Math.min(2, 620 / bgW); const size = Math.round(16 * k);
  grid.style.position = 'relative'; grid.style.width = `${Math.round(bgW * k)}px`; grid.style.height = `${Math.round(bgH * k)}px`;
  if (it.bg) { grid.classList.add('has-bg'); grid.style.backgroundImage = `url("./${it.bg}?v=${DATA_V}")`; grid.style.backgroundSize = `${Math.round((it.texW || bgW) * k)}px ${Math.round((it.texH || bgH) * k)}px`; grid.style.backgroundPosition = '0 0'; } else { grid.classList.remove('has-bg'); grid.style.backgroundImage = ''; }
  grid.innerHTML = slots.map((s, i) => { const organId = state.build[i]; const o = organId ? state.organById.get(organId) : null; const style = `left:${Math.round(s.x * k)}px;top:${Math.round(s.y * k)}px;width:${size}px;height:${size}px`; return `<div class="slot ${o ? '' : 'empty'}" data-i="${i}" style="${style}" title="${o ? esc(o.name) : '空槽位'}">${o ? icon(o.id, size) : ''}${s.type ? `<span class="st">${esc(s.type.split('_')[0])}</span>` : ''}</div>`; }).join('');
  grid.onpointerdown = (e) => { if (e.button !== 0) return; const el = e.target.closest('.slot'); if (!el) return; const i = Number(el.dataset.i); const id = state.build[i]; if (id) beginDrag(e, 'slot', id, i, el); };
  grid.onclick = (e) => { const el = e.target.closest('.slot'); if (el && !dragState.moved) { $$('.slot.selected').forEach((x) => x.classList.remove('selected')); el.classList.add('selected'); if (!state.build[Number(el.dataset.i)]) openPicker(Number(el.dataset.i)); } };
  grid.oncontextmenu = (e) => { const el = e.target.closest('.slot'); if (!el) return; e.preventDefault(); delete state.build[Number(el.dataset.i)]; renderSlots(); };
  grid.ondblclick = (e) => { const el = e.target.closest('.slot'); if (el && state.build[Number(el.dataset.i)]) { delete state.build[Number(el.dataset.i)]; renderSlots(); } };
  const users = it.usedBy.length ? ` · 用于 ${it.usedBy.length} 种胸腔` : ' · 未被任何胸腔类型使用'; $('#cavityHint').textContent = `${it.name}${users}${it.defaultOrgans.length ? ` · 默认 ${it.defaultOrgans.length} 件器官` : ''}`; renderTotals();
}

function renderTotals() {
  const c = cavity();
  const acc = {};
  (c.baseScores || []).forEach((score) => { acc[score.id] = (acc[score.id] || 0) + Number(score.value); });
  Object.values(state.build).forEach((id) => {
    const o = state.organById.get(id);
    if (o) Object.entries(o.scores).forEach(([k, v]) => { acc[k] = (acc[k] || 0) + v; });
  });
  const rows = Object.entries(acc).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .map(([k, v]) => `<div class="total-row"><span class="muted">${esc(state.scores[k]?.name || k)}</span><span>${v > 0 ? '+' : ''}${round(v)}</span></div>`).join('');
  const filled = Object.keys(state.build).length;
  $('#totals').innerHTML = (filled ? `<div class="total-row"><span class="muted">已放器官</span><span>${filled}</span></div>` : '') + (rows || '<span class="hint">尚未放入器官</span>');
  renderSpecial();
  renderBondEffects();
}

function placedOrgans() {
  const seen = new Set();
  return Object.values(state.build).map((id) => state.organById.get(id)).filter((o) => o && !seen.has(o.id) && seen.add(o.id));
}

function renderSpecial() {
  const lines = [];
  placedOrgans().forEach((o) => {
    const fx = (o.effectsResolved && o.effectsResolved.length ? o.effectsResolved : o.effects) || [];
    const activation = o.activationEffects || [];
    const slots = o.slotEffects || [];
    if (!fx.length && !activation.length && !slots.length) return;
    const body = [];
    if (fx.length) body.push(`<div>${fx.map((t) => t.trim()).filter(Boolean).map(renderRich).join('<br>')}</div>`);
    if (activation.length) body.push(`<div class="activation-line">槽位激活：${activation.map((entry) => renderRich(entry.text || entry)).join('<br>')}</div>`);
    if (slots.length) body.push(`<div class="slot-fx">${slots.map((text) => esc(text)).join('<br>')}</div>`);
    lines.push(`<div class="fx-row"><span class="fx-name">${esc(o.name)}</span><span class="fx-text">${body.join('')}</span></div>`);
  });
  $('#special').innerHTML = lines.length ? lines.join('') : '<span class="hint">所选器官没有特殊效果</span>';
}

function renderBondEffects() {
  const counts = {};
  placedOrgans().forEach((o) => (state.bondTags.get(o.id) || []).forEach((tag) => { counts[tag] = (counts[tag] || 0) + 1; }));
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

/* ---------- picker ---------- */
function openPicker(i) {
  state.pickSlot = i;
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
  const list = state.organs.filter((o) => !q || (o.name + o.path).toLowerCase().includes(q)).slice(0, 120);
  $('#pickList').innerHTML = list.map((o) => `
    <button class="card" data-id="${o.id}">
      ${icon(o.id, 24)}
      <span class="card-body"><span class="n">${esc(o.name)}</span><span class="g">${GROUPS[o.group] || o.group}</span></span>
    </button>`).join('');
}

boot();
