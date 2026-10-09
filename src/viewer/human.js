// Dati incorporati da build.mjs (src/human/manifest.json + SVG composti): gruppi, stili di capelli, sagome, preset
const DATA = PAGE_DATA.human;


// ---- dati --------------------------------------------------------------
// sel: selettore che dice se il personaggio ha quella parte (per esempio la punta della scarpa non c'è in tutte);
// può essere una funzione del personaggio (i ruoli secondari dipendono dal capo scelto)
const topRole = (role) => (v) => v.top !== 'base' && `#top-${v.top} .c-${role}`;
const bottomRole = (role) => (v) => v.bottom !== 'base' && `#bottom-${v.bottom} .c-${role}`;
// group: sezione del pannello; palette: i colori rapidi proposti sotto il campo
const COLOR_FIELDS = [
  { key: 'skin',       label: 'Pelle',                css: '--skin', sel: '.c-skin', group: 'body', palette: 'skin' },
  { key: 'hair',       label: 'Capelli',              css: '--hair', sel: '[class*="c-hair-"]', group: 'body', palette: 'hair' },
  { key: 'beard',      label: 'Barba',                css: '--beard', sel: (v) => v.beard !== 'none' && `#beard-${v.beard}`, group: 'body', palette: 'hair' },
  { key: 'shirt',      label: 'Maglia',               css: '--shirt', sel: '.c-shirt', group: 'top', palette: 'fabric' },
  { key: 'shirtTrim',  label: 'Bordi',                css: '--shirt-trim', sel: topRole('trim'), group: 'top', palette: 'fabric' },
  { key: 'shirtAccent', label: 'Dettagli',            css: '--shirt-accent', sel: topRole('accent'), group: 'top', palette: 'fabric' },
  { key: 'shirtAccent2', label: 'Dettagli 2',         css: '--shirt-accent2', sel: topRole('accent2'), group: 'top', palette: 'fabric' },
  { key: 'shirtUnder', label: 'Maglietta sotto',      css: '--shirt-under', sel: topRole('under'), group: 'top', palette: 'fabric' },
  { key: 'pants',      label: 'Pantaloni',            css: '--pants', sel: '.c-pants', group: 'bottom', palette: 'fabric' },
  { key: 'pantsTrim',  label: 'Bordi',                css: '--pants-trim', sel: bottomRole('trim'), group: 'bottom', palette: 'fabric' },
  { key: 'pantsAccent', label: 'Dettagli',            css: '--pants-accent', sel: bottomRole('accent'), group: 'bottom', palette: 'fabric' },
  { key: 'pantsUnder', label: 'Calze',                css: '--pants-under', sel: bottomRole('under'), group: 'bottom', palette: 'fabric' },
  { key: 'shoeUpperL', label: 'Scarpa sinistra',      css: '--shoe-upper-l', sel: '.c-upper-l', group: 'shoes', palette: null },
  { key: 'shoeUpperR', label: 'Scarpa destra',        css: '--shoe-upper-r', sel: '.c-upper-r', group: 'shoes', palette: null },
  { key: 'shoeToe',    label: 'Punta scarpa dx',      css: '--shoe-toe', sel: '.c-toe', group: 'shoes', palette: null },
  { key: 'shoeTongue', label: 'Linguetta scarpa sx',  css: '--shoe-tongue', sel: '.c-tongue', group: 'shoes', palette: null },
  { key: 'shoeLace',   label: 'Lacci scarpa dx',      css: '--shoe-lace', sel: '.c-lace', group: 'shoes', palette: null },
  { key: 'shoeSole',   label: 'Suola',                css: '--shoe-sole', sel: '.c-sole', group: 'shoes', palette: null },
  { key: 'outline',    label: 'Contorno',             css: '--outline', sel: '.c-stroke', group: 'lines', palette: 'ink' },
  { key: 'eye',        label: 'Occhi',                css: '--eye', sel: '.c-eye', group: 'lines', palette: 'ink' },
];
const COLOR_GROUPS = [
  { key: 'body', label: 'Corpo' }, { key: 'top', label: 'Maglia' }, { key: 'bottom', label: 'Pantaloni' },
  { key: 'shoes', label: 'Scarpe', quick: [{ label: 'Tomaia', keys: ['shoeUpperL', 'shoeUpperR', 'shoeToe'], palette: 'fabric' },
                                        { label: 'Suola', keys: ['shoeSole'], palette: 'sole' }] },
  { key: 'lines', label: 'Contorno e occhi' },
];
const FIELD_BY_VAR = Object.fromEntries(COLOR_FIELDS.map(f => [f.css.slice(2), f]));

