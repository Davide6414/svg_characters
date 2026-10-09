#!/usr/bin/env python3
"""Traccia le protuberanze (corna, palchi, pinne, creste) dai fogli di riferimento.

Uso:
  python3 tools/trace_protrusions.py --frame src/alien/bodies/maschio/adulto.json --out src/alien/protrusions

Per ogni figura della tabella FIGURES scrive `<id>.svg` + `<id>.json` in --out. Le coordinate sono quelle della testa di
riferimento (--frame: una sagoma aliena, di solito `maschio/adulto`): la build le adatta alla testa di ogni sagoma.
Vedi lib/protrusion.py per i due tipi di parte (`cut`, dietro la testa; `region`, davanti).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.protrusion import trace_protrusion      # noqa: E402
from lib.protrusion_export import write_protrusion   # noqa: E402
from lib.sheet import Sheet                       # noqa: E402

TESTE = 'reference/protuberanze-teste.webp'      # quattro teste con il busto (il busto non ha contorno in basso)
FIGURE = 'reference/protuberanze-figure.webp'    # quattro figure intere
ANTENNE = 'reference/protuberanze-antenne.webp'  # quattro figure intere con le antenne
POLY = lambda *pts: list(pts)

# id, nome, foglio, riquadro della figura, `bust` (la figura è un busto), parti (poligoni di taglio o punti dentro una regione).
#   fit {sx, sy, dx, dy}: ritocchi alla posizione e alla scala sulla testa di riferimento (stesse unità del riquadro di riferimento)
#   bridge: segmenti scuri che chiudono un'interruzione del tratto del foglio
FIGURES = [
    dict(id='corna-a-spirale', name='Corna a spirale', sheet=TESTE, box=(200, 10, 720, 495), bust=True,
         bridge=[((546, 198), (572, 222))],
         parts=[dict(kind='region', seed=(292, 174)), dict(kind='region', seed=(640, 165))]),
    dict(id='palchi', name='Palchi', sheet=TESTE, box=(770, 0, 1290, 525), bust=True,
         parts=[dict(kind='cut', poly=POLY((770, -10), (935, -10), (935, 165), (908, 186), (868, 224), (770, 224))),
                dict(kind='cut', poly=POLY((1105, -10), (1285, -10), (1285, 224), (1162, 224), (1125, 188), (1105, 165)))]),
    dict(id='corna-lunghe', name='Corna lunghe', sheet=TESTE, box=(240, 495, 640, 1060), bust=True,
         parts=[dict(kind='cut', poly=POLY((240, 495), (380, 495), (380, 670), (362, 678), (303, 723), (240, 723))),
                dict(kind='cut', poly=POLY((520, 495), (640, 495), (640, 742), (576, 742), (522, 680)))]),
    dict(id='corno-curvo', name='Corno curvo', sheet=TESTE, box=(760, 535, 1260, 1060), bust=True,
         parts=[dict(kind='cut', poly=POLY((760, 535), (918, 535), (918, 690), (862, 780), (760, 780))),
                dict(kind='cut', poly=POLY((1143, 535), (1260, 535), (1260, 795), (1158, 795), (1143, 722)))]),
    dict(id='cresta-a-foglia', name='Cresta a foglia', sheet=FIGURE, box=(400, 0, 680, 555), fit=dict(dx=6),
         parts=[dict(kind='cut', poly=POLY((400, -10), (570, -10), (570, 70), (537, 76), (500, 82), (467, 102), (450, 127), (447, 160), (400, 160)))]),
    dict(id='pinne', name='Pinne laterali', sheet=FIGURE, box=(770, 40, 1100, 543),
         parts=[dict(kind='cut', poly=POLY((770, 60), (857, 60), (857, 112), (845, 164), (860, 216), (860, 260), (770, 260))),
                dict(kind='cut', poly=POLY((1100, 60), (1023, 60), (1023, 112), (1035, 164), (1020, 216), (1020, 260), (1100, 260)))]),
    dict(id='cresta-al-vento', name='Cresta al vento', sheet=FIGURE, box=(340, 555, 680, 1086), fit=dict(dx=14),
         parts=[dict(kind='cut', poly=POLY((330, 560), (515, 560), (515, 606), (490, 630), (476, 665), (470, 700), (466, 722), (330, 722))),
                dict(kind='cut', poly=POLY((500, 555), (600, 555), (600, 605), (580, 606), (550, 606), (520, 607), (500, 607)))]),
    dict(id='spine', name='Cresta a spine', sheet=FIGURE, box=(790, 545, 1100, 1086),
         parts=[dict(kind='cut', poly=POLY((790, 545), (1100, 545), (1100, 745), (790, 745)), not_circle=(945, 694, 90))]),
    dict(id='antenne-a-pallina', name='Antenne a pallina', sheet=ANTENNE, box=(52, 127, 383, 1016),
         parts=[dict(kind='cut', poly=POLY((90, 70), (210, 70), (210, 214), (172, 224), (150, 236), (90, 236))),
                dict(kind='cut', poly=POLY((265, 70), (390, 70), (390, 228), (302, 234), (280, 222), (265, 222)))]),
    dict(id='antenne-lunghe', name='Antenne lunghe', sheet=ANTENNE, box=(395, 60, 723, 1017),
         parts=[dict(kind='cut', poly=POLY((420, 60), (545, 60), (545, 222), (538, 223), (515, 227), (420, 227))),
                dict(kind='cut', poly=POLY((590, 60), (740, 60), (740, 226), (622, 226), (600, 224), (590, 224)))]),
    dict(id='antenna-a-perline', name='Antenna a perline', sheet=ANTENNE, box=(725, 67, 1050, 1018),
         parts=[dict(kind='cut', poly=POLY((840, 60), (940, 60), (940, 224), (913, 226), (863, 224), (840, 224)))]),
    dict(id='antenne-a-pagaia', name='Antenne a pagaia', sheet=ANTENNE, box=(1065, 128, 1414, 1018),
         parts=[dict(kind='cut', poly=POLY((1060, 110), (1205, 110), (1205, 228), (1178, 243), (1160, 250), (1060, 250))),
                dict(kind='cut', poly=POLY((1270, 110), (1415, 110), (1415, 250), (1317, 250), (1305, 243), (1292, 234), (1270, 226)))]),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--frame', required=True, help='.json di una sagoma aliena: la testa di riferimento')
    ap.add_argument('--out', required=True, help='cartella di destinazione (es. src/alien/protrusions)')
    ap.add_argument('--only', help='solo questo id')
    a = ap.parse_args()
    head = json.load(open(a.frame, encoding='utf8'))['head']
    frame = {k: head[k] for k in ('skullX', 'skullHalf', 'T')}
    sheets = {}
    for spec in FIGURES:
        if a.only and spec['id'] != a.only:
            continue
        sheet = sheets.setdefault(spec['sheet'], Sheet(spec['sheet']))
        prot = trace_protrusion(sheet, spec, frame)
        write_protrusion(a.out, spec, frame, prot)
        print(f'{spec["id"]}: {len(prot["back"])} parti dietro la testa, {len(prot["front"])} davanti')


if __name__ == '__main__':
    main()
