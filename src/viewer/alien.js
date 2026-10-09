// Sezione degli alieni. Dati incorporati da build.mjs (src/alien/manifest.json + SVG composti): gruppi, sagome, preset.
// Usa solo le utilità di common.js; non dipende dalla sezione degli umani (gli id della sua pagina cominciano con `alien-`).
const DATA = PAGE_DATA.alien;

// ---- dati --------------------------------------------------------------
// sel: selettore che dice se la sagoma ha quella parte; può essere una funzione del personaggio (i ruoli secondari dipendono dal capo
// scelto); group: sezione del pannello; palette: i colori rapidi sotto il campo
const topRole = (role) => (v) => v.top !== 'base' && `#alien-top-${v.top} .c-${role}`;
const bottomRole = (role) => (v) => v.bottom !== 'base' && `#alien-bottom-${v.bottom} .c-${role}`;
const COLOR_FIELDS = [
  { key: 'skin',    label: 'Pelle',                css: '--skin',    sel: '.c-skin',   group: 'body',   palette: 'alienSkin' },
  { key: 'eye',     label: 'Occhi',                css: '--eye',     sel: '.c-eye',    group: 'body',   palette: 'alienEye' },
  { key: 'prot',    label: 'Protuberanze',         css: '--prot',    sel: '.c-prot',   group: 'body',   palette: 'alienSkin' },   // null = segue la pelle
  { key: 'shirt',   label: 'Maglia',               css: '--shirt',   sel: '.c-shirt',  group: 'top',    palette: 'fabric' },
  { key: 'shirtTrim',    label: 'Bordi',           css: '--shirt-trim',    sel: topRole('trim'),    group: 'top', palette: 'fabric' },
  { key: 'shirtAccent',  label: 'Dettagli',        css: '--shirt-accent',  sel: topRole('accent'),  group: 'top', palette: 'fabric' },
  { key: 'shirtAccent2', label: 'Dettagli 2',      css: '--shirt-accent2', sel: topRole('accent2'), group: 'top', palette: 'fabric' },
  { key: 'pants',   label: 'Pantaloni',            css: '--pants',   sel: '.c-pants',  group: 'bottom', palette: 'fabric' },
  { key: 'pantsTrim',    label: 'Bordi',           css: '--pants-trim',    sel: bottomRole('trim'),    group: 'bottom', palette: 'fabric' },
  { key: 'pantsAccent',  label: 'Dettagli',        css: '--pants-accent',  sel: bottomRole('accent'),  group: 'bottom', palette: 'fabric' },
  { key: 'pantsAccent2', label: 'Dettagli 2',      css: '--pants-accent2', sel: bottomRole('accent2'), group: 'bottom', palette: 'fabric' },
  { key: 'outline', label: 'Contorno e narici',    css: '--outline', sel: '.c-stroke', group: 'lines',  palette: 'ink' },
];
const COLOR_GROUPS = [
  { key: 'body', label: 'Corpo' }, { key: 'top', label: 'Maglia' }, { key: 'bottom', label: 'Pantaloni' }, { key: 'lines', label: 'Contorno' },
];
// Colori rapidi propri degli alieni (gli altri sono in common.js): pelle verde, grigia, azzurra, viola, rosata, arancio; occhi scuri o accesi.
PALETTES.alienSkin = ['#b8c99c', '#9fbf8a', '#7fae7a', '#c9d6a3', '#b9bec4', '#9aa3ad', '#d8dbdd', '#9db8d6', '#7fa3c9', '#b9a3d0', '#9a86c0', '#e3b3c4', '#e7b98a'];
PALETTES.alienEye = ['#15100c', '#2b1d4a', '#0f3b52', '#5a1620', '#2a5a2f', '#e8c33a', '#e8e8e8'];
const FIELD_BY_VAR = Object.fromEntries(COLOR_FIELDS.map(f => [f.css.slice(2), f]));

