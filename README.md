# svg_characters

Personaggi in SVG pensati per essere **combinati**: dieci sagome (cinque maschili e cinque femminili, da bambino a
adulto) × venti stili di capelli × cinque barbe (per gli uomini) × maglie e pantaloni × colori a piacere, più un visualizzatore HTML per provare gli
incroci.

## Organizzazione

```
src/                        ← QUI si lavora: tutto ciò che si modifica a mano o si ricava dai fogli
  manifest.json             gruppi, ordine di sagome, capelli e vestiti, palette comune, preset del visualizzatore
                            (un preset può dare un nome e colori di partenza: pelle, capelli, scarpe)
  style.css                 classi dei colori, visibilità di capelli e vestiti, animazione idle (uguali per tutte)
  bodies/
    maschio/                bambino · ragazzo · slanciato · adulto · robusto   (.svg = geometria, .json = misure)
    femmina/                bambina · ragazza · slanciata · adulta · robusta
  hair/                     spettinati · coda · chignon · ciuffo-scuro · ciuffo-castano ·        (.svg + .json)
                            arruffati · due-chignon · caschetto · rasati-lato · ricci ·
                            calvizie · stempiato · pettinati-indietro · coda-grigia · chignon-grigio ·
                            caschetto-scalato · coda-alta · lisci-frangia · lunghi-mossi · coda-laterale
  beards/                   barba-incolta · barba-corta · barba-piena · pizzetto · barba-lunga   (.svg + .json)
  clothes/<gruppo>/<sagoma>/  ogni capo sta SOLO sulla sagoma per cui è disegnato (.svg + .json)
    tops/ · bottoms/        le maglie e i pantaloni di quella sagoma
    reference.json          solo maschio/adulto: il corpo su cui sono disegnati i primi cinque capi per tipo
  viewer/template.html      il visualizzatore

characters/                 ← GENERATO da build.mjs: ogni sagoma con i suoi capelli e i suoi vestiti
  maschio/…  femmina/…        (file SVG autonomi)
index.html                  ← GENERATO: visualizzatore (si apre anche con doppio clic)

build.mjs                   compone characters/ e index.html:  node build.mjs
lib/fit.mjs                 deformazione (thin-plate spline) che adatta capelli e capi alla loro sagoma
serve.mjs                   server statico opzionale:  node serve.mjs → http://localhost:5191

reference/                  fogli di riferimento da cui sono tracciate le sorgenti
  sagome-maschili · sagome-femminili · capelli · capelli-2 · capelli-3 · capelli-anziani · barbe ·
  vestiti-maschili-pantaloni · vestiti-maschili-maglie ·
  vestiti-maschili-outfit · vestiti-femminili · vestiti-femminili-2 · archivio/
tools/                      strumenti Python per tracciare i fogli (vedi tools/README.md)
```

Regola pratica: **si modifica `src/`, poi `node build.mjs`**. `characters/` e `index.html` non si toccano a mano.

## Come si compone un personaggio

`build.mjs` prende una sagoma da `src/bodies/` e le aggiunge:

- **il CSS comune** (`style.css`) con i colori di default di quella sagoma, presi dal suo `.json`;
- **gli stili di capelli adatti alla sua età** (vedi sotto), adattati alla sua testa;
- **le barbe** che valgono per il suo gruppo e la sua età (solo uomini, vedi *Barbe*), adattate alla sua testa;
- **i suoi vestiti** (`src/clothes/<gruppo>/<sagoma>/`), quelli elencati per lei in `clothes` nel manifest.

Poi scrive `characters/<gruppo>/<sagoma>.svg`. Gli stili di capelli sono disegnati una volta sola e **si adattano a ogni
sagoma**; i vestiti **no**: ogni capo è disegnato su una sagoma e vive solo lì. In ogni file ne è visibile uno solo per
tipo, gli altri sono nascosti con variabili CSS.

**Adattamento dei capelli.** Sono disegnati su una testa di riferimento (`hairFrame` nel manifest) e per ogni sagoma
vengono scalati in x (da orecchio a fronte) e in y (da cima a linea degli occhi), usando i punti `head` del suo `.json`.

