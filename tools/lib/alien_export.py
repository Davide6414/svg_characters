"""Scrittura dei file sorgente di una sagoma aliena: `<nome>.svg` (solo geometria) e `<nome>.json` (dati misurati)."""
import json
import os

from .export import PAIR, _d, _path
from .geom import fmt


def _extent(body):
    xs, ys = [], []
    for ps in body['parts'].values():
        for p in ps:
            for m in PAIR.finditer(_d(p['d'])):
                xs.append(float(m.group(1))); ys.append(float(m.group(2)))
    return min(xs), min(ys), max(xs), max(ys)


def alien_svg(body, title):
    """SVG della sola sagoma, dal fondo al primo piano: testa, braccio lontano, gambe, pantaloncini, braccio vicino,
    maglia. Gli id delle parti cominciano con `alien-` (la pagina contiene anche gli umani). I colori e l'animazione
    li aggiunge `build.mjs` (build/alien.mjs)."""
    P = body['parts']
    seams = {}
    for s in body['seams']:
        seams.setdefault(s['part'], []).append(s)

    def seam_paths(part, indent):
        return [' ' * indent + f'<path class="c-open c-stroke{" c-fine" if s["fine"] else ""}{" c-fold" if s["kind"] == "fold" else ""}" d="{s["d"]}"/>'
                for s in seams.get(part, [])]

    def region(role, fill, indent):
        """Riempimento e contorno di ogni regione del ruolo, poi le sue linee interne."""
        pad = ' ' * indent
        out = [f'{pad}' + _path(f'{fill} c-stroke', p['d']) for p in P[role]]
        return out + seam_paths(role, indent)

    x0, y0, x1, y1 = _extent(body)
    L = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{fmt(x0 - 4)} {fmt(y0 - 4)} {fmt(x1 - x0 + 8)} {fmt(y1 - y0 + 8)}">',
         f'  <title>{title}</title>',
         '  <g id="alien-head" class="c-alien-head">']
    # la testa (col collo, che sta sotto il colletto) in due passate: riempimento, poi contorno, come per gli umani
    L += ['    <!-- @prot-back -->']                                                       # protuberanze dietro la testa (corna, pinne…)
    L += ['    ' + _path('c-skin', p['d']) for p in P['head']]
    # il riempimento scende sotto il colletto della maglietta (la testa che si alza non apre fessure): un capo col proprio colletto
    # non ne ha bisogno, e fuori dalla maglietta la pelle sporgerebbe senza contorno (`alien-neckfill`: la build lo spegne coi capi)
    L += ['    ' + _path('c-skin alien-neckfill', p['fill']) for p in P['head'] if p.get('fill')]
    L += ['    ' + _path('c-open c-stroke', p['d']) for p in P['head']]
    L += seam_paths('head', 4)
    L += ['    <!-- @prot -->']                                                            # e quelle davanti (sopra il contorno, sotto occhi e narici)
    for n in body['nostrils']:
        L.append(f'    <ellipse class="c-dot" cx="{fmt(n["cx"])}" cy="{fmt(n["cy"])}" rx="{fmt(n["rx"])}" ry="{fmt(n["ry"])}"/>')
    for e in body['eyes']:
        L.append(f'    <ellipse class="c-eye c-alien-blink" cx="{fmt(e["cx"])}" cy="{fmt(e["cy"])}" rx="{fmt(e["rx"])}" ry="{fmt(e["ry"])}"/>')
    # ogni parte ha un gruppo `alien-base-…` col disegno della sagoma e un segnaposto per ciò che un capo ci aggiunge o ci mette al
    # posto (le braccia di una maglia, le gambe di dei pantaloni): la build li riempie e il CSS spegne il gruppo di base
    L += ['  </g>', '  <!-- @back -->', '  <g id="alien-arm-right" class="c-alien-arm">', '    <g class="alien-base-arms">'] + region('arm-right', 'c-skin', 6)
    L += ['    </g>', '    <!-- @arm-right -->']
    L += ['  </g>', '  <g id="alien-legs">', '    <g id="alien-leg-left">', '      <g class="alien-base-legs">'] + region('leg-left', 'c-skin', 8)
    L += ['      </g>', '      <!-- @leg-left -->', '    </g>', '    <g id="alien-leg-right">', '      <g class="alien-base-legs">'] + region('leg-right', 'c-skin', 8)
    L += ['      </g>', '      <!-- @leg-right -->', '    </g>', '  </g>', '  <g id="alien-pants">', '    <g id="alien-base-pants">'] + region('pants', 'c-pants', 6)
    L += ['    </g>', '    <!-- @bottom -->', '  </g>', '  <g id="alien-arm-left" class="c-alien-arm">', '    <g class="alien-base-arms">'] + region('arm-left', 'c-skin', 6)
    L += ['    </g>', '    <!-- @arm-left -->', '  </g>', '  <g id="alien-torso" class="c-alien-torso">', '    <g id="alien-base-torso">'] + region('torso', 'c-shirt', 6)
    L += ['    </g>', '    <!-- @top -->']
    L += ['  </g>', '</svg>']
    return '\n'.join(L) + '\n'


def write_alien(out_dir, name, title, body):
    """Scrive `<out_dir>/<name>.svg` e `<out_dir>/<name>.json` (nome, misure della testa, punti di riferimento, colori)."""
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name + '.svg'), 'w', encoding='utf8') as f:
        f.write(alien_svg(body, title))
    meta = dict(name=title, head={k: round(v, 1) for k, v in body['head'].items()}, landmarks=body['landmarks'], colors=body['colors'])
    with open(os.path.join(out_dir, name + '.json'), 'w', encoding='utf8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write('\n')