// parte → id nel disegno (la visibilità è una variabile CSS --show-alien-<chiave>, definita in src/alien/style.css)
const PARTS = [
  { key: 'head',  label: 'Testa',        ids: ['alien-head'] },
  { key: 'torso', label: 'Maglia',       ids: ['alien-torso', 'alien-back'] },
  { key: 'arms',  label: 'Braccia',      ids: ['alien-arm-left', 'alien-arm-right'] },
  { key: 'pants', label: 'Pantaloni',    ids: ['alien-pants'] },
  { key: 'legs',  label: 'Gambe',        ids: ['alien-legs'] },
  { key: 'prot',  label: 'Protuberanze', ids: ['alien-prot', 'alien-prot-back'] },
];

// Sagome: ogni SVG composto ha già il suo CSS con i colori di default.
const PROT = DATA.protrusions;
const bodies = DATA.bodies.map(({ id, group, name, svg, protrusions }) => {
  const source = new DOMParser().parseFromString(svg, 'image/svg+xml').documentElement;
  const viewBox = source.getAttribute('viewBox');
  const [, , w, h] = viewBox.split(/\s+/).map(Number);
  return { id, group, name, svg, protrusions, source, viewBox, w, h, css: source.querySelector('style').textContent, symbol: `alien-character-${id.replace('/', '-')}` };
});
const bodyById = Object.fromEntries(bodies.map(b => [b.id, b]));
const ASPECT = bodies.length ? bodies.reduce((t, b) => t + b.h, 0) / bodies.reduce((t, b) => t + b.w, 0) : 2.5;
const LINE_W = DATA.lineWidth;

// I colori di partenza sono i default scritti nel CSS di ogni SVG, quindi non vanno ripetuti qui. Maglia e pantaloni hanno i colori
// del capo scelto ("base" = la maglietta e i pantaloncini della sagoma).
const cssDefault = (css, prop, scope = '') =>
  css.match(new RegExp(`${scope}[^}]*?var\\(\\s*${prop}\\s*,\\s*(#[0-9a-fA-F]{6})`))?.[1].toLowerCase();
const NEUTRAL = '#888888';       // per i ruoli che il capo non ha (non si vedono)
const scopeOf = (v, f) => {
  const [, kind, role] = f.key.match(/^(shirt|pants)(Trim|Accent2|Accent)?$/) ?? [];
  if (!kind) return '';
  const item = kind === 'shirt' ? v.top : v.bottom;
  if (item === 'base') return `\\.c-${kind}\\s*\\{`;
  return `#alien-${kind === 'shirt' ? 'top' : 'bottom'}-${item} \\.c-${(role ?? 'Main').toLowerCase()}\\s*\\{`;
};
const defaultColors = (v) => Object.fromEntries(COLOR_FIELDS.map(f => [f.key, f.key === 'prot' ? null : cssDefault(v.body.css, f.css, scopeOf(v, f)) ?? NEUTRAL]));
const shown = (v, key) => v.colors[key] ?? v.colors.skin;             // le protuberanze, finché non scegli un colore, hanno quello della pelle

// Un personaggio = sagoma + protuberanza + maglia + pantaloni + colori. Parte da un preset del manifest; `home` è il gruppo del preset.
const makeVariant = (preset) => {
  const body = bodyById[preset.body];
  const v = { body, home: body.group, preset, prot: preset.prot ?? 'none', top: preset.top ?? 'base', bottom: preset.bottom ?? 'base' };
  v.colors = defaultColors(v);
  for (const [name, value] of Object.entries(preset.colors ?? {})) if (FIELD_BY_VAR[name]) v.colors[FIELD_BY_VAR[name].key] = value.toLowerCase();
  return v;
};
const nameOf = (v) => (v.preset.name && v.body.id === v.preset.body ? v.preset.name : v.body.name);
const variants = DATA.presets.map(makeVariant);
// i capi disponibili per la sagoma attuale: ogni capo sta solo sulla sagoma per cui è disegnato
const outfitOf = (v) => DATA.clothes[v.body.id] ?? { tops: [], bottoms: [] };
// parti del corpo che maglia e pantaloni scelti disegnano al posto di quelle della sagoma (le braccia, le gambe)
const replacedParts = (v) => new Set([['tops', v.top], ['bottoms', v.bottom]].flatMap(([list, id]) => outfitOf(v)[list].find(c => c.id === id)?.replaces ?? []));
const uniq = (items) => [...new Map(items.map(i => [i.id, i])).values()];
const ALL_TOPS = uniq(Object.values(DATA.clothes).flatMap(c => c.tops)), ALL_BOTTOMS = uniq(Object.values(DATA.clothes).flatMap(c => c.bottoms));

