#!/usr/bin/env python3
"""Traccia gli stili di capelli dal foglio `reference/capelli.webp` (sfondo trasparente).

Uso:  python3 tools/trace_hair.py reference/capelli.webp --out src/hair

Scrive `<id>.svg` (sagoma + linee interne, nelle coordinate del riquadro dei capelli) e `<id>.json`
(nome e colore di default) per ogni stile della tabella HAIRS qui sotto.

Come si tara uno stile (HAIRS):
  box    riquadro dello stile nel foglio
  notch  centro dell'incavo dell'orecchio nel foglio
  ear    dove deve finire quel punto nel riquadro dei capelli (orecchio della testa di riferimento)
  s      scala foglio → riquadro dei capelli (0.78-0.80 per le teste di riferimento)
  keep   indici delle linee interne da tenere (dalla più lunga): le altre sono ispessimenti dei
         punti concavi del contorno
  thick  indici delle linee interne col tratto pieno come il contorno (le altre sono sottili)
Per allineare un nuovo stile conviene sovrapporlo alla testa di riferimento e provare scala e punto di appoggio.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image                        # noqa: E402
from lib.hair import HairSheet, fill_color, interior_lines, silhouette   # noqa: E402

HAIRS = [
    dict(id='spettinati', name='Spettinati', box=(30, 315, 347, 585), notch=(112, 535), ear=(95, 378), s=0.78, keep=[], thick=[]),
    dict(id='coda', name='Coda e frangia', box=(346, 340, 700, 640), notch=(488, 527), ear=(100, 372), s=0.80, keep=[0, 1, 2, 3, 4, 5, 6], thick=[0]),
    dict(id='chignon', name='Chignon', box=(695, 340, 1010, 615), notch=(792, 533), ear=(100, 371), s=0.80, keep=[0, 1, 2, 3, 4, 5, 6], thick=[0, 1]),
    dict(id='ciuffo-scuro', name='Ciuffo scuro', box=(1015, 335, 1325, 580), notch=(1087, 532), ear=(95, 378), s=0.78, keep=[], thick=[]),
    dict(id='ciuffo-castano', name='Ciuffo castano', box=(1325, 330, 1650, 580), notch=(1413, 543), ear=(95, 378), s=0.78, keep=[0], thick=[]),
]


def hair_svg(h, sil, lines):
    rows = [f'    <path class="c-hair-{h["id"]} c-stroke" d="{sil}"/>']
    for i in h['keep']:
        fine = '' if i in h['thick'] else ' c-fine'
        rows.append(f'    <path class="c-open c-stroke{fine}" d="{lines[i]["d"]}"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300">\n'
            f'  <title>{h["name"]}</title>\n  <g id="hair-{h["id"]}">\n' + '\n'.join(rows) + '\n  </g>\n</svg>\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sheet', help='foglio dei capelli (RGBA)')
    ap.add_argument('--out', required=True, help='cartella di destinazione (es. src/hair)')
    a = ap.parse_args()
    sheet = HairSheet(Image.open(a.sheet))
    os.makedirs(a.out, exist_ok=True)
    for h in HAIRS:
        sil = silhouette(sheet, h)
        lines = interior_lines(sheet, h)
        with open(os.path.join(a.out, h['id'] + '.svg'), 'w', encoding='utf8') as f:
            f.write(hair_svg(h, sil, lines))
        with open(os.path.join(a.out, h['id'] + '.json'), 'w', encoding='utf8') as f:
            json.dump(dict(name=h['name'], color=fill_color(sheet, h)), f, ensure_ascii=False, indent=2)
            f.write('\n')
        print(f'{h["id"]}: sagoma + {len(h["keep"])} linee interne (trovate {len(lines)})')


if __name__ == '__main__':
    main()
