#!/usr/bin/env python3
"""Traccia gli stili di capelli da un foglio di soli capelli su sfondo trasparente.

Uso:  python3 tools/trace_hair.py reference/capelli.webp --out src/hair
      python3 tools/trace_hair.py reference/capelli-3.webp --out src/hair

La tabella si sceglie dal nome del foglio (HAIRS[nome senza estensione]), una riga per stile.
Scrive `<id>.svg` (sagoma + linee interne, nelle coordinate del riquadro dei capelli) e `<id>.json`
(nome e colore di default) per ogni stile della tabella.

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

HAIRS = {
    'capelli': [
        dict(id='spettinati', name='Spettinati', box=(30, 315, 347, 585), notch=(112, 535), ear=(95, 378), s=0.78, keep=[], thick=[]),
        dict(id='coda', name='Coda e frangia', box=(346, 340, 700, 640), notch=(488, 527), ear=(100, 372), s=0.80, keep=[0, 1, 2, 3, 4, 5, 6], thick=[0]),
        dict(id='chignon', name='Chignon', box=(695, 340, 1010, 615), notch=(792, 533), ear=(100, 371), s=0.80, keep=[0, 1, 2, 3, 4, 5, 6], thick=[0, 1]),
        dict(id='ciuffo-scuro', name='Ciuffo scuro', box=(1015, 335, 1325, 580), notch=(1087, 532), ear=(95, 378), s=0.78, keep=[], thick=[]),
        dict(id='ciuffo-castano', name='Ciuffo castano', box=(1325, 330, 1650, 580), notch=(1413, 543), ear=(95, 378), s=0.78, keep=[0], thick=[]),
    ],
    'capelli-3': [
        dict(id='caschetto-scalato', name='Caschetto scalato', box=(0, 385, 285, 650), seed=(177, 405), notch=(240, 540), ear=(237, 351), s=0.80, keep=[0, 1, 2, 3, 4, 5, 6, 7], thick=[]),
        dict(id='coda-alta', name='Coda alta', box=(275, 350, 600, 700), seed=(490, 388), notch=(549, 530), ear=(237, 357), s=0.80, keep=[0, 1, 2, 3, 4, 5, 6, 7], thick=[0]),
        dict(id='lisci-frangia', name='Lisci con frangia', box=(570, 375, 860, 755), seed=(752, 392), notch=(811, 535), ear=(237, 365), s=0.86, keep=[0, 1, 2, 3, 4, 5, 6, 7, 8], thick=[]),
        dict(id='lunghi-mossi', name='Lunghi mossi', box=(850, 370, 1165, 700), seed=(1030, 390), notch=(1102, 535), ear=(237, 369), s=0.86, keep=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], thick=[]),
        dict(id='coda-laterale', name='Coda laterale bassa', box=(1160, 375, 1440, 775), seed=(1336, 398), notch=(1392, 540), ear=(237, 361), s=0.80, keep=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], thick=[0, 2]),
    ],
}


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
    stem = os.path.splitext(os.path.basename(a.sheet))[0]
    if stem not in HAIRS:
        sys.exit(f'Nessuna tabella per il foglio {stem}: aggiungere HAIRS[{stem!r}]')
    for h in HAIRS[stem]:
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
