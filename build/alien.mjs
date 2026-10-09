// Sezione "alieni": compone le sagome aliene (src/alien/), indipendente da quella degli umani.
//
//   src/alien/bodies/<gruppo>/<sagoma>.svg + .json   sagome (solo geometria + dati misurati)
//   src/alien/style.css                              classi dei colori, visibilità delle parti, animazione idle
//   src/alien/manifest.json                          gruppi, ordine, palette, spessore del contorno, preset
//
//   → { files, data, summary }: gli SVG composti (characters/alieno/<gruppo>/<sagoma>.svg), i dati del visualizzatore
//     e una riga di riepilogo. Li scrive build.mjs.
//
// Gli alieni hanno solo la maglia e i pantaloncini della sagoma (colori a piacere): niente capelli, barbe o capi da
// scegliere, quindi la composizione è più semplice di quella degli umani. Gli id delle parti cominciano con `alien-` e
// le classi dell'animazione con `c-alien-`, così il CSS di un alieno non tocca mai quello di un umano nella stessa pagina.
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
    for (const mark of ['@prot-back', '@prot']) if (!svg.includes(`<!-- ${mark} -->`)) throw new Error(`${SRC}bodies/${path}.svg: manca il segnaposto <!-- ${mark} --> (rifare con tools/trace_alien.py)`);
    const inner = svg.slice(svg.indexOf('</title>') + '</title>'.length, svg.lastIndexOf('</svg>'));
    return { id: path, group, file, ...(await readJson(`${SRC}bodies/${path}.json`)), inner };
  }));
  for (const p of manifest.presets) if (!bodies.some((b) => b.id === p.body)) throw new Error(`${SRC}manifest.json: preset "${p.name}" su una sagoma sconosciuta (${p.body})`);

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
    const pts = [...coords(b.inner), ...b.prots.flatMap((pr) => coords(pr.back + pr.front))], xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    return [Math.min(...xs) - 3.5, Math.min(...ys) - 3.5, Math.max(...xs) + 3.5, Math.max(...ys) + 3.5];
  };
  for (const b of bodies) b.ext = ext(b);
  const W = bodies.length ? Math.ceil(Math.max(...bodies.map((b) => b.ext[2] - b.ext[0]))) : 0;
  const Y0 = bodies.length ? Math.floor(Math.min(...bodies.map((b) => b.ext[1]))) : 0;
  const H = bodies.length ? Math.ceil(Math.max(...bodies.map((b) => b.ext[3]))) - Y0 : 0;

  // ---- composizione ----------------------------------------------------------
  function css(body, preset) {
    const vars = { 'line-w': manifest.lineWidth, ...manifest.palette, ...body.colors, ...preset?.colors };
    const out = styleTemplate.replace(/\{\{([\w-]+)\}\}/g, (m, k) => {
      // una protuberanza alla volta (nessuna di default, o quella del preset): --show-alien-prot-NOME (inline | none)
      if (k === 'prot-show') return body.prots.map((pr) => `${[pr.front && `#alien-prot-${pr.id}`, pr.back && `#alien-prot-${pr.id}-back`].filter(Boolean).join(', ')} { display: var(--show-alien-prot-${pr.id}, ${pr.id === preset?.prot ? 'inline' : 'none'}) }`).join('\n');
      if (!(k in vars)) throw new Error(`${SRC}style.css: segnaposto {{${k}}} senza valore per ${body.id}`);
      return vars[k];
    });
    return out.trimEnd().split('\n').map((l) => (l ? '    ' + l : l)).join('\n');
  }
  function compose(body) {
    const preset = manifest.presets.find((p) => p.body === body.id);
    const x0 = Math.round((body.ext[0] + body.ext[2]) / 2 - W / 2);
    const layer = (id, key) => {
      const parts = body.prots.filter((pr) => pr[key]).map((pr) => `      <g id="alien-prot-${pr.id}${key === 'back' ? '-back' : ''}">\n${pr[key]}\n      </g>`);
      return parts.length ? `<g id="alien-prot${key === 'back' ? '-back' : ''}">\n${parts.join('\n')}\n    </g>` : '';
    };
    const inner = body.inner.replace('<!-- @prot-back -->', () => layer('prot', 'back')).replace('<!-- @prot -->', () => layer('prot', 'front'));
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${x0} ${Y0} ${W} ${H}" width="${W}" height="${H}" role="img" aria-labelledby="t">
  <title id="t">${body.name}</title>
  <style>
${css(body, preset)}
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
      presets: manifest.presets,
    },
    summary: `alieni: ${bodies.length} sagome, ${prots.length} protuberanze, ${manifest.presets.length} personaggi di partenza (riquadro ${W}×${H})`,
  };
}
