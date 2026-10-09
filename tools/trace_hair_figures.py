#!/usr/bin/env python3
"""Traccia le acconciature da un foglio di figure intere (ogni figura ha la testa con uno stile diverso).

Uso:
  python3 tools/trace_hair_figures.py reference/capelli-anziani.webp --out src/hair
  python3 tools/trace_hair_figures.py reference/capelli-2.webp --out src/hair

La tabella si sceglie dal nome del foglio (HAIRS[nome senza estensione]), una riga per figura da sinistra a destra.
Scrive `<id>.svg` (riempimento, contorno solo dove il foglio ha un tratto, linee interne, nelle coordinate del
riquadro dei capelli) e `<id>.json` (nome, colore di default, età a cui si adatta).

Ogni stile ha:
  id, name   come negli altri stili
  ages       età delle sagome a cui si applica (vedi `ages` nel manifest); senza: tutte
  strays     True: cerca anche i capelli sparsi sopra una testa calva
  fit_top    True: la cima del cranio si vede (testa calva) e si allinea anche quella (scala verticale a parte)
  shaved     differenza di luminosità oltre la quale i capelli più chiari sono una zona rasata (disegnata trasparente,
             sotto il contorno della testa: la build la ritaglia sulla testa di ogni sagoma)
  behind     'right': i ciuffi a destra degli occhi stanno dietro la testa (la testa li copre col suo contorno): si
             disegnano prima della testa, prolungati dentro il cranio, così restano attaccati a ogni testa
  scale, kx, ky, dy   correzioni dell'allineamento (scala, solo x, solo y, spostamento verticale) se servono
Per l'allineamento e l'isolamento vedi `lib/hair_figures.py`; il colore si cambia poi con --hair come gli altri stili.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.hair_figures import trace_hair_figure      # noqa: E402
from lib.sheet import Sheet                         # noqa: E402

ADULTS, NOT_KIDS = ('adulto',), ('ragazzo', 'adulto')
HAIRS = {
    'capelli-anziani': [
        dict(id='calvizie', name='Calvizie con ciuffi', ages=ADULTS, strays=True, fit_top=True, behind='right'),
        dict(id='coda-grigia', name='Coda bassa', ages=NOT_KIDS),
        dict(id='chignon-grigio', name='Chignon basso', ages=NOT_KIDS),
        dict(id='stempiato', name='Stempiato', ages=ADULTS),
        dict(id='pettinati-indietro', name="Pettinati all'indietro", ages=NOT_KIDS),
    ],
    'capelli-2': [
        dict(id='arruffati', name='Arruffati'),
        dict(id='due-chignon', name='Due chignon', scale=1.04, dy=-4),
        dict(id='caschetto', name='Caschetto'),
        dict(id='rasati-lato', name='Rasati di lato', shaved=25),
        dict(id='ricci', name='Ricci'),
    ],
}


def hair_svg(h, r):
    """Righe di `<g id="hair-<id>">`. Le classi `c-behind` (ciuffi dietro la testa) e `c-shaved` (zona rasata: sulla pelle,
    sotto il contorno della testa) dicono a `build.mjs` in quale livello della testa vanno; le altre stanno davanti."""
    c = f'c-hair-{h["id"]}'
    rows = []
    if r['behind']:
        rows.append(f'    <path class="{c} c-behind" d="{"".join(r["behind"])}"' + (' fill-rule="evenodd"' if len(r['behind']) > 1 else '') + '/>')
        rows += [f'    <path class="c-open c-stroke c-behind" d="{d}"/>' for d in r['behind_outline']]
        for ln in r['behind_lines']:
            width = '' if ln['thick'] >= 4.6 else ' c-fine' if ln['thick'] >= 3.2 else ' c-hair'
            rows.append(f'    <path class="c-open c-stroke{width} c-behind" d="{ln["d"]}"/>')
    rows.append(f'    <path class="{c}" d="{"".join(r["fill"])}"' + (' fill-rule="evenodd"' if len(r['fill']) > 1 else '') + '/>')
    if r['shaved']:
        rows.append(f'    <path class="{c} c-shaved" d="{"".join(r["shaved"])}"/>')
    rows += [f'    <path class="c-open c-stroke" d="{d}"/>' for d in r['outline']]
    for ln in r['lines']:                      # ciocche: tratto pieno, fine o sottile secondo lo spessore nel foglio
        width = '' if ln['thick'] >= 4.6 else ' c-fine' if ln['thick'] >= 3.2 else ' c-hair'
        rows.append(f'    <path class="c-open c-stroke{width}" d="{ln["d"]}"/>')
    rows += [f'    <path class="c-open c-stroke c-fine" d="{d}"/>' for d in r['strays']]
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300">\n'
            f'  <title>{h["name"]}</title>\n  <g id="hair-{h["id"]}">\n' + '\n'.join(rows) + '\n  </g>\n</svg>\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sheet', help='foglio con le figure')
    ap.add_argument('--out', required=True, help='cartella di destinazione (es. src/hair)')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    stem = os.path.splitext(os.path.basename(a.sheet))[0]
    if stem not in HAIRS:
        sys.exit(f'Nessuna tabella per il foglio {stem}: aggiungere HAIRS[{stem!r}]')
    table = HAIRS[stem]
    sheet = Sheet(a.sheet)
    boxes = sheet.figures()
    if len(boxes) != len(table):
        sys.exit(f'Il foglio ha {len(boxes)} figure ma la tabella ne ha {len(table)}')
    os.makedirs(a.out, exist_ok=True)
    for h, box in zip(table, boxes):
        if a.verbose:
            print(h['id'])
        r = trace_hair_figure(sheet, box, h, verbose=a.verbose)
        with open(os.path.join(a.out, h['id'] + '.svg'), 'w', encoding='utf8') as f:
            f.write(hair_svg(h, r))
        meta = dict(name=h['name'], color=r['color'])
        if h.get('ages'):
            meta['ages'] = list(h['ages'])
        with open(os.path.join(a.out, h['id'] + '.json'), 'w', encoding='utf8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print(f'{h["id"]}: {len(r["outline"])} tratti di contorno, {len(r["lines"])} linee interne'
              + (f', {len(r["strays"])} capelli sparsi' if r['strays'] else '') + (', zona rasata' if r['shaved'] else ''))


if __name__ == '__main__':
    main()
