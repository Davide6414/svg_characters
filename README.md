# svg_characters

Personaggi in SVG pensati per essere **combinati**, in due sezioni separate:

- **Umani**: dieci sagome (cinque maschili e cinque femminili, da bambino a adulto) × venti stili di capelli × cinque barbe
  (per gli uomini) × maglie e pantaloni × colori a piacere;
- **Alieni**: otto sagome aliene (quattro maschili e quattro femminili: bambino, ragazzo, adulto e una sagoma curva) con la loro maglietta e i loro pantaloncini oppure un abito su misura (otto capi: maglia + pantaloni o gonna), dodici protuberanze (corna, palchi, pinne, creste, antenne) e colori a piacere (vedi *Alieni*).

Un visualizzatore HTML (`index.html`, con una scheda per sezione) permette di provare gli incroci.

## Organizzazione

```
src/                        ← QUI si lavora: tutto ciò che si modifica a mano o si ricava dai fogli
  human/                    risorse degli UMANI
    manifest.json           gruppi, ordine di sagome, capelli e vestiti, palette comune, preset del visualizzatore
                            (un preset può dare un nome e colori di partenza: pelle, capelli, scarpe)
    style.css               classi dei colori, visibilità di capelli e vestiti, animazione idle (uguali per tutte)
    bodies/
      maschio/              bambino · ragazzo · slanciato · adulto · robusto   (.svg = geometria, .json = misure)
      femmina/              bambina · ragazza · slanciata · adulta · robusta
    hair/                   spettinati · coda · chignon · ciuffo-scuro · ciuffo-castano ·        (.svg + .json)
                            arruffati · due-chignon · caschetto · rasati-lato · ricci ·
                            calvizie · stempiato · pettinati-indietro · coda-grigia · chignon-grigio ·
                            caschetto-scalato · coda-alta · lisci-frangia · lunghi-mossi · coda-laterale
    beards/                 barba-incolta · barba-corta · barba-piena · pizzetto · barba-lunga   (.svg + .json)
    clothes/<gruppo>/<sagoma>/  ogni capo sta SOLO sulla sagoma per cui è disegnato (.svg + .json)
      tops/ · bottoms/      le maglie e i pantaloni di quella sagoma
      reference.json        solo maschio/adulto: il corpo su cui sono disegnati i primi cinque capi per tipo
  alien/                    risorse degli ALIENI (separate da quelle degli umani, vedi *Alieni*)
    manifest.json           palette, spessore del contorno, gruppi, sagome, preset del visualizzatore
    style.css               classi dei colori, visibilità delle parti, animazione idle
    bodies/<gruppo>/        le sagome aliene   (.svg = geometria, .json = misure)
    clothes/<gruppo>/<sagoma>/{tops,bottoms}/   i capi alieni di quella sagoma
  viewer/                   il visualizzatore: una sezione della pagina per ogni tipo di sagoma
    template.html           guscio della pagina (intestazione, schede Umani/Alieni, stili comuni)
    common.js               utilità comuni: colori rapidi, export, cambio di sezione
    human.html + human.js   la sezione degli umani
    alien.html + alien.js   la sezione degli alieni

characters/                 ← GENERATO da build.mjs: ogni sagoma composta (file SVG autonomi)
  maschio/…  femmina/…        umani, con i loro capelli e i loro vestiti
  alieno/<gruppo>/…           alieni
index.html                  ← GENERATO: visualizzatore (si apre anche con doppio clic)

build.mjs                   orchestra la build:  node build.mjs  (scrive characters/ e index.html)
build/human.mjs             compone gli umani (src/human/)
build/alien.mjs             compone gli alieni (src/alien/)
build/viewer.mjs            compone la pagina (src/viewer/) con i dati di ogni sezione
build/util.mjs              funzioni comuni alle due sezioni (lettura dei sorgenti, coordinate dei percorsi)
lib/fit.mjs                 deformazione (thin-plate spline) che adatta capelli e capi alla loro sagoma (umani)
serve.mjs                   server statico opzionale:  node serve.mjs → http://localhost:5191

reference/                  fogli di riferimento da cui sono tracciate le sorgenti
  sagome-maschili · sagome-femminili · capelli · capelli-2 · capelli-3 · capelli-anziani · barbe ·
  vestiti-maschili-pantaloni · vestiti-maschili-maglie ·
  vestiti-maschili-outfit · vestiti-femminili · vestiti-femminili-2 · vestiti-femminili-3 · vestiti-femminili-4 · archivio/
  alieno-modello (l'alieno nudo da cui parte lo stile) · sagome-aliene-maschili · sagome-aliene-femminili ·
  vestiti-alieni-maschili · vestiti-alieni-femminili ·
  protuberanze-teste · protuberanze-figure · protuberanze-antenne
tools/                      strumenti Python per tracciare i fogli (vedi tools/README.md)
```