// Cambiando sagoma i colori che non hai modificato (uguali al default di prima) seguono il nuovo default.
const follow = (v, before, after) => {
  for (const key of Object.keys(v.colors)) if (v.colors[key] === before[key]) v.colors[key] = after[key];
};

const state = {
  selected: 0,
  group: 'all',
  view: 'single',
  bg: 'white',
  zoom: 100,
  lineW: LINE_W,
  idle: !matchMedia('(prefers-reduced-motion: reduce)').matches,
  parts: Object.fromEntries(PARTS.map(p => [p.key, true])),
};
const MAX_COLS = 8;
const visible = () => variants.map((_, i) => i).filter(i => state.group === 'all' || variants[i].home === state.group);

// ---- SVG sorgente → <symbol> riusabile (uno per sagoma) -------------------
{
  const defs = document.createElementNS(SVG_NS, 'defs');
  for (const b of bodies) {
    const style = document.createElementNS(SVG_NS, 'style');
    style.textContent = b.css;
    const symbol = document.createElementNS(SVG_NS, 'symbol');
    symbol.id = b.symbol;
    symbol.setAttribute('viewBox', b.viewBox); // l'<svg> che lo usa ha viewBox 0 0 w h: l'origine dei file non è 0
    for (const node of b.source.children) {
      if (node.localName !== 'style' && node.localName !== 'title') symbol.appendChild(document.importNode(node, true));
    }
    defs.append(style, symbol);
  }
  $('defs-host').append(defs);
}

// ---- helper ------------------------------------------------------------
const A = (id) => $(`alien-${id}`);
const cssVars = (v, index = 0, animated = state.idle) => {
  const vars = { '--line-w': state.lineW };
  for (const f of COLOR_FIELDS) if (v.colors[f.key] !== null) vars[f.css] = v.colors[f.key];       // --prot manca finché segue la pelle
  for (const pr of PROT) vars[`--show-alien-prot-${pr.id}`] = v.prot === pr.id ? 'inline' : 'none';
  for (const p of PARTS) vars[`--show-alien-${p.key}`] = state.parts[p.key] ? 'inline' : 'none';
  // maglia e pantaloni: la scelta (o la sagoma di base) si vede se la sua parte è attiva (le parti spente nascondono il gruppo intero);
  // le braccia e le gambe della sagoma si vedono se nessun capo scelto le sostituisce
  for (const id of ['base', ...ALL_TOPS.map(t => t.id)]) vars[`--show-alien-top-${id}`] = v.top === id ? 'inline' : 'none';
  for (const id of ['base', ...ALL_BOTTOMS.map(t => t.id)]) vars[`--show-alien-bottom-${id}`] = v.bottom === id ? 'inline' : 'none';
  // le fasce di una maglia o di dei pantaloni (`-under`) servono solo con la maglietta o i pantaloncini di base dall'altra parte
  for (const t of ALL_TOPS) vars[`--show-alien-top-${t.id}-under`] = v.top === t.id && v.bottom === 'base' ? 'inline' : 'none';
  for (const b of ALL_BOTTOMS) vars[`--show-alien-bottom-${b.id}-under`] = v.bottom === b.id && v.top === 'base' ? 'inline' : 'none';
  vars['--show-alien-base-arms'] = replacedParts(v).has('arms') ? 'none' : 'inline';
  vars['--show-alien-base-legs'] = replacedParts(v).has('legs') ? 'none' : 'inline';
  vars['--idle-n'] = animated ? 'infinite' : '0';
  vars['--idle-delay'] = `${-index * 0.7}s`; // sfasa le figure: non respirano tutte all'unisono
  return vars;
};
const styleAttr = (v, index) => Object.entries(cssVars(v, index, state.idle)).map(([k, val]) => `${k}:${val}`).join(';');
const figureSvg = (v, i) =>
  `<svg viewBox="0 0 ${v.body.w} ${v.body.h}" data-i="${i}" style="${styleAttr(v, i)}" role="img" aria-label="${nameOf(v)}"><use href="#${v.body.symbol}"/></svg>`;
