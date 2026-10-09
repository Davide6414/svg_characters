// Il visualizzatore (index.html): il guscio della pagina (src/viewer/template.html) con una sezione per ogni tipo di sagoma.
//
//   src/viewer/template.html   intestazione, schede delle sezioni, stili comuni
//   src/viewer/common.js       utilità comuni: colori rapidi, export, cambio di sezione
//   src/viewer/human.html + human.js   sezione degli umani (pannello e script)
//   src/viewer/alien.html + alien.js   sezione degli alieni (pannello e script)
//
// Le sezioni non si conoscono: ognuna ha i suoi id (quelli degli alieni cominciano con `alien-`) e il suo script, chiuso
// in una funzione per non condividere nomi. I dati di entrambe (`{ human, alien }`) vanno incorporati una volta sola.
import { read } from './util.mjs';

const SECTIONS = ['human', 'alien'];

export async function buildViewer(data) {
  let html = await read('src/viewer/template.html');
  const put = (token, text) => {
    if (!html.includes(token)) throw new Error(`src/viewer/template.html: manca il segnaposto ${token}`);
    html = html.replace(token, () => text);
  };
  for (const id of SECTIONS) put(`<!-- @section ${id} -->`, (await read(`src/viewer/${id}.html`)).trimEnd());
  put('<!-- @script common -->', `<script>\n${(await read('src/viewer/common.js')).trimEnd()}\n</script>`);
  for (const id of SECTIONS) put(`<!-- @script ${id} -->`, `<script>\n(() => {\n${(await read(`src/viewer/${id}.js`)).trimEnd()}\n})();\n</script>`);
  // "<" escapato per non chiudere per sbaglio il tag <script>
  put('"__DATA__"', JSON.stringify(data).replace(/</g, '\\u003c'));
  return html;
}
