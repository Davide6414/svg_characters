"""Scrittura dei file sorgente di un capo alieno: `<id>.svg` (geometria nelle coordinate della sagoma) e `<id>.json`."""
import json
import os
import re

PAIR = re.compile(r'(-?\d+\.?\d*),(-?\d+\.?\d*)')


def _row(r, indent):
    d = ''.join(r['d'])
    return f'{indent}<path class="{r["cls"]}" d="{d}"' + (' fill-rule="evenodd"' if len(r['d']) > 1 else '') + '/>'


def garment_svg(garment, title):
    """Gruppi del capo: `garment` (davanti), `back` (dietro le braccia: la coda di un mantello), `under` (sotto i
    pantaloncini: la maglia che scende dietro), e le parti del corpo che il capo sostituisce: `arm-left`/`arm-right` (maglie),
    `leg-left`/`leg-right` (pantaloni). Gli id dei gruppi li fa diventare unici la build (build/alien.mjs)."""
    groups, xs, ys = [], [], []

    def group(gid, rows):
        if not rows:
            return
        groups.append(f'  <g id="{gid}">\n' + '\n'.join(_row(r, '    ') for r in rows) + '\n  </g>')
        for r in rows:
            for m in PAIR.finditer(''.join(r['d'])):
                xs.append(float(m.group(1))); ys.append(float(m.group(2)))

    for gid in ('garment', 'back', 'under'):
        group(gid, garment['layers'][gid])
    for gid, rows in garment['parts'].items():
        group(gid, rows)
    vb = f'{min(xs) - 4:.1f} {min(ys) - 4:.1f} {max(xs) - min(xs) + 8:.1f} {max(ys) - min(ys) + 8:.1f}'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">\n  <title>{title}</title>\n' + '\n'.join(groups) + '\n</svg>\n'


def write_garment(out_dir, gid, title, garment):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, gid + '.svg'), 'w', encoding='utf8') as f:
        f.write(garment_svg(garment, title))
    meta = dict(name=title, colors=garment['colors'], replaces=garment['replaces'])
    with open(os.path.join(out_dir, gid + '.json'), 'w', encoding='utf8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write('\n')