const groupsOf = (idx) => DATA.groups.filter(g => idx.some(i => variants[i].home === g.id));

// ---- rendering ---------------------------------------------------------
// Ricostruisce le figure (cambio di vista, gruppo, sagoma o personaggio)…
function renderStage() {
  const idx = visible(), groups = groupsOf(idx);
  const inGroup = (g) => idx.filter(i => variants[i].home === g.id);
  const figures = A('figures');
  figures.className = `figures ${state.view}`;
  // le figure di un gruppo vanno a capo dopo MAX_COLS (con tutti i capi e le protuberanze i personaggi sono tanti)
  const cols = Math.min(MAX_COLS, Math.max(1, ...groups.map(g => inGroup(g).length)));
  A('stage').style.setProperty('--cols', cols);
  A('stage').style.setProperty('--rows', Math.max(1, groups.reduce((n, g) => n + Math.ceil(inGroup(g).length / cols), 0)));
  if (!variants.length) {
    figures.innerHTML = '<p class="hint">Nessuna sagoma aliena ancora.</p>';
  } else if (state.view === 'single') {
    figures.innerHTML = figureSvg(variants[state.selected], state.selected);
  } else {
    figures.innerHTML = groups.map(g => `<div class="group">${groups.length > 1 ? `<span class="group-label">${g.name}</span>` : ''}<div class="row">${
      inGroup(g).map(i => `<button type="button" class="fig" data-i="${i}" aria-pressed="${i === state.selected}">${figureSvg(variants[i], i)}<span>${nameOf(variants[i])}</span></button>`).join('')
    }</div></div>`).join('');
  }
  A('variants').hidden = state.view === 'all';
  A('variants').innerHTML = groups.map(g => `<div class="vgroup"><h3>${g.name}</h3><div class="vrow">${
    inGroup(g).map(i => `<button type="button" class="variant" data-i="${i}" aria-pressed="${i === state.selected}">${figureSvg(variants[i], i)}<span>${nameOf(variants[i])}</span></button>`).join('')
  }</div></div>`).join('');
  refresh();
}

// …mentre colori, spessore, parti, sfondo e zoom aggiornano solo gli stili sul posto,
// così l'animazione idle non riparte a ogni modifica.
function refresh() {
  const stage = A('stage');
  stage.dataset.bg = state.bg;
  stage.style.setProperty('--zoom', state.zoom / 100);
  stage.style.setProperty('--ar', ASPECT);
  for (const svg of document.querySelectorAll('#alien-figures svg, #alien-variants svg')) {
    const i = +svg.dataset.i;
    svg.setAttribute('style', styleAttr(variants[i], i));
  }
}

function renderGroupSeg() {
  A('group-seg').hidden = DATA.groups.length < 2;                // con un solo gruppo il filtro non serve
  A('group-seg').innerHTML = [{ id: 'all', name: 'Tutti' }, ...DATA.groups].map(g =>
    `<button type="button" data-group="${g.id}" aria-pressed="${g.id === state.group}">${g.name}</button>`).join('');
}

