// Genera index.html incorporando i personaggi (characters/*.svg) nel template del visualizzatore.
// Uso: node build.mjs
import { readFile, writeFile } from 'node:fs/promises';

// Ordine di visualizzazione = ordine dei tasti 1–5 del visualizzatore
const ORDER = ['bambino', 'ragazzo', 'slanciato', 'adulto', 'robusto'];

const characters = await Promise.all(ORDER.map(async (id) => ({
  id,
  svg: await readFile(new URL(`./characters/${id}.svg`, import.meta.url), 'utf8'),
})));
const template = await readFile(new URL('./viewer.template.html', import.meta.url), 'utf8');

const token = '"__CHARACTERS__"';
if (!template.includes(token)) throw new Error(`Segnaposto ${token} non trovato in viewer.template.html`);

// "<" escapato per non chiudere per sbaglio il tag <script>
const literal = JSON.stringify(characters).replace(/</g, '\\u003c');
await writeFile(new URL('./index.html', import.meta.url), template.replace(token, () => literal));
console.log(`index.html generato (${characters.length} personaggi)`);
