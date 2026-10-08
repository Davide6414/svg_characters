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
`<nome>.json` (nome visualizzato, punti di riferimento della testa, 22 punti di riferimento del corpo per adattare i
vestiti, colori di pantaloni e scarpe).

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
   potrace. I pantaloni scendono sotto le scarpe. Le fessure interne (orecchio, cuciture, pieghe) diventano linee
   aperte. Misura anche i punti di riferimento (`landmarks`).
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

## Vestiti: `trace_clothes.py`

```
python3 tools/trace_clothes.py --group maschio --out src/clothes/maschio \
    --bottoms reference/vestiti-maschili-pantaloni.webp --tops reference/vestiti-maschili-maglie.webp
```

Servono due fogli con figure affiancate che indossano capi diversi **sullo stesso corpo**: uno con i pantaloni (e la
maglietta bianca di base), uno con i capi per il busto (e i pantaloni di base). Scrive in `--out`:

- `reference.json`: i punti di riferimento del corpo su cui sono disegnati i vestiti (la prima figura del foglio dei
  pantaloni, che ha maglietta e pantaloni semplici);
- `bottoms/<id>.svg` + `.json` e `tops/<id>.svg` + `.json`: i capi, nel riquadro di quel corpo.

Come lavora (`lib/clothes.py`): segmenta la figura come per le sagome, toglie ciò che è corpo (testa, mani) e ciò che
non è il capo (scarpe, e la maglietta o i pantaloni di base), e traccia le regioni rimaste: ogni regione ha un
**ruolo di colore** (`main`, `trim`, `accent`, `under`: principale, bordi, dettagli, maglietta sotto un capo aperto)
assegnato in automatico dal colore e dalle dimensioni. Le linee interne (cuciture, tasche, cerniera) e i bottoni
diventano linee e puntini. Il capo viene portato nel riquadro del corpo di riferimento allineando testa e suolo.

**Correzione dei ruoli.** Le tabelle `BOTTOMS` e `TOPS` in cima al file hanno una riga per figura (da sinistra a
destra): id, nome e le correzioni `{indice regione: ruolo}`. Per vedere gli indici si lancia con `-v`.

L'adattamento ai singoli corpi non si fa qui ma in `build.mjs` (vedi il README principale).

## Limiti noti

- La classificazione delle regioni si basa su colore e posizione: un foglio con una posa diversa (o una persona
  con più parti, per esempio un cappello) richiede nuove regole in `parts.classify` e `clothes.classify_outfit`.
- Le linee interne sono quelle scure o più scure dell'intorno: un tratto molto chiaro su un fondo chiaro non viene
  rilevato.
- I vestiti si adattano ai corpi con una deformazione guidata da pochi punti: segue le proporzioni generali, non i
  dettagli. Su un corpo molto diverso da quello di riferimento (per esempio un bambino con testa grande) il
  risultato è plausibile ma non identico a un disegno fatto apposta.
