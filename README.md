# svg_characters

Personaggi in SVG pensati per essere **combinati**: dieci sagome (cinque maschili e cinque femminili, da bambino a
adulto) × cinque stili di capelli × colori a piacere, più un visualizzatore HTML per provare gli incroci.

## Organizzazione

```
src/                        ← QUI si lavora: tutto ciò che si modifica a mano o si ricava dai fogli
  manifest.json             gruppi, ordine delle sagome e dei capelli, palette comune, preset del visualizzatore
  style.css                 classi dei colori, visibilità dei capelli, animazione idle (uguali per tutte le sagome)
  bodies/
    maschio/                bambino · ragazzo · slanciato · adulto · robusto   (.svg = geometria, .json = misure)
    femmina/                bambina · ragazza · slanciata · adulta · robusta
  hair/                     spettinati · coda · chignon · ciuffo-scuro · ciuffo-castano   (.svg + .json)
  viewer/template.html      il visualizzatore

characters/                 ← GENERATO da build.mjs: ogni sagoma con tutti i capelli, file SVG autonomi
  maschio/…  femmina/…
index.html                  ← GENERATO: visualizzatore (si apre anche con doppio clic)

build.mjs                   compone characters/ e index.html:  node build.mjs
serve.mjs                   server statico opzionale:  node serve.mjs → http://localhost:5191

reference/                  fogli di riferimento da cui sono tracciate le sorgenti
  sagome-maschili.webp · sagome-femminili.webp · capelli.webp · archivio/
tools/                      strumenti Python per tracciare i fogli (vedi tools/README.md)
```

Regola pratica: **si modifica `src/`, poi `node build.mjs`**. `characters/` e `index.html` non si toccano a mano.

## Come si compone un personaggio

`build.mjs` prende una sagoma da `src/bodies/`, le aggiunge i cinque stili di capelli e il CSS comune (`style.css`
con i colori di default di quella sagoma, presi dal suo `.json`) e scrive `characters/<gruppo>/<sagoma>.svg`.

I capelli sono disegnati una volta sola, su una testa di riferimento (`hairFrame` nel manifest). Per ogni sagoma
vengono scalati in x (da orecchio a fronte) e in y (da cima a linea degli occhi) per combaciare con la sua testa,
usando i punti di riferimento `head` del suo `.json`. Le coordinate vengono riscritte, quindi lo spessore del
contorno resta uguale ovunque. Per questo **ogni sagoma si combina con ogni stile**, e una sagoma o uno stile nuovi
si aggiungono senza toccare gli altri.

## Struttura dell'SVG di una sagoma

Parti separate in gruppi con `id`, dal fondo al primo piano (uguali in tutte le sagome):
`arm-right` → `pants` → `shoes` (`shoe-left`, `shoe-right`) → `arm-left` → `head` (con `hair` dentro) → `torso`.

- Ogni parte è una regione chiusa col suo contorno, e le regioni vicine si toccano a metà del tratto scuro del foglio, quindi non ci sono buchi né sovrapposizioni fra le linee.
- Dentro le regioni ci sono le linee aperte: orecchio, cuciture delle maniche e del busto, cucitura interna e pieghe all'orlo dei pantaloni. Nei bambini c'è anche la tasca (un dettaglio dei pantaloni).
- I pantaloni scendono un poco sotto le scarpe, così l'orlo non si vede.
- Scarpe, come regioni riempite: suola, tomaia (`c-upper-l` / `c-upper-r`), linguetta a sinistra, punta e zona lacci (`c-toe`, `c-lace`) a destra. Alcune sagome non hanno la punta come regione a parte: `--shoe-toe` non ha effetto su di loro (il visualizzatore non mostra quel campo).
- Il sorgente in `src/bodies/` contiene solo la geometria e il segnaposto `<!-- @hair -->` dentro `head`; i colori e i capelli li aggiunge la build.

### Scala e riquadro

