"""Scrittura dei file sorgente di una protuberanza: `<id>.svg` (solo geometria) e `<id>.json` (nome e riquadro di riferimento)."""
import json
import os
import re

from .geom import fmt

PAIR = re.compile(r'(-?\d+\.?\d*),(-?\d+\.?\d*)')


def protrusion_svg(spec, prot):
    """Un gruppo `prot-<id>`. Le parti dietro la testa hanno la classe `c-behind` (la build le mette prima del riempimento della
    testa): riempimento senza tratto, poi il contorno esterno e le linee interne. Le parti davanti sono regioni intere (riempimento
    e contorno) sopra la testa. Il colore del riempimento è `c-prot`: quello della pelle, salvo una scelta diversa."""
    L, xs, ys = [], [], []
    for part in prot['back']:
        for d in part['fill']:
            L.append(f'    <path class="c-prot c-behind" d="{d}"/>')
        L += [f'    <path class="c-open c-stroke c-behind" d="{d}"/>' for d in part['outline']]
        L += [f'    <path class="c-open c-stroke c-fine c-behind" d="{d}"/>' for d in part['lines']]
        xs += [float(m.group(1)) for d in part['fill'] for m in PAIR.finditer(d)]
        ys += [float(m.group(2)) for d in part['fill'] for m in PAIR.finditer(d)]
    for part in prot['front']:
        for d in part['fill']:
            L.append(f'    <path class="c-prot c-stroke" d="{d}"/>')
        L += [f'    <path class="c-open c-stroke c-fine" d="{d}"/>' for d in part['lines']]
        xs += [float(m.group(1)) for d in part['fill'] for m in PAIR.finditer(d)]
        ys += [float(m.group(2)) for d in part['fill'] for m in PAIR.finditer(d)]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{fmt(min(xs) - 4)} {fmt(min(ys) - 4)} {fmt(max(xs) - min(xs) + 8)} {fmt(max(ys) - min(ys) + 8)}">\n'
            f'  <title>{spec["name"]}</title>\n  <g id="prot-{spec["id"]}">\n' + '\n'.join(L) + '\n  </g>\n</svg>\n')


def write_protrusion(out_dir, spec, frame, prot):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, spec['id'] + '.svg'), 'w', encoding='utf8') as f:
        f.write(protrusion_svg(spec, prot))
    meta = dict(name=spec['name'], frame={k: round(v, 1) for k, v in frame.items()})
    with open(os.path.join(out_dir, spec['id'] + '.json'), 'w', encoding='utf8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write('\n')
