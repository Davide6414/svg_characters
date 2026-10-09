// Audit delle combinazioni: rende ogni sagoma con ogni maglia, pantaloni e stile di capelli e cerca i difetti.
//
//   NODE_PATH=$(npm root -g) node tools/audit.mjs          (serve playwright: npm i -g playwright)
//   → audit/report.html (casi segnalati con il ritaglio del difetto) e audit/report.json
//
// Ogni combinazione si rende due volte nel browser: con i colori veri (per le immagini) e con i "colori di analisi",
// una tinta piatta per parte (pelle, capelli, maglia, pantaloni, scarpe, contorno, occhi), così ogni pixel dice a che
// parte appartiene. Il confronto è con la sagoma base (maglietta e pantaloni suoi, senza capelli):
//   vuoto nel busto / braccia / caviglie  sfondo dove la sagoma base è piena (fra le braccia, nelle braccia, sopra le scarpe)
//   fessura chiusa                    sfondo sottile racchiuso dalla figura che nella sagoma base non c'era
//   pezzo staccato                    una parte disegnata che non tocca il resto della figura
//   tagliato dal riquadro             la figura tocca il bordo del viewBox
//   estensione visibile               la parte dei pantaloni che sale sotto la maglia si vede per più di qualche px
//   livello sotto                     le parti sotto e dietro (…-under, …-back, riempimenti) coprono il braccio o sporgono
//   animazione                        i vuoti nel fotogramma estremo del respiro (busto e braccia allungati, testa su)
//   occhi coperti                     i capelli coprono gli occhi
//   export                            l'SVG esportato dal visualizzatore non è uguale a quello mostrato
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch {
  console.error('Serve playwright: npm i -g playwright, poi  NODE_PATH=$(npm root -g) node tools/audit.mjs');
  process.exit(1);
}
const root = new URL('../', import.meta.url);
const read = (p) => readFile(new URL(p, root), 'utf8');
const json = async (p) => JSON.parse(await read(p));

const manifest = await json('src/human/manifest.json');
const bodies = [];
for (const id of manifest.bodies) {
  const svg = await read(`characters/${id}.svg`);
  const meta = await json(`src/human/bodies/${id}.json`);
  bodies.push({ id, group: id.split('/')[0], name: meta.name, svg, landmarks: meta.landmarks,
                hair: manifest.hair.filter((h) => svg.includes(`<g id="hair-${h}">`)),
                beards: (manifest.beards ?? []).filter((x) => svg.includes(`<g id="beard-${x}">`)) });
}
const clothes = {};
for (const b of bodies) {
  clothes[b.id] = { tops: [{ id: 'base', name: 'Maglietta base', replaces: [] }], bottoms: [{ id: 'base', name: 'Pantaloni base', replaces: [] }] };
  for (const kind of ['tops', 'bottoms']) for (const id of manifest.clothes[b.id]?.[kind] ?? []) {
    const meta = await json(`src/human/clothes/${b.id}/${kind}/${id}.json`);
    clothes[b.id][kind].push({ id, name: meta.name, replaces: meta.replaces ?? [] });
  }
}
const hairNames = Object.fromEntries(await Promise.all(manifest.hair.map(async (h) => [h, (await json(`src/human/hair/${h}.json`)).name])));

// Soglie (px della sagoma, cioè del foglio di riferimento): sotto queste un difetto non si vede o è coperto dal tratto.
const LIMITS = { gapTrunk: 3, gapArm: 6, gapLeg: 4, newHoles: 3, floating: 3, clip: 1, pantsHigh: 22, underArm: 6,
                 underOut: 6, animGap: 8, eyes: 0.9, exportDiff: 30 };
const LABELS = {
  gapTrunk: 'Vuoto nel busto', gapArm: 'Vuoto nelle braccia', gapLeg: 'Vuoto alle caviglie', newHoles: 'Fessura chiusa',
  floating: 'Pezzo staccato', clip: 'Tagliato dal riquadro', pantsHigh: 'Estensione dei pantaloni visibile', underArm: 'Livello sotto copre il braccio',
  underOut: 'Livello sotto sporge', animGap: 'Vuoto durante il respiro', eyes: 'Occhi coperti dai capelli', exportDiff: 'Export diverso',
};

