#!/usr/bin/env python3
"""Traccia i vestiti da due fogli di riferimento: pantaloni e capi per il busto, disegnati sullo stesso corpo.

Uso:
  python3 tools/trace_clothes.py --out src/human/clothes/maschio/adulto \\
      --bottoms reference/vestiti-maschili-pantaloni.webp --tops reference/vestiti-maschili-maglie.webp

Scrive in --out (la cartella della sagoma a cui i capi appartengono, la più simile al corpo del foglio):
  reference.json            punti di riferimento del corpo su cui sono disegnati i vestiti (prima figura dei pantaloni)
  bottoms/<id>.svg + .json  pantaloni
  tops/<id>.svg + .json     capi per il busto
I vestiti sono nel riquadro di quel corpo; `build.mjs` li adatta alla sagoma della cartella (che deve avere proporzioni
simili: i capi non si adattano ad altre corporature).

Come si tara un capo (tabelle BOTTOMS e TOPS, una riga per figura, da sinistra a destra):
  id, nome, e le correzioni dei ruoli {indice regione: ruolo}. Il ruolo di ogni regione (main, trim, accent,
  under) è automatico; per vedere gli indici si lancia con -v e si correggono quelli sbagliati.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.clothes import trace_garment                  # noqa: E402
from lib.clothes_export import write_garment           # noqa: E402
from lib.parts import trace_body                       # noqa: E402
from lib.sheet import Sheet                            # noqa: E402

BOTTOMS = [
    ('jeans', 'Jeans', {}),
    ('chino', 'Chino', {}),
    ('jogger', 'Jogger', {14: 'trim', 13: 'trim', 6: 'trim', 8: 'trim', 7: 'trim', 11: 'trim'}),   # coste alle caviglie e in vita
    ('cargo', 'Cargo', {}),
    ('larghi', 'Pantaloni larghi', {}),
]
TOPS = [
    ('felpa', 'Felpa', {8: 'trim', 7: 'trim', 6: 'trim', 5: 'accent', 4: 'accent'}),            # coste e cordini
    ('giacca', 'Giacca', {16: 'trim', 15: 'trim', 14: 'trim', 12: 'trim', 13: 'trim', 9: 'accent', 8: 'accent'}),
    ('polo', 'Polo', {4: 'trim', 5: 'trim'}),                                                    # patta e bordo manica
    ('maglione', 'Maglione', {3: 'trim', 7: 'trim', 6: 'trim', 5: 'trim'}),                      # girocollo, coste
    ('camicia', 'Camicia aperta', {}),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, help='cartella della sagoma di destinazione (es. src/human/clothes/maschio/adulto)')
    ap.add_argument('--bottoms', required=True, help='foglio dei pantaloni')
    ap.add_argument('--tops', required=True, help='foglio dei capi per il busto')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()

    bottoms, tops = Sheet(a.bottoms), Sheet(a.tops)
    # corpo di riferimento: la prima figura dei pantaloni (maglietta e pantaloni semplici)
    ref_body = trace_body(bottoms, bottoms.figures()[0])
    ref = dict(head=ref_body['head'], landmarks=ref_body['landmarks'])
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'reference.json'), 'w', encoding='utf8') as f:
        json.dump(dict(head={k: round(v, 1) for k, v in ref['head'].items()}, landmarks=ref['landmarks']),
                  f, ensure_ascii=False, indent=2)
        f.write('\n')

    for sheet, kind, table, folder in ((bottoms, 'bottom', BOTTOMS, 'bottoms'), (tops, 'top', TOPS, 'tops')):
        boxes = sheet.figures()
        if len(boxes) != len(table):
            sys.exit(f'Il foglio {kind} ha {len(boxes)} figure ma la tabella ne ha {len(table)}')
        for (gid, name, overrides), box in zip(table, boxes):
            if a.verbose:
                print(f'{folder}/{gid}')
            garment = trace_garment(sheet, box, kind, ref=None if sheet is bottoms and box == boxes[0] else ref,
                                    overrides=overrides, verbose=a.verbose)
            write_garment(os.path.join(a.out, folder), gid, name, garment, drawn_on_reference=True)
            print(f'{folder}/{gid}: {len(garment["regions"])} regioni, {len(garment["seams"])} linee, {len(garment["dots"])} puntini, colori {garment["colors"]}')


if __name__ == '__main__':
    main()
