# svg_characters

Personaggi in SVG pensati per essere **combinati**: dieci sagome (cinque maschili e cinque femminili, da bambino a
adulto) × cinque stili di capelli × maglie e pantaloni × colori a piacere, più un visualizzatore HTML per provare gli
incroci.

## Organizzazione

```
src/                        ← QUI si lavora: tutto ciò che si modifica a mano o si ricava dai fogli
  manifest.json             gruppi, ordine di sagome, capelli e vestiti, palette comune, preset del visualizzatore
  style.css                 classi dei colori, visibilità di capelli e vestiti, animazione idle (uguali per tutte)
  bodies/
    maschio/                bambino · ragazzo · slanciato · adulto · robusto   (.svg = geometria, .json = misure)
    femmina/                bambina · ragazza · slanciata · adulta · robusta
  hair/                     spettinati · coda · chignon · ciuffo-scuro · ciuffo-castano   (.svg + .json)
  clothes/
    maschio/                reference.json = punti di riferimento del corpo su cui sono disegnati i vestiti
                            (le femmine indossano gli stessi capi: `clothesFrom` nel manifest)
      tops/                 felpa · giacca · polo · maglione · camicia           (.svg + .json)
      bottoms/              jeans · chino · jogger · cargo · larghi              (.svg + .json)
  viewer/template.html      il visualizzatore

characters/                 ← GENERATO da build.mjs: ogni sagoma con tutti i capelli e i vestiti del suo gruppo
  maschio/…  femmina/…        (file SVG autonomi)
index.html                  ← GENERATO: visualizzatore (si apre anche con doppio clic)

build.mjs                   compone characters/ e index.html:  node build.mjs
lib/fit.mjs                 deformazione (thin-plate spline) che adatta i vestiti ai corpi
serve.mjs                   server statico opzionale:  node serve.mjs → http://localhost:5191

reference/                  fogli di riferimento da cui sono tracciate le sorgenti
  sagome-maschili · sagome-femminili · capelli · vestiti-maschili-pantaloni · vestiti-maschili-maglie · archivio/
tools/                      strumenti Python per tracciare i fogli (vedi tools/README.md)
```

Regola pratica: **si modifica `src/`, poi `node build.mjs`**. `characters/` e `index.html` non si toccano a mano.

## Come si compone un personaggio

`build.mjs` prende una sagoma da `src/bodies/` e le aggiunge:

- **il CSS comune** (`style.css`) con i colori di default di quella sagoma, presi dal suo `.json`;
- **i cinque stili di capelli**, adattati alla sua testa;
- **tutti i vestiti del suo gruppo**, adattati al suo corpo.

Poi scrive `characters/<gruppo>/<sagoma>.svg`. Capelli e vestiti sono disegnati una volta sola e **si adattano a ogni
sagoma**: una sagoma, uno stile di capelli o un capo nuovi si aggiungono senza toccare gli altri. In ogni file ne è
visibile uno solo per tipo, gli altri sono nascosti con variabili CSS.

**Adattamento dei capelli.** Sono disegnati su una testa di riferimento (`hairFrame` nel manifest) e per ogni sagoma
vengono scalati in x (da orecchio a fronte) e in y (da cima a linea degli occhi), usando i punti `head` del suo `.json`.

**Adattamento dei vestiti.** Ogni capo è disegnato su un corpo di riferimento (`src/clothes/<gruppo>/reference.json`).
Ogni sagoma ha nel suo `.json` 22 punti di riferimento (collo, angoli del riquadro di busto, braccia e pantaloni, e
il pugno di ciascun braccio, che tiene le cuffie allineate al polso). `lib/fit.mjs` costruisce la deformazione morbida che porta i punti del corpo di riferimento su quelli
della sagoma e la applica al capo: maniche, cuffie, orli e tasche seguono quindi le proporzioni di ciascun corpo.
In entrambi i casi le coordinate vengono riscritte, quindi lo spessore del contorno resta uguale ovunque.

**Gruppi diversi, stessi capi.** Con `clothesFrom` nel manifest un gruppo può indossare anche i capi disegnati per un
altro (oggi `"femmina": "maschio"`): ogni capo si adatta partendo dal corpo di riferimento su cui è stato disegnato, e
un gruppo può avere i suoi capi più quelli presi da un altro. Gli id dei capi sono unici fra i gruppi.

## Struttura dell'SVG di una sagoma

Parti separate in gruppi con `id`, dal fondo al primo piano (uguali in tutte le sagome):
`arm-right` → `pants` (e i `bottom-<id>`) → `shoes` (`shoe-left`, `shoe-right`) → `arm-left` → `head` (con `hair` dentro) → `torso` (e i `top-<id>`).

- Ogni parte è una regione chiusa col suo contorno, e le regioni vicine si toccano a metà del tratto scuro del foglio, quindi non ci sono buchi né sovrapposizioni fra le linee.
- Dentro le regioni ci sono le linee aperte: orecchio, cuciture delle maniche e del busto, cucitura interna e pieghe all'orlo dei pantaloni. Nei bambini c'è anche la tasca (un dettaglio dei pantaloni).
- I pantaloni scendono un poco sotto le scarpe, così l'orlo non si vede.
- Scarpe, come regioni riempite: suola, tomaia (`c-upper-l` / `c-upper-r`), linguetta a sinistra, punta e zona lacci (`c-toe`, `c-lace`) a destra. Alcune sagome non hanno la punta come regione a parte: `--shoe-toe` non ha effetto su di loro (il visualizzatore non mostra quel campo).
- Il sorgente in `src/bodies/` contiene solo la geometria e il segnaposto `<!-- @hair -->` dentro `head`; colori, capelli e vestiti li aggiunge la build.

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