// ------------------------------------------------------------------ codice che gira nel browser
function browserSide() {
  const S = 1.5;                                  // scala di rendering
  const PAL = [[0, 0, 0], [255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0], [255, 0, 255], [0, 255, 255]];
  const BG = 0, LINE = 1, SKIN = 2, HAIR = 3, TOP = 4, PANTS = 5, SHOE = 6, EYE = 7;
  const AUDIT = { '--outline': '#000000', '--skin': '#ff0000', '--hair': '#00ff00', '--beard': '#00ff00', '--eye': '#00ffff' };
  for (const v of ['--shirt', '--shirt-trim', '--shirt-accent', '--shirt-accent2', '--shirt-under']) AUDIT[v] = '#0000ff';
  for (const v of ['--pants', '--pants-trim', '--pants-accent', '--pants-under']) AUDIT[v] = '#ffff00';
  for (const v of ['--shoe-upper-l', '--shoe-upper-r', '--shoe-toe', '--shoe-tongue', '--shoe-lace', '--shoe-sole']) AUDIT[v] = '#ff00ff';
  const ANIM = `.c-idle-torso { animation: none !important; transform: scaleY(1.014) }
    .c-idle-arm { animation: none !important; transform: scaleY(1.01) }
    .c-idle-head { animation: none !important; transform: translateY(-2px) rotate(-0.5deg) }`;
  const NO_UNDER = '[id$="-under"], [id$="-back"], [id$="-fill"] { display: none !important }';   // livelli sotto e dietro
  const THIN = 5;                                 // px: mezza larghezza massima di una fessura
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  let B, C;                                      // dati delle sagome e dei vestiti (da Node)

  function styled(b, o) {
    const g = C[b.id], scale = o.scale ?? S;
    const v = { '--idle-n': '0', ...(o.audit ? AUDIT : {}), ...(o.vars ?? {}) };
    for (const t of g.tops) v[`--show-top-${t.id}`] = t.id === o.top ? 'inline' : 'none';
    for (const t of g.bottoms) v[`--show-bottom-${t.id}`] = t.id === o.bottom ? 'inline' : 'none';
    if (o.hair) for (const h of b.hair) v[`--show-hair-${h}`] = h === o.hair ? 'inline' : 'none';
    else v['--show-hair'] = 'none';
    for (const x of b.beards ?? []) v[`--show-beard-${x}`] = x === o.beard ? 'inline' : 'none';
    const rep = [...g.tops.find((t) => t.id === o.top).replaces, ...g.bottoms.find((t) => t.id === o.bottom).replaces];
    v['--show-body-arms'] = rep.includes('arms') ? 'none' : 'inline';
    const style = Object.entries(v).map(([k, x]) => `${k}:${x}`).join(';');
    let s = b.svg.replace(/<svg xmlns="http:\/\/www.w3.org\/2000\/svg" viewBox="([^"]+)" width="(\d+)" height="(\d+)"/,
      (m, vb, w, h) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vb}" width="${w * scale}" height="${h * scale}" style="${style}"`);
    if (o.css) s = s.replace('</style>', `${o.css}\n  </style>`);
    return s;
  }

  async function raster(svg, w, h) {
    const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }));
    const img = new Image();
    img.src = url;
    await img.decode();
    canvas.width = w; canvas.height = h;
    ctx.clearRect(0, 0, w, h);
    ctx.drawImage(img, 0, 0, w, h);
    URL.revokeObjectURL(url);
    return ctx.getImageData(0, 0, w, h).data;
  }

  function classify(px, n) {
    const cls = new Uint8Array(n);
    for (let i = 0; i < n; i++) {
      if (px[4 * i + 3] < 128) continue;
      const r = px[4 * i], g = px[4 * i + 1], b = px[4 * i + 2];
      let best = 0, bd = 1e9;
      for (let k = 0; k < PAL.length; k++) {
        const d = (r - PAL[k][0]) ** 2 + (g - PAL[k][1]) ** 2 + (b - PAL[k][2]) ** 2;
        if (d < bd) { bd = d; best = k; }
      }
      cls[i] = best + 1;
    }
    return cls;
  }

  // componenti connesse di una maschera: etichette, aree, se toccano il bordo, riquadri
  function components(mask, W, H, conn8) {
    const lab = new Int32Array(W * H), area = [0], border = [false], box = [null];
    const q = new Int32Array(W * H);
    let n = 0;
    for (let s = 0; s < W * H; s++) {
      if (!mask[s] || lab[s]) continue;
      n++; let head = 0, tail = 0; q[tail++] = s; lab[s] = n;
      let a = 0, bd = false, x0 = W, y0 = H, x1 = 0, y1 = 0;
      while (head < tail) {
        const p = q[head++], x = p % W, y = (p / W) | 0; a++;
        if (x === 0 || y === 0 || x === W - 1 || y === H - 1) bd = true;
        if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          if (!dx && !dy) continue;
          if (!conn8 && dx && dy) continue;
          const nx = x + dx, ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
          const t = ny * W + nx;
          if (mask[t] && !lab[t]) { lab[t] = n; q[tail++] = t; }
        }
      }
      area.push(a); border.push(bd); box.push([x0, y0, x1, y1]);
    }
    return { lab, n, area, border, box };
  }

  function erode(mask, W, H, r) {
    let m = mask;
    for (let k = 0; k < r; k++) {
      const o = new Uint8Array(W * H);
      for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
        const i = y * W + x;
        o[i] = m[i] && m[i - 1] && m[i + 1] && m[i - W] && m[i + W] ? 1 : 0;
      }
      m = o;
    }
    return m;
  }

  // distanza (chamfer 3-4) di ogni pixel della maschera dal pixel più vicino fuori dalla maschera, in px di rendering
  function distance(mask, W, H) {
    const d = new Float32Array(W * H);
    for (let i = 0; i < W * H; i++) d[i] = mask[i] ? 1e9 : 0;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const i = y * W + x; if (!d[i]) continue;
      if (x > 0) d[i] = Math.min(d[i], d[i - 1] + 1);
      if (y > 0) { d[i] = Math.min(d[i], d[i - W] + 1); if (x > 0) d[i] = Math.min(d[i], d[i - W - 1] + 1.414); if (x < W - 1) d[i] = Math.min(d[i], d[i - W + 1] + 1.414); }
    }
    for (let y = H - 1; y >= 0; y--) for (let x = W - 1; x >= 0; x--) {
      const i = y * W + x; if (!d[i]) continue;
      if (x < W - 1) d[i] = Math.min(d[i], d[i + 1] + 1);
      if (y < H - 1) { d[i] = Math.min(d[i], d[i + W] + 1); if (x < W - 1) d[i] = Math.min(d[i], d[i + W + 1] + 1.414); if (x > 0) d[i] = Math.min(d[i], d[i + W - 1] + 1.414); }
    }
    return d;
  }

  // riquadro (coordinate della sagoma) di un insieme di pixel
  function bboxOf(idx, W, vb) {
    if (!idx.length) return null;
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const i of idx) { const x = i % W, y = (i / W) | 0; x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
    return [vb[0] + x0 / S, vb[1] + y0 / S, vb[0] + (x1 + 1) / S, vb[1] + (y1 + 1) / S].map((v) => Math.round(v));
  }

  // cavallo: prima riga sotto la vita con sfondo fra due tratti che contengono pantaloni (o gambe)
  function crotchOf(cls, W, x0, x1, y0, y1) {
    for (let y = y0 + 5; y < y1; y++) {
      const runs = []; let cur = null;
      for (let x = x0; x <= x1; x++) {
        const c = cls[y * W + x];
        if (c) { if (!cur) cur = { legs: false }; if (c === PANTS || c === SKIN) cur.legs = true; }
        else if (cur) { runs.push(cur); cur = null; }
      }
      if (cur) runs.push(cur);
      if (runs.filter((r) => r.legs).length >= 2) return y;
    }
    return y1;
  }

  // Dati fissi di una sagoma, dalla sua versione base (maglietta e pantaloni suoi, senza capelli)
  async function prepare(b) {
    const vb = b.svg.match(/viewBox="([^"]+)"/)[1].split(' ').map(Number);
    const W = Math.round(vb[2] * S), H = Math.round(vb[3] * S), N = W * H;
    const tc = (X, Y) => [Math.round((X - vb[0]) * S), Math.round((Y - vb[1]) * S)];
    const base = classify(await raster(styled(b, { top: 'base', bottom: 'base', audit: true }), W, H), N);
    const L = b.landmarks;
    const opaque = base.map((c) => (c ? 1 : 0));
    const opaqueEr = erode(opaque, W, H, Math.round(2 * S));
    const [px0] = tc(L['pants-tl'][0], 0), [px1] = tc(L['pants-tr'][0], 0);
    const [, py0] = tc(0, L['pants-tl'][1]), [, py1] = tc(0, L['pants-bl'][1]);
    const crotch = crotchOf(base, W, px0, px1, py0, py1);
    const [tx0, ny] = tc(L['torso-tl'][0], L['neck-l'][1]), [tx1, hem] = tc(L['torso-tr'][0], L['torso-bl'][1]);
    const tw = tx1 - tx0;
    const trunk = new Uint8Array(N), arm = new Uint8Array(N), leg = new Uint8Array(N);
    // il busto: fra le due braccia (lo spazio fra braccio e fianco cambia da una maglia all'altra e non è un vuoto)
    const [, ax] = [0, tc(L['armL-tr'][0], 0)[0]], [bx] = tc(L['armR-tl'][0], 0);
    const bx0 = Math.max(tx0 + Math.round(0.1 * tw), ax), bx1 = Math.min(tx1 - Math.round(0.1 * tw), bx);
    for (let y = ny; y < crotch - 3; y++) for (let x = bx0; x < bx1; x++) trunk[y * W + x] = opaqueEr[y * W + x];
    const skin = base.map((c) => (c === SKIN ? 1 : 0));
    const skinEr = erode(skin, W, H, Math.round(3 * S));
    for (const side of ['armL', 'armR']) {
      const [ax0, ay0] = tc(...L[`${side}-tl`]), [ax1, ay1] = tc(...L[`${side}-br`]);
      for (let y = ay0; y < ay1; y++) for (let x = ax0; x < ax1; x++) arm[y * W + x] = skinEr[y * W + x];
    }
    // le caviglie: per ogni colonna, la cima della scarpa (il vuoto vero è fra l'orlo e la scarpa, nella stessa colonna)
    const shoeTop = new Int32Array(W).fill(-1);
    for (let x = 0; x < W; x++) for (let y = crotch; y < H; y++) if (base[y * W + x] === SHOE) { shoeTop[x] = y; break; }
    const holes = components(base.map((c) => (c ? 0 : 1)), W, H, false);
    const baseHole = new Uint8Array(N);
    for (let i = 0; i < N; i++) if (holes.lab[i] && !holes.border[holes.lab[i]]) baseHole[i] = 1;
    let eyes = 0; for (let i = 0; i < N; i++) if (base[i] === EYE) eyes++;
    return { b, vb, W, H, N, base, trunk, arm, leg, baseHole, hem, tx0, tx1, ny, crotch, eyes, px0, px1, py0, py1, shoeTop };
  }

  // headOnly: per i capelli contano solo i difetti della testa (i vestiti sono già controllati a parte)
  function metrics(P, cls, cls2, headOnly = false, armsReplaced = false) {
    const { W, H, N, vb } = P, a = 1 / (S * S), out = {}, where = {}, pixels = {};
    const take = (key, idx, value) => { out[key] = value ?? Math.round(idx.length * a * 10) / 10; where[key] = bboxOf(idx, W, vb); pixels[key] = idx; };
    // il busto finisce al cavallo più alto fra quello della sagoma base e quello dei pantaloni scelti (lo spazio fra le
    // gambe non è un vuoto)
    const crotchEnd = (Math.min(P.crotch, crotchOf(cls, W, P.px0, P.px1, P.py0, P.py1)) - Math.round(3 * S)) * W;
    const gt = [], ga = [], gl = [];
    for (let i = 0; i < N; i++) if (!cls[i]) { if (P.trunk[i] && i < crotchEnd) gt.push(i); if (P.arm[i] && !armsReplaced) ga.push(i); }
    // vuoto alla caviglia: sfondo fra la scarpa (sotto) e la gamba o l'orlo (sopra, entro 22 px), nella stessa colonna
    for (let x = 0; x < W; x++) {
      const ys = P.shoeTop[x];
      if (ys < 0 || cls[ys * W + x] !== SHOE) continue;
      let y = ys - 1, run = [];
      while (y > ys - 22 * S && !cls[y * W + x]) run.push(y-- * W + x);
      if (run.length && y > ys - 22 * S && cls[y * W + x] && cls[y * W + x] !== SHOE) gl.push(...run);
    }
    if (!headOnly) { take('gapTrunk', gt); take('gapArm', ga); take('gapLeg', gl); }
    // buchi chiusi nuovi: solo le fessure sottili (larghe fino a 2·THIN px); uno spazio largo fra braccio e fianco è normale
    const bgMask = cls.map((c) => (c ? 0 : 1));
    const bgc = components(bgMask, W, H, false), dist = distance(bgMask, W, H), thick = new Float32Array(bgc.n + 1), nh = [];
    for (let i = 0; i < N; i++) { const l = bgc.lab[i]; if (l && !bgc.border[l] && !P.baseHole[i] && dist[i] > thick[l]) thick[l] = dist[i]; }
    const maxI = headOnly ? P.ny * W : N;
    // nei capelli lunghi lo sfondo racchiuso fra ciocche, testa e spalle (a meno di un contorno dai capelli) fa parte del
    // disegno, sono le "finestre" del foglio: non conta come fessura nuova (sono grandi e cambiano con la sagoma)
    const hairHole = new Set();
    if (headOnly) {
      const r = Math.max(1, Math.round(6 * S));        // fra i capelli e lo sfondo c'è il loro contorno (5.4 px)
      for (let i = 0; i < maxI; i++) {
        if (cls[i] !== HAIR) continue;
        const x = i % W;
        for (let d = 1; d <= r; d += 2) for (const j of [i - d, i + d, i - d * W, i + d * W]) {
          if (j >= 0 && j < N && Math.abs((j % W) - x) <= d && bgc.lab[j] && !bgc.border[bgc.lab[j]]) hairHole.add(bgc.lab[j]);
        }
      }
    }
    for (let i = 0; i < maxI; i++) {
      const l = bgc.lab[i];
      if (l && !bgc.border[l] && !P.baseHole[i] && !hairHole.has(l) && thick[l] <= THIN * S) nh.push(i);
    }
    take('newHoles', nh);
    const fg = components(cls.map((c) => (c ? 1 : 0)), W, H, true);
    let main = 0; for (let k = 1; k <= fg.n; k++) if (fg.area[k] > (fg.area[main] ?? 0)) main = k;
    const fl = []; for (let i = 0; i < N; i++) { const l = fg.lab[i]; if (l && l !== main && fg.area[l] >= 2 * S * S) fl.push(i); }
    take('floating', fl);
    const cl = []; for (let i = 0; i < N; i++) { if (!cls[i]) continue; const x = i % W, y = (i / W) | 0; if (x === 0 || y === 0 || x === W - 1) cl.push(i); }
    take('clip', cl);
    if (headOnly) return { out, where, pixels };
    if (cls2) {
      // l'estensione dei pantaloni che si vede (sopra la loro cintura): la colonna più alta, in px
      // (solo al centro del busto: ai lati, vicino alle braccia, è il riempimento di fondo che chiude una fessura)
      const ph = [], run = new Int32Array(W); let tall = 0;
      const c0 = P.tx0 + 0.2 * (P.tx1 - P.tx0), c1 = P.tx1 - 0.2 * (P.tx1 - P.tx0);
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        const i = y * W + x;
        if (x > c0 && x < c1 && cls[i] === PANTS && cls2[i] !== PANTS && cls2[i] !== LINE) { ph.push(i); run[x]++; tall = Math.max(tall, run[x]); } else run[x] = 0;
      }
      take('pantsHigh', ph, Math.round(tall / S));
      const ua = [], uoMask = new Uint8Array(N);
      for (let i = 0; i < N; i++) {
        if (cls[i] === cls2[i]) continue;
        const x = i % W;
        if (cls2[i] === SKIN && (cls[i] === TOP || cls[i] === PANTS) && (x < P.tx0 + 0.25 * (P.tx1 - P.tx0) || x > P.tx1 - 0.25 * (P.tx1 - P.tx0))) ua.push(i);
        if (!cls2[i] && cls[i] && (x < P.tx0 || x > P.tx1)) uoMask[i] = 1;
      }
      const uoEr = erode(uoMask, W, H, 1), uo = [];              // via i contorni sub-pixel
      for (let i = 0; i < N; i++) if (uoEr[i]) uo.push(i);
      take('underArm', ua); take('underOut', uo);
    }
    return { out, where, pixels };
  }

  const prepared = {};
  window.audit = {
    async init(bodies, clothes) { B = bodies; C = clothes; for (const b of B) prepared[b.id] = await prepare(b); return Object.fromEntries(B.map((b) => [b.id, { crotch: prepared[b.id].crotch / S + prepared[b.id].vb[1] }])); },
    // maglia × pantaloni (senza capelli), con e senza i livelli sotto, e nel fotogramma estremo del respiro
    async outfits(id) {
      const P = prepared[id], b = P.b, g = C[b.id], res = [];
      for (const t of g.tops) for (const bo of g.bottoms) {
        const o = { top: t.id, bottom: bo.id, audit: true };
        const cls = classify(await raster(styled(b, o), P.W, P.H), P.N);
        const cls2 = classify(await raster(styled(b, { ...o, css: NO_UNDER }), P.W, P.H), P.N);
        const rep = t.replaces.includes('arms') || bo.replaces.includes('arms');
        const m = metrics(P, cls, cls2, false, rep);
        const anim = metrics(P, classify(await raster(styled(b, { ...o, css: ANIM }), P.W, P.H), P.N), null, false, rep);
        const animGap = Math.max(0, anim.out.gapTrunk + anim.out.gapArm + anim.out.newHoles - (m.out.gapTrunk + m.out.gapArm + m.out.newHoles));
        m.out.animGap = Math.round(animGap * 10) / 10;
        m.where.animGap = anim.where.newHoles ?? anim.where.gapTrunk ?? anim.where.gapArm;
        m.pixels.animGap = [...anim.pixels.gapTrunk, ...anim.pixels.gapArm, ...anim.pixels.newHoles];
        res.push({ body: id, top: t.id, bottom: bo.id, out: m.out, where: m.where });
      }
      return res;
    },
    // capelli × maglie (pantaloni base)
    async hair(id) {
      const P = prepared[id], b = P.b, g = C[b.id], res = [];
      for (const h of b.hair) {
        let hairBase = 0;
        for (const t of g.tops) {
          const cls = classify(await raster(styled(b, { top: t.id, bottom: 'base', hair: h, audit: true }), P.W, P.H), P.N);
          const m = metrics(P, cls, null, true);
          let eyes = 0, hairPx = 0; for (let i = 0; i < P.N; i++) { if (cls[i] === EYE) eyes++; if (cls[i] === HAIR) hairPx++; }
          if (t.id === 'base') hairBase = hairPx;
          m.out.eyes = Math.round(eyes / P.eyes * 100) / 100;
          m.out.hairHidden = Math.round(Math.max(0, hairBase - hairPx) / (S * S));
          res.push({ body: id, hair: h, top: t.id, bottom: 'base', out: m.out, where: m.where });
        }
      }
      return res;
    },
    // barbe (senza capelli, maglietta e pantaloni base): contano solo i difetti della testa
    async beards(id) {
      const P = prepared[id], b = P.b, res = [];
      for (const x of b.beards) {
        const cls = classify(await raster(styled(b, { top: 'base', bottom: 'base', beard: x, audit: true }), P.W, P.H), P.N);
        const m = metrics(P, cls, null, true);
        res.push({ body: id, top: 'base', bottom: 'base', beard: x, out: m.out, where: m.where });
      }
      return res;
    },
    // immagine (colori veri) di una combinazione, con i pixel del difetto `key` in rosa
    async shot(c, key, pad = 36) {
      const P = prepared[c.body], b = P.b, s = 2;
      const W = Math.round(P.vb[2] * s), H = Math.round(P.vb[3] * s);
      const css = key === 'animGap' ? ANIM : '';
      const px = await raster(styled(b, { top: c.top, bottom: c.bottom, hair: c.hair, beard: c.beard, scale: s, css }), W, H);
      let idx = [];
      if (key && key !== 'exportDiff') {
        const o = { top: c.top, bottom: c.bottom, hair: c.hair, beard: c.beard, audit: true };
        const cls = classify(await raster(styled(b, { ...o, css }), P.W, P.H), P.N);
        const cls2 = ['underArm', 'underOut', 'pantsHigh'].includes(key) ? classify(await raster(styled(b, { ...o, css: NO_UNDER }), P.W, P.H), P.N) : null;
        const rp = [...C[b.id].tops.find((t) => t.id === c.top).replaces, ...C[b.id].bottoms.find((t) => t.id === c.bottom).replaces].includes('arms');
        const m = metrics(P, cls, cls2, !!c.hair, rp);
        idx = key === 'animGap' ? [...m.pixels.gapTrunk, ...m.pixels.gapArm, ...m.pixels.newHoles]
            : key === 'eyes' ? [] : (m.pixels[key] ?? []);
      }
      for (const i of idx) {                         // pixel (scala S) → riquadro di s×s/S pixel nell'immagine (scala s)
        const x0 = Math.floor((i % P.W) * s / S), y0 = Math.floor(((i / P.W) | 0) * s / S);
        for (let dy = 0; dy < Math.ceil(s / S); dy++) for (let dx = 0; dx < Math.ceil(s / S); dx++) {
          const j = 4 * ((y0 + dy) * W + x0 + dx);
          px[j] = 255; px[j + 1] = 20; px[j + 2] = 147; px[j + 3] = 255;
        }
      }
      const full = document.createElement('canvas'); full.width = W; full.height = H;
      full.getContext('2d').putImageData(new ImageData(px, W, H), 0, 0);
      const bx = idx.length ? bboxOf(idx, P.W, P.vb) : (c.where?.[key] ?? [P.vb[0], P.vb[1], P.vb[0] + P.vb[2], P.vb[1] + P.vb[3]]);
      const x0 = Math.max(0, (bx[0] - P.vb[0] - pad) * s), y0 = Math.max(0, (bx[1] - P.vb[1] - pad) * s);
      const x1 = Math.min(W, (bx[2] - P.vb[0] + pad) * s), y1 = Math.min(H, (bx[3] - P.vb[1] + pad) * s);
      const out = document.createElement('canvas'); out.width = x1 - x0; out.height = y1 - y0;
      const o = out.getContext('2d');
      o.fillStyle = '#fff'; o.fillRect(0, 0, out.width, out.height);
      o.drawImage(full, x0, y0, out.width, out.height, 0, 0, out.width, out.height);
      return out.toDataURL('image/png');
    },
  };
}

