// Sezione "alieni": compone le sagome aliene (src/alien/), indipendente da quella degli umani.
//
//   src/alien/bodies/<gruppo>/<sagoma>.svg + .json   sagome (solo geometria + dati misurati)
//   src/alien/style.css                              classi dei colori, visibilità delle parti, animazione idle
//   src/alien/manifest.json                          gruppi, ordine, palette, spessore del contorno, preset
//
//   → { files, data, summary }: gli SVG composti (characters/alieno/<gruppo>/<sagoma>.svg), i dati del visualizzatore
//     e una riga di riepilogo. Li scrive build.mjs.
//
//   src/alien/clothes/<gruppo>/<sagoma>/{tops,bottoms}/<id>.svg + .json   i capi di quella sagoma (e solo di quella)
//   src/alien/protrusions/<id>.svg + .json                                 corna, pinne, antenne (sulla testa di riferimento)
//
// Niente capelli né barbe: la testa ha le protuberanze, il corpo la maglietta e i pantaloncini della sagoma oppure un capo
// (maglia e pantaloni/gonna, disegnati sulla sagoma stessa). Un capo porta con sé le parti del corpo che scopre e quelle
// della sagoma nasconde (le braccia di una maglia, le gambe di dei pantaloni): la sagoma ha un gruppo `alien-base-…` per
// ognuna, che il CSS spegne quando il capo le sostituisce. Gli id delle parti cominciano con `alien-` e le classi
// dell'animazione con `c-alien-`, così il CSS di un alieno non tocca mai quello di un umano nella stessa pagina.
import { read, readJson, fmt, coords, mapPaths } from './util.mjs';

const SRC = 'src/alien/';
const PARTS = ['alien-head', 'alien-torso', 'alien-arm-left', 'alien-arm-right', 'alien-pants', 'alien-legs'];

