#!/usr/bin/env python3
"""Traccia le sagome di un foglio di riferimento (figure affiancate su sfondo chiaro).

Uso:
  python3 tools/trace_bodies.py reference/sagome-maschili.webp --out src/bodies/maschio \\
      --names bambino,ragazzo,slanciato,adulto,robusto

Per ogni figura (da sinistra a destra) scrive `<nome>.svg` e `<nome>.json` in --out. Il nome visualizzato
è il nome del file con l'iniziale maiuscola (si può modificare nel JSON).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.export import write_body          # noqa: E402
from lib.parts import GROUND, trace_body   # noqa: E402
from lib.sheet import Sheet                # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sheet', help='immagine del foglio di riferimento')
    ap.add_argument('--out', required=True, help='cartella di destinazione (es. src/bodies/maschio)')
    ap.add_argument('--names', required=True, help='nomi dei file, da sinistra a destra, separati da virgola')
    ap.add_argument('--ground', type=float, default=GROUND, help='y della linea del suolo (default %(default)s)')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()

    sheet = Sheet(a.sheet)
    names = [n.strip() for n in a.names.split(',')]
    boxes = sheet.figures()
    if len(boxes) != len(names):
        sys.exit(f'Il foglio ha {len(boxes)} figure ma sono stati dati {len(names)} nomi')
    for name, box in zip(names, boxes):
        body = trace_body(sheet, box, ground=a.ground, verbose=a.verbose)
        write_body(a.out, name, name.capitalize(), body)
        print(f'{name}: {sum(len(v) for v in body["parts"].values())} parti, {len(body["seams"])} linee interne')


if __name__ == '__main__':
    main()