// ------------------------------------------------------------------ export del visualizzatore
// Nel visualizzatore (index.html): per ogni sagoma, ogni maglia, pantaloni e stile una volta, l'SVG esportato deve
// rendersi uguale al file della sagoma con le stesse variabili.
async function exportCheck(page) {
  return page.evaluate(async () => {
    const { state, bodies, variants, DATA, defaultColors, cssVars, buildExportSvg } = window.humanViewer;     // la sezione degli umani (src/viewer/human.js)
    const canvas = document.createElement('canvas'), ctx = canvas.getContext('2d', { willReadFrequently: true });
    const raster = async (svg, w, h) => {
      const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }));
      const img = new Image(); img.src = url; await img.decode();
      canvas.width = w; canvas.height = h; ctx.clearRect(0, 0, w, h); ctx.drawImage(img, 0, 0, w, h);
      URL.revokeObjectURL(url); return ctx.getImageData(0, 0, w, h).data;
    };
    const res = [];
    state.idle = false;
    for (const body of bodies) {
      const vi = variants.findIndex((x) => x.body === body);
      if (vi < 0) continue;
      const c = DATA.clothes[body.id];
      const cases = [...c.tops.map((t) => ({ top: t.id })), ...c.bottoms.map((t) => ({ bottom: t.id })), ...body.hair.map((h) => ({ hair: h }))];
      for (const k of cases) {
        state.selected = vi;
        const v = variants[vi];
        const saved = { top: v.top, bottom: v.bottom, hair: v.hair, colors: { ...v.colors } };
        Object.assign(v, k);
        v.colors = defaultColors(v);
        const exp = buildExportSvg(false);
        const style = Object.entries(cssVars(v, 0, false)).map(([a, b]) => `${a}:${b}`).join(';');
        const ref = v.body.svg.replace('<svg xmlns="http://www.w3.org/2000/svg"', `<svg xmlns="http://www.w3.org/2000/svg" style="${style}"`);
        const [a, b] = [await raster(exp, v.body.w, v.body.h), await raster(ref, v.body.w, v.body.h)];
        let diff = 0;
        for (let i = 0; i < a.length; i += 4) if (Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2]) + Math.abs(a[i + 3] - b[i + 3]) > 40) diff++;
        res.push({ body: v.body.id, top: v.top, bottom: v.bottom, hair: v.hair, out: { exportDiff: diff }, varLeft: /var\(--/.test(exp) });
        Object.assign(v, saved);
      }
    }
    return res;
  });
}

