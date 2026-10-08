"""Foglio di riferimento: immagine con più figure affiancate su sfondo chiaro."""
import numpy as np
from PIL import Image


class Sheet:
    def __init__(self, path):
        self.path = path
        self.rgb = np.asarray(Image.open(path).convert('RGB')).astype(np.float32)
        self.lum = 0.299 * self.rgb[..., 0] + 0.587 * self.rgb[..., 1] + 0.114 * self.rgb[..., 2]

    def figures(self, thresh=235, gap=12, margin=10):
        """Riquadri (x0, y0, x1, y1) delle figure, da sinistra a destra: colonne di pixel non di sfondo
        separate da più di `gap` pixel vuoti, con un margine attorno."""
        fg = self.lum < thresh
        cols = np.where(fg.any(axis=0))[0]
        groups, start, prev = [], cols[0], cols[0]
        for c in cols[1:]:
            if c - prev > gap:
                groups.append((start, prev)); start = c
            prev = c
        groups.append((start, prev))
        boxes = []
        for x0, x1 in groups:
            rows = np.where(fg[:, x0:x1 + 1].any(axis=1))[0]
            boxes.append((int(x0 - margin), int(rows.min() - margin), int(x1 + margin), int(rows.max() + margin + 1)))
        return boxes
