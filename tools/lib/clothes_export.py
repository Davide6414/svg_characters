"""Scrittura dei file sorgente di un capo: `<id>.svg` (geometria nel riquadro del corpo di riferimento) e `<id>.json`."""
import json
import os
import re

from .geom import fmt

PAIR = re.compile(r'(-?\d+\.?\d*),(-?\d+\.?\d*)')


def _rows(garment, layer):
    rows, part = [], None
    for r in garment['regions']:
        if r.get('layer', 'main') != layer:
            continue
        if r.get('part') != part:                     # le regioni di una parte del corpo che il capo sostituisce (braccia) stanno in un gruppo
            if part:
                rows.append('    </g>')
            part = r.get('part')
            if part:
                rows.append(f'    <g class="g-{part}">')
        stroke = r.get('stroke', True)
        rows.append(f'    <path class="c-{r["role"]}{" c-stroke" if stroke else ""}" d="{"".join(r["d"])}"' + (' fill-rule="evenodd"' if len(r['d']) > 1 else '') + '/>')
    if part:
        rows.append('    </g>')
    for sm in garment['seams']:
        if sm.get('layer', 'main') == layer:
            width = ' c-hair' if sm.get('hair') else ' c-fine' if sm['fine'] else ''
            rows.append(f'    <path class="c-open c-stroke{width}" d="{sm["d"]}"/>')
    for dt in garment['dots']:
        if dt.get('layer', 'main') == layer:
            rows.append(f'    <circle class="c-dot" cx="{fmt(dt["cx"])}" cy="{fmt(dt["cy"])}" r="{fmt(dt["r"])}"/>')
    return rows


def garment_svg(garment, title):
    """`<g id="garment">` è il capo; `<g id="underlay">` (se c'è) sta sotto i pantaloni (pelle scoperta dalla maglia,
    fasce che salgono o scendono sotto un altro capo); `<g id="backlay">` dietro a tutto (il capo sotto le braccia)."""
    xs, ys = [], []
    for r in garment['regions']:
        for m in PAIR.finditer(''.join(r['d'])):
            xs.append(float(m.group(1))); ys.append(float(m.group(2)))
    vb = f'{fmt(min(xs) - 4)} {fmt(min(ys) - 4)} {fmt(max(xs) - min(xs) + 8)} {fmt(max(ys) - min(ys) + 8)}'
    groups = '\n'.join(f'  <g id="{gid}">\n' + '\n'.join(rows) + '\n  </g>'
                       for gid, rows in (('garment', _rows(garment, 'main')), ('underlay', _rows(garment, 'under')),
                                         ('backlay', _rows(garment, 'back'))) if rows)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">\n  <title>{title}</title>\n{groups}\n</svg>\n'


def write_garment(out_dir, gid, title, garment, drawn_on_reference=False):
    """`drawn_on_reference`: il capo è disegnato sul corpo di riferimento della cartella (`reference.json`) invece che
    sulla sagoma stessa: `build.mjs` lo adatta alla sagoma. `landmarks` del capo, se ci sono, sostituiscono quelli della
    sagoma nel punto di partenza dell'adattamento; `replaces` = parti del corpo (arms) che il capo disegna al posto di
    quelle della sagoma."""
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, gid + '.svg'), 'w', encoding='utf8') as f:
        f.write(garment_svg(garment, title))
    meta = dict(name=title, colors=garment['colors'])
    if drawn_on_reference:
        meta['ref'] = 'reference'
    if garment.get('landmarks'):
        meta['landmarks'] = garment['landmarks']
    if garment.get('replaces'):
        meta['replaces'] = garment['replaces']
    with open(os.path.join(out_dir, gid + '.json'), 'w', encoding='utf8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write('\n')