// ------------------------------------------------------------------ controlli statici dei file
async function staticChecks(page) {
  return page.evaluate((list) => {
    const issues = [];
    for (const { id, svg } of list) {
      const doc = new DOMParser().parseFromString(svg, 'image/svg+xml');
      if (doc.querySelector('parsererror')) { issues.push(`${id}: XML non valido`); continue; }
      const ids = [...doc.querySelectorAll('[id]')].map((e) => e.id);
      const dup = ids.filter((x, i) => ids.indexOf(x) !== i);
      if (dup.length) issues.push(`${id}: id ripetuti ${[...new Set(dup)].join(', ')}`);
      // ogni classe di riempimento deve avere una regola (altrimenti il percorso viene nero)
      const host = document.createElement('div');
      host.innerHTML = svg;
      document.body.append(host);
      for (const el of host.querySelectorAll('path, circle, ellipse, use')) {
        const cls = el.getAttribute('class') ?? '';
        if (/c-open/.test(cls) || el.closest('defs')) continue;      // le forme in <defs> prendono il colore da chi le usa
        if (getComputedStyle(el).fill === 'rgb(0, 0, 0)') issues.push(`${id}: "${cls}" senza colore (nero)`);
      }
      host.remove();
    }
    return [...new Set(issues)];
  }, bodies.map(({ id, svg }) => ({ id, svg })));
}

