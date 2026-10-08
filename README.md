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
| `reference/capelli.webp` | Immagine di ispirazione dei 5 stili di capelli (sfondo trasparente). |

## Struttura dell'SVG

Parti separate in gruppi con `id`, dal fondo al primo piano:
`arm-right` → `pants` → `shoes` (`shoe-left`, `shoe-right`) → `arm-left` → `head` → `torso`.

Il disegno è in coordinate dell'immagine di riferimento; un `<g transform="translate(-40 -240)">` lo riporta a `0,0`. Il viewBox è `-58 -28 308 683`: oltre al personaggio (`0 0 250 655`) lascia spazio a sinistra per la coda e in alto per i ciuffi.

## Capelli

Il gruppo `hair` sta **dentro** `head`, sopra gli occhi, così i capelli seguono il movimento idle della testa. Contiene 5 stili, ciascuno un gruppo `hair-N` con la sagoma (riempimento + contorno) e qualche linea interna per ciocche e separazioni. Ne è visibile uno solo:

| Stile | `id` | Colore di default |
| --- | --- | --- |
| 1. Spettinati | `hair-1` | `#452d20` |
| 2. Coda con frangia (la coda cade a sinistra, sul retro della testa) | `hair-2` | `#673a25` |
| 3. Chignon | `hair-3` | `#39231b` |
| 4. Ciuffo scuro di lato | `hair-4` | `#352a25` |
| 5. Ciuffo castano di lato | `hair-5` | `#5c3423` |

Nel file da solo si vede lo stile 1. Per sceglierne un altro basta impostare `--show-hair-1: none` e `--show-hair-N: inline` (per esempio nello `style` dell'elemento `<svg>`); `--show-hair: none` nasconde tutti i capelli. Il colore si cambia con `--hair`, uguale per tutti gli stili.

Le sagome sono state tracciate dall'immagine `reference/capelli.webp` (scala 0,78–0,80 e allineamento sull'orecchio) e poi riportate con lo stesso spessore di contorno del resto del personaggio (`--line-w`). Nel visualizzatore ogni variante parte con lo stile e il colore del suo omonimo nell'immagine, ma stile e colore si cambiano dal pannello.

## Animazione idle

Definita direttamente in `character.svg` (CSS `@keyframes`, solo `transform`), quindi parte anche aprendo il file da solo nel browser:

- **respiro**: busto e braccia si allungano di ~1% ancorati alla base, la testa si alza di 2 px con 0.14 s di ritardo (cicli di 1.9 s, andata e ritorno);
- **battito di ciglia**: gli occhi si schiacciano brevemente ogni 4.6 s.

Con `prefers-reduced-motion` l'SVG resta fermo. Nel visualizzatore c'è l'interruttore *Animazione*; il PNG esportato è sempre un fotogramma fermo.

## Variabili CSS

`--outline`, `--line-w`, `--skin`, `--hair`, `--shirt`, `--pants`, `--shoe-upper-l`, `--shoe-upper-r`, `--shoe-toe`, `--shoe-tongue`, `--shoe-lace`, `--shoe-sole`, `--eye`, più `--idle-n` (`0` spegne l'animazione), `--idle-delay` (sfasa più istanze) e `--show-hair` / `--show-hair-1` … `--show-hair-5` (`inline` | `none`, vedi sopra).

Il bottone *Scarica SVG* del visualizzatore scrive i valori scelti direttamente nel file (e tiene solo lo stile di capelli scelto), quindi il risultato si apre anche in Illustrator, Inkscape o Figma (che ignorano `var()`).
