// Compone i personaggi e genera il visualizzatore.
//
//   src/bodies/<gruppo>/<sagoma>.svg + .json   sagome (solo geometria + dati misurati)
//   src/hair/<stile>.svg + .json               stili di capelli (coordinate del riquadro dei capelli)
//   src/clothes/<gruppo>/{tops,bottoms}/…      vestiti, disegnati su un corpo di riferimento (reference.json del gruppo o `on` del capo)
//   src/style.css                              classi dei colori, visibilità di capelli e vestiti, animazione idle
//   src/manifest.json                          gruppi, ordine, palette comune, vestiti, preset
//
//   → characters/<gruppo>/<sagoma>.svg         ogni sagoma con TUTTI i capelli e i vestiti del suo gruppo, file autonomo
//   → index.html                               visualizzatore (src/viewer/template.html + dati)
//
// Uso: node build.mjs
import { readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import { dirname } from 'node:path';
import { makeTps } from './lib/fit.mjs';

const root = new URL('./', import.meta.url);
const read = (path) => readFile(new URL(path, root), 'utf8');
const readJson = async (path) => JSON.parse(await read(path));

const PAIR = /(-?\d+\.?\d*),(-?\d+\.?\d*)/g;     // coppie "x,y" dei percorsi (comandi sempre assoluti)
const D_ATTR = / d="([^"]*)"/g;
const fmt = (v) => { const s = v.toFixed(1); return (s.endsWith('.0') ? s.slice(0, -2) : s).replace(/^-0$/, '0'); };
const mapPaths = (xml, f) => xml.replace(D_ATTR, (_, d) => ` d="${d.replace(PAIR, (__, x, y) => f(+x, +y).map(fmt).join(','))}"`);
const mapCircles = (xml, f) => xml.replace(/cx="([^"]*)" cy="([^"]*)"/g, (_, x, y) => { const [X, Y] = f(+x, +y); return `cx="${fmt(X)}" cy="${fmt(Y)}"`; });
const coords = (xml) => [...xml.matchAll(D_ATTR)].flatMap(([, d]) => [...d.matchAll(PAIR)].map((m) => [+m[1], +m[2]]));

// ---- sorgenti ------------------------------------------------------------
const manifest = await readJson('src/manifest.json');
const styleTemplate = await read('src/style.css');

const hair = await Promise.all(manifest.hair.map(async (id) => {
  const svg = await read(`src/hair/${id}.svg`);
  const group = svg.match(/<g id="hair-[\s\S]*<\/g>/)?.[0];
  if (!group) throw new Error(`src/hair/${id}.svg: gruppo <g id="hair-…"> non trovato`);
  return { id, ...(await readJson(`src/hair/${id}.json`)), group };
}));

const bodies = await Promise.all(manifest.bodies.map(async (path) => {
  const [group, file] = path.split('/');
  const svg = await read(`src/bodies/${path}.svg`);
  if (!svg.includes('<!-- @hair -->')) throw new Error(`src/bodies/${path}.svg: manca il segnaposto <!-- @hair -->`);
  const inner = svg.slice(svg.indexOf('</title>') + '</title>'.length, svg.lastIndexOf('</svg>'));
  // i riempimenti di fondo hanno un id per sagoma (il visualizzatore mette tutte le sagome nella stessa pagina)
  const fills = {};
  const named = inner.replace(/<path id="fill-(top|bottom)"/g, (m, k) => { fills[k] = `fill-${k}-${group}-${file}`; return `<path id="${fills[k]}"`; });
  return { id: path, group, file, ...(await readJson(`src/bodies/${path}.json`)), inner: named, fills };
}));

// ---- vestiti -----------------------------------------------------------------
// Un capo ('top' = sopra il busto, 'bottom' = pantaloni) è disegnato su un corpo di riferimento: quello del gruppo
// (src/clothes/<gruppo>/reference.json) oppure la sagoma indicata dal capo (`on`, per esempio "femmina/ragazza").
// `<g id="garment">` è il capo; `<g id="underlay">`, se c'è, sta sotto i pantaloni (pelle scoperta da una maglia corta,
// fasce che salgono o scendono sotto un altro capo); `<g id="backlay">` dietro a tutto (il capo sotto le braccia).
const KINDS = { tops: 'top', bottoms: 'bottom' };
const bodyById = Object.fromEntries(bodies.map((b) => [b.id, b]));
const groupContent = (svg, id) => svg.match(new RegExp(`<g id="${id}">\\n([\\s\\S]*?)\\n  </g>`))?.[1];
const clothes = {};
for (const [group, lists] of Object.entries(manifest.clothes ?? {})) {
  const groupRef = await read(`src/clothes/${group}/reference.json`).then(JSON.parse, () => null);
  clothes[group] = { items: [] };
  for (const [folder, kind] of Object.entries(KINDS)) {
    for (const id of lists[folder] ?? []) {
      const path = `src/clothes/${group}/${folder}/${id}`;
      const svg = await read(`${path}.svg`);
      const content = groupContent(svg, 'garment');
      if (!content) throw new Error(`${path}.svg: gruppo <g id="garment"> non trovato`);
      const meta = await readJson(`${path}.json`);
      const ref = meta.on ? { landmarks: { ...bodyById[meta.on].landmarks, ...meta.landmarks } } : groupRef;
      if (!ref) throw new Error(`${path}: serve src/clothes/${group}/reference.json oppure "on" nel json`);
      clothes[group].items.push({ id, kind, group, ref, ...meta, content, under: groupContent(svg, 'underlay') ?? '', back: groupContent(svg, 'backlay') ?? '' });
    }
  }
}

// Adattamento: thin-plate spline dai punti di riferimento del corpo di riferimento a quelli della sagoma.
// Le coordinate vengono riscritte (lo spessore del contorno resta uguale); la rigidità tiene la deformazione dolce.
const FIT_STIFFNESS = 0.02;
// Ogni capo si adatta partendo dal corpo su cui è stato disegnato (`ref`). Gli id sono unici fra i gruppi.
const allIds = Object.values(clothes).flatMap((c) => c.items.map((g) => `${g.kind}-${g.id}`));
if (new Set(allIds).size !== allIds.length) throw new Error('src/clothes: id di capo ripetuto fra gruppi diversi');
const wardrobe = (group) => clothes[group]?.items ?? [];
function clothesFor(body) {
  const fits = new Map();
  const fit = (ref) => {
    if (!fits.has(ref)) {
      const names = Object.keys(ref.landmarks).filter((n) => n in body.landmarks);
      fits.set(ref, makeTps(names.map((n) => ref.landmarks[n]), names.map((n) => body.landmarks[n]), FIT_STIFFNESS));
    }
    return fits.get(ref);
  };
  const map = (xml, f) => mapCircles(mapPaths(xml, f), f);
  return wardrobe(body.group).map((g) => { const f = fit(g.ref); return { ...g, content: map(g.content, f), under: map(g.under, f), back: map(g.back, f) }; });
}
for (const b of bodies) b.clothes = clothesFor(b);

// ---- capelli adattati a ogni testa -----------------------------------------
// I capelli sono disegnati sulla testa di riferimento (hairFrame): per ogni sagoma si scalano in x
// (da orecchio a fronte) e in y (da cima a linea degli occhi) per far combaciare la testa. Le coordinate
// vengono riscritte, così lo spessore del contorno resta uguale ovunque.
// Uno stile può valere solo per alcune età (`ages` nel suo .json; le età delle sagome sono in `ages` del manifest):
// le acconciature da anziani non si danno ai bambini.
const F = manifest.hairFrame;
const ageOf = (id) => Object.entries(manifest.ages ?? {}).find(([, ids]) => ids.includes(id))?.[0];
function hairFor(body) {
  const { L, R, T, eyeY } = body.head;
  const sx = (R - L) / (F.R - F.L), sy = (eyeY - T) / (F.eyeY - F.T);
  const f = (x, y) => [L + sx * (x - F.L), T + sy * (y - F.T)];
  return hair.filter((h) => !h.ages || h.ages.includes(ageOf(body.id))).map((h) => ({ ...h, group: mapPaths(h.group, f) }));
}
for (const b of bodies) b.hair = hairFor(b);

// ---- riquadro comune: stessa scala e linea del suolo, spazio per i capelli ------------
const ext = (b) => {
  const pts = [...coords(b.inner), ...b.hair.flatMap((h) => coords(h.group)), ...b.clothes.flatMap((g) => coords(g.content + g.under + g.back))];
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  return [Math.min(...xs) - 3.5, Math.min(...ys) - 3.5, Math.max(...xs) + 3.5, Math.max(...ys) + 3.5];
};
for (const b of bodies) b.ext = ext(b);
const W = Math.ceil(Math.max(...bodies.map((b) => b.ext[2] - b.ext[0])));
const Y0 = Math.floor(Math.min(...bodies.map((b) => b.ext[1])));
const H = Math.ceil(Math.max(...bodies.map((b) => b.ext[3]))) - Y0;

// ---- composizione ----------------------------------------------------------
// colori per ruolo dei vestiti: --shirt (busto) e --pants (pantaloni) sono il colore principale, le altre
// variabili i ruoli secondari; la visibilità si sceglie con --show-top-<id> / --show-bottom-<id>
const ROLE_VAR = { top: { main: '--shirt', trim: '--shirt-trim', accent: '--shirt-accent', accent2: '--shirt-accent2', under: '--shirt-under' },
                   bottom: { main: '--pants', trim: '--pants-trim', accent: '--pants-accent', under: '--pants-under' } };
function clothesCss(body, defaults) {
  const fills = body.clothes.flatMap((g) => Object.entries(g.colors).map(([role, color]) =>
    // il gruppo del capo per ultimo: il visualizzatore legge il colore di default da "#top-<id> .c-<ruolo> {"
    `${[...(g.under ? ['-under'] : []), '-back', ''].map((x) => `#${g.kind}-${g.id}${x} .c-${role}`).join(', ')} { fill: var(${ROLE_VAR[g.kind][role]}, ${color}) }`));
  const show = [['top', '#torso, #torso-fill'], ['bottom', '#pants, #pants-under, #pants-fill']].flatMap(([kind, base]) => [
    `${base} { display: var(--show-${kind}-base, ${defaults[kind] === 'base' ? 'inline' : 'none'}) }`,
    ...body.clothes.filter((g) => g.kind === kind).map((g) =>
      `#${kind}-${g.id}${g.under ? `, #${kind}-${g.id}-under` : ''}, #${kind}-${g.id}-back { display: var(--show-${kind}-${g.id}, ${defaults[kind] === g.id ? 'inline' : 'none'}) }`)]);
  return { fills: fills.join('\n'), show: show.join('\n') };
}

// Il respiro allunga il busto attorno alla sua base. Tutto ciò che sta sul busto (maglietta, maglie, le loro parti sotto e
// dietro, la pelle dello scollo) usa la stessa origine, in coordinate assolute: con l'origine di ogni gruppo (la base del
// suo ingombro) livelli diversi si muoverebbero in modo diverso e fra loro si aprirebbero fessure.
const originClass = (body) => `c-origin-${body.group}-${body.file}`;
const originCss = (body) => {
  const L = body.landmarks, x = (L['torso-bl'][0] + L['torso-br'][0]) / 2, y = L['torso-bl'][1];
  return `.c-idle-torso.${originClass(body)} { transform-box: view-box; transform-origin: ${fmt(x)}px ${fmt(y)}px }`;
};

function css(body, defaultHair, defaults, preset) {
  const vars = { ...manifest.palette, ...body.colors, ...preset?.colors };
  const cl = clothesCss(body, defaults);
  let out = styleTemplate.replace(/\{\{([\w-]+)\}\}/g, (m, k) => {
    if (k === 'hair-fills') return body.hair.map((h) => `.c-hair-${h.id} { fill: var(--hair, ${preset?.colors?.hair ?? h.color}) }`).join('\n');
    if (k === 'hair-show') return body.hair.map((h) => `#hair-${h.id} { display: var(--show-hair-${h.id}, ${h.id === defaultHair ? 'inline' : 'none'}) }`).join('\n');
    if (k === 'hair-default') return defaultHair;
    if (k === 'outfit-default') return `${defaults.top} + ${defaults.bottom}`;
    if (k === 'body-arms-default') return body.clothes.some((g) => defaults[g.kind] === g.id && g.replaces?.includes('arms')) ? 'none' : 'inline';
    if (k === 'clothes-fills') return cl.fills;
    if (k === 'clothes-show') return cl.show;
    if (k === 'idle-origin') return originCss(body);
    if (!(k in vars)) throw new Error(`style.css: segnaposto {{${k}}} senza valore per ${body.id}`);
    return vars[k];
  });
  return out.trimEnd().split('\n').map((l) => (l ? '    ' + l : l)).join('\n');
}

function compose(body) {
  const preset = manifest.presets.find((p) => p.body === body.id);
  const defaultHair = preset?.hair ?? body.hair[0].id;
  if (!body.hair.some((h) => h.id === defaultHair)) throw new Error(`preset di ${body.id}: lo stile ${defaultHair} non vale per questa sagoma`);
  const defaults = { top: preset?.top ?? 'base', bottom: preset?.bottom ?? 'base' };
  // le maglie respirano col busto (stessa animazione della maglietta base), i pantaloni stanno fermi
  // le maglie (e le loro parti sotto e dietro) respirano col busto, attorno allo stesso punto: la base del busto
  const breathe = (kind) => (kind === 'top' ? ` class="c-idle-torso ${originClass(body)}"` : '');
  const group = (kind) => body.clothes.filter((g) => g.kind === kind).map((g) => `  <!-- ${g.name} -->\n  <g id="${kind}-${g.id}"${breathe(kind)}>\n${g.content}\n  </g>`).join('\n');
  const ordered = [...body.clothes.filter((g) => g.kind === 'bottom'), ...body.clothes.filter((g) => g.kind === 'top')];
  const underlay = ordered.filter((g) => g.under).map((g) => `  <!-- ${g.name}: parti sotto i pantaloni -->\n  <g id="${g.kind}-${g.id}-under"${breathe(g.kind)}>\n${g.under}\n  </g>`).join('\n');
  // dietro alle braccia: i riempimenti di fondo della sagoma (definiti una volta, richiamati col colore di ogni capo) e le
  // parti del capo sotto le braccia
  const fillRef = { top: body.fills.top, bottom: body.fills.bottom };
  const use = (kind, cls) => (fillRef[kind] ? `    <use href="#${fillRef[kind]}" class="${cls}"/>\n` : '');
  const backlay = [
    `  <g id="pants-fill">\n${use('bottom', 'c-pants')}  </g>`, `  <g id="torso-fill"${breathe('top')}>\n${use('top', 'c-shirt')}  </g>`,
    ...ordered.map((g) => `  <!-- ${g.name}: sotto le braccia -->\n  <g id="${g.kind}-${g.id}-back"${breathe(g.kind)}>\n${use(g.kind, 'c-main')}${g.back}\n  </g>`),
  ].join('\n');
  const x0 = Math.round((body.ext[0] + body.ext[2]) / 2 - W / 2);
  const hairXml = '\n    <!-- Capelli: nel gruppo della testa (così seguono il respiro), sotto gli occhi. Stile mostrato di default: ' + defaultHair + ' -->\n' +
    '    <g id="hair">\n' + body.hair.map((h) => `      <!-- ${h.name} -->\n` + h.group.split('\n').map((l) => '    ' + l).join('\n')).join('\n') + '\n    </g>';
  // i pantaloni vanno prima delle scarpe, le maglie dopo il busto
  let inner = body.inner.replace('    <!-- @hair -->', hairXml.replace(/^\n/, '\n'))
    .replace('<g id="torso" class="c-idle-torso">', `<g id="torso"${breathe('top')}>`)
    .replace('<g id="neck-fill">', `<g id="neck-fill"${breathe('top')}>`);
  // dietro al braccio lontano: prima i riempimenti e le parti dietro, poi le parti sotto (fasce in vita, pancia scoperta)
  inner = inner.replace('  <g id="pants-under">', backlay + '\n  <g id="pants-under">');
  if (underlay) inner = inner.replace('  <g id="arm-right"', underlay + '\n  <g id="arm-right"');
  if (group('bottom')) inner = inner.replace('  <g id="shoes">', group('bottom') + '\n  <g id="shoes">');
  if (group('top')) inner = inner.replace(/\s*$/, '\n') + group('top') + '\n';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${x0} ${Y0} ${W} ${H}" width="${W}" height="${H}" role="img" aria-labelledby="t">
  <title id="t">${body.name}</title>
  <style>
${css(body, defaultHair, defaults, preset)}
  </style>

  <!-- Coordinate dei fogli di riferimento: stessa scala e stessa linea del suolo (y = 900) per tutte le sagome, quindi le altezze restano confrontabili. -->${inner}</svg>
`;
}

await rm(new URL('characters/', root), { recursive: true, force: true });
for (const b of bodies) {
  b.svg = compose(b);
  const out = new URL(`characters/${b.id}.svg`, root);
  await mkdir(dirname(out.pathname), { recursive: true });
  await writeFile(out, b.svg);
}

// ---- visualizzatore ---------------------------------------------------------
const data = {
  groups: manifest.groups,
  hair: hair.map(({ id, name, color }) => ({ id, name, color })),
  bodies: bodies.map(({ id, group, name, svg, hair: hs }) => ({ id, group, name, svg, hair: hs.map((h) => h.id) })),
  clothes: Object.fromEntries(manifest.groups.filter((g) => wardrobe(g.id).length).map((g) => [g.id, Object.fromEntries(Object.keys(KINDS).map((folder) =>
    [folder, wardrobe(g.id).filter((i) => i.kind === KINDS[folder]).map(({ id, name, replaces }) => ({ id, name, replaces: replaces ?? [] }))]))])),
  presets: manifest.presets,
};
const template = await read('src/viewer/template.html');
const token = '"__DATA__"';
if (!template.includes(token)) throw new Error(`Segnaposto ${token} non trovato in src/viewer/template.html`);
// "<" escapato per non chiudere per sbaglio il tag <script>
await writeFile(new URL('index.html', root), template.replace(token, () => JSON.stringify(data).replace(/</g, '\\u003c')));
console.log(`characters/: ${bodies.length} sagome, ${hair.length} stili di capelli (${Math.min(...bodies.map((b) => b.hair.length))}-${Math.max(...bodies.map((b) => b.hair.length))} per sagoma), vestiti: ${Object.entries(clothes).map(([g, c]) => `${g} ${c.items.length}`).join(', ') || 'nessuno'} (riquadro ${W}×${H}) · index.html generato`);