// ------------------------------------------------------------------ esecuzione
const t0 = Date.now();
const browser = await chromium.launch();
const page = await browser.newPage();
await page.setContent('<!doctype html><body></body>');
await page.addScriptTag({ content: `(${browserSide.toString()})()` });
// opzioni: --only=<parte dell'id della sagoma>, --skip=hair|outfits|beards|export (per rifare più in fretta una parte)
const only = process.argv.find((a) => a.startsWith('--only='))?.slice(7);
const skip = new Set((process.argv.find((a) => a.startsWith('--skip='))?.slice(7) ?? '').split(','));
const todo = bodies.filter((b) => !only || b.id.includes(only));
const info = await page.evaluate(([b, c]) => window.audit.init(b, c), [todo, clothes]);
const results = [];
for (const b of todo) {
  const r1 = skip.has('outfits') ? [] : await page.evaluate((id) => window.audit.outfits(id), b.id);
  const r2 = skip.has('hair') ? [] : await page.evaluate((id) => window.audit.hair(id), b.id);
  const r3 = skip.has('beards') ? [] : await page.evaluate((id) => window.audit.beards(id), b.id);
  results.push(...r1, ...r2, ...r3);
  console.log(`${b.id}: ${r1.length} combinazioni di vestiti, ${r2.length} di capelli, ${r3.length} di barbe (cavallo y ${Math.round(info[b.id].crotch)}) · ${Math.round((Date.now() - t0) / 1000)} s`);
}
const statics = await staticChecks(page);
const viewer = await browser.newPage();
await viewer.goto(new URL('index.html', root).href);
await viewer.waitForTimeout(300);
const exports = only || skip.has('export') ? [] : await exportCheck(viewer);
results.push(...exports);

