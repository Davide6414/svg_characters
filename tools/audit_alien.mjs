// Audit degli alieni: rende ogni sagoma con ogni combinazione di maglia e pantaloni (di base o del capo) e cerca i difetti.
//
//   NODE_PATH=$(npm root -g) node tools/audit_alien.mjs          (serve playwright: npm i -g playwright)
//
// Per ogni combinazione, nel browser, su sfondo magenta:
//   vuoto nell'animazione   sfondo racchiuso dalla figura nel fotogramma estremo del respiro (busto e braccia allungati, testa su)
//                           che nella posa base non c'era: fra le parti si è aperta una fessura
//   export                  l'SVG che scarica il visualizzatore (variabili CSS risolte, parti spente tolte) non è uguale, pixel per
//                           pixel, a quello mostrato (la sagoma composta con gli stessi valori delle variabili)
// Fino a 12 px di scarto nell’export sono antialiasing. Esce con codice 1 se trova qualcosa.
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch {
  console.error('Serve playwright: npm i -g playwright, poi  NODE_PATH=$(npm root -g) node tools/audit_alien.mjs');
  process.exit(1);
}
const root = new URL('../', import.meta.url);
const manifest = JSON.parse(await readFile(new URL('src/alien/manifest.json', root), 'utf8'));
const indexUrl = new URL('index.html', root).href + '#alieni';

// variabili di visibilità di una combinazione (come le imposta il visualizzatore)
function varsFor(clothes, top, bottom) {
  const { tops, bottoms } = clothes;
  const v = { '--idle-n': '0' };
  for (const id of ['base', ...tops]) v[`--show-alien-top-${id}`] = top === id ? 'inline' : 'none';
  for (const id of ['base', ...bottoms]) v[`--show-alien-bottom-${id}`] = bottom === id ? 'inline' : 'none';
  for (const id of tops) v[`--show-alien-top-${id}-under`] = top === id && bottom === 'base' ? 'inline' : 'none';
  for (const id of bottoms) v[`--show-alien-bottom-${id}-under`] = bottom === id && top === 'base' ? 'inline' : 'none';
  v['--show-alien-base-arms'] = top === 'base' ? 'inline' : 'none';
  v['--show-alien-base-legs'] = bottom === 'base' ? 'inline' : 'none';
  return v;
}
const style = (v) => Object.entries(v).map(([k, x]) => `${k}:${x}`).join(';');

// nel browser: sfondo racchiuso (magenta non collegato al bordo) in due immagini; restituisce le componenti nuove della seconda
const ANALYZE = async ([a, b, scale]) => {
  const load = async (url) => {
    const bmp = await createImageBitmap(await (await fetch(url)).blob());
    const c = document.createElement('canvas');
    c.width = Math.floor(bmp.width / scale); c.height = Math.floor(bmp.height / scale);
    const g = c.getContext('2d'); g.drawImage(bmp, 0, 0, c.width, c.height);
    return { w: c.width, h: c.height, d: g.getImageData(0, 0, c.width, c.height).data };
  };
  const enclosed = (img) => {
    const { w, h, d } = img, mag = new Uint8Array(w * h);
    for (let i = 0; i < w * h; i++) mag[i] = d[i * 4] > 235 && d[i * 4 + 1] < 45 && d[i * 4 + 2] > 235 ? 1 : 0;
    const lab = new Int32Array(w * h), sizes = [0], border = new Set();
    for (let s = 0; s < w * h; s++) {
      if (!mag[s] || lab[s]) continue;
      const id = sizes.length; let n = 0; const q = [s]; lab[s] = id;
      while (q.length) {
        const p = q.pop(); n++;
        const x = p % w, y = (p / w) | 0;
        if (x === 0 || y === 0 || x === w - 1 || y === h - 1) border.add(id);
        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const nx = x + dx, ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
          const j = ny * w + nx;
          if (mag[j] && !lab[j]) { lab[j] = id; q.push(j); }
        }
      }
      sizes.push(n);
    }
    return { lab, sizes, border, w, h };
  };
  const A = enclosed(await load(a)), B = enclosed(await load(b));
  // vicinanza ai vuoti della posa base (si spostano di poco quando le parti si allungano)
  const near = new Uint8Array(A.w * A.h);
  for (let i = 0; i < A.w * A.h; i++) if (A.lab[i] && !A.border.has(A.lab[i])) {
    const x = i % A.w, y = (i / A.w) | 0;
    for (let dy = -8; dy <= 8; dy++) for (let dx = -8; dx <= 8; dx++) {
      const nx = x + dx, ny = y + dy;
      if (nx >= 0 && ny >= 0 && nx < A.w && ny < A.h) near[ny * A.w + nx] = 1;
    }
  }
  const fresh = new Map();
  for (let i = 0; i < B.w * B.h; i++) if (B.lab[i] && !B.border.has(B.lab[i]) && !near[i]) fresh.set(B.lab[i], (fresh.get(B.lab[i]) ?? 0) + 1);
  return [...fresh.values()];
};
// nel browser: pixel diversi fra due immagini
const DIFF = async ([a, b]) => {
  const load = async (url) => {
    const bmp = await createImageBitmap(await (await fetch(url)).blob());
    const c = document.createElement('canvas'); c.width = bmp.width; c.height = bmp.height;
    const g = c.getContext('2d'); g.drawImage(bmp, 0, 0);
    return g.getImageData(0, 0, c.width, c.height);
  };
  const A = await load(a), B = await load(b);
  if (A.width !== B.width || A.height !== B.height) return -1;
  let n = 0;
  for (let i = 0; i < A.data.length; i += 4) if (Math.abs(A.data[i] - B.data[i]) + Math.abs(A.data[i + 1] - B.data[i + 1]) + Math.abs(A.data[i + 2] - B.data[i + 2]) > 150) n++;
  return n;
};