const PARTS = [
  { key: 'head',  label: 'Testa' },
  { key: 'hair',  label: 'Capelli' },
  { key: 'torso', label: 'Maglia' },
  { key: 'arms',  label: 'Braccia' },
  { key: 'pants', label: 'Pantaloni' },
  { key: 'shoes', label: 'Scarpe' },
];

const HAIR = DATA.hair, BEARD = DATA.beards;
document.getElementById('hair-count').textContent = HAIR.length;
document.getElementById('beard-count').textContent = BEARD.length;

// Sagome: ogni SVG composto ha già tutti gli stili di capelli, adattati alla sua testa.
const bodies = DATA.bodies.map(({ id, group, name, svg, hair, beards }) => {
  const source = new DOMParser().parseFromString(svg, 'image/svg+xml').documentElement;
  const viewBox = source.getAttribute('viewBox');
  const [, , w, h] = viewBox.split(/\s+/).map(Number);
  return { id, group, name, svg, hair, beards, source, viewBox, w, h, css: source.querySelector('style').textContent,
           symbol: `character-${id.replace('/', '-')}` };
});
const bodyById = Object.fromEntries(bodies.map(b => [b.id, b]));
// proporzione media dei riquadri (le figure affiancate si dimensionano su questa)
const ASPECT = bodies.reduce((t, b) => t + b.h, 0) / bodies.reduce((t, b) => t + b.w, 0);

// I colori di partenza sono i default scritti nel CSS di ogni SVG, quindi non vanno ripetuti qui.
// Maglia e pantaloni hanno i colori del capo scelto ("base" = quelli della sagoma).
const cssDefault = (css, prop, scope = '') =>
  css.match(new RegExp(`${scope}[^}]*?var\\(\\s*${prop}\\s*,\\s*(#[0-9a-fA-F]{6})`))?.[1].toLowerCase();
const NEUTRAL = '#888888';       // per i ruoli che il capo non ha (non si vedono)
const scopeOf = (v, f) => {
  if (f.key === 'hair') return `\\.c-hair-${v.hair}\\s*\\{`;
  if (f.key === 'beard') return v.beard === 'none' ? '' : `\\.c-(?:beard|bdot)-${v.beard}\\s*\\{`;
  const [, kind, role] = f.key.match(/^(shirt|pants)(Trim|Accent2|Accent|Under)?$/) ?? [];
  if (!kind) return '';
  const item = kind === 'shirt' ? v.top : v.bottom, r = (role ?? 'Main').toLowerCase();
  if (item === 'base') return `\\.c-${kind}\\s*\\{`;
  return `#${kind === 'shirt' ? 'top' : 'bottom'}-${item} \\.c-${r}\\s*\\{`;
};
const defaultColors = (v) => Object.fromEntries(COLOR_FIELDS.map(f => [f.key, cssDefault(v.body.css, f.css, scopeOf(v, f)) ?? NEUTRAL]));