// casi segnalati per categoria, dal peggiore
const flagged = {};
for (const r of results) for (const [k, v] of Object.entries(r.out)) {
  if (!(k in LIMITS)) continue;
  if (k === 'floating' && r.beard === 'barba-incolta') continue;      // i puntini della barba incolta sono staccati apposta
  const bad = k === 'eyes' ? v < LIMITS.eyes : v >= LIMITS[k];
  if (bad) (flagged[k] ??= []).push(r);
}
for (const k of Object.keys(flagged)) flagged[k].sort((a, b) => (k === 'eyes' ? a.out[k] - b.out[k] : b.out[k] - a.out[k]));

// riepilogo per capo: in quante combinazioni compare in un caso segnalato
const byItem = {};
for (const [k, list] of Object.entries(flagged)) for (const r of list) {
  for (const item of [r.top && r.top !== 'base' ? `maglia ${r.top}` : null, r.bottom && r.bottom !== 'base' ? `pantaloni ${r.bottom}` : null,
                      r.hair ? `capelli ${r.hair}` : null, r.beard ? `barba ${r.beard}` : null, `sagoma ${r.body}`].filter(Boolean)) {
    (byItem[item] ??= {})[k] = ((byItem[item] ??= {})[k] ?? 0) + 1;
  }
}

