#!/usr/bin/env python3
"""Traccia le barbe da un foglio di figure intere (ogni figura ha la testa calva con una barba diversa).

Uso:
  python3 tools/trace_beards.py reference/barbe.webp --out src/beards

La tabella si sceglie dal nome del foglio (BEARDS[nome senza estensione]), una riga per figura da sinistra a destra.
Scrive `<id>.svg` (livello sotto il contorno della testa + sagoma, contorno e linee, nelle coordinate del riquadro dei
capelli) e `<id>.json` (nome, colore di default, gruppi e età a cui si applica).

Ogni barba ha:
  id, name   come gli stili di capelli
  groups     gruppi delle sagome a cui si applica (vedi `groups` del manifest); senza: tutti
  ages       età delle sagome a cui si applica (vedi `ages` del manifest); senza: tutte
  stubble    True: barba incolta (puntini sulla pelle invece di una sagoma)
  scale, below, dot_lum, dot_max, min_line   correzioni dell'allineamento e delle soglie se servono
Per l'allineamento e l'isolamento vedi `lib/beard_figures.py`; il colore si cambia poi con --beard come gli altri.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.beard_figures import trace_beard_figure     # noqa: E402
from lib.sheet import Sheet                          # noqa: E402

MEN = ('maschio',)
ADULTS, NOT_KIDS = ('adulto',), ('ragazzo', 'adulto')
BEARDS = {
    'barbe': [
        dict(id='barba-incolta', name='Barba incolta', groups=MEN, ages=NOT_KIDS, stubble=True),
        dict(id='barba-corta', name='Barba corta', groups=MEN, ages=ADULTS),
        dict(id='barba-piena', name='Barba piena', groups=MEN, ages=ADULTS),
        dict(id='pizzetto', name='Baffi e pizzetto', groups=MEN, ages=ADULTS),
        dict(id='barba-lunga', name='Barba lunga', groups=MEN, ages=ADULTS),
    ],
}


def ff(v):
    t = f'{v:.1f}'
    t = t[:-2] if t.endswith('.0') else t
    return '0' if t == '-0' else t


def beard_svg(b, r):
    c = f'c-beard-{b["id"]}'
    skin, front = [], []
    if r['ext']:                                   # livello sotto il contorno della testa (ritagliato sulla testa)
        skin.append(f'    <path class="{c} c-skinlayer" d="{"".join(r["ext"])}"' + (' fill-rule="evenodd"' if len(r['ext']) > 1 else '') + '/>')
    if r['dots']:
        # puntini: tratti di lunghezza minima con estremi tondi (un solo percorso)
        d = ''.join(f'M{ff(x - 0.15)},{ff(y)}L{ff(x + 0.15)},{ff(y)}' for x, y in r['dots'])
        skin.append(f'    <path class="c-bdot c-bdot-{b["id"]} c-skinlayer" d="{d}"/>')
    if r['fill']:
        front.append(f'    <path class="{c}" d="{"".join(r["fill"])}"' + (' fill-rule="evenodd"' if len(r['fill']) > 1 else '') + '/>')
    front += [f'    <path class="c-open c-stroke" d="{d}"/>' for d in r['outline']]
    for ln in r['lines']:
        width = '' if ln['thick'] >= 4.6 else ' c-fine' if ln['thick'] >= 3.2 else ' c-hair'
        front.append(f'    <path class="c-open c-stroke{width}" d="{ln["d"]}"/>')
    front += [f'    <path class="c-open c-stroke c-fine" d="{d}"/>' for d in r['marks']]
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300">\n'
            f'  <title>{b["name"]}</title>\n  <g id="beard-{b["id"]}">\n' + '\n'.join(skin + front) + '\n  </g>\n</svg>\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sheet', help='foglio con le figure')
    ap.add_argument('--out', required=True, help='cartella di destinazione (es. src/beards)')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    stem = os.path.splitext(os.path.basename(a.sheet))[0]
    if stem not in BEARDS:
        sys.exit(f'Nessuna tabella per il foglio {stem}: aggiungere BEARDS[{stem!r}]')
    table = BEARDS[stem]
    sheet = Sheet(a.sheet)
    boxes = sheet.figures()
    if len(boxes) != len(table):
        sys.exit(f'Il foglio ha {len(boxes)} figure ma la tabella ne ha {len(table)}')
    os.makedirs(a.out, exist_ok=True)
    for b, box in zip(table, boxes):
        if a.verbose:
            print(b['id'])
        r = trace_beard_figure(sheet, box, b, verbose=a.verbose)
        with open(os.path.join(a.out, b['id'] + '.svg'), 'w', encoding='utf8') as f:
            f.write(beard_svg(b, r))
        meta = dict(name=b['name'], color=r['color'])
        if b.get('groups'):
            meta['groups'] = list(b['groups'])
        if b.get('ages'):
            meta['ages'] = list(b['ages'])
        with open(os.path.join(a.out, b['id'] + '.json'), 'w', encoding='utf8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print(f'{b["id"]}: sagoma {len(r["fill"])} percorsi, {len(r["outline"])} tratti di contorno, {len(r["lines"])} linee interne'
              + (f', {len(r["dots"])} puntini' if r['dots'] else '') + f', colore {r["color"]}')


if __name__ == '__main__':
    main()