export async function buildAlien() {
  const manifest = await readJson(SRC + 'manifest.json');
  const styleTemplate = await read(SRC + 'style.css');

  const bodies = await Promise.all(manifest.bodies.map(async (path) => {
    const [group, file] = path.split('/');
    if (!manifest.groups.some((g) => g.id === group)) throw new Error(`${SRC}manifest.json: gruppo sconosciuto in ${path}`);
    const svg = await read(`${SRC}bodies/${path}.svg`);
    for (const id of PARTS) if (!svg.includes(`id="${id}"`)) throw new Error(`${SRC}bodies/${path}.svg: manca la parte ${id}`);
    for (const mark of ['@prot-back', '@prot', '@back', '@top', '@bottom', '@arm-left', '@arm-right', '@leg-left', '@leg-right']) if (!svg.includes(`<!-- ${mark} -->`)) throw new Error(`${SRC}bodies/${path}.svg: manca il segnaposto <!-- ${mark} --> (rifare con tools/trace_alien.py)`);
    const inner = svg.slice(svg.indexOf('</title>') + '</title>'.length, svg.lastIndexOf('</svg>'));
    return { id: path, group, file, ...(await readJson(`${SRC}bodies/${path}.json`)), inner };
  }));
  for (const p of manifest.presets) if (!bodies.some((b) => b.id === p.body)) throw new Error(`${SRC}manifest.json: preset "${p.name}" su una sagoma sconosciuta (${p.body})`);

  // ---- vestiti -----------------------------------------------------------------------------
  // Ogni capo ('top' = maglia, 'bottom' = pantaloni o gonna) appartiene a UNA sagoma ed è disegnato su di essa (stesse coordinate): sta
  // in src/alien/clothes/<gruppo>/<sagoma>/ e si vede solo su quella. Il suo SVG ha i gruppi `garment` (davanti), `back` (dietro le
  // braccia: la coda di un mantello), `under` (dietro i pantaloncini: la maglia che scende), e le parti del corpo che sostituisce:
  // `arm-left`/`arm-right` (maglie), `leg-left`/`leg-right` (pantaloni). Il manifest elenca i capi di ogni sagoma.
  const KINDS = [['top', 'tops'], ['bottom', 'bottoms']];
  const REPLACED = { top: { arms: ['arm-left', 'arm-right'] }, bottom: { legs: ['leg-left', 'leg-right'] } };
  for (const b of bodies) {
    b.clothes = [];
    const listed = manifest.clothes?.[b.id] ?? {};
    for (const [kind, folder] of KINDS) {
      for (const id of listed[folder] ?? []) {
        const dir = `${SRC}clothes/${b.id}/${folder}/${id}`;
        const svg = await read(`${dir}.svg`);
        const group = (gid) => svg.match(new RegExp(`<g id="${gid}">\\n([\\s\\S]*?)\\n  </g>`))?.[1] ?? '';
        const meta = await readJson(`${dir}.json`);
        const g = { id, kind, ...meta, front: group('garment'), back: group('back'), under: group('under') };
        g.parts = {};
        for (const part of meta.replaces ?? []) {
          if (!REPLACED[kind][part]) throw new Error(`${dir}.json: un capo "${kind}" non può sostituire "${part}"`);
          for (const gid of REPLACED[kind][part]) {
            g.parts[gid] = group(gid);
            if (!g.parts[gid]) throw new Error(`${dir}.svg: manca il gruppo ${gid} (il capo sostituisce ${part})`);
          }
        }
        if (kind === 'bottom' && g.back) throw new Error(`${dir}.svg: il livello back dei pantaloni non è gestito`);
        b.clothes.push(g);
      }
    }
  }
  for (const p of manifest.presets) {
    const b = bodies.find((x) => x.id === p.body);
    for (const [kind, folder] of KINDS) if (p[kind] && !b.clothes.some((g) => g.kind === kind && g.id === p[kind])) throw new Error(`${SRC}manifest.json: preset "${p.name}": ${kind} sconosciuto (${p[kind]})`);
  }

  // ---- protuberanze (corna, palchi, pinne, creste) ---------------------------------------------
  // Disegnate una volta sola sulla testa di riferimento (`frame` nel loro .json: posizione e distanza degli occhi, cima e altezza
  // degli occhi), come i capelli degli umani: per ogni sagoma si spostano e si scalano con le stesse misure della sua testa. Un
  // percorso `c-behind` sta dietro la testa (la base continua dentro il cranio, dove la testa lo copre), gli altri davanti.
  const prots = await Promise.all((manifest.protrusions ?? []).map(async (id) => {
    const svg = await read(`${SRC}protrusions/${id}.svg`);
    const whole = svg.match(/<g id="prot-[\s\S]*<\/g>/)?.[0];
    if (!whole) throw new Error(`${SRC}protrusions/${id}.svg: gruppo <g id="prot-…"> non trovato`);
    const rows = whole.split('\n').slice(1, -1).filter((l) => l.trim());
    const behind = rows.filter((l) => l.includes('c-behind'));
    return { id, ...(await readJson(`${SRC}protrusions/${id}.json`)), back: behind.join('\n'), front: rows.filter((l) => !behind.includes(l)).join('\n') };
  }));
  const frame = prots[0]?.frame;
  for (const pr of prots) if (JSON.stringify(pr.frame) !== JSON.stringify(frame)) throw new Error(`${SRC}protrusions/${pr.id}.json: testa di riferimento diversa dalle altre (rifare con tools/trace_protrusions.py)`);
  for (const p of manifest.presets) if (p.prot && !prots.some((pr) => pr.id === p.prot)) throw new Error(`${SRC}manifest.json: preset "${p.name}": protuberanza sconosciuta (${p.prot})`);
  function protsFor(body) {
    const { skullX, skullHalf, T } = body.head, k = skullHalf / frame.skullHalf;      // scala uniforme: cima e centro del cranio
    const f = (x, y) => [skullX + k * (x - frame.skullX), T + k * (y - frame.T)];
    return prots.map((pr) => ({ ...pr, back: mapPaths(pr.back, f), front: mapPaths(pr.front, f) }));
  }
  for (const b of bodies) b.prots = protsFor(b);

  // ---- riquadro comune: stessa scala e linea del suolo, uguale per tutte le sagome -------------
  const ext = (b) => {
    const pts = [...coords(b.inner), ...b.prots.flatMap((pr) => coords(pr.back + pr.front)), ...b.clothes.flatMap((g) => coords(g.front + g.back + g.under + Object.values(g.parts).join('')))], xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    return [Math.min(...xs) - 3.5, Math.min(...ys) - 3.5, Math.max(...xs) + 3.5, Math.max(...ys) + 3.5];
  };
  for (const b of bodies) b.ext = ext(b);
  const W = bodies.length ? Math.ceil(Math.max(...bodies.map((b) => b.ext[2] - b.ext[0]))) : 0;
  const Y0 = bodies.length ? Math.floor(Math.min(...bodies.map((b) => b.ext[1]))) : 0;
  const H = bodies.length ? Math.ceil(Math.max(...bodies.map((b) => b.ext[3]))) - Y0 : 0;

  // ---- composizione ----------------------------------------------------------
  // colori per ruolo dei capi: --shirt (maglia) e --pants (pantaloni) sono il colore principale, le altre variabili i ruoli secondari;
  // la visibilità si sceglie con --show-alien-top-<id> / --show-alien-bottom-<id> ('base' = la maglietta e i pantaloncini della sagoma)
  const ROLE_VAR = { top: { main: '--shirt', trim: '--shirt-trim', accent: '--shirt-accent', accent2: '--shirt-accent2' },
                     bottom: { main: '--pants', trim: '--pants-trim', accent: '--pants-accent', accent2: '--pants-accent2' } };
  const layersOf = (g) => ['', ...(g.back ? ['-back'] : []), ...(g.under ? ['-under'] : [])].map((x) => `#alien-${g.kind}-${g.id}${x}`);
  // la fascia `under` (la maglia che scende, i pantaloni che salgono) serve solo con la maglietta o i pantaloncini di base dall'altra parte:
  // un abito intero (maglia e pantaloni della stessa figura) combacia da sé, e la fascia sporgerebbe dove nel foglio c'è lo sfondo
  function clothesCss(body, defaults) {
    const fills = body.clothes.flatMap((g) => Object.entries(g.colors).map(([role, color]) => {
      if (!ROLE_VAR[g.kind][role]) throw new Error(`${SRC}clothes/${body.id}: ${g.id}: ruolo di colore sconosciuto (${role})`);
      // il gruppo del capo per ultimo: il visualizzatore legge il colore di default da "#alien-top-<id> .c-<ruolo> {"
      return `${[...layersOf(g).slice(1), layersOf(g)[0]].map((id) => `${id} .c-${role}`).join(', ')} { fill: var(${ROLE_VAR[g.kind][role]}, ${color}) }`;
    }));
    const replaced = (kind) => body.clothes.some((g) => g.kind === kind && defaults[kind] === g.id);
    const gone = (part) => body.clothes.some((g) => defaults[g.kind] === g.id && g.replaces?.includes(part));
    const show = [
      `#alien-base-torso { display: var(--show-alien-top-base, ${defaults.top === 'base' ? 'inline' : 'none'}) }`,
      `.alien-neckfill { display: var(--show-alien-top-base, ${defaults.top === 'base' ? 'inline' : 'none'}) }`,
      `#alien-base-pants { display: var(--show-alien-bottom-base, ${defaults.bottom === 'base' ? 'inline' : 'none'}) }`,
      `.alien-base-arms { display: var(--show-alien-base-arms, ${gone('arms') ? 'none' : 'inline'}) }`,
      `.alien-base-legs { display: var(--show-alien-base-legs, ${gone('legs') ? 'none' : 'inline'}) }`,
      ...body.clothes.map((g) => `${[`#alien-${g.kind}-${g.id}`, ...(g.back ? [`#alien-${g.kind}-${g.id}-back`] : []), ...Object.keys(g.parts).map((p) => `#alien-${g.kind}-${g.id}-${p}`)].join(', ')} { display: var(--show-alien-${g.kind}-${g.id}, ${defaults[g.kind] === g.id ? 'inline' : 'none'}) }`),
      ...body.clothes.filter((g) => g.under).map((g) => `#alien-${g.kind}-${g.id}-under { display: var(--show-alien-${g.kind}-${g.id}-under, ${defaults[g.kind] === g.id && defaults[g.kind === 'top' ? 'bottom' : 'top'] === 'base' ? 'inline' : 'none'}) }`),
    ];
    return { fills: fills.join('\n'), show: show.join('\n') };
  }

  // Il respiro allunga il busto attorno alla sua base. Tutto ciò che sta sul busto (maglietta, maglie, le loro parti dietro e sotto)
  // usa la stessa origine, in coordinate assolute: con l'origine di ogni gruppo (la base del suo ingombro, che cambia col capo scelto)
  // livelli diversi si muoverebbero in modo diverso e fra loro si aprirebbero fessure.
  const originClass = (body) => `c-alien-o-${body.group}-${body.file}`;
  const originCss = (body) => {
    const L = body.landmarks, x = (L['torso-bl'][0] + L['torso-br'][0]) / 2, y = L['torso-bl'][1];
    return `.c-alien-torso.${originClass(body)} { transform-box: view-box; transform-origin: ${fmt(x)}px ${fmt(y)}px }`;
  };
  function css(body, preset, defaults) {
    const vars = { 'line-w': manifest.lineWidth, ...manifest.palette, ...body.colors, ...preset?.colors };
    const cl = clothesCss(body, defaults);
    const out = styleTemplate.replace(/\{\{([\w-]+)\}\}/g, (m, k) => {
      // una protuberanza alla volta (nessuna di default, o quella del preset): --show-alien-prot-NOME (inline | none)
      if (k === 'prot-show') return body.prots.map((pr) => `${[pr.front && `#alien-prot-${pr.id}`, pr.back && `#alien-prot-${pr.id}-back`].filter(Boolean).join(', ')} { display: var(--show-alien-prot-${pr.id}, ${pr.id === preset?.prot ? 'inline' : 'none'}) }`).join('\n');
      if (k === 'clothes-fills') return cl.fills;
      if (k === 'clothes-show') return cl.show;
      if (k === 'idle-origin') return originCss(body);
      if (!(k in vars)) throw new Error(`${SRC}style.css: segnaposto {{${k}}} senza valore per ${body.id}`);
      return vars[k];
    });
    return out.trimEnd().split('\n').map((l) => (l ? '    ' + l : l)).join('\n');
  }
  const indent = (text, n) => text.split('\n').map((l) => (l ? ' '.repeat(n) + l : l)).join('\n');
  function compose(body) {
    const preset = manifest.presets.find((p) => p.body === body.id);
    const defaults = { top: preset?.top ?? 'base', bottom: preset?.bottom ?? 'base' };
    const x0 = Math.round((body.ext[0] + body.ext[2]) / 2 - W / 2);
    const layer = (id, key) => {
      const parts = body.prots.filter((pr) => pr[key]).map((pr) => `      <g id="alien-prot-${pr.id}${key === 'back' ? '-back' : ''}">\n${pr[key]}\n      </g>`);
      return parts.length ? `<g id="alien-prot${key === 'back' ? '-back' : ''}">\n${parts.join('\n')}\n    </g>` : '';
    };
    // i capi: davanti (maglie sul busto, pantaloni al posto dei pantaloncini), dietro e sotto (con il busto, ma più indietro) e
    // le parti del corpo che sostituiscono, dentro il gruppo della parte di cui prendono il posto
    const tops = body.clothes.filter((g) => g.kind === 'top'), bottoms = body.clothes.filter((g) => g.kind === 'bottom');
    const wrap = (items, make) => items.map(make).filter(Boolean).join('\n');
    const group = (id, content, pad = 4) => (content ? `${' '.repeat(pad)}<g id="${id}">\n${indent(content, 2)}\n${' '.repeat(pad)}</g>` : '');
    const behind = tops.filter((g) => g.back || g.under);
    const backXml = behind.length ? `<g id="alien-back" class="c-alien-torso ${originClass(body)}">\n${wrap(behind, (g) => [group(`alien-top-${g.id}-back`, g.back), group(`alien-top-${g.id}-under`, g.under)].filter(Boolean).join('\n'))}\n  </g>` : '';
    const replace = (mark, kindList, part) => wrap(kindList, (g) => group(`alien-${g.kind}-${g.id}-${part}`, g.parts[part], mark.startsWith('leg') ? 6 : 4));
    let inner = body.inner.replace('<!-- @prot-back -->', () => layer('prot', 'back')).replace('<!-- @prot -->', () => layer('prot', 'front'))
      .replace('<g id="alien-torso" class="c-alien-torso">', `<g id="alien-torso" class="c-alien-torso ${originClass(body)}">`)
      .replace('<!-- @back -->', () => backXml)
      .replace('<!-- @top -->', () => wrap(tops, (g) => group(`alien-top-${g.id}`, g.front)))
      .replace('<!-- @bottom -->', () => wrap(bottoms, (g) => [group(`alien-bottom-${g.id}-under`, g.under), group(`alien-bottom-${g.id}`, g.front)].filter(Boolean).join('\n')));
    for (const part of ['arm-left', 'arm-right']) inner = inner.replace(`<!-- @${part} -->`, () => replace(part, tops, part));
    for (const part of ['leg-left', 'leg-right']) inner = inner.replace(`<!-- @${part} -->`, () => replace(part, bottoms, part));
    inner = inner.split('\n').filter((l) => !/^\s*<!-- @[\w-]+ -->\s*$/.test(l) || l.trim() === '').join('\n').replace(/\n\s*\n/g, '\n');
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${x0} ${Y0} ${W} ${H}" width="${W}" height="${H}" role="img" aria-labelledby="t">
  <title id="t">${body.name}</title>
  <style>
${css(body, preset, defaults)}
  </style>

  <!-- Stessa scala e stessa linea del suolo (y = 900) per tutte le sagome aliene (e per quelle umane), quindi le altezze restano confrontabili. -->${inner}</svg>
`;
  }
  for (const b of bodies) b.svg = compose(b);

  // ---- risultato: gli SVG composti, i dati del visualizzatore e il riepilogo ---------
  return {
    files: bodies.map((b) => ({ path: `characters/alieno/${b.id}.svg`, svg: b.svg })),
    data: {
      groups: manifest.groups,
      lineWidth: manifest.lineWidth,
      protrusions: prots.map(({ id, name }) => ({ id, name })),
      bodies: bodies.map(({ id, group, name, svg, prots: ps }) => ({ id, group, name, svg, protrusions: ps.map((pr) => pr.id) })),
      clothes: Object.fromEntries(bodies.map((b) => [b.id, Object.fromEntries(KINDS.map(([kind, folder]) => [folder, b.clothes.filter((g) => g.kind === kind).map((g) => ({ id: g.id, name: g.name, roles: Object.keys(g.colors), replaces: g.replaces ?? [] }))]))])),
      presets: manifest.presets,
    },
    summary: `alieni: ${bodies.length} sagome, ${bodies.reduce((n, b) => n + b.clothes.length, 0)} capi, ${prots.length} protuberanze, ${manifest.presets.length} personaggi di partenza (riquadro ${W}×${H})`,
  };
}
