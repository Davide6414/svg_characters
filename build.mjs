// Genera index.html incorporando character.svg nel template del visualizzatore.
// Uso: node build.mjs
import { readFile, writeFile } from 'node:fs/promises';

const svg = await readFile(new URL('./character.svg', import.meta.url), 'utf8');
const template = await readFile(new URL('./viewer.template.html', import.meta.url), 'utf8');

const token = '"__CHARACTER_SVG__"';
if (!template.includes(token)) throw new Error(`Segnaposto ${token} non trovato in viewer.template.html`);

// "<" escapato per non chiudere per sbaglio il tag <script>
const literal = JSON.stringify(svg).replace(/</g, '\\u003c');
await writeFile(new URL('./index.html', import.meta.url), template.replace(token, () => literal));
console.log('index.html generato');