const browser = await chromium.launch();
const shot = await browser.newPage({ deviceScaleFactor: 3 });
const tool = await browser.newPage();
const viewer = await browser.newPage({ viewport: { width: 1280, height: 1000 }, reducedMotion: 'reduce' });
await viewer.addInitScript(() => { window.__copied = []; navigator.clipboard.writeText = async (t) => { window.__copied.push(t); }; });
await viewer.goto(indexUrl);
await viewer.waitForTimeout(400);
const only = process.env.AUDIT_ONLY;
const dataUrl = (buf) => `data:image/png;base64,${buf.toString('base64')}`;

let cases = 0;
const problems = [];
for (const body of manifest.bodies.filter((b) => !only || b.includes(only))) {
  const clothes = manifest.clothes?.[body] ?? { tops: [], bottoms: [] };
  const svg = (await readFile(new URL(`characters/alieno/${body}.svg`, root), 'utf8')).replace(/^<\?xml[^>]*>\s*/, '');
  await viewer.check(`input[name="alien-body"][value="${body}"]`);
  for (const top of ['base', ...clothes.tops]) for (const bottom of ['base', ...clothes.bottoms]) {
    cases++;
    const label = `${body} · ${top} + ${bottom}`;
    const v = varsFor(clothes, top, bottom);
    await shot.setContent(`<body style="margin:0;background:#ff00ff">${svg.replace('<svg ', `<svg style="${style(v)}" `)}</body>`);
    const el = await shot.$('svg');
    const base = await el.screenshot();
    await shot.addStyleTag({ content: `.c-alien-torso { animation: none !important; transform: scaleY(1.014) }
      .c-alien-arm { animation: none !important; transform: scaleY(1.01) }
      .c-alien-head { animation: none !important; transform: translateY(-2px) rotate(-0.5deg) }` });
    const extreme = await el.screenshot();
    const holes = (await tool.evaluate(ANALYZE, [dataUrl(base), dataUrl(extreme), 3])).filter((n) => n >= 3);
    if (holes.length) problems.push(`${label}: vuoto nell'animazione (${holes.join(', ')} px)`);

    // export: scelta nel visualizzatore → SVG scaricato, reso su sfondo bianco, contro la sagoma composta con gli stessi valori
    await viewer.check(`input[name="alien-top"][value="${top}"]`);
    await viewer.check(`input[name="alien-bottom"][value="${bottom}"]`);
    await viewer.click('#alien-copy-svg');
    const exported = await viewer.evaluate(() => window.__copied.at(-1));
    const white = (markup) => `<body style="margin:0;background:#fff">${markup}</body>`;
    await shot.setContent(white(exported.replace(/^<\?xml[^>]*>\s*/, '')));
    const a = await (await shot.$('svg')).screenshot();
    const vv = { ...v, '--line-w': manifest.lineWidth };
    await shot.setContent(white(svg.replace('<svg ', `<svg style="${style(vv)}" `)));
    const b = await (await shot.$('svg')).screenshot();
    const diff = await tool.evaluate(DIFF, [dataUrl(a), dataUrl(b)]);
    if (process.env.AUDIT_DEBUG && diff !== 0) { const fs = await import('node:fs'); fs.writeFileSync('/tmp/audit_a.png', a); fs.writeFileSync('/tmp/audit_b.png', b); fs.writeFileSync('/tmp/audit_export.svg', exported); }
    if (diff < 0 || diff > 12) problems.push(`${label}: export diverso da quello mostrato (${diff < 0 ? 'dimensioni' : diff + ' px'})`);
  }
}
await browser.close();
console.log(`${cases} combinazioni controllate in ${manifest.bodies.length} sagome`);
if (problems.length) { console.log(problems.join('\n')); process.exit(1); }
console.log('nessun difetto');