// Un personaggio = sagoma + capelli + maglia + pantaloni + colori. Parte da un preset del manifest; `home` è il
// gruppo del preset: resta lì (nei filtri e nelle righe) anche se poi gli dai la sagoma di un altro gruppo.
const makeVariant = (preset) => {
  const body = bodyById[preset.body];
  const v = { body, hair: preset.hair, beard: preset.beard ?? 'none', top: preset.top ?? 'base', bottom: preset.bottom ?? 'base', home: body.group, preset };
  v.colors = defaultColors(v);
  // colori del preset (per esempio pelle, capelli e scarpe di un outfit), con i nomi delle variabili CSS
  for (const [name, value] of Object.entries(preset.colors ?? {})) if (FIELD_BY_VAR[name]) v.colors[FIELD_BY_VAR[name].key] = value.toLowerCase();
  return v;
};
// nome del personaggio: quello del preset finché ha la sua sagoma, altrimenti il nome della sagoma
const nameOf = (v) => (v.preset.name && v.body.id === v.preset.body ? v.preset.name : v.body.name);
const variants = DATA.presets.map(makeVariant);
// i capi disponibili per la sagoma attuale: ogni capo sta solo sulla sagoma per cui è disegnato
const outfitOf = (v) => DATA.clothes[v.body.id] ?? { tops: [], bottoms: [] };
// parti del corpo che maglia e pantaloni scelti disegnano al posto di quelle della sagoma (per esempio le braccia)
const replacedParts = (v) => new Set([['tops', v.top], ['bottoms', v.bottom]].flatMap(([list, id]) => outfitOf(v)[list].find(c => c.id === id)?.replaces ?? []));
const uniq = (items) => [...new Map(items.map(i => [i.id, i])).values()];
const ALL_TOPS = uniq(Object.values(DATA.clothes).flatMap(c => c.tops)), ALL_BOTTOMS = uniq(Object.values(DATA.clothes).flatMap(c => c.bottoms));

// Cambiando sagoma o stile, i colori che non hai modificato (uguali al default di prima) seguono il nuovo default.
const follow = (v, before, after) => {
  for (const key of Object.keys(v.colors)) if (v.colors[key] === before[key]) v.colors[key] = after[key];
};

const state = {
  selected: 0,
  group: 'all',
  view: 'single',
  bg: 'white',
  zoom: 100,
  lineW: 5.4,
  idle: !matchMedia('(prefers-reduced-motion: reduce)').matches,
  parts: Object.fromEntries(PARTS.map(p => [p.key, true])),
};
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
  document.getElementById('defs-host').append(defs);
}

// ---- helper ------------------------------------------------------------
const cssVars = (v, index = 0, animated = state.idle) => {
  const vars = { '--line-w': state.lineW };
  for (const f of COLOR_FIELDS) vars[f.css] = v.colors[f.key];
  for (const p of PARTS) vars[`--show-${p.key}`] = state.parts[p.key] ? 'inline' : 'none';   // torso e pants: vedi sotto
  for (const h of HAIR) vars[`--show-hair-${h.id}`] = v.hair === h.id ? 'inline' : 'none';
  for (const b of BEARD) vars[`--show-beard-${b.id}`] = v.beard === b.id ? 'inline' : 'none';
  // maglia e pantaloni: la scelta (o la sagoma base) si vede solo se la parte è attiva
  for (const id of ['base', ...ALL_TOPS.map(t => t.id)]) vars[`--show-top-${id}`] = state.parts.torso && v.top === id ? 'inline' : 'none';
  for (const id of ['base', ...ALL_BOTTOMS.map(t => t.id)]) vars[`--show-bottom-${id}`] = state.parts.pants && v.bottom === id ? 'inline' : 'none';
  vars['--show-body-arms'] = state.parts.arms && !replacedParts(v).has('arms') ? 'inline' : 'none';   // un capo può disegnare le braccia
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
  const figures = $('figures');
  figures.className = `figures ${state.view}`;
  $('stage').style.setProperty('--cols', Math.max(...groups.map(g => inGroup(g).length)));
  $('stage').style.setProperty('--rows', groups.length);
  if (state.view === 'single') {
    figures.innerHTML = figureSvg(variants[state.selected], state.selected);
  } else {
    figures.innerHTML = groups.map(g => `<div class="group">${groups.length > 1 ? `<span class="group-label">${g.name}</span>` : ''}<div class="row">${
      inGroup(g).map(i => `<button type="button" class="fig" data-i="${i}" aria-pressed="${i === state.selected}">${figureSvg(variants[i], i)}<span>${nameOf(variants[i])}</span></button>`).join('')
    }</div></div>`).join('');
  }
  $('variants').hidden = state.view === 'all';
  $('variants').innerHTML = groups.map(g => `<div class="vgroup"><h3>${g.name}</h3><div class="vrow">${
    inGroup(g).map(i => `<button type="button" class="variant" data-i="${i}" aria-pressed="${i === state.selected}">${figureSvg(variants[i], i)}<span>${nameOf(variants[i])}</span></button>`).join('')
  }</div></div>`).join('');
  refresh();
}

