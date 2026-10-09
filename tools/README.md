# Strumenti di tracciatura

Servono a ricavare le sorgenti in `src/` dai fogli di riferimento in `reference/`. Non servono per usare i
personaggi: quelli si ricostruiscono con `node build.mjs`.

```
pip install -r tools/requirements.txt      # numpy, Pillow, potracer (potrace in Python puro)
```

Sono deterministici: rigenerando da `reference/` si ottengono file identici a quelli in `src/`.

## Sagome: `trace_bodies.py`

```
python3 tools/trace_bodies.py reference/sagome-maschili.webp  --out src/bodies/maschio \
    --names bambino,ragazzo,slanciato,adulto,robusto
python3 tools/trace_bodies.py reference/sagome-femminili.webp --out src/bodies/femmina \
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

Dopo la tracciatura: aggiungere le sagome a `bodies` e `presets` in `src/manifest.json` e lanciare `node build.mjs`.
Se cambiano i punti di riferimento (`landmarks`) vanno rigenerate anche le sagome già esistenti.

## Capelli: `trace_hair.py`

```
python3 tools/trace_hair.py reference/capelli.webp --out src/hair
```

Traccia gli stili elencati nella tabella `HAIRS` in cima al file: ognuno ha il riquadro nel foglio, il punto
dell'orecchio e la scala che lo allineano alla testa di riferimento (`hairFrame` nel manifest), e quali linee
interne tenere. Per un nuovo stile: aggiungere una riga alla tabella (conviene provare scala e punto di appoggio
sovrapponendo lo stile alla testa di riferimento), poi aggiungere l'id a `hair` nel manifest.

## Capelli da figure intere: `trace_hair_figures.py`

```
python3 tools/trace_hair_figures.py reference/capelli-2.webp --out src/hair
python3 tools/trace_hair_figures.py reference/capelli-anziani.webp --out src/hair
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

La tabella `HAIRS[nome del foglio]` ha una riga per figura: id, nome, età (`ages`) e le opzioni sopra. L'età dice a quali
sagome si applica lo stile (`ages` nel manifest): gli stili da anziani non vanno ai bambini.

## Vestiti: un capo, una sagoma

Ogni capo sta **solo sulla sagoma su cui è disegnato**: i file sono in `src/clothes/<gruppo>/<sagoma>/{tops,bottoms}/`
e il manifest li elenca per sagoma (`clothes["maschio/adulto"].tops`…). Mischiare i capi fra corporature diverse dava
sempre problemi di vestibilità, quindi non esiste più nessun adattamento fra sagome. Un capo per un'altra sagoma si
traccia di nuovo su quella sagoma. Due strumenti, secondo il foglio.

## Due fogli sullo stesso corpo: `trace_clothes.py`

```
python3 tools/trace_clothes.py --out src/clothes/maschio/adulto \
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
python3 tools/trace_outfits.py reference/vestiti-femminili.webp   --bodies src/bodies/femmina --out src/clothes/femmina
python3 tools/trace_outfits.py reference/vestiti-femminili-2.webp --bodies src/bodies/femmina --out src/clothes/femmina
python3 tools/trace_outfits.py reference/vestiti-maschili-outfit.webp --bodies src/bodies/maschio --out src/clothes/maschio
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
  come cucitura; `extend_top`: la regione sale fino in vita (i fianchi nascosti da un abito);
- `neck`: la pelle sotto il collo della sagoma (V, scollo ampio, cappuccio aperto) sta nella regione della testa del
  foglio, non in una regione del capo: si ritaglia sotto la riga del collo della sagoma;
- `layers` e `pad_under`: parti che stanno in un livello sotto i pantaloni (la pancia di un top corto, e la fessura fra
  braccio e busto che il foglio lascia vuota), allungate in verticale sotto la maglia e i pantaloni vicini;
- `parts`: regioni che sostituiscono le braccia della sagoma (spalle e braccia scoperte) e `arms`: le regioni delle
  braccia, quando le maniche sono più corte di quelle della sagoma di base: l'orlo della manica si aggancia all'inizio
  del braccio con dei punti di riferimento corretti (`landmarks` nel json del capo);
- `under_up`, `behind`: i pantaloni salgono sotto la maglia e proseguono dietro le braccia, così con altre maglie della
  stessa sagoma non restano buchi in vita; `under_down`: lo stesso per una maglia corta o infilata, che scende sotto i
  pantaloni; `to_shoes`: scendono sotto le scarpe. I bordi alto e basso dei pantaloni si agganciano a quelli dei
  pantaloni della sagoma (`landmarks`) quando sono vicini (entro 20 px: una vita alta o una cintura restano dove sono);
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
ricavano dal foglio e si scrivono nel preset (`colors`).

## Limiti noti

- La classificazione delle regioni si basa su colore e posizione: un foglio con una posa diversa (o una persona
  con più parti, per esempio un cappello) richiede nuove regole in `parts.classify` e `clothes.classify_outfit`.
- Le linee interne sono quelle scure o più scure dell'intorno: un tratto molto chiaro su un fondo chiaro non viene
  rilevato.
- Un capo vive solo sulla sagoma su cui è tracciato. L'unica deformazione che resta è quella dei primi dieci capi
  maschili (disegnati su un corpo di riferimento un poco diverso da `maschio/adulto`), guidata dai punti di riferimento
  dei due corpi: va bene solo per scarti piccoli. `node tools/audit.mjs` (README principale) trova i casi in cui un
  abbinamento lascia vuoti o sovrapposizioni.
