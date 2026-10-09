// Compone i personaggi e genera il visualizzatore.
//
//   src/human/   risorse umane (sagome maschili e femminili, capelli, barbe, vestiti)      → build/human.mjs
//   src/viewer/  il visualizzatore: guscio della pagina e una sezione per ogni tipo di sagoma
//
//   → characters/<gruppo>/<sagoma>.svg   ogni sagoma composta, file autonomo
//   → index.html                         visualizzatore (src/viewer/template.html + dati)
//
// Uso: node build.mjs
import { writeFile, mkdir, rm } from 'node:fs/promises';
import { dirname } from 'node:path';
import { root, read } from './build/util.mjs';
import { buildHuman } from './build/human.mjs';

const human = await buildHuman();

await rm(new URL('characters/', root), { recursive: true, force: true });
for (const { path, svg } of human.files) {
  const out = new URL(path, root);
  await mkdir(dirname(out.pathname), { recursive: true });
  await writeFile(out, svg);
}

// ---- visualizzatore ---------------------------------------------------------
const template = await read('src/viewer/template.html');
const token = '"__DATA__"';
if (!template.includes(token)) throw new Error(`Segnaposto ${token} non trovato in src/viewer/template.html`);
// "<" escapato per non chiudere per sbaglio il tag <script>
await writeFile(new URL('index.html', root), template.replace(token, () => JSON.stringify(human.data).replace(/</g, '\\u003c')));
console.log(`characters/: ${human.summary} · index.html generato`);