// …mentre colori, spessore, parti, sfondo e zoom aggiornano solo gli stili sul posto,
// così l'animazione idle non riparte a ogni modifica.
function refresh() {
  const stage = $('stage');
  stage.dataset.bg = state.bg;
  stage.style.setProperty('--zoom', state.zoom / 100);
  stage.style.setProperty('--ar', ASPECT);
  for (const svg of document.querySelectorAll('#figures svg, #variants svg')) {
    const i = +svg.dataset.i;
    svg.setAttribute('style', styleAttr(variants[i], i));
  }
}

function renderGroupSeg() {
  $('group-seg').innerHTML = [{ id: 'all', name: 'Tutti' }, ...DATA.groups].map(g =>
    `<button type="button" data-group="${g.id}" aria-pressed="${g.id === state.group}">${g.name}</button>`).join('');
}

const hasPart = (v, f) => { const sel = typeof f.sel === 'function' ? f.sel(v) : f.sel; return !!sel && !!v.body.source.querySelector(sel); };

function renderColorRows() {
  const v = variants[state.selected], def = defaultColors(v);
  $('variant-name').textContent = nameOf(v);
  const fields = COLOR_FIELDS.filter(f => hasPart(v, f));
  $('colors').innerHTML = COLOR_GROUPS.map(g => {
    const fs = fields.filter(f => f.group === g.key);
    const quick = (g.quick ?? []).map(q => `<div class="quick"><span>${q.label}</span>${swatchRow(q.keys, q.palette, `${g.label} · ${q.label}`)}</div>`).join('');
    return fs.length ? `<div class="cgroup"><h3>${g.label}</h3>${quick}${fs.map(f => `
      <div class="color">
        <input type="color" id="c-${f.key}" value="${v.colors[f.key]}" aria-label="${f.label}">
        <label for="c-${f.key}">${f.label}</label>
        <input type="text" class="hex" id="h-${f.key}" value="${v.colors[f.key]}" maxlength="7" spellcheck="false" aria-label="${f.label} (esadecimale)">
        <button type="button" class="undo${v.colors[f.key] === def[f.key] ? ' off' : ''}" id="u-${f.key}" data-undo="${f.key}" title="Colore di default (${def[f.key]})" aria-label="${f.label}: colore di default">↺</button>
        ${f.palette ? swatchRow([f.key], f.palette, f.label) : ''}
      </div>`).join('')}</div>` : '';
  }).join('');
}

// Imposta un colore e aggiorna campo, codice e ripristino senza ricostruire il pannello.
function setColor(key, value) {
  const v = variants[state.selected];
  v.colors[key] = value.toLowerCase();
  if ($(`c-${key}`)) $(`c-${key}`).value = v.colors[key];
  if ($(`h-${key}`)) { $(`h-${key}`).value = v.colors[key]; $(`h-${key}`).removeAttribute('aria-invalid'); }
  $(`u-${key}`)?.classList.toggle('off', v.colors[key] === defaultColors(v)[key]);
}

// Colori casuali, presi dalle tavolozze: vestiti (maglia e pantaloni ben distinti, scarpe in tinta o neutre) o
// pelle e capelli.
function randomClothes(v) {
  const F = PALETTES.fabric, light = ['#f5f1ee', '#fbf6ee', '#e9e4dc'];
  const shirt = rnd(F);
  let pants = rnd(F);
  for (let k = 0; k < 20 && (pants === shirt || Math.abs(lum(pants) - lum(shirt)) < 45); k++) pants = rnd(F);
  const other = (c) => { let x = rnd(F); while (x === c) x = rnd(F); return x; };
  const shoe = rnd(['#f5f1ee', '#3d3d3d', '#1f2a44', '#8b5a3c', rnd(F)]), sole = lum(shoe) > 200 ? '#f5f1ee' : rnd(['#f5f1ee', '#3d3d3d']);
  Object.assign(v.colors, {
    shirt, shirtTrim: rnd([shirt, other(shirt), '#f5f1ee']), shirtAccent: other(shirt), shirtAccent2: other(shirt), shirtUnder: rnd(light),
    pants, pantsTrim: rnd([pants, other(pants)]), pantsAccent: other(pants), pantsUnder: rnd([...light, other(pants)]),
    shoeUpperL: shoe, shoeUpperR: shoe, shoeToe: rnd([shoe, sole]), shoeTongue: rnd([shoe, '#f5f1ee']), shoeLace: '#f5f1ee', shoeSole: sole,
  });
}
function randomLook(v) {
  v.colors.skin = rnd(PALETTES.skin);
  v.colors.hair = Math.random() < 0.85 ? rnd(PALETTES.hair.slice(0, 9)) : rnd(PALETTES.hair.slice(9));
  v.colors.beard = v.colors.hair;
}

