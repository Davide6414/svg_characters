# Strumenti di tracciatura

Servono a ricavare le sorgenti in `src/` dai fogli di riferimento in `reference/`. Non servono per usare i
personaggi: quelli si ricostruiscono con `node build.mjs`.

```
pip install -r tools/requirements.txt      # numpy, Pillow, potracer (potrace in Python puro)
```

Sono deterministici: rigenerando da `reference/` si ottengono file identici a quelli in `src/`.

## Sagome: `trace_bodies.py`

```
python3 tools/trace_bodies.py reference/sagome-maschili.webp  --out src/human/bodies/maschio \
    --names bambino,ragazzo,slanciato,adulto,robusto
python3 tools/trace_bodies.py reference/sagome-femminili.webp --out src/human/bodies/femmina \
    --names bambina,ragazza,slanciata,adulta,robusta
```

Per ogni figura (da sinistra a destra) scrive `<nome>.svg` (solo geometria, vedi il README principale) e
`<nome>.json` (nome visualizzato, punti di riferimento della testa, 34 punti di riferimento del corpo, colori di
pantaloni e scarpe).

Cosa si aspetta il foglio: figure affiancate su sfondo chiaro, nella stessa posa e con lo stesso disegno (testa con
orecchio a sinistra, braccio sinistro davanti, maglia, pantaloni, due scarpe), con un contorno scuro continuo.

Come lavora (moduli in `lib/`):

1. `sheet.py` trova le figure: colonne di pixel non di sfondo separate da spazio vuoto.
2. `segment.py` segmenta ogni figura: il contorno è la rete di pixel scuri (luminanza ≤ 34), le regioni sono le
   componenti connesse del resto, gli occhi sono le macchie scure staccate dalla rete (allungate, in alto). Le altre
   macchie staccate restano come linee interne, i puntini tondi si registrano (bottoni). Dove tomaia e suola di una
   scarpa risultano un'unica regione (manca la linea fra le due) le separa per colore o con un taglio geometrico.
3. `parts.py` dà un ruolo a ogni regione (testa, maglia, braccia, pantaloni, suola, tomaia, linguetta, punta,
   lacci), fa crescere le regioni dentro il contorno fino a metà del tratto (Voronoi) e traccia ogni cella con
   potrace. I pantaloni scendono sotto le scarpe e salgono sotto la maglia (`pants-under`, una fascia in un livello
   sotto). Le fessure interne (orecchio, cuciture, pieghe) diventano linee aperte. Misura anche i punti di riferimento
   (`landmarks`): riquadri di busto, braccia e pantaloni, collo, pugni, bordi del busto contro le braccia, fianchi,
   scarpe e ginocchia. Sono misure del corpo, non dei vestiti base: le larghezze delle gambe, per esempio, non ci
   sono (i pantaloni base svasati o dritti sono uno stile), le scarpe sì.
4. Tutte le sagome vengono spostate in verticale perché le suole poggino su y = 900: stessa linea del suolo.
5. `export.py` scrive i file.

Dopo la tracciatura: aggiungere le sagome a `bodies` e `presets` in `src/human/manifest.json` e lanciare `node build.mjs`.
Se cambiano i punti di riferimento (`landmarks`) vanno rigenerate anche le sagome già esistenti.

## Capelli: `trace_hair.py`

```
python3 tools/trace_hair.py reference/capelli.webp --out src/human/hair
python3 tools/trace_hair.py reference/capelli-3.webp --out src/human/hair
```

Per i fogli di **soli capelli su sfondo trasparente** (RGBA). La tabella `HAIRS[nome del foglio]` ha una riga per
stile: il riquadro nel foglio, il punto di appoggio (`notch`) e dove deve finire nel riquadro dei capelli (`ear`), la
scala (`s`) e quali linee interne tenere (`keep`, `thick`). `seed` è un punto dentro lo stile: resta solo la sua
componente connessa (negli stili vicini i riquadri si sovrappongono). Se un filo sottile (il laccio di una coda)
sparisce con l'erosione del contorno la sagoma viene scritta come più isole.

