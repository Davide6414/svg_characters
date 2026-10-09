"""Scrittura dei file sorgente di una sagoma: `<nome>.svg` (solo geometria) e `<nome>.json` (dati misurati)."""
import json
import os
import re

from .geom import fmt

PAIR = re.compile(r'(-?\d+\.?\d*),(-?\d+\.?\d*)')


def _d(ds):
    return ''.join(ds)


def _path(cls, ds, extra=''):
    return f'<path class="{cls}"{extra} d="{_d(ds)}"/>'


def _extent(body):
    xs, ys = [], []
    for ps in body['parts'].values():
        for p in ps:
            for m in PAIR.finditer(_d(p['d'])):
                xs.append(float(m.group(1))); ys.append(float(m.group(2)))
    return min(xs), min(ys), max(xs), max(ys)


def body_svg(body, title):
    """SVG della sola sagoma: stessi gruppi in tutte le sagome, dal fondo al primo piano. I colori e i capelli
    li aggiunge `build.mjs` (i segnaposto `<!-- @hair-back -->`, `<!-- @hair-skin -->` e `<!-- @hair -->` dicono dove vanno i
    capelli, dentro `head`)."""
    P = body['parts']
    seams = {}
    for s in body['seams']:
        seams.setdefault(s['part'], []).append(s)

    def seam_paths(part, indent):
        return [' ' * indent + f'<path class="c-open c-stroke{" c-fine" if s["fine"] else ""}" d="{s["d"]}"/>'
                for s in seams.get(part, [])]

    x0, y0, x1, y1 = _extent(body)
    L = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{fmt(x0 - 4)} {fmt(y0 - 4)} {fmt(x1 - x0 + 8)} {fmt(y1 - y0 + 8)}">',
         f'  <title>{title}</title>',
         '  <defs>']                                                   # riempimenti di fondo (vedi parts.trace_body):
    for name in ('fill-top', 'fill-bottom'):                           # la build li richiama in ogni capo, col suo colore
        for p in P.get(name, []):
            L.append(f'    <path id="{name}" d="{_d(p["d"])}"/>')
    L += ['  </defs>', '  <g id="neck-fill">']
    L += ['    ' + _path('c-skin', p['d']) for p in P.get('fill-neck', [])]
    L += ['  </g>', '  <g id="pants-under">']                 # i pantaloni sotto la maglia (vedi WAIST_UP in parts.py),
    L += ['    ' + _path('c-pants c-stroke', p['d']) for p in P['pants-under']]   # dietro al braccio lontano
    L += ['  </g>', '  <g id="arm-right" class="c-idle-arm">']
    L += ['    ' + _path('c-skin c-stroke', p['d']) for p in P['arm-right']]
    L += ['  </g>', '  <g id="pants">']
    for p in P['pants']:
        L.append('    ' + _path('c-pants c-stroke', p['d'], ' fill-rule="evenodd"' if len(p['d']) > 1 else ''))
    L += ['    ' + _path('c-pants c-stroke c-fine', p['d']) for p in P.get('pants-detail', [])]
    L += seam_paths('pants', 4)
    soles = sorted(P['sole'], key=lambda p: p['cx'])
    L += ['  </g>', '  <g id="shoes">', '    <g id="shoe-left">', '      ' + _path('c-sole c-stroke', soles[0]['d'])]
    L += ['      ' + _path('c-upper-l c-stroke', p['d']) for p in P['upper-l']]
    L += ['      ' + _path('c-tongue c-stroke', p['d']) for p in P['tongue']]
    L += ['    </g>', '    <g id="shoe-right">', '      ' + _path('c-sole c-stroke', soles[1]['d'])]
    L += ['      ' + _path('c-upper-r c-stroke', p['d']) for p in P['upper-r']]
    L += ['      ' + _path('c-toe c-stroke', p['d']) for p in P.get('toe', [])]
    L += ['      ' + _path('c-lace c-stroke c-fine', p['d']) for p in P.get('lace', [])]
    L += ['    </g>', '  </g>', '  <g id="arm-left" class="c-idle-arm">']
    L += ['    ' + _path('c-skin c-stroke', p['d']) for p in P['arm-left']]
    # la testa è disegnata in due passate (riempimento, poi contorno) per dare ai capelli tre livelli: dietro la testa
    # (un ciuffo che spunta oltre il cranio), sulla pelle ma sotto il contorno (una zona rasata) e davanti
    L += ['  </g>', '  <g id="head" class="c-idle-head">', '    <!-- @hair-back -->']
    L += ['    ' + _path('c-skin', p['d']) for p in P['head']]
    L += ['    <!-- @hair-skin -->']
    L += ['    ' + _path('c-open c-stroke', p['d']) for p in P['head']]
    L += seam_paths('head', 4)
    L += ['    <!-- @hair -->']                     # i capelli sotto gli occhi: una frangia lunga non li copre mai
    for e in body['eyes']:
        L.append(f'    <ellipse class="c-eye c-blink" cx="{fmt(e["cx"])}" cy="{fmt(e["cy"])}" rx="{fmt(e["rx"])}" ry="{fmt(e["ry"])}"/>')
    L += ['  </g>', '  <g id="torso" class="c-idle-torso">']
    L += ['    ' + _path('c-shirt c-stroke', p['d']) for p in P['torso']]
    L += seam_paths('torso', 4)
    L += ['  </g>', '</svg>']
    return '\n'.join(L) + '\n'


def write_body(out_dir, name, title, body):
    """Scrive `<out_dir>/<name>.svg` e `<out_dir>/<name>.json` (nome, punti di riferimento della testa, colori)."""
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name + '.svg'), 'w', encoding='utf8') as f:
        f.write(body_svg(body, title))
    meta = dict(name=title, head={k: round(v, 1) for k, v in body['head'].items()}, landmarks=body['landmarks'], colors=body['colors'])
    with open(os.path.join(out_dir, name + '.json'), 'w', encoding='utf8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write('\n')