const hasPart = (v, f) => { const sel = typeof f.sel === 'function' ? f.sel(v) : f.sel; return !!sel && !!v.body.source.querySelector(sel); };

function renderColorRows() {
  const v = variants[state.selected];
  if (!v) { A('colors').innerHTML = ''; return; }
  const def = defaultColors(v);
  A('variant-name').textContent = nameOf(v);
  const fields = COLOR_FIELDS.filter(f => hasPart(v, f));
  A('colors').innerHTML = COLOR_GROUPS.map(g => {
    const fs = fields.filter(f => f.group === g.key);
    return fs.length ? `<div class="cgroup"><h3>${g.label}</h3>${fs.map(f => `
      <div class="color">
        <input type="color" id="alien-c-${f.key}" value="${shown(v, f.key)}" aria-label="${f.label}">
        <label for="alien-c-${f.key}">${f.label}</label>
        <input type="text" class="hex" id="alien-h-${f.key}" value="${shown(v, f.key)}" maxlength="7" spellcheck="false" aria-label="${f.label} (esadecimale)">
        <button type="button" class="undo${v.colors[f.key] === def[f.key] ? ' off' : ''}" id="alien-u-${f.key}" data-undo="${f.key}" title="Colore di default (${def[f.key] ?? 'come la pelle'})" aria-label="${f.label}: colore di default">↺</button>
        ${f.palette ? swatchRow([f.key], f.palette, f.label) : ''}
      </div>`).join('')}</div>` : '';
  }).join('');
}

// Imposta un colore e aggiorna campo, codice e ripristino senza ricostruire il pannello.
function setColor(key, value) {
  const v = variants[state.selected];
  v.colors[key] = value === null ? null : value.toLowerCase();
  if ($(`alien-c-${key}`)) $(`alien-c-${key}`).value = shown(v, key);
  if ($(`alien-h-${key}`)) { $(`alien-h-${key}`).value = shown(v, key); $(`alien-h-${key}`).removeAttribute('aria-invalid'); }
  $(`alien-u-${key}`)?.classList.toggle('off', v.colors[key] === defaultColors(v)[key]);
  if (key === 'skin' && v.colors.prot === null) {                       // le protuberanze che seguono la pelle cambiano con lei
    if ($('alien-c-prot')) $('alien-c-prot').value = v.colors.skin;
    if ($('alien-h-prot')) $('alien-h-prot').value = v.colors.skin;
  }
}

// Colori casuali, presi dalle tavolozze: pelle e occhi, oppure maglia e pantaloncini ben distinti.
function randomLook(v) {
  v.colors.skin = rnd(PALETTES.alienSkin);
  v.colors.eye = rnd(PALETTES.alienEye);
}
function randomClothes(v) {
  const F = PALETTES.fabric, shirt = rnd(F);
  let pants = rnd(F);
  for (let k = 0; k < 20 && (pants === shirt || Math.abs(lum(pants) - lum(shirt)) < 45); k++) pants = rnd(F);
  const other = (c) => { let x = rnd(F); while (x === c) x = rnd(F); return x; };
  Object.assign(v.colors, {
    shirt, shirtTrim: rnd([shirt, other(shirt), '#f5f1ee']), shirtAccent: other(shirt), shirtAccent2: other(shirt),
    pants, pantsTrim: rnd([pants, other(pants)]), pantsAccent: other(pants), pantsAccent2: other(pants),
  });
}

function renderProtrusions() {
  const v = variants[state.selected], list = PROT.filter(p => v?.body.protrusions.includes(p.id));
  A('prot-list').innerHTML = [{ id: 'none', name: 'Nessuna' }, ...list].map(p =>
    `<label><input type="radio" name="alien-prot" value="${p.id}" ${p.id === (v?.prot ?? 'none') ? 'checked' : ''}>${p.name}</label>`).join('');
}