Per allineare un nuovo stile conviene sovrapporlo alla testa di riferimento (`hairFrame` nel manifest) e provare
scala e punto di appoggio:
- `capelli.webp`: il punto di appoggio è la tacca dell'orecchio, che finisce sull'orecchio della testa (`ear`);
- `capelli-3.webp` (capelli lunghi, senza tacca): è il bordo destro dell'apertura per il viso all'altezza degli occhi,
  che finisce poco prima del contorno destro della testa (`ear` x = 237 invece di 242: i capelli si appoggiano al
  viso, senza striscia di sfondo), con la scala 0.80 (0.86 per i lunghi, che altrimenti lasciano scoperto il retro
  del cranio); l'altezza si regola in modo che la cima dei capelli stia circa 12 px sopra il cranio.

Poi aggiungere l'id a `hair` nel manifest e lanciare `node build.mjs`.

## Capelli da figure intere: `trace_hair_figures.py`

```
python3 tools/trace_hair_figures.py reference/capelli-2.webp --out src/human/hair
python3 tools/trace_hair_figures.py reference/capelli-anziani.webp --out src/human/hair
```

Per un foglio di figure intere, ognuna con un'acconciatura diversa (`lib/hair_figures.py`). I capelli vanno isolati dalla
testa:

1. **Occhi**: le due macchie scure più spesse in alto (resistono a un'apertura morfologica anche se toccano una ciocca).
   Le teste delle figure hanno le proporzioni della testa di riferimento, quindi l'allineamento al riquadro dei capelli
   (`hairFrame`) si fa con gli occhi: stessa posizione, scala dalla distanza fra gli occhi. Per una testa calva
   (`fit_top`) si allinea anche la cima del cranio.
2. **Capelli**: nella zona della testa (sopra la maglietta), i pixel lontani dal colore della pelle o meno caldi (i
   grigi). I pixel sfumati vicino al contorno restano da assegnare: capelli, pelle e resto crescono fin dentro il
   contorno e il confine cade a metà del tratto, come per le sagome.
3. **Contorno**: solo dove il foglio ha un tratto scuro (fra capelli e fronte spesso c'è solo il cambio di colore), come
   linee aperte; il riempimento è senza tratto. Le **linee interne** (ciocche) sono i tratti scuri dentro la sagoma, con
   tre spessori; i **capelli sparsi** (`strays`) quelli sottili sopra una testa calva; la **zona rasata** (`shaved`)
   i capelli più chiari della media, disegnati con lo stesso colore trasparente (`.c-shaved`).
4. **Parti attaccate al cranio.** La testa di ogni sagoma ha un contorno diverso da quello del foglio, quindi ciò che
   deve toccare il cranio non si disegna "a occhio" ma in modo che la build lo faccia combaciare con ogni testa:
   - la zona rasata si allarga in orizzontale oltre il contorno della testa del foglio e non ha tratto verso l'esterno
     (quello è il contorno della testa); la build la ritaglia sulla testa della sagoma (livello `hair-skin`, classe
     `c-shaved`);
   - `behind='right'`: i ciuffi a destra degli occhi stanno dietro la testa (livello `hair-back`, classe `c-behind`): si
     prolungano dentro il cranio, dove la testa li copre, e hanno il tratto lungo tutto il bordo;
   - i capelli sparsi partono da dentro il cranio (si prolungano di ~11 px oltre il contorno) e solo i capelli lunghi
     che stanno sul cranio si tengono.
   Il resto (la massa dei capelli) sta davanti e può sporgere oltre la testa.

La tabella `HAIRS[nome del foglio]` ha una riga per figura: id, nome, età (`ages`) e le opzioni sopra. L'età dice a quali
sagome si applica lo stile (`ages` nel manifest): gli stili da anziani non vanno ai bambini.

## Barbe: `trace_beards.py`

```
python3 tools/trace_beards.py reference/barbe.webp --out src/human/beards
```

Per un foglio di figure intere con la stessa testa calva e una barba diversa (`lib/beard_figures.py`). Come per i capelli da
figure, le figure si allineano alla testa di riferimento con gli occhi e le coordinate sono quelle del riquadro dei capelli
(`hairFrame`): la build adatta la barba a ogni testa con la stessa deformazione dei capelli. La tabella `BEARDS[nome del
foglio]` ha una riga per figura: id, nome, `groups` e `ages` (a quali sagome vale) e le opzioni (`stubble`, soglie).

1. **Barba**: i pixel scuri e caldi (marrone) nel viso basso, con un'apertura che toglie il bordo sfumato del contorno e
   una chiusura che ricompone una barba a ciocche; la pelle e il resto si segmentano come per i capelli (le regioni
   crescono fin dentro il contorno, il confine cade a metà del tratto). Il buco della bocca resta un buco.
2. **Contorno e linee**: dove il foglio ha un tratto scuro, anche attorno al buco della bocca.
3. **Sotto il contorno della testa** (`ext`, classe `c-skinlayer`): la sagoma allargata di 7 px solo verso l'esterno (mai sulla
   pelle del viso), che la build ritaglia sulla testa della sagoma e disegna fra il riempimento e il contorno: così la barba
   arriva sempre fino al bordo del viso, qualunque sia la testa.
4. **Barba incolta** (`stubble`): non c'è una sagoma ma puntini grigi sulla pelle, lontani dal contorno spesso (soglia di
   luminanza `dot_lum`, area massima `dot_max`), scritti in un solo percorso con gli estremi tondi; il segno della bocca è
   la sola macchia più grande (`mark_max`) e diventa una linea.

