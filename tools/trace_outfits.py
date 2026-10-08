#!/usr/bin/env python3
"""Traccia gli outfit di un foglio in cui ogni figura indossa maglia e pantaloni sul proprio corpo.

Uso:
  python3 tools/trace_outfits.py reference/vestiti-femminili.webp --group femmina \\
      --bodies src/bodies/femmina --out src/clothes/femmina

La tabella delle figure si sceglie dal nome del foglio (OUTFITS[nome senza estensione]).

Per ogni figura (da sinistra a destra) scrive in --out `tops/<id>.svg + .json` e `bottoms/<id>.svg + .json`. Ogni capo
è disegnato sulla sagoma della figura (stesso nome in --bodies): il suo json dice su quale (`on`) e `build.mjs` lo
adatta alle altre. A differenza di `trace_clothes.py` (stesso corpo, capi diversi) qui le regioni di ogni figura si
assegnano a mano nelle tabelle OUTFITS: per vedere gli indici si lancia con -v.

Ogni capo ha:
  regions    {indice regione: ruolo}. Ruoli: main, trim, accent, accent2, under, skin (pelle lasciata scoperta)
  split      {indice regione: [(ruolo, regola[, area minima]), …]} dettagli senza contorno ricavati dal colore dentro
             la regione (regole: white, orange, lighter, darker, red, lilac) e disegnati sopra senza tratto
  behind     {indice: regioni dei bracci} la regione prosegue dietro le braccia (un pugno sui pantaloni lascia un vuoto)
  to_shoes   regioni che scendono sotto le scarpe (pantaloni, calze, gambe), così l'orlo non si vede
  layers     {indice: 'under'} regioni che stanno sotto i pantaloni (la pancia scoperta di un top corto)
  pad_under  {indice: dict(near=regioni vicine, up=, down=)} allunga in verticale quelle regioni sotto le regioni vicine
  under_up   {indice: px} i pantaloni salgono di tanti px sotto la maglia (in un livello sotto), così con una maglia
             più corta o con un orlo diverso non resta un buco in vita
  under_down {indice: px} lo stesso per una maglia corta o infilata: scende sotto i pantaloni
  join       {indice: (altre regioni,)} regioni da unire in una sola (le gambe dei leggings sotto un abito)
  extend_top {indice: px} la regione sale di tanti px (i fianchi nascosti da un abito)
  neck       True se lo scollo lascia vedere la pelle sotto il collo della sagoma (V, scollo ampio, cappuccio aperto)
  parts      {indice: 'arms'} regioni che sostituiscono le braccia della sagoma (spalle e braccia scoperte)
  arms       (braccio sinistro, braccio destro): indici delle regioni dei bracci, per le maniche corte (vedi sotto)
  folds      regioni dove cercare anche le pieghe chiare (per i pantaloni: la regione principale, in automatico)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.clothes_export import write_garment           # noqa: E402
from lib.outfits import trace_outfit                    # noqa: E402
from lib.sheet import Sheet                             # noqa: E402

# Per ogni foglio una riga per figura, da sinistra a destra: la sagoma su cui è disegnata, la maglia e i pantaloni.
OUTFITS = {}
OUTFITS['vestiti-femminili'] = [
    dict(body='bambina',
         top=dict(id='maglietta-fiore', name='Maglietta con fiore', regions={3: 'main'}, arms=(4, 5),
                  split={3: [('accent', 'white'), ('accent2', 'orange')]}),                       # petali e centro del fiore
         bottom=dict(id='pantaloncini', name='Pantaloncini risvoltati', regions={6: 'main', 7: 'skin', 8: 'skin'},
                     behind={6: (3,)}, under_up={6: 30},
                     split={6: [('trim', 'lighter')], 7: [('under', 'white')], 8: [('under', 'white')]},   # risvolto e calze
                     to_shoes=(7, 8))),
    dict(body='ragazza',
         top=dict(id='felpa-cappuccio', name='Felpa con cappuccio', regions={3: 'main', 4: 'under', 5: 'accent', 6: 'accent'},
                  neck=True, folds=(3,)),                                                                      # cordini e maglietta sotto
         bottom=dict(id='jeans-scuri', name='Jeans scuri', regions={7: 'main'}, to_shoes=(7,),
                     behind={7: (3, 4, 5, 6)}, under_up={7: 30})),
    dict(body='slanciata',
         top=dict(id='top-corto', name='Top corto', regions={3: 'main', 4: 'skin', 5: 'skin', 6: 'skin', 8: 'skin'},
                  layers={8: 'under'}, pad_under={8: dict(near=(3, 9), up=14, down=40)}, parts={4: 'arms', 5: 'arms', 6: 'arms'}, neck=True),   # braccia e pancia scoperte
         bottom=dict(id='jeans-a-zampa', name='Jeans a zampa', regions={9: 'main'}, to_shoes=(9,))),
    dict(body='adulta',
         top=dict(id='maglietta-v', name='Maglietta scollo a V', regions={3: 'main'}, arms=(6, 7), neck=True),
         bottom=dict(id='pantaloni-neri', name='Pantaloni neri larghi', regions={9: 'main'}, to_shoes=(9,),
                     behind={9: (3,)}, under_up={9: 30})),
    dict(body='robusta',
         top=dict(id='cardigan', name='Cardigan', regions={3: 'main', 4: 'main', 5: 'under', 6: 'main', 9: 'main'}, neck=True,
                  folds=(3, 4)),
         bottom=dict(id='pantaloni-marroni', name='Pantaloni marroni', regions={10: 'main'}, to_shoes=(10,), behind={10: (3, 4, 5, 7)}, under_up={10: 20})),
]


OUTFITS['vestiti-femminili-2'] = [
    dict(body='bambina',
         top=dict(id='abitino', name='Abitino con colletto', regions={5: 'main', 3: 'trim', 4: 'trim'}, arms=(6, 7),
                  split={5: [('accent', 'white'), ('accent2', 'orange')]}, folds=(5,)),             # colletto, fiore, pieghe
         bottom=dict(id='leggings', name='Leggings', regions={8: 'main', 14: 'skin'}, join={8: (9,)}, to_shoes=(8, 14),
                     behind={8: (5,)}, extend_top={8: 45}, under_up={8: 30})),                         # le gambe unite fino in vita
    dict(body='ragazza',
         top=dict(id='maglia-righe', name='Maglia a righe', regions={3: 'main', 4: 'trim', 5: 'trim'},
                  split={3: [('accent', 'red')]}),                                                     # righe e polsini
         bottom=dict(id='jeans-cargo', name='Jeans cargo', regions={8: 'main', 6: 'main', 7: 'main', 11: 'main', 12: 'main',
                                                                    13: 'main', 14: 'main'},
                     to_shoes=(8,), behind={8: (3, 4, 5)}, under_up={8: 30})),
    dict(body='slanciata',
         top=dict(id='giacca-jeans', name='Giacca di jeans', regions={5: 'main', 6: 'main', 3: 'main', 4: 'main', 8: 'main',
                                                                      9: 'main', 10: 'main', 11: 'trim', 12: 'trim', 7: 'under'},
                  neck=True, under_down={7: 30}),                                                                          # risvolti delle maniche, top sotto
         bottom=dict(id='jeans-neri', name='Jeans neri risvoltati', regions={18: 'main', 14: 'main', 15: 'main', 16: 'main',
                                                                             19: 'trim', 20: 'trim', 21: 'skin', 22: 'skin'},
                     to_shoes=(21, 22), behind={18: (5, 6, 7)}, under_up={18: 30})),
    dict(body='adulta',
         top=dict(id='maglione-v', name='Maglione a coste', regions={3: 'main'}, arms=(4, 6), neck=True, folds=(3,)),
         bottom=dict(id='pantaloni-oliva', name='Pantaloni oliva', regions={5: 'main', 7: 'skin'}, to_shoes=(5, 7),
                     behind={5: (3,)}, under_up={5: 30})),
    dict(body='robusta',
         top=dict(id='cardigan-fiori', name='Cardigan e maglia a fiori', regions={3: 'main', 4: 'main', 6: 'main', 9: 'main', 5: 'under'},
                  split={5: [('accent', 'lilac')]}, neck=True, folds=(3, 4)),                         # fiori sulla maglia
         bottom=dict(id='pantaloni-scuri', name='Pantaloni marrone scuro', regions={10: 'main'}, to_shoes=(10,),
                     behind={10: (3, 4, 5, 7)}, under_up={10: 20})),
]

OUTFITS['vestiti-maschili-outfit'] = [
    dict(body='bambino',
         top=dict(id='maglietta-riga', name='Maglietta con riga', regions={3: 'main'}, arms=(4, 5),
                  split={3: [('accent', 'darker')]}),                                                  # la riga sul petto
         bottom=dict(id='bermuda-cargo', name='Bermuda cargo', regions={7: 'main', 6: 'main', 8: 'main', 9: 'main', 10: 'main',
                                                                       11: 'main', 12: 'skin', 13: 'skin', 14: 'under', 15: 'under'},
                     to_shoes=(14, 15), behind={7: (3,)}, under_up={7: 30})),                          # gambe e calze
    dict(body='ragazzo',
         top=dict(id='felpa-rossa', name='Felpa con cappuccio', regions={3: 'main'}, neck=True, folds=(3,)),
         bottom=dict(id='jeans-grigi', name='Jeans grigi', regions={11: 'main'}, join={11: (12,)}, to_shoes=(11,),
                     behind={11: (3,)}, under_up={11: 30})),
    dict(body='slanciato',
         top=dict(id='camicia-risvoltata', name='Camicia con maniche arrotolate',
                  regions={3: 'main', 6: 'main', 4: 'main', 7: 'main', 8: 'main', 9: 'main', 5: 'under'}, neck=True),
         bottom=dict(id='pantaloni-kaki', name='Pantaloni kaki', regions={12: 'main'}, to_shoes=(12,),
                     behind={12: (3, 5, 6)}, under_up={12: 30})),
    dict(body='adulto',
         top=dict(id='polo-blu', name='Polo blu', regions={3: 'main', 4: 'main'}, arms=(6, 7),
                  split={4: [('trim', 'lighter', 10)]}, under_down={3: 30}),                           # bottoni della patta; infilata
         bottom=dict(id='pantaloni-cintura', name='Pantaloni con cintura',
                     regions={10: 'main', 15: 'main', 9: 'accent', 11: 'accent', 12: 'accent', 13: 'accent', 14: 'accent', 8: 'trim'},
                     to_shoes=(10,), under_up={10: 30})),                                              # cintura e fibbia
    dict(body='robusto',
         top=dict(id='cardigan-grigio', name='Cardigan grigio', regions={3: 'main', 4: 'main', 5: 'under'}, neck=True,
                  folds=(3, 4)),
         bottom=dict(id='jeans-chiari', name='Jeans chiari', regions={6: 'main'}, to_shoes=(6,),
                     behind={6: (3, 4, 5)}, under_up={6: 30})),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sheet', help='foglio con gli outfit')
    ap.add_argument('--group', required=True, help='gruppo delle sagome (es. femmina)')
    ap.add_argument('--bodies', required=True, help='cartella delle sagome tracciate (es. src/bodies/femmina)')
    ap.add_argument('--out', required=True, help='cartella di destinazione (es. src/clothes/femmina)')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()

    stem = os.path.splitext(os.path.basename(a.sheet))[0]
    if stem not in OUTFITS:
        sys.exit(f'Nessuna tabella per il foglio {stem}: aggiungere OUTFITS[{stem!r}]')
    table = OUTFITS[stem]
    sheet = Sheet(a.sheet)
    boxes = sheet.figures()
    if len(boxes) != len(table):
        sys.exit(f'Il foglio ha {len(boxes)} figure ma la tabella ne ha {len(table)}')
    for spec, box in zip(table, boxes):
        with open(os.path.join(a.bodies, spec['body'] + '.json'), encoding='utf8') as f:
            ref = json.load(f)
        if a.verbose:
            print(spec['body'])
        res = trace_outfit(sheet, box, ref, spec, verbose=a.verbose)
        for kind, folder in (('top', 'tops'), ('bottom', 'bottoms')):
            cs, garment = spec[kind], res[kind]
            write_garment(os.path.join(a.out, folder), cs['id'], cs['name'], garment, on=f'{a.group}/{spec["body"]}')
            print(f'{folder}/{cs["id"]}: {len(garment["regions"])} regioni, {len(garment["seams"])} linee, {len(garment["dots"])} puntini, colori {garment["colors"]}')


if __name__ == '__main__':
    main()