function renderOutfit() {
  const v = variants[state.selected], c = outfitOf(v);
  const list = (kind, items, base, current) => `${[{ id: 'base', name: base }, ...items].map(i =>
    `<label><input type="radio" name="alien-${kind}" value="${i.id}" ${i.id === current ? 'checked' : ''}>${i.name}</label>`).join('')}${
    items.length ? '' : '<p class="hint">Per questa sagoma non ci sono ancora capi.</p>'}`;
  A('top-list').innerHTML = list('top', c.tops, 'Maglietta', v.top);
  A('bottom-list').innerHTML = list('bottom', c.bottoms, 'Pantaloncini', v.bottom);
}

function renderParts() {
  A('parts').innerHTML = PARTS.map(p =>
    `<label><input type="checkbox" data-part="${p.key}" ${state.parts[p.key] ? 'checked' : ''}>${p.label}</label>`).join('');
}

function renderBodies() {
  const v = variants[state.selected], current = v?.body.id;
  A('body-list').innerHTML = DATA.groups.map(g => `<div><h3>${g.name}</h3><div class="parts">${
    bodies.filter(b => b.group === g.id).map(b =>
      `<label><input type="radio" name="alien-body" value="${b.id}" ${b.id === current ? 'checked' : ''}>${b.name}</label>`).join('')
  }</div></div>`).join('');
}

function select(i) {
  state.selected = i;
  renderBodies();
  renderProtrusions();
  renderOutfit();
  renderColorRows();
  renderStage();
}

// ---- export ------------------------------------------------------------
// Scrive nel file i valori correnti al posto delle variabili CSS, così l'SVG
// funziona ovunque (Illustrator, Inkscape, Figma…) e non solo nel browser.
function buildExportSvg(animated = state.idle) {
  const v = variants[state.selected];
  const vars = cssVars(v, 0, animated);
  const doc = new DOMParser().parseFromString(v.body.svg, 'image/svg+xml');
  const root = doc.documentElement;
  const style = root.querySelector('style');
  let css = style.textContent
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/var\(--idle-n, 0\)/g, '0'); // chi ha "riduci animazioni" attivo continua a vedere l'SVG fermo
  // le variabili dal valore più interno (le protuberanze: var(--prot, var(--skin, …)) seguono la pelle se --prot manca)
  for (let before = ''; before !== css;) { before = css; css = css.replace(/var\((--[\w-]+),\s*([^()]+)\)/g, (_, name, fallback) => vars[name] ?? fallback.trim()); }
  style.textContent = css
    .replace(/calc\(([\d.]+) \* ([\d.]+)\)/g, (_, a, b) => String(+(a * b).toFixed(2)))
    .replace(/calc\((-?[\d.]+)s \+ ([\d.]+)s\)/g, (_, a, b) => `${+(+a + +b).toFixed(2)}s`);
  root.querySelector('title').textContent = `Alieno – ${v.body.name}`;
  // le parti spente non vanno nel file (Illustrator e Figma non rispettano display:none); delle protuberanze resta solo quella scelta
  for (const pr of PROT) if (pr.id !== v.prot) root.querySelectorAll(`#alien-prot-${pr.id}, #alien-prot-${pr.id}-back`).forEach(n => n.remove());
  root.querySelectorAll('#alien-prot, #alien-prot-back').forEach(n => { if (!n.children.length) n.remove(); });
  for (const p of PARTS) if (!state.parts[p.key]) for (const id of p.ids) root.querySelector(`#${id}`)?.remove();
  // di maglie e pantaloni resta solo ciò che è scelto (e della sagoma di base solo ciò che nessun capo sostituisce)
  const layers = (kind, id) => ['', '-back', '-under', '-arm-left', '-arm-right', '-leg-left', '-leg-right'].map(x => `#alien-${kind}-${id}${x}`).join(', ');
  for (const t of ALL_TOPS) if (t.id !== v.top) root.querySelectorAll(layers('top', t.id)).forEach(n => n.remove());
  for (const b of ALL_BOTTOMS) if (b.id !== v.bottom) root.querySelectorAll(layers('bottom', b.id)).forEach(n => n.remove());
  if (v.bottom !== 'base') root.querySelectorAll(`#alien-top-${v.top}-under`).forEach(n => n.remove());       // le fasce: vedi cssVars
  if (v.top !== 'base') root.querySelectorAll(`#alien-bottom-${v.bottom}-under`).forEach(n => n.remove());
  if (v.top !== 'base') root.querySelectorAll('#alien-base-torso, .alien-neckfill').forEach(n => n.remove());
  if (v.bottom !== 'base') root.querySelectorAll('#alien-base-pants').forEach(n => n.remove());
  const replaced = replacedParts(v);
  if (replaced.has('arms')) root.querySelectorAll('.alien-base-arms').forEach(n => n.remove());
  if (replaced.has('legs')) root.querySelectorAll('.alien-base-legs').forEach(n => n.remove());
  root.querySelectorAll('#alien-back').forEach(n => { if (!n.children.length) n.remove(); });
  return XML_HEAD + new XMLSerializer().serializeToString(root);
}
const fileStem = () => `alieno-${variants[state.selected].body.id.replace('/', '-')}`;