## Vestiti: un capo, una sagoma

Ogni capo sta **solo sulla sagoma su cui è disegnato**: i file sono in `src/human/clothes/<gruppo>/<sagoma>/{tops,bottoms}/`
e il manifest li elenca per sagoma (`clothes["maschio/adulto"].tops`…). Mischiare i capi fra corporature diverse dava
sempre problemi di vestibilità, quindi non esiste più nessun adattamento fra sagome. Un capo per un'altra sagoma si
traccia di nuovo su quella sagoma. Due strumenti, secondo il foglio.

## Due fogli sullo stesso corpo: `trace_clothes.py`

```
python3 tools/trace_clothes.py --out src/human/clothes/maschio/adulto \
    --bottoms reference/vestiti-maschili-pantaloni.webp --tops reference/vestiti-maschili-maglie.webp
```

Servono due fogli con figure affiancate che indossano capi diversi **sullo stesso corpo**: uno con i pantaloni (e la
maglietta bianca di base), uno con i capi per il busto (e i pantaloni di base). `--out` è la cartella della sagoma a cui
i capi appartengono: la più simile a quel corpo (il corpo dei fogli maschili è un adulto a meno del 5% da
`maschio/adulto`). Scrive in `--out`:

- `reference.json`: i punti di riferimento del corpo su cui sono disegnati i vestiti (la prima figura del foglio dei
  pantaloni, che ha maglietta e pantaloni semplici);
- `bottoms/<id>.svg` + `.json` e `tops/<id>.svg` + `.json`: i capi, nel riquadro di quel corpo, con `"ref": "reference"`
  nel json: la build li deforma leggermente dal corpo del foglio alla sagoma della cartella.

Come lavora (`lib/clothes.py`): segmenta la figura come per le sagome, toglie ciò che è corpo (testa, mani) e ciò che
non è il capo (scarpe, e la maglietta o i pantaloni di base), e traccia le regioni rimaste: ogni regione ha un
**ruolo di colore** (`main`, `trim`, `accent`, `under`: principale, bordi, dettagli, maglietta sotto un capo aperto)
assegnato in automatico dal colore e dalle dimensioni. Le linee interne (cuciture, tasche, cerniera) e i bottoni
diventano linee e puntini. Il capo viene portato nel riquadro del corpo di riferimento allineando testa e suolo.

**Correzione dei ruoli.** Le tabelle `BOTTOMS` e `TOPS` in cima al file hanno una riga per figura (da sinistra a
destra): id, nome e le correzioni `{indice regione: ruolo}`. Per vedere gli indici si lancia con `-v`.

## Outfit: `trace_outfits.py`

```
python3 tools/trace_outfits.py reference/vestiti-femminili.webp   --bodies src/human/bodies/femmina --out src/human/clothes/femmina
python3 tools/trace_outfits.py reference/vestiti-femminili-2.webp --bodies src/human/bodies/femmina --out src/human/clothes/femmina
python3 tools/trace_outfits.py reference/vestiti-femminili-3.webp --bodies src/human/bodies/femmina --out src/human/clothes/femmina
python3 tools/trace_outfits.py reference/vestiti-femminili-4.webp --bodies src/human/bodies/femmina --out src/human/clothes/femmina
python3 tools/trace_outfits.py reference/vestiti-maschili-outfit.webp --bodies src/human/bodies/maschio --out src/human/clothes/maschio
python3 tools/trace_outfits.py reference/vestiti-maschili-2.webp --bodies src/human/bodies/maschio --out src/human/clothes/maschio
python3 tools/trace_outfits.py reference/vestiti-maschili-3.webp --bodies src/human/bodies/maschio --out src/human/clothes/maschio
python3 tools/trace_outfits.py reference/vestiti-maschili-4.webp --bodies src/human/bodies/maschio --out src/human/clothes/maschio
```