function renderParts() {
  $('parts').innerHTML = PARTS.map(p =>
    `<label><input type="checkbox" data-part="${p.key}" ${state.parts[p.key] ? 'checked' : ''}>${p.label}</label>`).join('');
}

function renderHairStyles() {
  const v = variants[state.selected], current = v.hair;
  // solo gli stili che valgono per la sagoma (le acconciature da anziani non ci sono sui bambini)
  $('hair-styles').innerHTML = HAIR.filter(h => v.body.hair.includes(h.id)).map(h =>
    `<label><input type="radio" name="hair-style" value="${h.id}" ${h.id === current ? 'checked' : ''}>${h.name}</label>`).join('');
}

function renderBeards() {
  const v = variants[state.selected], list = BEARD.filter(b => v.body.beards.includes(b.id));
  $('beard-section').hidden = !list.length;          // le sagome senza barba (femminili, bambini) non hanno la sezione
  $('beard-styles').innerHTML = [{ id: 'none', name: 'Nessuna' }, ...list].map(b =>
    `<label><input type="radio" name="beard-style" value="${b.id}" ${b.id === v.beard ? 'checked' : ''}>${b.name}</label>`).join('');
}

function renderOutfit() {
  const v = variants[state.selected], c = outfitOf(v);
  const list = (kind, items, base, current) => `${[{ id: 'base', name: base }, ...items].map(i =>
    `<label><input type="radio" name="${kind}" value="${i.id}" ${i.id === current ? 'checked' : ''}>${i.name}</label>`).join('')}${
    items.length ? '' : '<p class="hint">Per questa sagoma non ci sono ancora capi.</p>'}`;
  $('top-list').innerHTML = list('top', c.tops, 'Maglietta', v.top);
  $('bottom-list').innerHTML = list('bottom', c.bottoms, 'Base', v.bottom);
}

function renderBodies() {
  const current = variants[state.selected].body.id;
  $('body-list').innerHTML = DATA.groups.map(g => `<div><h3>${g.name}</h3><div class="parts">${
    bodies.filter(b => b.group === g.id).map(b =>
      `<label><input type="radio" name="body" value="${b.id}" ${b.id === current ? 'checked' : ''}>${b.name}</label>`).join('')
  }</div></div>`).join('');
}