**Un capo, una sagoma.** Mischiare i vestiti fra corporature diverse dava sempre problemi di vestibilità (maniche,
orli e vita su corpi con proporzioni diverse), quindi ogni capo è tracciato sulla figura che lo indossa nel suo foglio
e resta su quella sagoma: nessuna deformazione fra corpi. Un capo nuovo per un'altra sagoma si traccia di nuovo su
quella sagoma. Gli id dei capi devono essere unici dentro una sagoma (su sagome diverse possono ripetersi).

Un capo può correggere alcuni punti di riferimento della propria sagoma (`landmarks` nel suo `.json`, per esempio
l'orlo di una manica corta o il bordo alto dei pantaloni): la build li usa per spostare quei punti. Fa eccezione la
prima serie maschile (10 capi, due fogli disegnati sullo stesso corpo di riferimento, un adulto appena diverso dalla
sagoma `maschio/adulto`): i suoi capi hanno `"ref": "reference"` nel `.json` e la build li adatta alla sagoma adulto
con una deformazione morbida (thin-plate spline, `lib/fit.mjs`) dai punti di `src/clothes/maschio/adulto/reference.json`
a quelli della sagoma. Ogni sagoma ha nel suo `.json` i punti di riferimento (collo; angoli del riquadro di busto, braccia
e pantaloni; pugni; bordi del busto; cima e suola delle scarpe e altezza del ginocchio). Le coordinate vengono sempre
riscritte, quindi lo spessore del contorno resta uguale ovunque.

## Struttura dell'SVG di una sagoma

Parti separate in gruppi con `id`, dal fondo al primo piano (uguali in tutte le sagome):
`neck-fill` e i livelli dietro (`pants-fill`, `torso-fill`, `bottom-<id>-back`, `top-<id>-back`) → `head` (riempimento e contorno separati, con capelli e barba in livelli, vedi *Capelli* e *Barbe*; gli occhi per ultimi) → parti sotto i pantaloni (`pants-under`, `bottom-<id>-under`, `top-<id>-under`) → `arm-right` → `pants` (e i `bottom-<id>`) → `shoes` (`shoe-left`, `shoe-right`) → `arm-left` → `torso` (e i `top-<id>`).

- Ogni parte è una regione chiusa col suo contorno, e le regioni vicine si toccano a metà del tratto scuro del foglio, quindi non ci sono buchi né sovrapposizioni fra le linee.
- Dentro le regioni ci sono le linee aperte: orecchio, cuciture delle maniche e del busto, cucitura interna e pieghe all'orlo dei pantaloni. Nei bambini c'è anche la tasca (un dettaglio dei pantaloni).
- I pantaloni scendono un poco sotto le scarpe, così l'orlo non si vede, e salgono sotto la maglia con una fascia
  (`pants-under`, e lo stesso per ogni capo): con una maglia più corta di quella base non resta un buco in vita.
- **Riempimenti di fondo**, dietro a tutto, perché nessun abbinamento lasci fessure: il bordo del busto e dei fianchi
  vicino alle braccia (`<defs>`: `fill-top-…`, `fill-bottom-…`), richiamato con `<use>` dentro ogni maglia e pantalone
  (`top-<id>-back`, `bottom-<id>-back`) col colore principale di quel capo; ogni maglia vi aggiunge la sua parte sotto le
  braccia. E una fascia di pelle sotto il collo (`neck-fill`), che si vede solo con una maglia più scollata della base.
  Sulla sagoma base sono tutti coperti da braccia e busto. Servono agli abbinamenti dentro la stessa sagoma (una maglia
  con pantaloni disegnati su un altro foglio, o con la maglietta e i pantaloni base): l'audit li ha tenuti perché senza
  tornano buchi piccoli sul collo, sotto le braccia e in vita.
- Scarpe, come regioni riempite: suola, tomaia (`c-upper-l` / `c-upper-r`), linguetta a sinistra, punta e zona lacci (`c-toe`, `c-lace`) a destra. Alcune sagome non hanno la punta come regione a parte: `--shoe-toe` non ha effetto su di loro (il visualizzatore non mostra quel campo).
- Il sorgente in `src/bodies/` contiene solo la geometria e i segnaposto `<!-- @hair-back -->`, `<!-- @hair-skin -->`, `<!-- @beard-skin -->`, `<!-- @beard -->` e `<!-- @hair -->` dentro `head`; colori, capelli, barbe e vestiti li aggiunge la build.

### Scala e riquadro

Le coordinate sono quelle dei fogli di riferimento, uguali per tutte le sagome: stessa scala e stessa linea del suolo (`y = 900`). Le altezze restano quindi confrontabili: se si mettono gli SVG alla stessa altezza, il bambino resta più basso dell'adulto. Tutti hanno lo stesso riquadro (oggi 322×742), che lascia spazio ai capelli (coda e ciuffi). L'origine del `viewBox` cambia da file a file (la figura è centrata sull'ingombro di corpo e capelli): per questo l'`<svg>` che usa un `<symbol>` di questi file deve avere `viewBox="0 0 322 742"`, come fa il visualizzatore.

## Capelli

I capelli stanno **dentro** `head`, così seguono il movimento idle della testa, e sono disegnati prima degli occhi: una
frangia lunga passa dietro gli occhi e non li copre. La testa sta dietro a braccia, busto e pantaloni (vedi sopra): le
ciocche che scendono sulle spalle non coprono mai le braccia. Ogni stile è un gruppo `hair-<id>` con la sagoma (riempimento +
contorno) e qualche linea interna per ciocche e separazioni. Ne è visibile uno solo: per default quello del preset di
quella sagoma.

**Tre livelli nella testa.** Le parti dei capelli che devono stare attaccate al cranio non si possono disegnare come il
resto: la testa di ogni sagoma ha un contorno un poco diverso da quello del foglio, e una striscia o un ciuffo
disegnati "a occhio" resterebbero staccati. Perciò la testa è disegnata in due passate (riempimento della pelle, poi
contorno) e un'acconciatura può avere parti in tre livelli, scelti dalla classe del percorso nel suo `.svg`:

- `c-behind`, **dietro la testa** (`hair-back`, prima del riempimento): un ciuffo che spunta oltre il cranio, come quelli
  della calvizie dal lato degli occhi. Il tracciatore lo prolunga dentro il cranio, dove la testa lo copre, quindi
  resta attaccato qualunque sia la testa; ha il tratto solo sul bordo esterno, dalla parte della testa c'è il contorno
  della testa;
- `c-shaved`, **sulla pelle ma sotto il contorno** (`hair-skin`): la zona rasata, trasparente. Il tracciatore la allarga
  oltre il contorno della testa e non disegna il suo tratto verso l'esterno; la build la ritaglia sulla testa di ogni
  sagoma (`clip-path` con il riempimento della testa, `head-clip-<gruppo>-<sagoma>` in `<defs>`), quindi arriva sempre
  fino al contorno e non resta una striscia di pelle né un doppio contorno;
- tutto il resto, **davanti** (`hair`).

I capelli sparsi della calvizie partono da dentro il cranio e oltrepassano il contorno, quindi toccano la testa anche
se il cranio è un poco più alto o più basso di quello del foglio. Ogni livello ha un gruppo per stile
(`hair-<id>-back`, `hair-<id>-skin`) con la stessa visibilità dello stile.

| Stile (`id`) | Nome | Colore di default |
| --- | --- | --- |
| `spettinati` | Spettinati | `#462e21` |
| `coda` | Coda e frangia (la coda cade a sinistra, sul retro della testa) | `#683a26` |
| `chignon` | Chignon | `#39241c` |
| `ciuffo-scuro` | Ciuffo scuro | `#362b26` |
| `ciuffo-castano` | Ciuffo castano | `#5d3523` |
| `arruffati` | Arruffati | `#423123` |
| `due-chignon` | Due chignon | `#523625` |
| `caschetto` | Caschetto | `#473327` |
| `rasati-lato` | Rasati di lato (la zona rasata è il colore dei capelli, trasparente) | `#3b322b` |
| `ricci` | Ricci | `#4e3424` |
| `calvizie` | Calvizie con ciuffi (e qualche capello sparso) · solo adulti | `#9b8f89` |
| `stempiato` | Stempiato · solo adulti | `#9d928d` |
| `pettinati-indietro` | Pettinati all'indietro · ragazzi e adulti | `#d3c4bc` |
| `coda-grigia` | Coda bassa · ragazzi e adulti | `#a2948c` |
| `chignon-grigio` | Chignon basso · ragazzi e adulti | `#c7b8af` |
| `caschetto-scalato` | Caschetto scalato (frangia da un lato, lunghezza del mento) | `#4e332a` |
| `coda-alta` | Coda alta con frangia (la coda sale a sinistra) | `#513328` |
| `lisci-frangia` | Lisci con frangia dritta (lunghi, scendono sulle spalle) | `#3b2d28` |
| `lunghi-mossi` | Lunghi mossi con la riga di lato | `#623a26` |
| `coda-laterale` | Coda laterale bassa (cade a sinistra, con un laccio) | `#885d44` |

**Capelli lunghi.** Gli ultimi cinque stili (`capelli-3`) scendono ai lati del viso fino alle spalle. Stanno nel gruppo
della testa come gli altri, quindi braccia e maglia (disegnate dopo la testa) li coprono dove si sovrappongono: i capelli
restano dietro le spalle e le braccia e si vedono solo fuori dal busto. Come la `coda` hanno un'apertura per il viso: la testa di ogni
sagoma ci sta dentro e le ciocche a destra arrivano al contorno della faccia. Un po' di sfondo resta visibile fra le
ciocche, il collo e le spalle (le "finestre" del foglio), per esempio fra la coda e la guancia.

**Età.** Le acconciature da anziani non si danno ai bambini: uno stile può dire a quali età vale (`ages` nel suo `.json`) e
le età delle sagome sono in `ages` del manifest (bambino, ragazzo, adulto). Una sagoma contiene solo gli stili della sua
età, e il visualizzatore mostra solo quelli: dando a un personaggio una sagoma più giovane, uno stile che non vale più
torna a quello del preset o al primo disponibile. Calvizie e stempiato sono solo per gli adulti; coda bassa, chignon
basso e pettinati all'indietro anche per i ragazzi; gli altri per tutti. I colori di default degli stili da anziani sono
grigi, ma come per gli altri il colore si cambia con `--hair`.

Per sceglierne un altro basta impostare `--show-hair-<id>: none` / `inline` (per esempio nello `style` dell'elemento `<svg>`); `--show-hair: none` nasconde tutti i capelli. Il colore si cambia con `--hair`, uguale per tutti gli stili.

## Barbe

Una barba è un'altra opzione del viso, come i capelli: si sceglie con `--show-beard-<id>: inline` (nessuna di default,
`--show-beard: none` le nasconde tutte), il colore si cambia con `--beard`. Valgono solo per le sagome maschili e,
tranne la barba incolta (anche ragazzi), per gli adulti (`groups` e `ages` nel `.json` di ogni barba). Vengono dal
foglio `reference/barbe.webp`, tracciate con `tools/trace_beards.py`.

| Barba (`id`) | Nome | Colore di default |
| --- | --- | --- |
| `barba-incolta` | Barba incolta (puntini sul mento e sulla mascella) · ragazzi e adulti | `#130f0c` |
| `barba-corta` | Barba corta (lungo la mascella, con i baffi) | `#4b382c` |
| `barba-piena` | Barba piena | `#4a372a` |
| `pizzetto` | Baffi e pizzetto | `#443328` |
| `barba-lunga` | Barba lunga a punte | `#493629` |

Sono nel gruppo della testa, dopo il contorno e sotto i capelli. Come per la zona rasata dei capelli, la testa di ogni sagoma
ha un contorno un po' diverso da quello del foglio: la barba ha perciò due parti. Quella **davanti** è la sagoma con
il suo contorno e il buco della bocca (dove si vede la pelle); quella **sotto il contorno della testa** (`beard-skin`,
classe `c-skinlayer`) è la stessa sagoma allargata di qualche px verso l'esterno e ritagliata sulla testa
(`clip-path`, lo stesso `head-clip-…` dei capelli): la barba arriva sempre fino al bordo del viso e non resta una striscia
di pelle fra la barba e il mento. Le parti che scendono oltre il mento restano davanti, sopra il contorno. La barba
incolta è fatta di puntini (un solo percorso, con gli estremi tondi) nello stesso livello.

## Vestiti

La maglietta (`torso`) e i pantaloni (`pants`) della sagoma sono la versione **base**. In più ogni sagoma ha i suoi capi,
disegnati su di lei e solo lì (`src/clothes/<gruppo>/<sagoma>/`, elencati per sagoma in `clothes` nel manifest):

| Sagoma | Maglie (`top-<id>`) | Pantaloni (`bottom-<id>`) |
| --- | --- | --- |
| Bambino | `maglietta-riga` (bianca con una riga sul petto) | `bermuda-cargo` (tasche laterali, con gambe e calze) |
| Ragazzo | `felpa-rossa` (cappuccio, cordini, tasca, polsini) | `jeans-grigi` (cucitura centrale) |
| Slanciato | `camicia-risvoltata` (aperta, maniche arrotolate, taschino, maglietta sotto) | `pantaloni-kaki` |
| Adulto | `felpa` (cappuccio, cordini, tasca a marsupio) · `giacca` (colletto, cerniera, tasche, coste) · `polo` (colletto, patta con bottoni) · `maglione` (girocollo, coste) · `camicia` (aperta sulla maglietta) · `polo-blu` (bottoni, infilata nei pantaloni) | `jeans` · `chino` · `jogger` (coste e cordino) · `cargo` (tasche laterali) · `larghi` (gamba larga, pieghe) · `pantaloni-cintura` (cintura e fibbia) |
| Robusto | `cardigan-grigio` (bottoni, coste, maglietta sotto) | `jeans-chiari` |
| Bambina | `maglietta-fiore` (rosa con fiore) · `abitino` (colletto, fiore, pieghe) | `pantaloncini` (di jeans risvoltati, con gambe e calze) · `leggings` (con le caviglie) |
| Ragazza | `felpa-cappuccio` (cappuccio aperto, cordini, tasca a marsupio) · `maglia-righe` (righe e polsini) | `jeans-scuri` (tasche, cucitura) · `jeans-cargo` (tasche laterali) |
| Slanciata | `top-corto` (canotta nera: spalle, braccia e pancia scoperte) · `giacca-jeans` (aperta su un top nero, maniche risvoltate) | `jeans-a-zampa` (passanti, bottone, tasche) · `jeans-neri` (risvoltati, caviglie scoperte) |
| Adulta | `maglietta-v` (verde oliva, scollo a V) · `maglione-v` (a coste, maniche a tre quarti) | `pantaloni-neri` (gamba larga) · `pantaloni-oliva` |
| Robusta | `cardigan` (maniche arrotolate, bottoni, maglietta sotto) · `cardigan-fiori` (tasca, coste, su una maglia a fiori) | `pantaloni-marroni` · `pantaloni-scuri` |

Gli id dei capi devono essere unici dentro una sagoma, non fra sagome. Un abbinamento è sempre fra capi della stessa
sagoma (o con la maglietta e i pantaloni base di quella sagoma).

Si sceglie un capo per tipo con `--show-top-<id>` e `--show-bottom-<id>` (`inline` | `none`; `base` per la versione della sagoma). Un capo sostituisce la versione base. Ogni capo ha fino a quattro **ruoli di colore**:

| Ruolo | Maglie | Pantaloni | A cosa serve |
| --- | --- | --- | --- |
| principale | `--shirt` | `--pants` | il colore del capo |
| bordi | `--shirt-trim` | `--pants-trim` | coste, colletti, patte, cuffie, risvolti |
| dettagli | `--shirt-accent` (e `--shirt-accent2`) | `--pants-accent` | cerniera, cordini, righe, fiori, cintura |
| sotto | `--shirt-under` | `--pants-under` | la maglietta sotto un capo aperto; le calze |

Righe e fantasie sono dettagli: una maglia a righe ha le righe in `--shirt-accent`, la maglia a fiori i fiori.

Un capo ha solo i ruoli che gli servono (la polo non ha dettagli, la camicia non ha bordi). La pelle che un capo lascia
scoperta (gambe sotto i pantaloncini, pancia, spalle) usa `--skin`, come il resto del corpo.

**Capi da fogli di outfit.** I capi femminili e la seconda serie maschile (uno per sagoma) vengono da fogli
(`vestiti-femminili`, `vestiti-femminili-2`, `vestiti-maschili-outfit`) in cui ogni figura indossa maglia e pantaloni sul
proprio corpo: il capo si traccia su quella figura e resta su quella sagoma. I fogli mostrano anche le scarpe di ogni
outfit: non sono capi ma colori, e li impostano i preset (`colors`). I dieci capi della prima serie maschile
vengono invece da due fogli sullo stesso corpo e stanno su `maschio/adulto`. Cose particolari rispetto ai primi capi
maschili:

- *Pelle scoperta*: i pantaloncini portano con sé gambe e calze (i pantaloni della sagoma si nascondono); il top corto porta spalle e braccia (`replaces: ["arms"]` nel `.json`, nel gruppo `.g-arms`: le braccia della sagoma si nascondono con `--show-body-arms: none`, e `--show-arms` nasconde tutte le braccia) e la pancia.
- *Livello sotto* (`<g id="…-under">`): la pancia del top corto sta sotto i pantaloni, così non dipende dai pantaloni scelti; i pantaloni salgono di qualche px sotto la maglia, e una maglia corta o infilata (la polo, il top sotto la giacca di jeans) scende sotto i pantaloni, così negli incroci non restano buchi in vita.
- *Dettagli senza contorno* ricavati dal colore: fiori, righe, risvolti, calze, bottoni chiari.
- *Scollo*: la pelle sotto il collo (V, cappuccio, scollo ampio) è parte del capo.

## Animazione idle

Definita direttamente in ogni SVG (CSS `@keyframes`, solo `transform`), quindi parte anche aprendo il file da solo nel browser:

- **respiro**: busto e braccia si allungano di ~1% ancorati alla base, la testa si alza di 2 px con 0.14 s di ritardo (cicli di 1.9 s, andata e ritorno); le maglie (con le loro parti sotto e dietro) respirano col busto attorno allo stesso punto, la base del busto
  (`.c-origin-<gruppo>-<sagoma>`, coordinate assolute): così i livelli non si separano;
- **battito di ciglia**: gli occhi si schiacciano brevemente ogni 4.6 s.

Con `prefers-reduced-motion` l'SVG resta fermo. Nel visualizzatore c'è l'interruttore *Animazione*; il PNG esportato è sempre un fotogramma fermo.

## Variabili CSS

`--outline`, `--line-w`, `--skin`, `--hair`, `--shirt` (+ `-trim`, `-accent`, `-accent2`, `-under`), `--pants` (+ `-trim`, `-accent`, `-under`), `--shoe-upper-l`, `--shoe-upper-r`, `--shoe-toe`, `--shoe-tongue`, `--shoe-lace`, `--shoe-sole`, `--eye`, più `--idle-n` (`0` spegne l'animazione), `--idle-delay` (sfasa più istanze), `--show-hair` / `--show-hair-<id>`, `--beard` e `--show-beard` / `--show-beard-<id>`, `--show-top-<id>` e `--show-bottom-<id>` (`inline` | `none`), `--show-arms` e `--show-body-arms`.

## Visualizzatore

Ci sono sedici personaggi di partenza (i preset del manifest: uno o due per sagoma, ognuno con un abbinamento di capi della sua sagoma; la seconda serie femminile porta i capelli nuovi; *Adulto · polo* e *Robusto · cardigan* hanno la barba), divisi per gruppo (*Tutti / Maschio / Femmina*). Per quello selezionato si possono cambiare **sagoma** (tutte e dieci), **stile dei capelli**, **barba** (solo sagome maschili: la sezione compare solo per loro e solo con le barbe che valgono per la sagoma), **maglia**, **pantaloni** e ogni colore. I colori che non hai toccato seguono la sagoma e i capi scelti; quelli che hai scelto restano. I capi disponibili sono solo quelli della sagoma scelta: se cambi sagoma, maglia e pantaloni passano all'abito di partenza di quella sagoma (il primo dei suoi preset), e se la sagoma non ha capi restano la maglietta e i pantaloni base. Un personaggio resta nel gruppo del suo preset anche se gli dai la sagoma dell'altro gruppo. Tasti `1`–`9`, `0` o `←` `→` per cambiare personaggio.

**Colori.** I campi sono divisi per parte (corpo, maglia, pantaloni, scarpe, contorno e occhi) e mostrano solo i ruoli che il capo scelto ha. Sotto ogni campo ci sono dei colori rapidi: toni della pelle, colori di capelli naturali e di fantasia, una tavolozza di tessuti; per le scarpe una tavolozza unica per la tomaia e una per la suola. `↺` riporta un campo al suo colore di default; *Vestiti a caso* e *Pelle e capelli a caso* pescano dalle tavolozze (maglia e pantaloni ben distinti), *Colori di default* azzera tutto.

I colori di partenza sono i default scritti nel CSS di ogni SVG, più i `colors` del preset (pelle, capelli, scarpe). Il bottone *Scarica SVG* scrive i valori scelti direttamente nel file (e tiene solo i capelli, la barba, la maglia e i pantaloni scelti), quindi il risultato si apre anche in Illustrator, Inkscape o Figma (che ignorano `var()`).

## Aggiungere una sagoma, uno stile di capelli o dei vestiti

- **Sagoma**: tracciarla con `tools/trace_bodies.py` (o scrivere a mano `src/bodies/<gruppo>/<nome>.svg` + `.json` con la stessa struttura, compresi i punti `head` e `landmarks`), poi aggiungerla a `bodies` e a `presets` in `src/manifest.json`. Un gruppo nuovo (per esempio *Anziani*) è una cartella in più, più una voce in `groups`.
- **Stile di capelli**: `tools/trace_hair.py` o a mano in `src/hair/<id>.svg` + `.json`, poi l'id in `hair` nel manifest.
- **Barba**: `tools/trace_beards.py` (tabella `BEARDS` con gruppi ed età) in `src/beards/<id>.svg` + `.json`, poi l'id in `beards` nel manifest; un preset può averne una (`beard`, e `beard` in `colors`).
- **Vestiti**: ogni capo sta su una sola sagoma, quindi si traccia su quella. Con un foglio in cui ogni figura indossa un outfit sul proprio corpo (come per le femmine): `tools/trace_outfits.py`, con le regioni di ogni figura assegnate a mano nella sua tabella `OUTFITS` (la riga dice la sagoma). Con due fogli di figure sullo stesso corpo (pantaloni e maglie, come per la prima serie maschile): `tools/trace_clothes.py --out src/clothes/<gruppo>/<sagoma>`; il corpo di riferimento è la prima figura del foglio dei pantaloni e i capi vengono deformati dalla build su quella sagoma (deve essere simile). Poi i capi nel manifest, in `clothes["<gruppo>/<sagoma>"]` (`tops` e `bottoms`), e se si vuole in un preset (`top`, `bottom`, `colors`).
- Poi `node build.mjs`, e se si vuole l'audit (sotto).

## Audit delle combinazioni

```
NODE_PATH=$(npm root -g) node tools/audit.mjs      # serve playwright (npm i -g playwright), circa 2 minuti
```

Rende nel browser, per ogni sagoma, ogni maglia con ogni pantalone **della sua sagoma** (compresi la maglietta e i
pantaloni base) e ogni stile di capelli con ogni maglia, più ogni barba sulla sagoma che la prevede: 917 combinazioni, circa 2 minuti. Cerca i difetti
confrontando ogni combinazione con la sagoma base: vuoti nel busto, nelle braccia e alle caviglie, fessure sottili
chiuse dalla figura, pezzi staccati, parti tagliate dal riquadro, l'estensione dei pantaloni che si vede, livelli sotto
che coprono il braccio o sporgono, vuoti nel fotogramma estremo del respiro, occhi coperti dai capelli (lo sfondo racchiuso fra le ciocche dei capelli lunghi, la testa
e le spalle non conta: fa parte del disegno); controlla anche
che l'SVG esportato dal visualizzatore sia uguale a quello mostrato e che i file siano validi (XML, id unici, ogni parte
con un colore). Scrive `audit/report.html` (per ogni difetto le combinazioni peggiori, col difetto colorato) e
`audit/report.json`. Per rifare solo una parte: `--only=femmina/robusta`, `--skip=hair,export`.