Per un foglio in cui **ogni figura indossa maglia e pantaloni sul proprio corpo** (le cinque sagome di un gruppo, ognuna
con il suo outfit). La tabella delle figure si sceglie dal nome del foglio (`OUTFITS['vestiti-femminili-2']`…): la
riga dice su quale sagoma (`body`) sta la figura. La figura si allinea a quella sagoma con la testa e la linea del
suolo (le due coincidono entro un paio di px). Scrive `<--out>/<sagoma>/tops/<id>.svg + .json` e
`<--out>/<sagoma>/bottoms/<id>.svg + .json`: i capi restano su quella sagoma e non servono deformazioni.

A differenza di `trace_clothes.py`, qui le regioni di ogni figura si **assegnano a mano**: ogni tabella `OUTFITS` in cima al
file ha una riga per figura, con per ogni capo `{indice regione: ruolo}` (per vedere gli indici: `-v`, che stampa area
e colore di ogni regione). Oltre ai ruoli di colore c'è `skin` (pelle lasciata scoperta). Le altre chiavi, spiegate nel
docstring del file, gestiscono i casi che i fogli maschili non avevano (`lib/outfits.py`):

- `split`: dettagli senza contorno ricavati dal colore dentro una regione (regole `white`, `orange`, `lighter`,
  `darker`, `red`, `lilac`: fiori, righe, risvolti, calze, bottoni chiari). Si disegnano sopra la regione senza tratto,
  e il tratto del bordo della regione si ridisegna sopra (così non si copre); il colore di partenza è quello dei pixel
  del dettaglio più lontani dal fondo (i bordi sfumati non lo sbiadiscono);
- `join`: regioni da unire in una (le gambe dei leggings, i jeans tagliati dalla cucitura centrale): il confine resta
  come cucitura; `absorb`: lo stesso ma **senza** cucitura, per un cuneo che il foglio lascia fra manica e busto
  (`absorb={3: (5,)}`: la regione 5 diventa parte della 3); `extend_top`: la regione sale fino in vita (i fianchi nascosti da un abito);
- `neck`: la pelle sotto il collo della sagoma (V, scollo ampio, cappuccio aperto) sta nella regione della testa del
  foglio, non in una regione del capo: si ritaglia sotto la riga del collo della sagoma;
- `layers` e `pad_under`: parti che stanno in un livello sotto i pantaloni (la pancia di un top corto, e la fessura fra
  braccio e busto che il foglio lascia vuota), allungate in verticale sotto la maglia e i pantaloni vicini;
- `parts`: regioni che sostituiscono le braccia della sagoma (spalle e braccia scoperte) e `arms`: le regioni delle
  braccia, quando le maniche sono più corte di quelle della sagoma di base: l'orlo della manica si aggancia all'inizio
  del braccio con dei punti di riferimento corretti (`landmarks` nel json del capo);
- `under_up`, `behind`: i pantaloni salgono sotto la maglia e proseguono dietro le braccia, così con altre maglie della
  stessa sagoma non restano buchi in vita (se il bordo alto dei pantaloni è a gradini, perché il foglio lo nasconde sotto
  un lembo della giacca, `under_up={9: (30, True, 0)}`: la fascia è larga come i fianchi, con rientro ai lati 0; un quarto valore, `(30, True, 0, 70)`, alza la fascia a 70 px dal bordo alto: serve quando i fianchi sotto le falde sono più bassi); `under_down`: lo stesso per una maglia corta o infilata, che scende sotto i
  pantaloni (con un terzo valore, `(30, 1, 0.5)`, l'orlo è l'ultima riga larga almeno metà della più larga: serve quando la
  manica lunga è unita al busto); `neck_up`: la pelle del collo sale dietro la testa e chiude la fessura col bavero; `to_shoes`: scendono sotto le scarpe. I bordi alto e basso dei pantaloni si agganciano a quelli dei
  pantaloni della sagoma (`landmarks`) quando sono vicini (entro 20 px: una vita alta o una cintura restano dove sono);