// ---- eventi ------------------------------------------------------------
A('view-seg').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-view]');
  if (!b) return;
  state.view = b.dataset.view;
  setPressed(A('view-seg'), 'view', state.view);
  renderStage();
});

A('group-seg').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-group]');
  if (!b) return;
  state.group = b.dataset.group;
  setPressed(A('group-seg'), 'group', state.group);
  const idx = visible();
  if (idx.includes(state.selected)) renderStage();
  else select(idx[0]);
});

A('bg-seg').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-bg]');
  if (!b) return;
  state.bg = b.dataset.bg;
  setPressed(A('bg-seg'), 'bg', state.bg);
  refresh();
});

A('zoom').addEventListener('input', (e) => {
  state.zoom = +e.target.value;
  A('zoom-out').textContent = `${state.zoom}%`;
  refresh();
});

const pick = (e) => {
  const b = e.target.closest('button[data-i]');
  if (b) select(+b.dataset.i);
};
A('figures').addEventListener('click', pick);
A('variants').addEventListener('click', pick);

const HEX_COLOR = /^#[0-9a-f]{6}$/i;
A('colors').addEventListener('input', (e) => {
  const t = e.target;
  const key = t.id.replace(/^alien-[chu]-/, '');
  if (!COLOR_FIELDS.some(f => f.key === key)) return;
  let value = t.value.trim();
  if (t.classList.contains('hex')) {
    if (!value.startsWith('#')) value = `#${value}`;
    const ok = HEX_COLOR.test(value);
    t.setAttribute('aria-invalid', String(!ok));
    if (!ok) return;
  }
  setColor(key, value);
  refresh();
});

A('colors').addEventListener('click', (e) => {
  const sw = e.target.closest('button[data-color]'), undo = e.target.closest('button[data-undo]');
  if (sw) for (const key of sw.dataset.keys.split(',')) setColor(key, sw.dataset.color);
  else if (undo) setColor(undo.dataset.undo, defaultColors(variants[state.selected])[undo.dataset.undo]);
  else return;
  refresh();
});

A('color-actions').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-colors]');
  if (!b || !variants.length) return;
  const v = variants[state.selected];
  if (b.dataset.colors === 'clothes') randomClothes(v);
  else if (b.dataset.colors === 'look') randomLook(v);
  else v.colors = defaultColors(v);
  renderColorRows();
  refresh();
});

A('line-w').value = LINE_W;
A('line-w-out').textContent = (+LINE_W).toFixed(1);
A('line-w').addEventListener('input', (e) => {
  state.lineW = +e.target.value;
  A('line-w-out').textContent = state.lineW.toFixed(1);
  refresh();
});