// immagini dei peggiori casi di ogni categoria (al più PER_KIND), raggruppati per capo per non ripetere lo stesso difetto
const PER_KIND = 24;
const sections = [];
for (const [k, list] of Object.entries(flagged)) {
  const seen = new Set(), pick = [];
  for (const r of list) {
    const key = k === 'eyes' || r.hair || r.beard ? `${r.hair}|${r.beard}|${r.body}` : `${r.top}|${r.bottom}`;
    const key2 = `${r.top}|${r.bottom}|${r.hair}|${r.beard}|${r.body}`;
    if (seen.has(key) || seen.has(key2)) continue;
    seen.add(key); seen.add(key2); pick.push(r);
    if (pick.length >= PER_KIND) break;
  }
  const cards = [];
  for (const r of pick) {
    const img = await page.evaluate(([c, key]) => window.audit.shot(c, key), [r, k]);
    cards.push({ r, img });
  }
  sections.push({ k, total: list.length, cards });
}

const html = `<!doctype html><html lang="it"><meta charset="utf-8"><title>Audit dei personaggi</title>
<style>body{font:14px system-ui,sans-serif;margin:24px;color:#222;background:#faf9f7}h1{margin:0 0 4px}h2{margin:28px 0 8px}
table{border-collapse:collapse;font-size:13px}td,th{border-bottom:1px solid #e3e0dc;padding:3px 8px;text-align:left}
.cards{display:flex;flex-wrap:wrap;gap:10px}.card{background:#fff;border:1px solid #e3e0dc;border-radius:8px;padding:6px;width:220px}
.card img{display:block;max-width:100%;max-height:260px;margin:0 auto}.card p{margin:4px 0 0;font-size:12px;line-height:1.35}
.muted{color:#777}</style>
<h1>Audit dei personaggi</h1>
<p class="muted">${results.length} combinazioni controllate in ${Math.round((Date.now() - t0) / 1000)} s · ${todo.length} sagome · soglie: ${Object.entries(LIMITS).map(([k, v]) => `${LABELS[k]} ${k === 'eyes' ? '<' : '≥'} ${v}`).join(' · ')}</p>
<h2>Controlli dei file</h2>${statics.length ? `<ul>${statics.map((s) => `<li>${s}</li>`).join('')}</ul>` : '<p>Nessun problema: XML valido, id unici, ogni parte ha un colore.</p>'}
<h2>Riepilogo</h2><table><tr><th>Difetto</th><th>Combinazioni</th></tr>${Object.keys(LABELS).map((k) => `<tr><td>${LABELS[k]}</td><td>${flagged[k]?.length ?? 0}</td></tr>`).join('')}</table>
<h2>Per capo</h2><table><tr><th>Capo</th>${Object.keys(LABELS).map((k) => `<th>${LABELS[k]}</th>`).join('')}</tr>${Object.entries(byItem).sort((a, b) => Object.values(b[1]).reduce((s, x) => s + x, 0) - Object.values(a[1]).reduce((s, x) => s + x, 0)).map(([item, c]) => `<tr><td>${item}</td>${Object.keys(LABELS).map((k) => `<td>${c[k] ?? ''}</td>`).join('')}</tr>`).join('')}</table>
${sections.map(({ k, total, cards }) => `<h2>${LABELS[k]} · ${total}</h2><div class="cards">${cards.map(({ r, img }) => `<div class="card">${img ? `<img src="${img}">` : ''}<p><b>${r.body}</b><br>maglia ${r.top} · pantaloni ${r.bottom}${r.hair ? ` · capelli ${r.hair}` : ''}${r.beard ? ` · barba ${r.beard}` : ''}<br>${k === 'eyes' ? `occhi visibili ${Math.round(r.out[k] * 100)}%` : `${r.out[k]}${k === 'pantsHigh' ? ' px sopra l\'orlo' : k === 'exportDiff' ? ' pixel diversi' : ' px²'}`}</p></div>`).join('')}</div>`).join('')}
</html>`;
await mkdir(new URL('audit/', root), { recursive: true });
await writeFile(new URL('audit/report.html', root), html);
await writeFile(new URL('audit/report.json', root), JSON.stringify({ limits: LIMITS, statics, flagged: Object.fromEntries(Object.entries(flagged).map(([k, l]) => [k, l.map(({ body, top, bottom, hair, beard, out, where }) => ({ body, top, bottom, hair, beard, value: out[k], where: where?.[k] }))])), results: results.map(({ body, top, bottom, hair, beard, out }) => ({ body, top, bottom, hair, beard, out })) }, null, 1));
await browser.close();
console.log(`\n${results.length} combinazioni in ${Math.round((Date.now() - t0) / 1000)} s. File: ${statics.length ? statics.length + ' problemi' : 'ok'}`);
for (const k of Object.keys(LABELS)) console.log(`  ${LABELS[k].padEnd(32)} ${flagged[k]?.length ?? 0}`);
console.log('Rapporto: audit/report.html');