- `bridge` e `seal` (opzioni della *figura*, non del capo): nei fogli generati a volte manca un pezzo di contorno e una
  regione (la gonna della ragazza, vicino alle mani) si fonde con lo sfondo. `bridge=[((x1, y1), (x2, y2)), …]`
  disegna dei segmenti scuri, in px del foglio, che chiudono l'interruzione; `seal=1.0` ispessisce il tratto di quei
  px per chiudere le crepe di un pixel (si guardano le regioni con `-v` finché la gonna non è una regione sola);
  Altre opzioni della figura: `dark` (soglia di luminanza del contorno, 34 di solito: con un tratto interno più chiaro, come il fiocco
  marrone di un abito rosa, `dark=80` lo chiude in una regione) e `cuts=[(regione, y)]`: divide una regione con un taglio
  orizzontale all'altezza `y` del foglio (un abito senza la linea della vita: la parte sotto prende l'indice successivo all'ultimo,
  lo stampa `-v`);
- `color` e la regola `blue`: una regione a righe di due colori (la maglietta bianca e blu) ha una mediana sbiadita: `color={3: '#f3f5f9'}`
  fissa il colore principale e `split={3: [('accent', 'blue')]}` ricava le righe blu. Nella polo bianca il colletto e la patta erano collegati allo
  sfondo da un varco del contorno: `bridge` lo chiude e la parte diventa una regione (`trim`). `back=False` toglie la striscia dietro il capo
  (la camicia aperta del robusto la disegnava come un contorno doppio accanto al braccio).
- `to_ground`: nei fogli con scarpe diverse da quelle della sagoma (tacchi, ballerine, sandali) l'orlo dei pantaloni e le gambe di pelle finiscono
  in un punto che non combacia con le scarpe della sagoma (orli a gradini, gambe che galleggiano, un cinturino fuso nella caviglia).
  `to_ground={indice: rientro}` prolunga ogni gamba della regione con un rettangolo fino al suolo (e taglia i gradini a ±3 px), così
  la scarpa, disegnata sopra, la nasconde. `(rientro, px sopra il suolo, px sopra l'orlo)`: per pantaloni molto larghi la gamba si ferma a
  `px` dal suolo (la cima della scarpa, 34-40) e il terzo valore (10 di solito) è dove si misura la larghezza della gamba (26 se il piede punta di lato).
- `no_seams`, `min_seam`, `smooth`: ripulire un abito scuro dai ghirigori. `no_seams` toglie le linee interne di certe regioni (una gamba
  o un braccio di pelle, i pannelli fusi con `absorb`); `min_seam` alza la lunghezza minima delle linee (px del foglio) per
  perdere i trattini corti dei bordi doppi; `smooth={indice: px}` apre la regione (erosione e dilatazione) e toglie i
  bernoccoli di un cinturino fuso in una caviglia. Con `folds=()` si spengono anche le pieghe chiare dei pantaloni;
- `folds`: dove cercare anche le pieghe chiare (per i pantaloni, la regione principale, in automatico);
- `widen`, `clip_top`, `to_waist`: allargare una regione sotto le vicine (la pancia sotto le braccia), togliere le strisce
  strette in alto (un pezzo di pantalone che risale lungo il braccio), far salire i pantaloni fino alla vita della
  sagoma quando nel foglio la vita è coperta;
- in automatico ogni maglia ha anche il **livello dietro** (`backlay`): una striscia oltre i suoi fianchi, solo dove
  sulla figura c'è un braccio (`parts.back_strip`). Riempie la fessura sottile fra braccio e maglia quando la maglia
  si abbina a pantaloni di un altro foglio o alla base. Lo stesso fa `trace_clothes.py`; per i pantaloni basta il
  riempimento di fondo della sagoma (`trace_bodies.py`: il bordo del busto e dei fianchi fra le braccia, richiamato in
  ogni capo col suo colore, e la pelle allo scollo). Sono piccoli riempimenti: l'audit li ha tenuti perché senza di
  loro tornano piccoli buchi sul collo, sotto le braccia e in vita negli abbinamenti con la maglietta o i pantaloni
  base e con i capi di un altro foglio.

