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
import { read, readJson, fmt, coords } from './util.mjs';

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
    const inner = svg.slice(svg.indexOf('</title>') + '</title>'.length, svg.lastIndexOf('</svg>'));
    return { id: path, group, file, ...(await readJson(`${SRC}bodies/${path}.json`)), inner };
  }));
  for (const p of manifest.presets) if (!bodies.some((b) => b.id === p.body)) throw new Error(`${SRC}manifest.json: preset "${p.name}" su una sagoma sconosciuta (${p.body})`);

  // ---- riquadro comune: stessa scala e linea del suolo, uguale per tutte le sagome -------------
  const ext = (b) => {
    const pts = coords(b.inner), xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
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
      if (!(k in vars)) throw new Error(`${SRC}style.css: segnaposto {{${k}}} senza valore per ${body.id}`);
      return vars[k];
    });
    return out.trimEnd().split('\n').map((l) => (l ? '    ' + l : l)).join('\n');
  }
  function compose(body) {
    const preset = manifest.presets.find((p) => p.body === body.id);
    const x0 = Math.round((body.ext[0] + body.ext[2]) / 2 - W / 2);
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${x0} ${Y0} ${W} ${H}" width="${W}" height="${H}" role="img" aria-labelledby="t">
  <title id="t">${body.name}</title>
  <style>
${css(body, preset)}
  </style>

  <!-- Stessa scala e stessa linea del suolo (y = 900) per tutte le sagome aliene (e per quelle umane), quindi le altezze restano confrontabili. -->${body.inner}</svg>
`;
  }
  for (const b of bodies) b.svg = compose(b);

  // ---- risultato: gli SVG composti, i dati del visualizzatore e il riepilogo ---------
  return {
    files: bodies.map((b) => ({ path: `characters/alieno/${b.id}.svg`, svg: b.svg })),
    data: {
      groups: manifest.groups,
      lineWidth: manifest.lineWidth,
      bodies: bodies.map(({ id, group, name, svg }) => ({ id, group, name, svg })),
      presets: manifest.presets,
    },
    summary: `alieni: ${bodies.length} sagome, ${manifest.presets.length} personaggi di partenza (riquadro ${W}×${H})`,
  };
}
