// Compone i personaggi e genera il visualizzatore.
//
//   src/bodies/<gruppo>/<sagoma>.svg + .json   sagome (solo geometria + dati misurati)
//   src/hair/<stile>.svg + .json               stili di capelli (coordinate del riquadro dei capelli)
//   src/style.css                              classi dei colori, visibilità dei capelli, animazione idle
//   src/manifest.json                          gruppi, ordine, palette comune, preset
//
//   → characters/<gruppo>/<sagoma>.svg         ogni sagoma con TUTTI gli stili di capelli, file autonomo
//   → index.html                               visualizzatore (src/viewer/template.html + dati)
//
// Uso: node build.mjs
import { readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import { dirname } from 'node:path';

const root = new URL('./', import.meta.url);
const read = (path) => readFile(new URL(path, root), 'utf8');
const readJson = async (path) => JSON.parse(await read(path));

const PAIR = /(-?\d+\.?\d*),(-?\d+\.?\d*)/g;     // coppie "x,y" dei percorsi (comandi sempre assoluti)
const D_ATTR = / d="([^"]*)"/g;
const fmt = (v) => { const s = v.toFixed(1); return (s.endsWith('.0') ? s.slice(0, -2) : s).replace(/^-0$/, '0'); };
const mapPaths = (xml, f) => xml.replace(D_ATTR, (_, d) => ` d="${d.replace(PAIR, (__, x, y) => f(+x, +y).map(fmt).join(','))}"`);
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
  return { id: path, group, file, ...(await readJson(`src/bodies/${path}.json`)), inner };
}));

// ---- capelli adattati a ogni testa -----------------------------------------
// I capelli sono disegnati sulla testa di riferimento (hairFrame): per ogni sagoma si scalano in x
// (da orecchio a fronte) e in y (da cima a linea degli occhi) per far combaciare la testa. Le coordinate
// vengono riscritte, così lo spessore del contorno resta uguale ovunque.
const F = manifest.hairFrame;
function hairFor(body) {
  const { L, R, T, eyeY } = body.head;
  const sx = (R - L) / (F.R - F.L), sy = (eyeY - T) / (F.eyeY - F.T);
  const f = (x, y) => [L + sx * (x - F.L), T + sy * (y - F.T)];
  return hair.map((h) => ({ ...h, group: mapPaths(h.group, f) }));
}
for (const b of bodies) b.hair = hairFor(b);

// ---- riquadro comune: stessa scala e linea del suolo, spazio per i capelli ------------
const ext = (b) => {
  const pts = [...coords(b.inner), ...b.hair.flatMap((h) => coords(h.group))];
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  return [Math.min(...xs) - 3.5, Math.min(...ys) - 3.5, Math.max(...xs) + 3.5, Math.max(...ys) + 3.5];
};
for (const b of bodies) b.ext = ext(b);
const W = Math.ceil(Math.max(...bodies.map((b) => b.ext[2] - b.ext[0])));
const Y0 = Math.floor(Math.min(...bodies.map((b) => b.ext[1])));
const H = Math.ceil(Math.max(...bodies.map((b) => b.ext[3]))) - Y0;

// ---- composizione ----------------------------------------------------------
function css(body, defaultHair) {
  const vars = { ...manifest.palette, ...body.colors };
  let out = styleTemplate.replace(/\{\{([\w-]+)\}\}/g, (m, k) => {
    if (k === 'hair-fills') return body.hair.map((h) => `.c-hair-${h.id} { fill: var(--hair, ${h.color}) }`).join('\n');
    if (k === 'hair-show') return body.hair.map((h) => `#hair-${h.id} { display: var(--show-hair-${h.id}, ${h.id === defaultHair ? 'inline' : 'none'}) }`).join('\n');
    if (k === 'hair-default') return defaultHair;
    if (!(k in vars)) throw new Error(`style.css: segnaposto {{${k}}} senza valore per ${body.id}`);
    return vars[k];
  });
  return out.trimEnd().split('\n').map((l) => (l ? '    ' + l : l)).join('\n');
}

function compose(body) {
  const defaultHair = manifest.presets.find((p) => p.body === body.id)?.hair ?? manifest.hair[0];
  const x0 = Math.round((body.ext[0] + body.ext[2]) / 2 - W / 2);
  const hairXml = '\n    <!-- Capelli: nel gruppo della testa, così seguono il respiro. Stile mostrato di default: ' + defaultHair + ' -->\n' +
    '    <g id="hair">\n' + body.hair.map((h) => `      <!-- ${h.name} -->\n` + h.group.split('\n').map((l) => '    ' + l).join('\n')).join('\n') + '\n    </g>';
  const inner = body.inner.replace('    <!-- @hair -->', hairXml.replace(/^\n/, '\n'));
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${x0} ${Y0} ${W} ${H}" width="${W}" height="${H}" role="img" aria-labelledby="t">
  <title id="t">${body.name}</title>
  <style>
${css(body, defaultHair)}
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
  bodies: bodies.map(({ id, group, name, svg }) => ({ id, group, name, svg })),
  presets: manifest.presets,
};
const template = await read('src/viewer/template.html');
const token = '"__DATA__"';
if (!template.includes(token)) throw new Error(`Segnaposto ${token} non trovato in src/viewer/template.html`);
// "<" escapato per non chiudere per sbaglio il tag <script>
await writeFile(new URL('index.html', root), template.replace(token, () => JSON.stringify(data).replace(/</g, '\\u003c')));
console.log(`characters/: ${bodies.length} sagome × ${hair.length} stili di capelli (riquadro ${W}×${H}) · index.html generato`);
