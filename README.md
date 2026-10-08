# svg_characters

Cinque personaggi in SVG (bambino, ragazzo, slanciato, adulto, robusto), con un visualizzatore HTML per provare colori, capelli e parti visibili.

| File | Cosa fa |
| --- | --- |
| `characters/*.svg` | **Sorgenti**: un file per sagoma (`bambino`, `ragazzo`, `slanciato`, `adulto`, `robusto`), ciascuno con i 5 stili di capelli. Colori controllati da variabili CSS (`--skin`, `--shirt`, `--pants`, …) con un default ciascuno. |
| `index.html` | Visualizzatore (generato). Si apre anche con doppio clic. |
| `viewer.template.html` | Template del visualizzatore: gli SVG vengono incorporati da `build.mjs`. |
| `build.mjs` | `node build.mjs` rigenera `index.html` dopo ogni modifica agli SVG o al template. |
| `serve.mjs` | Server statico opzionale: `node serve.mjs` → http://localhost:5191 |
| `reference/sagome.webp` | Foglio di riferimento da cui sono state tracciate le 5 sagome. |
| `reference/capelli.webp` | Immagine di ispirazione dei 5 stili di capelli (sfondo trasparente). |
| `reference/1.webp` | Primo foglio di riferimento (5 colorazioni della stessa sagoma): superato dalle sagome diverse. |

## Struttura dell'SVG

Parti separate in gruppi con `id`, dal fondo al primo piano (stessa struttura in tutti i file):
`arm-right` → `pants` → `shoes` (`shoe-left`, `shoe-right`) → `arm-left` → `head` (con `hair` dentro) → `torso`.

- Ogni parte è una regione chiusa col suo contorno, e le regioni vicine si toccano a metà del tratto scuro del foglio, quindi non ci sono buchi né sovrapposizioni fra le linee.
- Dentro le regioni ci sono le linee aperte: orecchio, cuciture delle maniche, cucitura interna e pieghe all'orlo dei pantaloni. Nel bambino c'è anche la tasca (un dettaglio dei pantaloni).
- I pantaloni scendono un poco sotto le scarpe, così l'orlo non si vede.
- Scarpe, come regioni riempite: suola, tomaia (`c-upper-l` / `c-upper-r`), linguetta a sinistra, punta e zona lacci (`c-toe`, `c-lace`) a destra. Lo slanciato non ha la punta come regione a parte, quindi `--shoe-toe` non ha effetto su di lui (il visualizzatore non mostra quel campo).

### Scala e riquadro

Le coordinate sono quelle di `reference/sagome.webp`, uguali per tutti i personaggi: stessa scala e stessa linea del suolo (`y ≈ 900`). Le altezze restano quindi confrontabili: se si mettono gli SVG alla stessa altezza, il bambino resta più basso dell'adulto. Tutti hanno un riquadro di 316×722 che lascia spazio ai capelli (coda e ciuffi). L'origine del `viewBox` cambia da file a file (la figura è centrata sull'ingombro di corpo e capelli): per questo l'`<svg>` che usa un `<symbol>` di questi file deve avere `viewBox="0 0 316 722"`, come fa il visualizzatore.

## Capelli

Il gruppo `hair` sta **dentro** `head`, sopra gli occhi, così i capelli seguono il movimento idle della testa. Contiene 5 stili, ciascuno un gruppo `hair-N` con la sagoma (riempimento + contorno) e qualche linea interna per ciocche e separazioni. Ne è visibile uno solo, per default quello con il numero del personaggio:

| Stile | `id` | Colore di default | Personaggio |
| --- | --- | --- | --- |
| 1. Spettinati | `hair-1` | `#452d20` | bambino |
| 2. Coda con frangia (la coda cade a sinistra, sul retro della testa) | `hair-2` | `#673a25` | ragazzo |
| 3. Chignon | `hair-3` | `#39231b` | slanciato |
| 4. Ciuffo scuro di lato | `hair-4` | `#352a25` | adulto |
| 5. Ciuffo castano di lato | `hair-5` | `#5c3423` | robusto |

Per sceglierne un altro basta impostare `--show-hair-N: none` / `inline` (per esempio nello `style` dell'elemento `<svg>`); `--show-hair: none` nasconde tutti i capelli. Il colore si cambia con `--hair`, uguale per tutti gli stili.

Le sagome dei capelli sono state tracciate da `reference/capelli.webp` e poi adattate a ciascuna testa (scala 0,98–1,07 in larghezza e 0,93–1,02 in altezza, allineando orecchio, fronte e cima), con lo stesso spessore di contorno del resto del personaggio (`--line-w`). Nel visualizzatore stile e colore si cambiano dal pannello.

## Animazione idle

Definita direttamente in ogni SVG (CSS `@keyframes`, solo `transform`), quindi parte anche aprendo il file da solo nel browser:

- **respiro**: busto e braccia si allungano di ~1% ancorati alla base, la testa si alza di 2 px con 0.14 s di ritardo (cicli di 1.9 s, andata e ritorno);
- **battito di ciglia**: gli occhi si schiacciano brevemente ogni 4.6 s.

Con `prefers-reduced-motion` l'SVG resta fermo. Nel visualizzatore c'è l'interruttore *Animazione*; il PNG esportato è sempre un fotogramma fermo.

## Variabili CSS

`--outline`, `--line-w`, `--skin`, `--hair`, `--shirt`, `--pants`, `--shoe-upper-l`, `--shoe-upper-r`, `--shoe-toe`, `--shoe-tongue`, `--shoe-lace`, `--shoe-sole`, `--eye`, più `--idle-n` (`0` spegne l'animazione), `--idle-delay` (sfasa più istanze) e `--show-hair` / `--show-hair-1` … `--show-hair-5` (`inline` | `none`, vedi sopra).

Nel visualizzatore i colori di partenza di ogni personaggio sono i default scritti nel CSS del suo SVG, senza doppioni altrove. Il bottone *Scarica SVG* scrive i valori scelti direttamente nel file (e tiene solo lo stile di capelli scelto), quindi il risultato si apre anche in Illustrator, Inkscape o Figma (che ignorano `var()`).