Regola pratica: **si modifica `src/`, poi `node build.mjs`**. `characters/` e `index.html` non si toccano a mano.

Le due sezioni sono indipendenti: ognuna ha le sue risorse, la sua composizione (`build/human.mjs`, `build/alien.mjs`), il suo CSS, la sua
parte del visualizzatore e i suoi id (quelli degli alieni cominciano con `alien-`, le classi dell'animazione con `c-alien-`), così in
una stessa pagina non si influenzano. Le sezioni da *Come si compone un personaggio* a *Variabili CSS* descrivono gli **umani**; gli
**alieni** sono in *Alieni*.

## Come si compone un personaggio

`build.mjs` prende una sagoma da `src/human/bodies/` e le aggiunge:

- **il CSS comune** (`style.css`) con i colori di default di quella sagoma, presi dal suo `.json`;
- **gli stili di capelli adatti alla sua età** (vedi sotto), adattati alla sua testa;
- **le barbe** che valgono per il suo gruppo e la sua età (solo uomini, vedi *Barbe*), adattate alla sua testa;
- **i suoi vestiti** (`src/human/clothes/<gruppo>/<sagoma>/`), quelli elencati per lei in `clothes` nel manifest.

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
con una deformazione morbida (thin-plate spline, `lib/fit.mjs`) dai punti di `src/human/clothes/maschio/adulto/reference.json`
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
- Il sorgente in `src/human/bodies/` contiene solo la geometria e i segnaposto `<!-- @hair-back -->`, `<!-- @hair-skin -->`, `<!-- @beard-skin -->`, `<!-- @beard -->` e `<!-- @hair -->` dentro `head`; colori, capelli, barbe e vestiti li aggiunge la build.

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
disegnati su di lei e solo lì (`src/human/clothes/<gruppo>/<sagoma>/`, elencati per sagoma in `clothes` nel manifest):

| Sagoma | Maglie (`top-<id>`) | Pantaloni (`bottom-<id>`) |
| --- | --- | --- |
| Bambino | `maglietta-riga` (bianca con una riga sul petto) | `bermuda-cargo` (tasche laterali, con gambe e calze) |
| Ragazzo | `felpa-rossa` (cappuccio, cordini, tasca, polsini) | `jeans-grigi` (cucitura centrale) |
| Slanciato | `camicia-risvoltata` (aperta, maniche arrotolate, taschino, maglietta sotto) | `pantaloni-kaki` |
| Adulto | `felpa` (cappuccio, cordini, tasca a marsupio) · `giacca` (colletto, cerniera, tasche, coste) · `polo` (colletto, patta con bottoni) · `maglione` (girocollo, coste) · `camicia` (aperta sulla maglietta) · `polo-blu` (bottoni, infilata nei pantaloni) | `jeans` · `chino` · `jogger` (coste e cordino) · `cargo` (tasche laterali) · `larghi` (gamba larga, pieghe) · `pantaloni-cintura` (cintura e fibbia) |
| Robusto | `cardigan-grigio` (bottoni, coste, maglietta sotto) | `jeans-chiari` |
| Bambina | `maglietta-fiore` (rosa con fiore) · `abitino` (colletto, fiore, pieghe) · `abito-sbuffo` (corpetto bianco con maniche a sbuffo) · `abito-rosa` (corpetto senza maniche) | `pantaloncini` (di jeans risvoltati, con gambe e calze) · `leggings` (con le caviglie) · `gonna-fiocco` (gonna bianca con cintura e fiocco dietro, con gambe) · `gonna-tulle` (gonna a ruota rosa con grande fiocco) |
| Ragazza | `felpa-cappuccio` (cappuccio aperto, cordini, tasca a marsupio) · `maglia-righe` (righe e polsini) · `camicetta-colletto` (colletto alla coreana, maniche a sbuffo) · `abito-bordeaux` (corpetto con spalline) | `jeans-scuri` (tasche, cucitura) · `jeans-cargo` (tasche laterali) · `gonna-rosa` (a campana, con cintura e gambe) · `gonna-bordeaux` (a ruota con fiocco) |
| Slanciata | `top-corto` (canotta nera: spalle, braccia e pancia scoperte) · `giacca-jeans` (aperta su un top nero, maniche risvoltate) · `blusa-quadrata` (scollo quadrato, maniche lunghe) · `abito-nero` (corpetto con spalline sottili e collana) | `jeans-a-zampa` (passanti, bottone, tasche) · `jeans-neri` (risvoltati, caviglie scoperte) · `pantaloni-marroni-cintura` (gamba larga, cintura con fibbia) · `gonna-lunga-nera` (lunga con spacco, la gamba nello spacco è pelle) |
| Adulta | `maglietta-v` (verde oliva, scollo a V) · `maglione-v` (a coste, maniche a tre quarti) · `blazer-beige` (maniche arrotolate, risvolti, maglietta bianca sotto) · `camicetta-bluse` (a portafoglio, maniche a sbuffo con polsini) | `pantaloni-neri` (gamba larga) · `pantaloni-oliva` · `pantaloni-neri-cintura` (con cintura) · `gonna-verde` (al polpaccio, con fiocco) |
| Robusta | `cardigan` (maniche arrotolate, bottoni, maglietta sotto) · `cardigan-fiori` (tasca, coste, su una maglia a fiori) · `abito-portafoglio` (corpetto incrociato con maniche svolazzanti) · `tuta-blu` (corpetto della tuta, senza maniche) | `pantaloni-marroni` · `pantaloni-scuri` · `gonna-portafoglio` (gonna al polpaccio con cintura e fiocco, con gambe) · `tuta-pantaloni` (gamba larga, cintura con fibbia dorata) |

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
(`vestiti-femminili`, `vestiti-femminili-2`, `vestiti-femminili-3`, `vestiti-femminili-4`, `vestiti-maschili-outfit`) in cui ogni figura indossa maglia e pantaloni sul
proprio corpo: il capo si traccia su quella figura e resta su quella sagoma. I fogli mostrano anche le scarpe di ogni
outfit: non sono capi ma colori, e li impostano i preset (`colors`). I dieci capi della prima serie maschile
vengono invece da due fogli sullo stesso corpo e stanno su `maschio/adulto`. Cose particolari rispetto ai primi capi
maschili:

- *Pelle scoperta*: i pantaloncini portano con sé gambe e calze (i pantaloni della sagoma si nascondono); il top corto porta spalle e braccia (`replaces: ["arms"]` nel `.json`, nel gruppo `.g-arms`: le braccia della sagoma si nascondono con `--show-body-arms: none`, e `--show-arms` nasconde tutte le braccia) e la pancia.
- *Livello sotto* (`<g id="…-under">`): la pancia del top corto sta sotto i pantaloni, così non dipende dai pantaloni scelti; i pantaloni salgono di qualche px sotto la maglia, e una maglia corta o infilata (la polo, il top sotto la giacca di jeans) scende sotto i pantaloni, così negli incroci non restano buchi in vita.
- *Dettagli senza contorno* ricavati dal colore: fiori, righe, risvolti, calze, bottoni chiari.
- *Scollo*: la pelle sotto il collo (V, cappuccio, scollo ampio) è parte del capo.
- *Abiti e gonne* (terza e quarta serie femminile): un abito è diviso in due capi, il corpetto (una maglia, con le maniche) e la gonna (nei pantaloni, con cintura, fiocchi e le gambe scoperte sotto l'orlo, come i pantaloncini); la gonna sta dietro al braccio vicino e davanti ai pantaloni base, quindi vale con qualunque maglia della sagoma. Le gonne a campana sono più larghe della sagoma ma stanno nello stesso riquadro (322×742). Le scarpe del foglio (ballerine, mary jane, tacchi) non sono disegnate: restano le scarpe base della sagoma e dal foglio si prendono solo i colori, nei preset. Un abito intero senza la linea della vita (l'abito nero della slanciata) si divide con un taglio a una certa altezza: il corpetto è la maglia, la gonna lunga i pantaloni, e la cucitura in vita si vede solo come tratto sottile. Un capo senza maniche (o con spalline) disegna spalle e braccia da sé (`replaces: ["arms"]`, come il top corto): le braccia della sagoma si nascondono e con loro i riempimenti di fondo del busto e dei pantaloni vicino alle braccia, che altrimenti sporgerebbero dove le braccia del foglio sono in un'altra posizione. Il corpetto ha sempre una fascia sotto i pantaloni (`under_down`), lunga abbastanza per coprire la vita con qualunque altro pantalone della sagoma.

## Animazione idle

Definita direttamente in ogni SVG (CSS `@keyframes`, solo `transform`), quindi parte anche aprendo il file da solo nel browser:

- **respiro**: busto e braccia si allungano di ~1% ancorati alla base, la testa si alza di 2 px con 0.14 s di ritardo (cicli di 1.9 s, andata e ritorno); le maglie (con le loro parti sotto e dietro) respirano col busto attorno allo stesso punto, la base del busto
  (`.c-origin-<gruppo>-<sagoma>`, coordinate assolute): così i livelli non si separano;
- **battito di ciglia**: gli occhi si schiacciano brevemente ogni 4.6 s.

Con `prefers-reduced-motion` l'SVG resta fermo. Nel visualizzatore c'è l'interruttore *Animazione*; il PNG esportato è sempre un fotogramma fermo.

## Variabili CSS

`--outline`, `--line-w`, `--skin`, `--hair`, `--shirt` (+ `-trim`, `-accent`, `-accent2`, `-under`), `--pants` (+ `-trim`, `-accent`, `-under`), `--shoe-upper-l`, `--shoe-upper-r`, `--shoe-toe`, `--shoe-tongue`, `--shoe-lace`, `--shoe-sole`, `--eye`, più `--idle-n` (`0` spegne l'animazione), `--idle-delay` (sfasa più istanze), `--show-hair` / `--show-hair-<id>`, `--beard` e `--show-beard` / `--show-beard-<id>`, `--show-top-<id>` e `--show-bottom-<id>` (`inline` | `none`), `--show-arms` e `--show-body-arms`.

## Alieni

Gli alieni sono una sezione a parte: risorse in `src/alien/`, composizione in `build/alien.mjs`, file in `characters/alieno/`. Con gli
umani hanno in comune solo la scala (stessa linea del suolo `y = 900`, la figura più alta come un adulto) e le utilità della pagina.
Non hanno capelli né barbe: ogni sagoma ha la sua maglietta e i suoi pantaloncini (colori a piacere) oppure, a scelta, un **abito** disegnato
sulla sagoma (una maglia e dei pantaloni o una gonna: vedi *Vestiti*) e, a scelta, una **protuberanza** (corna, palchi, pinne, creste,
antenne: vedi sotto).

| Gruppo | Sagome | Dal foglio |
| --- | --- | --- |
| Maschio | `bambino` · `ragazzo` · `adulto` · `curvo` (spalle e testa piegate in avanti) | `reference/sagome-aliene-maschili.webp` |
| Femmina | `bambina` · `ragazza` · `adulta` · `curva` (spalle e testa piegate in avanti) | `reference/sagome-aliene-femminili.webp` |

Il disegno di partenza dello stile (un alieno nudo) è `reference/alieno-modello.webp`.

```
src/alien/manifest.json     palette di default (skin, shirt, pants, eye), lineWidth (spessore di partenza del contorno),
                            gruppi, sagome (`gruppo/nome`), protuberanze, capi (`clothes`: per sagoma i suoi `tops` e
                            `bottoms`) e preset (sagoma + nome + colori di partenza + eventuale `prot`, `top`, `bottom`)
src/alien/style.css         classi dei colori, visibilità delle parti e delle protuberanze, animazione idle
src/alien/bodies/<gruppo>/  <nome>.svg (geometria) + <nome>.json (nome, misure della testa, punti di riferimento, colori)
src/alien/protrusions/      <id>.svg (geometria) + <id>.json (nome e testa di riferimento)
src/alien/clothes/<gruppo>/<sagoma>/tops/ e bottoms/    <id>.svg (geometria) + <id>.json (nome, colori per ruolo, parti sostituite)
```

**Struttura dell'SVG di una sagoma.** Dal fondo al primo piano: `alien-head` (testa e collo, in due passate come per gli umani: riempimento
e contorno; poi narici `c-dot` e occhi `c-eye c-alien-blink`) → `alien-arm-right` → `alien-legs` (`alien-leg-left` e `alien-leg-right`, coi
piedi e le linee delle dita) → `alien-pants` (i pantaloncini) → `alien-arm-left` → `alien-torso` (la maglia). Il disegno della sagoma sta in
un gruppo `alien-base-…` dentro ogni parte (`alien-base-torso`, `alien-base-pants`, `alien-base-arms`, `alien-base-legs`), accanto ai
segnaposto dove la build mette i capi (vedi *Vestiti*). Ogni parte è una regione
chiusa col suo contorno; le regioni vicine si toccano a metà del tratto scuro del foglio, e le linee interne (dita delle mani e dei
piedi, cucitura dei pantaloncini, cuciture della maglia) sono linee aperte. Le pieghe più scure della stoffa (`c-fold`: la maglia del
`curvo` e `curva`, le tasche dei pantaloncini rosa) sono linee sottili col colore del contorno al 40%, così stanno bene su qualunque colore. Il riempimento della testa
scende di 10 px sotto il colletto (nascosto dalla maglia): quando la testa si alza nell'idle non si apre una fessura. Il sorgente
contiene solo la geometria: colori, CSS e riquadro comune (stessa scala e stessa linea del suolo per tutte) li aggiunge la build.

**Protuberanze.** Come i capelli degli umani sono disegnate una volta sola, su una testa di riferimento (`frame` nel loro `.json`: la
cima e il centro e la mezza larghezza del cranio di `maschio/adulto`), e la build le adatta a ogni sagoma con le stesse misure della sua
testa (`skullX`, `skullHalf`, `T` nel `.json` della sagoma, cima e calotta del cranio): scala uniforme, così non si deformano. Sono nel
gruppo della testa (seguono l'idle). Un percorso `c-behind` sta **dietro** la testa (`alien-prot-<id>-back`, prima del suo riempimento):
la base continua di qualche px dentro il cranio, dove la testa di ogni sagoma la copre, e il tratto c'è solo sul bordo esterno; gli
altri stanno **davanti** (`alien-prot-<id>`, sopra il contorno e sotto gli occhi: le corna a spirale, che passano davanti al cranio).

| Protuberanza (`id`) | Nome | Foglio |
| --- | --- | --- |
| `corna-a-spirale` | Corna a spirale (davanti alla testa) | `protuberanze-teste` |
| `palchi` | Palchi | `protuberanze-teste` |
| `corna-lunghe` | Corna lunghe | `protuberanze-teste` |
| `corno-curvo` | Corno curvo (uno grande e uno piccolo) | `protuberanze-teste` |
| `cresta-a-foglia` | Cresta a foglia (sul retro della testa) | `protuberanze-figure` |
| `pinne` | Pinne laterali | `protuberanze-figure` |
| `cresta-al-vento` | Cresta al vento | `protuberanze-figure` |
| `spine` | Cresta a spine (con le orecchie a punta) | `protuberanze-figure` |
| `antenne-a-pallina` | Antenne a pallina | `protuberanze-antenne` |
| `antenne-lunghe` | Antenne lunghe e curve | `protuberanze-antenne` |
| `antenna-a-perline` | Antenna centrale a perline | `protuberanze-antenne` |
| `antenne-a-pagaia` | Quattro antenne a pagaia | `protuberanze-antenne` |

Valgono per tutte le sagome; una alla volta (nessuna di default, o quella del preset: `prot` nel manifest). Il colore è quello della pelle
finché non se ne sceglie un altro (`--prot`).

**Vestiti.** Ogni capo è disegnato su una sola sagoma e si vede solo su quella (come per gli umani): `tops/` (la maglia) e `bottoms/` (i
pantaloni o la gonna). I fogli dei vestiti (`reference/vestiti-alieni-*.webp`) sono i fogli delle sagome nude con un abito disegnato sopra
a ogni figura, nella stessa posa e alla stessa scala (scarto < 0.3 px): le coordinate sono quelle della sagoma e la build non deforma
nulla. L'abito della figura si divide in maglia (collo, mantelline, tuniche…) e pantaloni (cintura, gonna, bermuda). Ogni capo ha:

- i **ruoli di colore** `main`, `trim`, `accent`, `accent2` (variabili `--shirt`, `--shirt-trim`, `--shirt-accent`, `--shirt-accent2` per le
  maglie; `--pants` e le stesse con `pants-` per i pantaloni): ogni regione del foglio è assegnata a mano a un ruolo, e i dettagli senza
  contorno (strisce, un rombo) si ricavano dal colore dentro la regione. I colori di partenza sono quelli del foglio. `skin` = pelle
  (`--skin`) che il capo lascia scoperta fra le sue parti;
- le **parti del corpo che sostituisce**: una maglia porta le proprie *braccia* (una manica più corta, o nessuna, scopre il braccio più in
  alto di dove comincia quello della sagoma, che sotto la maglietta è nascosto) e dei pantaloni le proprie *gambe* (un orlo più alto scopre
  la coscia). Le parti sono tracciate dalla stessa figura, quindi dita e piedi coincidono con quelli della sagoma, che il CSS spegne
  (`--show-alien-base-arms`, `--show-alien-base-legs`). Un capo che scende sul collo (o lascia una spalla scoperta che si fonde col collo)
  ha anche il **pezzo di collo** che copre il contorno inferiore della testa della sagoma (e il riempimento che scende sotto il
  colletto, `alien-neckfill`, si spegne con qualunque maglia: il capo ha il suo collo);
- i **livelli**: davanti (`alien-top-<id>` dentro `alien-torso`, `alien-bottom-<id>` dentro `alien-pants`), dietro le braccia e le
  gambe (`alien-top-<id>-back`: la coda di un mantello) e dietro i pantaloni (`alien-top-<id>-under`: la fascia con cui la maglia scende fino
  ai pantaloncini di base, o la pancia scoperta; i pantaloni salgono dietro la maglietta di base). I livelli dietro stanno in `alien-back`,
  dopo la testa. Tutto ciò che sta sul busto respira attorno allo stesso punto (la base della maglietta, `.c-alien-o-<gruppo>-<sagoma>`).

La scelta è `--show-alien-top-<id>` e `--show-alien-bottom-<id>` (`base` = la maglietta e i pantaloncini della sagoma). Gli otto capi:

| Sagoma | Maglia | Pantaloni |
| --- | --- | --- |
| `maschio/bambino` | `tunica-cappuccio` | `gonnellino` |
| `maschio/ragazzo` | `tunica-banda` | `kilt-scuro` |
| `maschio/adulto` | `poncho` | `kilt-verde` |
| `maschio/curvo` | `mantellina` | `bermuda` |
| `femmina/bambina` | `tunica-spallina` | `gonna-avvolgente` |
| `femmina/ragazza` | `tunica-monospalla` | `gonna-malva` |
| `femmina/adulta` | `corpetto-pendente` | `gonna-pannello` |
| `femmina/curva` | `mantello` | `gonna-sbieca` |

Si combinano a piacere fra loro e con la maglietta e i pantaloncini di base; gli otto abiti completi sono anche i personaggi di partenza
*… · tunica*, *… · kilt* ecc. Le combinazioni miste sono un'approssimazione: una maglia più corta dei pantaloncini di base lascia vedere
la pancia (o, per le tuniche lunghe, la maglia che scende), dei pantaloni più bassi della maglietta salgono dietro di essa.

**Variabili CSS.** `--skin`, `--shirt` (+ `-trim`, `-accent`, `-accent2`), `--pants` (+ `-trim`, `-accent`, `-accent2`), `--eye`, `--outline`, `--line-w`, `--prot` (colore delle protuberanze; se manca vale
`--skin`), `--idle-n` (`0` spegne l'animazione), `--idle-delay`, e la visibilità di ogni parte con `--show-alien-head`, `--show-alien-torso`,
`--show-alien-arms`, `--show-alien-pants`, `--show-alien-legs` e `--show-alien-prot` (tutte le protuberanze), più
`--show-alien-prot-<id>` (una sola), `--show-alien-top-<id>`, `--show-alien-bottom-<id>`, `--show-alien-base-arms` e
`--show-alien-base-legs` (`inline` | `none`). Le narici seguono `--outline`.

**Animazione idle.** Come per gli umani: busto e braccia respirano (si allungano di ~1%, ancorati alla base), la testa si alza di 2 px con un
piccolo ritardo, gli occhi sbattono ogni 4.6 s. Con `prefers-reduced-motion` l'SVG resta fermo. Nel fotogramma estremo del respiro non si
aprono vuoti fra le parti (controllato su tutte le sagome).

**Tracciatura.** `tools/trace_alien.py` ricava le sagome da un foglio di figure affiancate (vedi `tools/README.md`):

```
python3 tools/trace_alien.py reference/sagome-aliene-maschili.webp --out src/alien/bodies/maschio \
    --names bambino,ragazzo,adulto,curvo
python3 tools/trace_alien.py reference/sagome-aliene-femminili.webp --out src/alien/bodies/femmina \
    --names bambina,ragazza,adulta,curva
```

Poi: le sagome in `bodies` e un preset per ognuna in `src/alien/manifest.json`, lo spessore del contorno stampato dallo strumento in
`lineWidth`, e `node build.mjs`. Un gruppo nuovo è una cartella in più e una voce in `groups`. Rifacendo le sagome vanno rifatti anche
le protuberanze e i vestiti (si ancorano alle loro misure).

I vestiti si tracciano da un foglio dei vestiti allineato a quello delle sagome, con le regioni di ogni figura assegnate a mano ai ruoli
nella tabella `OUTFITS` di `tools/trace_alien_outfits.py` (`-v` stampa gli indici di regione):

```
python3 tools/trace_alien_outfits.py reference/vestiti-alieni-maschili.webp \
    --bodies-sheet reference/sagome-aliene-maschili.webp --bodies src/alien/bodies/maschio \
    --names bambino,ragazzo,adulto,curvo --out src/alien/clothes/maschio
python3 tools/trace_alien_outfits.py reference/vestiti-alieni-femminili.webp \
    --bodies-sheet reference/sagome-aliene-femminili.webp --bodies src/alien/bodies/femmina \
    --names bambina,ragazza,adulta,curva --out src/alien/clothes/femmina
```

Poi i capi in `clothes["<gruppo>/<sagoma>"]` del manifest (`tops` e `bottoms`) e, per un personaggio di partenza con quell'abito, in un preset
(`top`, `bottom`).

Le protuberanze si tracciano con `tools/trace_protrusions.py` (vedi `tools/README.md`); l'id va in `protrusions` del manifest e, se si vuole
un personaggio di partenza con quella protuberanza, in un preset (`prot`). Rifacendo le sagome vanno rifatte anche le protuberanze
(ne dipendono le misure della testa di riferimento).

## Visualizzatore

La pagina ha una scheda per sezione (**Umani**, **Alieni**; l'indirizzo `#umani` / `#alieni` apre quella voluta) e ognuna ha la sua
anteprima, il suo pannello e il suo stato: passando da una all'altra non si perde il personaggio scelto. Quanto segue descrive gli
umani; la sezione degli alieni ha lo stesso impianto con sagoma, colori (pelle, occhi, maglia e pantaloni coi loro ruoli secondari,
contorno), parti visibili (testa, maglia, braccia, pantaloni, gambe, protuberanze), scelta della protuberanza, della maglia e dei
pantaloni (solo i capi della sagoma scelta; cambiando sagoma tornano la maglietta e i pantaloncini di base), idle ed export. Nella vista
*Affiancati* le figure vanno a capo dopo otto per riga.

Ci sono ventisei personaggi di partenza (i preset del manifest: uno o due per sagoma, quattro per le femmine, ognuno con un abbinamento di capi della sua sagoma; la seconda, la terza e la quarta serie femminile portano i capelli nuovi; *Adulto · polo* e *Robusto · cardigan* hanno la barba), divisi per gruppo (*Tutti / Maschio / Femmina*). Per quello selezionato si possono cambiare **sagoma** (tutte e dieci), **stile dei capelli**, **barba** (solo sagome maschili: la sezione compare solo per loro e solo con le barbe che valgono per la sagoma), **maglia**, **pantaloni** e ogni colore. I colori che non hai toccato seguono la sagoma e i capi scelti; quelli che hai scelto restano. I capi disponibili sono solo quelli della sagoma scelta: se cambi sagoma, maglia e pantaloni passano all'abito di partenza di quella sagoma (il primo dei suoi preset), e se la sagoma non ha capi restano la maglietta e i pantaloni base. Un personaggio resta nel gruppo del suo preset anche se gli dai la sagoma dell'altro gruppo. Tasti `1`–`9`, `0` o `←` `→` per cambiare personaggio.

**Colori.** I campi sono divisi per parte (corpo, maglia, pantaloni, scarpe, contorno e occhi) e mostrano solo i ruoli che il capo scelto ha. Sotto ogni campo ci sono dei colori rapidi: toni della pelle, colori di capelli naturali e di fantasia, una tavolozza di tessuti; per le scarpe una tavolozza unica per la tomaia e una per la suola. `↺` riporta un campo al suo colore di default; *Vestiti a caso* e *Pelle e capelli a caso* pescano dalle tavolozze (maglia e pantaloni ben distinti), *Colori di default* azzera tutto.

I colori di partenza sono i default scritti nel CSS di ogni SVG, più i `colors` del preset (pelle, capelli, scarpe). Il bottone *Scarica SVG* scrive i valori scelti direttamente nel file (e tiene solo i capelli, la barba, la maglia e i pantaloni scelti), quindi il risultato si apre anche in Illustrator, Inkscape o Figma (che ignorano `var()`).

## Aggiungere una sagoma, uno stile di capelli o dei vestiti

- **Sagoma**: tracciarla con `tools/trace_bodies.py` (o scrivere a mano `src/human/bodies/<gruppo>/<nome>.svg` + `.json` con la stessa struttura, compresi i punti `head` e `landmarks`), poi aggiungerla a `bodies` e a `presets` in `src/human/manifest.json`. Un gruppo nuovo (per esempio *Anziani*) è una cartella in più, più una voce in `groups`.
- **Stile di capelli**: `tools/trace_hair.py` o a mano in `src/human/hair/<id>.svg` + `.json`, poi l'id in `hair` nel manifest.
- **Barba**: `tools/trace_beards.py` (tabella `BEARDS` con gruppi ed età) in `src/human/beards/<id>.svg` + `.json`, poi l'id in `beards` nel manifest; un preset può averne una (`beard`, e `beard` in `colors`).
- **Vestiti**: ogni capo sta su una sola sagoma, quindi si traccia su quella. Con un foglio in cui ogni figura indossa un outfit sul proprio corpo (come per le femmine): `tools/trace_outfits.py`, con le regioni di ogni figura assegnate a mano nella sua tabella `OUTFITS` (la riga dice la sagoma). Con due fogli di figure sullo stesso corpo (pantaloni e maglie, come per la prima serie maschile): `tools/trace_clothes.py --out src/clothes/<gruppo>/<sagoma>`; il corpo di riferimento è la prima figura del foglio dei pantaloni e i capi vengono deformati dalla build su quella sagoma (deve essere simile). Poi i capi nel manifest, in `clothes["<gruppo>/<sagoma>"]` (`tops` e `bottoms`), e se si vuole in un preset (`top`, `bottom`, `colors`).
- **Alieni**: `tools/trace_alien.py` su un foglio di figure affiancate, poi `bodies` e `presets` in `src/alien/manifest.json`; i vestiti con `tools/trace_alien_outfits.py` da un foglio dei vestiti allineato a quello delle sagome (vedi *Alieni*).
- Poi `node build.mjs`, e se si vuole l'audit (sotto).

## Audit delle combinazioni (umani)

```
NODE_PATH=$(npm root -g) node tools/audit.mjs      # serve playwright (npm i -g playwright), circa 3 minuti
```

Rende nel browser, per ogni sagoma, ogni maglia con ogni pantalone **della sua sagoma** (compresi la maglietta e i
pantaloni base) e ogni stile di capelli con ogni maglia, più ogni barba sulla sagoma che la prevede: 1203 combinazioni, circa 3 minuti. Cerca i difetti
confrontando ogni combinazione con la sagoma base: vuoti nel busto, nelle braccia e alle caviglie, fessure sottili
chiuse dalla figura, pezzi staccati, parti tagliate dal riquadro, l'estensione dei pantaloni che si vede, livelli sotto
che coprono il braccio o sporgono, vuoti nel fotogramma estremo del respiro, occhi coperti dai capelli (lo sfondo racchiuso fra le ciocche dei capelli lunghi, la testa
e le spalle non conta: fa parte del disegno); controlla anche
che l'SVG esportato dal visualizzatore sia uguale a quello mostrato e che i file siano validi (XML, id unici, ogni parte
con un colore). Scrive `audit/report.html` (per ogni difetto le combinazioni peggiori, col difetto colorato) e
`audit/report.json`. Per rifare solo una parte: `--only=femmina/robusta`, `--skip=hair,export`.

## Audit delle combinazioni (alieni)

```
NODE_PATH=$(npm root -g) node tools/audit_alien.mjs      # serve playwright, circa 40 secondi
```

Rende nel browser ogni sagoma aliena con ogni combinazione di maglia e pantaloni (di base o del capo: 32 combinazioni) e controlla due
cose: che nel fotogramma estremo del respiro (busto e braccia allungati, testa su) non si apra fra le parti nessun vuoto che nella posa
base non c'era, e che l'SVG esportato dal visualizzatore sia uguale a quello mostrato. `AUDIT_ONLY=curvo` limita il controllo alle
sagome che contengono quel testo.
