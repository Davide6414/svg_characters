# svg_characters

Shape base di un personaggio in SVG, con un visualizzatore HTML per provare colori e varianti.

| File | Cosa fa |
| --- | --- |
| `character.svg` | **Sorgente**: il personaggio. Colori controllati da variabili CSS (`--skin`, `--shirt`, `--pants`, …) con un default ciascuno. |
| `index.html` | Visualizzatore (generato). Si apre anche con doppio clic. |
| `viewer.template.html` | Template del visualizzatore: l'SVG viene incorporato da `build.mjs`. |
| `build.mjs` | `node build.mjs` rigenera `index.html` dopo ogni modifica a `character.svg` o al template. |
| `serve.mjs` | Server statico opzionale: `node serve.mjs` → http://localhost:5191 |
| `reference/1.webp` | Immagine di riferimento da cui è stato ricavato il disegno. |

## Struttura dell'SVG

Parti separate in gruppi con `id`, dal fondo al primo piano:
`arm-right` → `pants` → `shoes` (`shoe-left`, `shoe-right`) → `arm-left` → `head` → `torso`.

Il disegno è in coordinate dell'immagine di riferimento; un `<g transform="translate(-40 -240)">` lo riporta a `0,0` (viewBox `0 0 250 655`).

## Animazione idle

Definita direttamente in `character.svg` (CSS `@keyframes`, solo `transform`), quindi parte anche aprendo il file da solo nel browser:

- **respiro**: busto e braccia si allungano di ~1% ancorati alla base, la testa si alza di 2 px con 0.14 s di ritardo (cicli di 1.9 s, andata e ritorno);
- **battito di ciglia**: gli occhi si schiacciano brevemente ogni 4.6 s.

Con `prefers-reduced-motion` l'SVG resta fermo. Nel visualizzatore c'è l'interruttore *Animazione*; il PNG esportato è sempre un fotogramma fermo.

## Variabili CSS

`--outline`, `--line-w`, `--skin`, `--shirt`, `--pants`, `--shoe-upper-l`, `--shoe-upper-r`, `--shoe-toe`, `--shoe-tongue`, `--shoe-lace`, `--shoe-sole`, `--eye`, più `--idle-n` (`0` spegne l'animazione) e `--idle-delay` (sfasa più istanze).

Il bottone *Scarica SVG* del visualizzatore scrive i valori scelti direttamente nel file, quindi il risultato si apre anche in Illustrator, Inkscape o Figma (che ignorano `var()`).