## Vestiti

La maglietta (`torso`) e i pantaloni (`pants`) della sagoma sono la versione **base**. Per i maschi ci sono in più:

| Maglie (`top-<id>`) | Pantaloni (`bottom-<id>`) |
| --- | --- |
| `felpa` (cappuccio, cordini, tasca a marsupio) | `jeans` |
| `giacca` (colletto, cerniera, tasche, coste) | `chino` |
| `polo` (colletto, patta con bottoni) | `jogger` (coste e cordino) |
| `maglione` (girocollo, coste) | `cargo` (tasche laterali) |
| `camicia` (camicia aperta sulla maglietta) | `larghi` (a gamba larga, con pieghe) |

Si sceglie un capo per tipo con `--show-top-<id>` e `--show-bottom-<id>` (`inline` | `none`; `base` per la versione della sagoma). Un capo sostituisce la versione base. Ogni capo ha fino a quattro **ruoli di colore**:

| Ruolo | Maglie | Pantaloni | A cosa serve |
| --- | --- | --- | --- |
| principale | `--shirt` | `--pants` | il colore del capo |
| bordi | `--shirt-trim` | `--pants-trim` | coste, colletti, patte, cuffie |
| dettagli | `--shirt-accent` | `--pants-accent` | cerniera, cordini |
| sotto | `--shirt-under` | — | la maglietta sotto un capo aperto |

Un capo ha solo i ruoli che gli servono (la polo non ha dettagli, la camicia non ha bordi).

**Femmine.** Non ci sono ancora capi disegnati apposta per le sagome femminili: indossano gli stessi capi dei maschi (felpa, giacca, polo, maglione, camicia, jeans, chino, jogger, cargo e pantaloni larghi sono in buona parte unisex), adattati ai loro corpi. Sono dritti: seguono le proporzioni generali (altezza, larghezza, lunghezza di braccia e gambe) ma non la vita e il busto. Per vestiti pensati per le femmine (maglie aderenti, gonne, abiti) servono i loro fogli, disegnati su una sagoma femminile: vedi in fondo.

## Animazione idle

Definita direttamente in ogni SVG (CSS `@keyframes`, solo `transform`), quindi parte anche aprendo il file da solo nel browser:

- **respiro**: busto e braccia si allungano di ~1% ancorati alla base, la testa si alza di 2 px con 0.14 s di ritardo (cicli di 1.9 s, andata e ritorno);
- **battito di ciglia**: gli occhi si schiacciano brevemente ogni 4.6 s.

Con `prefers-reduced-motion` l'SVG resta fermo. Nel visualizzatore c'è l'interruttore *Animazione*; il PNG esportato è sempre un fotogramma fermo.

## Variabili CSS

`--outline`, `--line-w`, `--skin`, `--hair`, `--shirt` (+ `-trim`, `-accent`, `-under`), `--pants` (+ `-trim`, `-accent`), `--shoe-upper-l`, `--shoe-upper-r`, `--shoe-toe`, `--shoe-tongue`, `--shoe-lace`, `--shoe-sole`, `--eye`, più `--idle-n` (`0` spegne l'animazione), `--idle-delay` (sfasa più istanze), `--show-hair` / `--show-hair-<id>`, `--show-top-<id>` e `--show-bottom-<id>` (`inline` | `none`).

## Visualizzatore

Ci sono dieci personaggi di partenza (i preset del manifest), divisi per gruppo (*Tutti / Maschio / Femmina*). Per quello selezionato si possono cambiare **sagoma** (tutte e dieci), **stile dei capelli**, **maglia**, **pantaloni** e ogni colore. I colori che non hai toccato seguono la sagoma e i capi scelti; quelli che hai scelto restano. I capi disponibili sono quelli del gruppo della sagoma (le femmine indossano i capi dei maschi); se dai a un personaggio una sagoma di un gruppo che non ha il capo scelto, maglia e pantaloni tornano alla versione base. Un personaggio resta nel gruppo del suo preset anche se gli dai la sagoma dell'altro gruppo. Tasti `1`–`9`, `0` o `←` `→` per cambiare personaggio.

I colori di partenza sono i default scritti nel CSS di ogni SVG, senza doppioni altrove. Il bottone *Scarica SVG* scrive i valori scelti direttamente nel file (e tiene solo i capelli, la maglia e i pantaloni scelti), quindi il risultato si apre anche in Illustrator, Inkscape o Figma (che ignorano `var()`).

## Aggiungere una sagoma, uno stile di capelli o dei vestiti

- **Sagoma**: tracciarla con `tools/trace_bodies.py` (o scrivere a mano `src/bodies/<gruppo>/<nome>.svg` + `.json` con la stessa struttura, compresi i punti `head` e `landmarks`), poi aggiungerla a `bodies` e a `presets` in `src/manifest.json`. Un gruppo nuovo (per esempio *Anziani*) è una cartella in più, più una voce in `groups`.
- **Stile di capelli**: `tools/trace_hair.py` o a mano in `src/hair/<id>.svg` + `.json`, poi l'id in `hair` nel manifest.
- **Vestiti**: `tools/trace_clothes.py` da due fogli (pantaloni e maglie disegnati sullo stesso corpo), poi i capi in `clothes.<gruppo>` nel manifest e, se si vuole, in un preset (`top`, `bottom`). Per i capi femminili: `tools/trace_clothes.py --group femmina --out src/clothes/femmina …` con i due fogli (pantaloni e maglie) disegnati su un corpo femminile, poi `clothes.femmina` nel manifest (con `clothesFrom` restano disponibili anche i capi dei maschi; cambiare gli id se coincidono). Il corpo di riferimento è la prima figura del foglio dei pantaloni.
- Poi `node build.mjs`.