Dopo la tracciatura: i capi in `clothes["<gruppo>/<sagoma>"]` del manifest; i colori delle scarpe di ogni outfit si
ricavano dal foglio e si scrivono nel preset (`colors`). Le scarpe dei fogli di abiti e gonne (ballerine, mary jane,
tacchi) non si disegnano: restano le scarpe base della sagoma e dal foglio si prendono solo i colori. Un abito si divide
in due capi: il corpetto con le maniche è una maglia, la gonna (con cintura, fiocchi e le gambe `skin` fino alle
scarpe, `to_shoes`) sono i pantaloni.

## Sagome aliene: `trace_alien.py`

```
python3 tools/trace_alien.py reference/sagome-aliene-maschili.webp --out src/alien/bodies/maschio \
    --names bambino,ragazzo,adulto,curvo
python3 tools/trace_alien.py reference/sagome-aliene-femminili.webp --out src/alien/bodies/femmina \
    --names bambina,ragazza,adulta,curva
```

Per un foglio di **figure aliene affiancate** su sfondo chiaro (stessa idea di `trace_bodies.py`, ma con ruoli propri: gli alieni
sono tutti della stessa pelle, quindi testa, braccia e gambe si distinguono per posizione e non per colore, e non ci sono scarpe).
Cosa si aspetta il foglio: figure con un contorno scuro continuo, due occhi (macchie scure staccate dal contorno), la maglia
chiara, i pantaloncini (di un colore qualunque: grigi, rosa…) e quattro regioni di pelle oltre alla testa (due braccia, due gambe coi piedi); il collo sta nella testa.
Per ogni figura scrive `<nome>.svg` (solo geometria, vedi *Alieni* nel README principale) e `<nome>.json` (nome visualizzato, misure
della testa, punti di riferimento, colori di partenza di pelle, maglia, pantaloncini e occhi).

Come lavora (`lib/alien.py`, `lib/alien_export.py`; la segmentazione è quella delle sagome umane, `lib/segment.py`):

1. Le regioni sono le componenti connesse del foglio fra i tratti scuri; le due macchie scure staccate in alto sono gli occhi, i
   puntini tondi sul viso (anche piccoli, 6 px²) le narici.
2. **Ruoli**: la testa è la regione con gli occhi; la maglia è la regione bianca più grande nella parte alta, i pantaloncini la regione
   più grande che non è né bianca né di pelle; le quattro regioni di pelle più grandi sono braccia e gambe (le due più in basso sono le gambe, le altre le
   braccia; sinistra e destra per posizione). Una regione piccola che tocca **una sola** parte (un dito o una punta chiusi da una
   linea) ne fa parte, restando una regione a sé col suo contorno; la pelle fra testa e maglia (il collo) va alla testa. Lo sfondo
   racchiuso fra i piedi, che tocca più parti, resta fuori.
3. Ogni parte è la cella di Voronoi della sua regione (il confine cade a metà del tratto) tracciata con potrace. I buchi chiari
   minuscoli dentro il tratto (un granello dove due contorni si sovrappongono) sono tratto, non regioni: se no il confine fra due
   parti ci gira intorno e il contorno viene un nodo. Le linee interne (dita, cuciture) sono i pixel scuri con una sola regione
   intorno, come per le sagome umane; le pieghe della maglia e le tasche dei pantaloncini (più scure della stoffa, `find_folds`) sono linee `c-fold`. Le linee
   sottilissime (spessore < 1.5 px) sono ombre dove due contorni si incrociano e si scartano.
   Il riempimento della testa scende sotto il colletto (`NECK_FILL`) per non lasciare fessure quando la testa si alza.
4. **Scala e suolo**: la stessa scala per tutte le figure del foglio (la più alta diventa alta `--height` px, 690 come un adulto
   umano, così le altezze restano confrontabili) e i piedi su y = 900. Alla fine lo strumento stampa lo spessore del contorno nella scala
   finale: si scrive in `lineWidth` di `src/alien/manifest.json`.