A('parts').addEventListener('change', (e) => {
  const key = e.target.dataset.part;
  if (!key) return;
  state.parts[key] = e.target.checked;
  refresh();
});

A('idle').addEventListener('change', (e) => {
  state.idle = e.target.checked;
  refresh();
});

// Cambiando sagoma, maglia o pantaloni i colori che non hai modificato (uguali al default di prima) seguono il nuovo default; quelli che
// hai scelto restano.
const change = (mutate) => {
  const v = variants[state.selected], before = defaultColors(v);
  mutate(v);
  // un capo che la nuova sagoma non ha (i capi sono per sagoma) lascia il posto alla maglietta e ai pantaloncini di base
  const c = outfitOf(v);
  if (v.prot !== 'none' && !v.body.protrusions.includes(v.prot)) v.prot = 'none';
  if (v.top !== 'base' && !c.tops.some(t => t.id === v.top)) v.top = 'base';
  if (v.bottom !== 'base' && !c.bottoms.some(b => b.id === v.bottom)) v.bottom = 'base';
  follow(v, before, defaultColors(v));
};

A('body-list').addEventListener('change', (e) => {
  if (e.target.name !== 'alien-body') return;
  change(v => { v.body = bodyById[e.target.value]; });
  renderProtrusions();
  renderOutfit();
  renderColorRows();
  renderStage();
});

for (const kind of ['top', 'bottom']) {
  A(`${kind}-list`).addEventListener('change', (e) => {
    if (e.target.name !== `alien-${kind}`) return;
    change(v => { v[kind] = e.target.value; });
    renderColorRows();
    refresh();
  });
}

A('prot-list').addEventListener('change', (e) => {
  if (e.target.name !== 'alien-prot') return;
  variants[state.selected].prot = e.target.value;
  refresh();
});

A('reset').addEventListener('click', () => {
  variants[state.selected] = makeVariant(DATA.presets[state.selected]);
  select(state.selected);
  toast('Personaggio ripristinato');
});

A('dl-svg').addEventListener('click', () => {
  download(new Blob([buildExportSvg()], { type: 'image/svg+xml' }), `${fileStem()}.svg`);
});

A('dl-png').addEventListener('click', async () => {
  try {
    // il PNG è un fotogramma: si esporta sempre la posa base, senza animazione
    const { w, h } = variants[state.selected].body;
    download(await svgToPngBlob(buildExportSvg(false), 3, w, h), `${fileStem()}.png`);
  } catch {
    toast('Export PNG non riuscito');
  }
});

A('copy-svg').addEventListener('click', async () => {
  await copyText(buildExportSvg());
  toast('SVG copiato negli appunti');
});

document.addEventListener('keydown', (e) => {
  if (!sectionActive('alien') || e.target.closest('[role="tablist"]') || !variants.length) return;     // i tasti valgono solo nella sezione visibile
  if (e.target.matches('input[type="text"], textarea') || e.ctrlKey || e.metaKey || e.altKey) return;
  const idx = visible(), pos = idx.indexOf(state.selected);
  const slider = e.target.matches('input[type="range"]');
  if (/^[0-9]$/.test(e.key)) {
    const n = e.key === '0' ? 10 : +e.key;       // 1–9 e 0 (= decimo) fra i personaggi visibili
    if (n <= idx.length) select(idx[n - 1]);
  }
  else if (e.key === 'ArrowRight' && !slider) select(idx[(pos + 1) % idx.length]);
  else if (e.key === 'ArrowLeft' && !slider) select(idx[(pos - 1 + idx.length) % idx.length]);
});

// Lo script sta in una funzione (le sezioni non condividono nomi): unico punto d'accesso dall'esterno (i test).
window.alienViewer = { state, bodies, variants, DATA, defaultColors, cssVars, buildExportSvg };

// ---- avvio -------------------------------------------------------------
renderGroupSeg();
renderParts();
A('idle').checked = state.idle;
select(0);