function select(i) {
  state.selected = i;
  renderBodies();
  renderHairStyles();
  renderBeards();
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
  style.textContent = style.textContent
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/var\(--idle-n, 0\)/g, '0') // chi ha "riduci animazioni" attivo continua a vedere l'SVG fermo
    .replace(/var\((--[\w-]+),\s*([^)]+)\)/g, (_, name, fallback) => vars[name] ?? fallback.trim())
    .replace(/calc\(([\d.]+) \* ([\d.]+)\)/g, (_, a, b) => String(+(a * b).toFixed(2)))
    .replace(/calc\((-?[\d.]+)s \+ ([\d.]+)s\)/g, (_, a, b) => `${+(+a + +b).toFixed(2)}s`);
  root.querySelector('title').textContent = `Personaggio – ${v.body.name}`;
  const hidden = { head: ['head'], hair: ['hair', 'hair-back', 'hair-skin'], torso: ['torso', 'torso-fill', 'neck-fill'], arms: ['arm-left', 'arm-right'], pants: ['pants', 'pants-under', 'pants-fill'], shoes: ['shoes'] };
  for (const p of PARTS) {
    if (state.parts[p.key]) continue;
    for (const id of hidden[p.key]) root.querySelector(`#${id}`)?.remove();
  }
  // di capelli, maglie e pantaloni resta solo ciò che è scelto (Illustrator e Figma non rispettano display:none)
  for (const h of HAIR) if (h.id !== v.hair) root.querySelectorAll(`#hair-${h.id}, #hair-${h.id}-back, #hair-${h.id}-skin`).forEach(n => n.remove());
  root.querySelectorAll('#hair-back, #hair-skin').forEach(n => { if (!n.children.length) n.remove(); });   // livelli vuoti: lo stile scelto non li usa
  for (const b of BEARD) if (b.id !== v.beard) root.querySelectorAll(`#beard-${b.id}, #beard-${b.id}-skin`).forEach(n => n.remove());
  root.querySelectorAll('#beard, #beard-skin').forEach(n => { if (!n.children.length) n.remove(); });
  const parts = (kind, id) => `#${kind}-${id}, #${kind}-${id}-under, #${kind}-${id}-back`;      // il capo e i suoi livelli
  for (const t of ALL_TOPS) if (t.id !== v.top) root.querySelectorAll(parts('top', t.id)).forEach(n => n.remove());
  for (const b of ALL_BOTTOMS) if (b.id !== v.bottom) root.querySelectorAll(parts('bottom', b.id)).forEach(n => n.remove());
  if (!state.parts.arms) root.querySelectorAll('.g-arms').forEach(n => n.remove());
  if (replacedParts(v).has('arms')) for (const id of ['arm-left', 'arm-right']) root.querySelector(`#${id}`)?.remove();
  if (v.top !== 'base') root.querySelectorAll('#torso, #torso-fill').forEach(n => n.remove());   // la maglietta base sta sotto un altro capo: non serve
  if (v.bottom !== 'base') root.querySelectorAll('#pants, #pants-under, #pants-fill').forEach(n => n.remove());
  if (!state.parts.torso) root.querySelectorAll(parts('top', v.top)).forEach(n => n.remove());
  if (!state.parts.pants) root.querySelectorAll(parts('bottom', v.bottom)).forEach(n => n.remove());
  return XML_HEAD + new XMLSerializer().serializeToString(root);
}
const fileStem = () => `personaggio-${variants[state.selected].body.id.replace('/', '-')}`;




// ---- eventi ------------------------------------------------------------

$('view-seg').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-view]');
  if (!b) return;
  state.view = b.dataset.view;
  setPressed($('view-seg'), 'view', state.view);
  renderStage();
});

$('group-seg').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-group]');
  if (!b) return;
  state.group = b.dataset.group;
  setPressed($('group-seg'), 'group', state.group);
  const idx = visible();
  if (idx.includes(state.selected)) renderStage();
  else select(idx[0]);
});

$('bg-seg').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-bg]');
  if (!b) return;
  state.bg = b.dataset.bg;
  setPressed($('bg-seg'), 'bg', state.bg);
  refresh();
});

$('zoom').addEventListener('input', (e) => {
  state.zoom = +e.target.value;
  $('zoom-out').textContent = `${state.zoom}%`;
  refresh();
});

const pick = (e) => {
  const b = e.target.closest('button[data-i]');
  if (b) select(+b.dataset.i);
};
$('figures').addEventListener('click', pick);
$('variants').addEventListener('click', pick);

$('colors').addEventListener('input', (e) => {
  const t = e.target;
  const key = t.id.slice(2);
  if (!COLOR_FIELDS.some(f => f.key === key)) return;
  let value = t.value.trim();
  if (t.classList.contains('hex')) {
    if (!value.startsWith('#')) value = `#${value}`;
    const ok = HEX.test(value);
    t.setAttribute('aria-invalid', String(!ok));
    if (!ok) return;
  }
  setColor(key, value);
  refresh();
});

$('colors').addEventListener('click', (e) => {
  const sw = e.target.closest('button[data-color]'), undo = e.target.closest('button[data-undo]');
  if (sw) for (const key of sw.dataset.keys.split(',')) setColor(key, sw.dataset.color);
  else if (undo) setColor(undo.dataset.undo, defaultColors(variants[state.selected])[undo.dataset.undo]);
  else return;
  refresh();
});