Se una figura si classifica male o il contorno ha un'interruzione (nei fogli generati a volte manca un pezzo di tratto e la
regione si fonde con lo sfondo), la tabella `FIXES` in cima a `trace_alien.py` ha una riga per foglio e per figura:
`roles` (`{indice regione: ruolo}`, gli indici si vedono con `-v`), `bridge` (segmenti scuri che chiudono l'interruzione) e `seal`.

Dopo la tracciatura: le sagome in `bodies` e un preset per ognuna in `src/alien/manifest.json`, poi `node build.mjs`.

## Vestiti alieni: `trace_alien_outfits.py`

```
python3 tools/trace_alien_outfits.py reference/vestiti-alieni-maschili.webp \
    --bodies-sheet reference/sagome-aliene-maschili.webp --bodies src/alien/bodies/maschio \
    --names bambino,ragazzo,adulto,curvo --out src/alien/clothes/maschio
python3 tools/trace_alien_outfits.py reference/vestiti-alieni-femminili.webp \
    --bodies-sheet reference/sagome-aliene-femminili.webp --bodies src/alien/bodies/femmina \
    --names bambina,ragazza,adulta,curva --out src/alien/clothes/femmina
```

Per un foglio in cui **ogni figura aliena indossa un abito sulla propria sagoma**, disegnato sopra il foglio delle sagome nude (stessa
posa, stessa scala, stesse teste e piedi: scarto misurato < 0.3 px). Per ogni figura scrive in `--out/<sagoma>/` `tops/<id>.svg|json` (la
maglia) e `bottoms/<id>.svg|json` (i pantaloni o la gonna). `--only a,b` traccia solo alcune sagome; `-v` stampa gli indici di regione
(area, colore), i ruoli assegnati, i dettagli e le fasce. Le regioni di ogni figura si assegnano a mano ai ruoli di colore (`main`, `trim`,
`accent`, `accent2`, `skin`) nella tabella `OUTFITS` in cima al file, con queste opzioni per capo: `split` (dettagli senza contorno
ricavati dal colore dentro la regione: strisce, un rombo), `absorb`, `back` (regioni dietro le braccia: la coda di un mantello),
`under_down` / `under_up` (la fascia con cui la maglia scende dietro i pantaloncini di base, o i pantaloni salgono dietro la maglietta),
`folds`, `smooth`, `neck`; per figura `arms` / `legs` (se la scelta automatica non va), `ignore`, `bridge`, `seal`, `dark`.

Come lavora (`lib/alien_outfits.py`, `lib/alien_clothes_export.py`; segmentazione e linee interne come per le sagome):

1. **Ancoraggio**: le coordinate si ancorano agli occhi della sagoma (`head.eyeX/eyeY` del suo `.json`) e alla scala del foglio delle
   sagome (`--bodies-sheet`): nessuna deformazione, il capo cade sul corpo.
2. **Capi**: ogni regione è la cella di Voronoi del suo contorno, tracciata con potrace; l'ordine di disegno è regioni, dettagli senza
   contorno, contorni sopra i dettagli, linee interne (cuciture, pieghe).
3. **Parti sostituite**: le due braccia (maglia) o le due gambe (pantaloni), le regioni di pelle più grandi del foglio, con le loro
   linee (dita, piedi): così una manica corta o un orlo alto scoprono ciò che sotto la maglietta e i pantaloncini di base è nascosto.
4. **Collo**: dove il foglio dei vestiti non ha il contorno inferiore della testa della sagoma (uno scollo più basso, una spalla
   scoperta) il capo ha un pezzo di pelle che lo copre (`stale` in `lib/alien_outfits.py`: il contorno della testa della sagoma, ±2 px,
   che nel foglio dei vestiti non c'è, sulla pelle). Con una spalla scoperta che si fonde col collo (`arms=(None, …)`) il pezzo è il
   braccio intero e il suo contorno è solo quello vero (`_outline_runs`: il bordo che cade sul tratto scuro, non il taglio).
5. **Fasce**: `under_down` (maglia) e `under_up` (pantaloni) sono rettangoli larghi come l'orlo, o come i pantaloncini di base
   (`width='pants'`, per la pancia scoperta `role='skin'`), che arrivano al fondo della maglietta di base.

Dopo la tracciatura: i capi in `clothes["<gruppo>/<sagoma>"]` del manifest (`src/alien/manifest.json`) e, per un personaggio di
partenza, in un preset (`top`, `bottom`), poi `node build.mjs`. Rifacendo le sagome (`trace_alien.py`) vanno rifatti anche i vestiti.

## Protuberanze: `trace_protrusions.py`

```
python3 tools/trace_protrusions.py --frame src/alien/bodies/maschio/adulto.json --out src/alien/protrusions
```

Per i fogli di **teste e figure aliene con una protuberanza** (corna, palchi, pinne, creste, antenne): `reference/protuberanze-teste.webp`
(quattro teste con il busto, che non ha il contorno in basso: lo strumento lo chiude con un segmento), `reference/protuberanze-figure.webp`
e `reference/protuberanze-antenne.webp` (quattro figure intere ciascuno). Scrive `<id>.svg` + `<id>.json` per ogni figura della tabella `FIGURES` in cima al file. `--frame` è la sagoma
che dà la testa di riferimento (di solito `maschio/adulto`): le coordinate delle protuberanze stanno nel suo riquadro (centro e mezza
larghezza del cranio, cima) e la build le adatta alla testa di ogni sagoma (`lib/protrusion.py`).

Nei fogli la protuberanza è **fusa con la testa**: stesso colore e, di solito, nessuna linea fra le due (le regioni non la separano), quindi
la tabella dice dove tagliarla. Ogni figura ha `parts`:

- `kind='cut'` (dietro la testa): `poly`, un poligono in px del foglio che racchiude la protuberanza e lascia fuori il cranio (il taglio
  passa lungo la base: dove la protuberanza attacca alla testa, un poco fuori dal cranio). La parte è la silhouette dentro il poligono.
  Il suo contorno esterno continua dentro la testa, dove quella di ogni sagoma lo copre: i bordi che arrivano al cranio si prolungano
  lungo la loro tangente (`TAIL` px, finché restano a `REACH` px dal cranio della figura; un estremo la cui tangente corre lungo la
  testa, fuori, non si prolunga) e il riempimento è la sagoma così chiusa. Così si chiude sul contorno di ogni sagoma, anche se la
  sua testa è un poco più stretta o più lontana (le pinne sulla testa inclinata). Il tratto è solo sul bordo esterno. Le linee
  interne (nervature, spirali) restano; quelle lungo il taglio (il contorno del cranio) no. Per un cranio tondo si
  può dare `not_circle=(cx, cy, r)`: la silhouette fuori da quel cerchio (la cresta a spine);
- `kind='region'` (davanti alla testa): `seed`, un punto dentro una regione chiusa dal tratto del foglio (un corno che passa davanti al
  cranio); riempimento e contorno interi. `bridge` della figura chiude un'interruzione del tratto (il corno di destra delle corna a spirale).

Altre opzioni della figura: `bust` (è un busto) e `fit={sx, sy, dx, dy}`, ritocchi alla posizione e alla scala sulla testa di riferimento
(le unità del riquadro di riferimento: per esempio `dx=14` sposta la cresta al vento verso la testa, dove la base si nasconde meglio).

Come adatta: la figura si porta sulla testa di riferimento con scala **uniforme** (rapporto fra le mezze larghezze della calotta del
cranio, dalla cima fino al 60% della distanza dagli occhi), cima e centro del cranio sovrapposti. Le teste dei fogli hanno proporzioni
un poco diverse da quelle delle sagome (un cranio più alto): una scala diversa in x e in y deformerebbe le corna.

Dopo la tracciatura: gli id in `protrusions` del manifest (`src/alien/manifest.json`), poi `node build.mjs`. Se si rifanno le sagome
(`trace_alien.py`) vanno rifatte anche le protuberanze (ne leggono la testa di riferimento).

## Limiti noti

- La classificazione delle regioni si basa su colore e posizione: un foglio con una posa diversa (o una persona
  con più parti, per esempio un cappello) richiede nuove regole in `parts.classify` e `clothes.classify_outfit`.
- Le linee interne sono quelle scure o più scure dell'intorno: un tratto molto chiaro su un fondo chiaro non viene
  rilevato.
- Un capo vive solo sulla sagoma su cui è tracciato. L'unica deformazione che resta è quella dei primi dieci capi
  maschili (disegnati su un corpo di riferimento un poco diverso da `maschio/adulto`), guidata dai punti di riferimento
  dei due corpi: va bene solo per scarti piccoli. `node tools/audit.mjs` (README principale) trova i casi in cui un
  abbinamento lascia vuoti o sovrapposizioni.
