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
`<nome>.json` (nome visualizzato, punti di riferimento della testa, colori di pantaloni e scarpe).

Cosa si aspetta il foglio: figure affiancate su sfondo chiaro, nella stessa posa e con lo stesso disegno (testa con
orecchio a sinistra, braccio sinistro davanti, maglia, pantaloni, due scarpe), con un contorno scuro continuo.

Come lavora (moduli in `lib/`):

1. `sheet.py` trova le figure: colonne di pixel non di sfondo separate da spazio vuoto.
2. `segment.py` segmenta ogni figura: il contorno è la rete di pixel scuri (luminanza ≤ 34), le regioni sono le
   componenti connesse del resto, gli occhi sono le macchie scure staccate dalla rete. Dove tomaia e suola di una
   scarpa risultano un'unica regione (manca la linea fra le due) le separa per colore o con un taglio geometrico.
3. `parts.py` dà un ruolo a ogni regione (testa, maglia, braccia, pantaloni, suola, tomaia, linguetta, punta,
   lacci), fa crescere le regioni dentro il contorno fino a metà del tratto (Voronoi) e traccia ogni cella con
   potrace. I pantaloni scendono sotto le scarpe. Le fessure interne (orecchio, cuciture, pieghe) diventano linee
   aperte.
4. Tutte le sagome vengono spostate in verticale perché le suole poggino su y = 900: stessa linea del suolo.
5. `export.py` scrive i file.

Dopo la tracciatura: aggiungere le sagome a `bodies` e `presets` in `src/manifest.json` e lanciare `node build.mjs`.

## Capelli: `trace_hair.py`

```
python3 tools/trace_hair.py reference/capelli.webp --out src/hair
```

Traccia gli stili elencati nella tabella `HAIRS` in cima al file: ognuno ha il riquadro nel foglio, il punto
dell'orecchio e la scala che lo allineano alla testa di riferimento (`hairFrame` nel manifest), e quali linee
interne tenere. Per un nuovo stile: aggiungere una riga alla tabella (conviene provare scala e punto di appoggio
sovrapponendo lo stile alla testa di riferimento), poi aggiungere l'id a `hair` nel manifest.

## Limiti noti

- La classificazione delle regioni si basa su colore e posizione: un foglio con una posa diversa (o una persona
  con più parti, per esempio un cappello) richiede nuove regole in `parts.classify`.
- Le linee interne sono quelle scure o più scure dell'intorno: un tratto molto chiaro su un fondo chiaro non viene
  rilevato.
