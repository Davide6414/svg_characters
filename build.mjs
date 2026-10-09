// Compone i personaggi e genera il visualizzatore.
//
//   src/human/   risorse umane (sagome maschili e femminili, capelli, barbe, vestiti)      → build/human.mjs
//   src/alien/   risorse aliene (sagome, stile, preset), separate da quelle umane                  → build/alien.mjs
//   src/viewer/  il visualizzatore: guscio della pagina e una sezione per ogni tipo di sagoma → build/viewer.mjs
//
//   → characters/<gruppo>/<sagoma>.svg          ogni sagoma umana composta, file autonomo
//   → characters/alieno/<gruppo>/<sagoma>.svg   ogni sagoma aliena composta, file autonomo
//   → index.html                         visualizzatore (src/viewer/ + i dati di ogni sezione)
//
// Uso: node build.mjs
import { writeFile, mkdir, rm } from 'node:fs/promises';
import { dirname } from 'node:path';
import { root } from './build/util.mjs';
import { buildHuman } from './build/human.mjs';
import { buildAlien } from './build/alien.mjs';
import { buildViewer } from './build/viewer.mjs';

// le due sezioni sono indipendenti: ognuna legge solo le sue risorse e non conosce l'altra
const human = await buildHuman();
const alien = await buildAlien();

await rm(new URL('characters/', root), { recursive: true, force: true });
for (const { path, svg } of [...human.files, ...alien.files]) {
  const out = new URL(path, root);
  await mkdir(dirname(out.pathname), { recursive: true });
  await writeFile(out, svg);
}

// ---- visualizzatore ---------------------------------------------------------
await writeFile(new URL('index.html', root), await buildViewer({ human: human.data, alien: alien.data }));
console.log(`characters/: ${human.summary} · ${alien.summary} · index.html generato`);