$('color-actions').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-colors]');
  if (!b) return;
  const v = variants[state.selected];
  if (b.dataset.colors === 'clothes') randomClothes(v);
  else if (b.dataset.colors === 'look') randomLook(v);
  else v.colors = defaultColors(v);
  renderColorRows();
  refresh();
});

$('line-w').addEventListener('input', (e) => {
  state.lineW = +e.target.value;
  $('line-w-out').textContent = state.lineW.toFixed(1);
  refresh();
});

$('parts').addEventListener('change', (e) => {
  const key = e.target.dataset.part;
  if (!key) return;
  state.parts[key] = e.target.checked;
  refresh();
});

$('idle').addEventListener('change', (e) => {
  state.idle = e.target.checked;
  refresh();
});

// Cambiando sagoma, capelli, maglia o pantaloni i colori che non hai modificato (uguali al default di prima)
// seguono il nuovo default; quelli che hai scelto restano.
const change = (mutate) => {
  const v = variants[state.selected];
  const before = defaultColors(v);
  mutate(v);
  // un capo che la nuova sagoma non ha (i capi sono per sagoma) lascia il posto all'abito di partenza di quella sagoma
  const c = outfitOf(v), home = DATA.presets.find(p => p.body === v.body.id);
  if (v.beard !== 'none' && !v.body.beards.includes(v.beard)) v.beard = 'none';             // la barba solo dove la sagoma la prevede
  if (!v.body.hair.includes(v.hair)) v.hair = v.body.hair.includes(v.preset.hair) ? v.preset.hair : v.body.hair[0];
  if (v.top !== 'base' && !c.tops.some(t => t.id === v.top)) v.top = home?.top ?? 'base';
  if (v.bottom !== 'base' && !c.bottoms.some(b => b.id === v.bottom)) v.bottom = home?.bottom ?? 'base';
  follow(v, before, defaultColors(v));
};

$('body-list').addEventListener('change', (e) => {
  if (e.target.name !== 'body') return;
  change(v => { v.body = bodyById[e.target.value]; });
  renderHairStyles();
  renderBeards();
  renderOutfit();
  renderColorRows();
  renderStage();
});

$('hair-styles').addEventListener('change', (e) => {
  if (e.target.name !== 'hair-style') return;
  change(v => { v.hair = e.target.value; });
  renderColorRows();
  refresh();
});

$('beard-styles').addEventListener('change', (e) => {
  if (e.target.name !== 'beard-style') return;
  change(v => { v.beard = e.target.value; });
  renderColorRows();
  refresh();
});

for (const kind of ['top', 'bottom']) {
  $(`${kind}-list`).addEventListener('change', (e) => {
    if (e.target.name !== kind) return;
    change(v => { v[kind] = e.target.value; });
    renderColorRows();
    refresh();
  });
}

$('reset').addEventListener('click', () => {
  variants[state.selected] = makeVariant(DATA.presets[state.selected]);
  select(state.selected);
  toast('Personaggio ripristinato');
});

$('dl-svg').addEventListener('click', () => {
  download(new Blob([buildExportSvg()], { type: 'image/svg+xml' }), `${fileStem()}.svg`);
});

$('dl-png').addEventListener('click', async () => {
  try {
    // il PNG è un fotogramma: si esporta sempre la posa base, senza animazione
    const { w, h } = variants[state.selected].body;
    download(await svgToPngBlob(buildExportSvg(false), 3, w, h), `${fileStem()}.png`);
  } catch {
    toast('Export PNG non riuscito');
  }
});

$('copy-svg').addEventListener('click', async () => {
  await copyText(buildExportSvg());
  toast('SVG copiato negli appunti');
});

document.addEventListener('keydown', (e) => {
  if (!sectionActive('human') || e.target.closest('[role="tablist"]')) return;       // i tasti valgono solo nella sezione visibile
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

// Lo script sta in una funzione (le sezioni non condividono nomi): questo è l'unico punto d'accesso dall'esterno, per
// tools/audit.mjs, che confronta l'SVG esportato con quello della sagoma.
window.humanViewer = { state, bodies, variants, DATA, defaultColors, cssVars, buildExportSvg };

// ---- avvio -------------------------------------------------------------
renderGroupSeg();
renderParts();
$('idle').checked = state.idle;
select(0);
