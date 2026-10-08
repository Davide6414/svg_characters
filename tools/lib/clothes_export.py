"""Scrittura dei file sorgente di un capo: `<id>.svg` (geometria nel riquadro del corpo di riferimento) e `<id>.json`."""
import json
import os
import re

from .geom import fmt

PAIR = re.compile(r'(-?\d+\.?\d*),(-?\d+\.?\d*)')


def garment_svg(garment, title):
    rows = []
    for r in garment['regions']:
        rows.append(f'    <path class="c-{r["role"]} c-stroke" d="{"".join(r["d"])}"' + (' fill-rule="evenodd"' if len(r['d']) > 1 else '') + '/>')
    for sm in garment['seams']:
        rows.append(f'    <path class="c-open c-stroke{" c-fine" if sm["fine"] else ""}" d="{sm["d"]}"/>')
    for dt in garment['dots']:
        rows.append(f'    <circle class="c-dot" cx="{fmt(dt["cx"])}" cy="{fmt(dt["cy"])}" r="{fmt(dt["r"])}"/>')
    xs, ys = [], []
    for r in garment['regions']:
        for m in PAIR.finditer(''.join(r['d'])):
            xs.append(float(m.group(1))); ys.append(float(m.group(2)))
    vb = f'{fmt(min(xs) - 4)} {fmt(min(ys) - 4)} {fmt(max(xs) - min(xs) + 8)} {fmt(max(ys) - min(ys) + 8)}'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">\n  <title>{title}</title>\n  <g id="garment">\n'
            + '\n'.join(rows) + '\n  </g>\n</svg>\n')


def write_garment(out_dir, gid, title, garment):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, gid + '.svg'), 'w', encoding='utf8') as f:
        f.write(garment_svg(garment, title))
    with open(os.path.join(out_dir, gid + '.json'), 'w', encoding='utf8') as f:
        json.dump(dict(name=title, colors=garment['colors']), f, ensure_ascii=False, indent=2)
        f.write('\n')