Le coordinate sono quelle dei fogli di riferimento, uguali per tutte le sagome: stessa scala e stessa linea del suolo (`y = 900`). Le altezze restano quindi confrontabili: se si mettono gli SVG alla stessa altezza, il bambino resta più basso dell'adulto. Tutti hanno lo stesso riquadro (oggi 316×742), che lascia spazio ai capelli (coda e ciuffi). L'origine del `viewBox` cambia da file a file (la figura è centrata sull'ingombro di corpo e capelli): per questo l'`<svg>` che usa un `<symbol>` di questi file deve avere `viewBox="0 0 316 742"`, come fa il visualizzatore.

## Capelli

Il gruppo `hair` sta **dentro** `head`, sopra gli occhi, così i capelli seguono il movimento idle della testa. Ogni stile è un gruppo `hair-<id>` con la sagoma (riempimento + contorno) e qualche linea interna per ciocche e separazioni. Ne è visibile uno solo: per default quello del preset di quella sagoma.

| Stile (`id`) | Nome | Colore di default |
| --- | --- | --- |
| `spettinati` | Spettinati | `#462e21` |
| `coda` | Coda e frangia (la coda cade a sinistra, sul retro della testa) | `#683a26` |
| `chignon` | Chignon | `#39241c` |
| `ciuffo-scuro` | Ciuffo scuro | `#362b26` |
| `ciuffo-castano` | Ciuffo castano | `#5d3523` |

Per sceglierne un altro basta impostare `--show-hair-<id>: none` / `inline` (per esempio nello `style` dell'elemento `<svg>`); `--show-hair: none` nasconde tutti i capelli. Il colore si cambia con `--hair`, uguale per tutti gli stili.

## Animazione idle

Definita direttamente in ogni SVG (CSS `@keyframes`, solo `transform`), quindi parte anche aprendo il file da solo nel browser:

- **respiro**: busto e braccia si allungano di ~1% ancorati alla base, la testa si alza di 2 px con 0.14 s di ritardo (cicli di 1.9 s, andata e ritorno);
- **battito di ciglia**: gli occhi si schiacciano brevemente ogni 4.6 s.

Con `prefers-reduced-motion` l'SVG resta fermo. Nel visualizzatore c'è l'interruttore *Animazione*; il PNG esportato è sempre un fotogramma fermo.

## Variabili CSS

`--outline`, `--line-w`, `--skin`, `--hair`, `--shirt`, `--pants`, `--shoe-upper-l`, `--shoe-upper-r`, `--shoe-toe`, `--shoe-tongue`, `--shoe-lace`, `--shoe-sole`, `--eye`, più `--idle-n` (`0` spegne l'animazione), `--idle-delay` (sfasa più istanze) e `--show-hair` / `--show-hair-<id>` (`inline` | `none`).

## Visualizzatore

Ci sono dieci personaggi di partenza (i preset del manifest), divisi per gruppo (*Tutti / Maschio / Femmina*). Per quello selezionato si può cambiare **sagoma** (tutte e dieci), **stile dei capelli** e ogni colore; i colori che non hai toccato seguono la sagoma e lo stile scelti. Un personaggio resta nel gruppo del suo preset anche se gli dai la sagoma dell'altro gruppo. Tasti `1`–`9`, `0` o `←` `→` per cambiare personaggio.

I colori di partenza sono i default scritti nel CSS di ogni SVG, senza doppioni altrove. Il bottone *Scarica SVG* scrive i valori scelti direttamente nel file (e tiene solo lo stile di capelli scelto), quindi il risultato si apre anche in Illustrator, Inkscape o Figma (che ignorano `var()`).

## Aggiungere una sagoma o uno stile di capelli

- **Sagoma**: tracciarla con `tools/trace_bodies.py` (o scrivere a mano `src/bodies/<gruppo>/<nome>.svg` + `.json` con la stessa struttura), poi aggiungerla a `bodies` e a `presets` in `src/manifest.json`. Un gruppo nuovo (per esempio *Anziani*) è una cartella in più, più una voce in `groups`.
- **Stile di capelli**: `tools/trace_hair.py` o a mano in `src/hair/<id>.svg` + `.json`, poi l'id in `hair` nel manifest.
- Poi `node build.mjs`.
