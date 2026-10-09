#!/usr/bin/env python3
"""Traccia le sagome aliene di un foglio di riferimento (figure affiancate su sfondo chiaro).

Uso:
  python3 tools/trace_alien.py reference/sagome-aliene-maschili.webp --out src/alien/bodies/maschio \\
      --names bambino,ragazzo,adulto,curvo

Per ogni figura (da sinistra a destra) scrive `<nome>.svg` e `<nome>.json` in --out. Il nome visualizzato è il nome del
file con l'iniziale maiuscola (si può modificare nel JSON). La stessa scala vale per tutte le figure del foglio (la più
alta diventa alta --height px, come un adulto umano), così le altezze restano confrontabili; i piedi poggiano su y = 900.
Alla fine stampa lo spessore del contorno del foglio nella scala finale (`lineWidth` in src/alien/manifest.json).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.alien import GROUND, HEIGHT, trace_alien_body    # noqa: E402
from lib.alien_export import write_alien                  # noqa: E402
from lib.sheet import Sheet                               # noqa: E402

# Correzioni per figura, per nome del foglio (stem del file): {nome della sagoma: opzioni}.
#   roles   {indice regione: ruolo}   regioni classificate male (indici con -v)
#   bridge  [((x1, y1), (x2, y2))]    segmenti scuri, in px del foglio, che chiudono un'interruzione del contorno
#   seal    px                        ispessisce il tratto per chiudere le crepe di un pixel
FIXES = {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sheet', help='immagine del foglio di riferimento')
    ap.add_argument('--out', required=True, help='cartella di destinazione (es. src/alien/bodies/maschio)')
    ap.add_argument('--names', required=True, help='nomi dei file, da sinistra a destra, separati da virgola')
    ap.add_argument('--height', type=float, default=HEIGHT, help='altezza in px della figura più alta (default %(default)s)')
    ap.add_argument('--ground', type=float, default=GROUND, help='y della linea del suolo (default %(default)s)')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()

    sheet = Sheet(a.sheet)
    names = [n.strip() for n in a.names.split(',')]
    boxes = sheet.figures()
    if len(boxes) != len(names):
        sys.exit(f'Il foglio ha {len(boxes)} figure ma sono stati dati {len(names)} nomi')
    margin = 10                                                       # il margine di Sheet.figures()
    scale = a.height / max(b[3] - b[1] - 2 * margin for b in boxes)
    fixes = FIXES.get(os.path.splitext(os.path.basename(a.sheet))[0], {})
    strokes = []
    for name, box in zip(names, boxes):
        body = trace_alien_body(sheet, box, scale, ground=a.ground, verbose=a.verbose, **fixes.get(name, {}))
        write_alien(a.out, name, name.capitalize(), body)
        strokes.append(body['stroke'])
        print(f'{name}: {sum(len(v) for v in body["parts"].values())} parti, {len(body["seams"])} linee interne, {len(body["nostrils"])} narici')
    print(f'scala {scale:.3f}; spessore del contorno ≈ {sorted(strokes)[len(strokes) // 2]:.1f} px (`lineWidth` in src/alien/manifest.json)')


if __name__ == '__main__':
    main()
