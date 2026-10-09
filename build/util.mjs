// Funzioni comuni alle due sezioni (umani e alieni): lettura dei sorgenti e riscrittura delle coordinate dei percorsi.
import { readFile } from 'node:fs/promises';

export const root = new URL('../', import.meta.url);
export const read = (path) => readFile(new URL(path, root), 'utf8');
export const readJson = async (path) => JSON.parse(await read(path));

export const PAIR = /(-?\d+\.?\d*),(-?\d+\.?\d*)/g;     // coppie "x,y" dei percorsi (comandi sempre assoluti)
export const D_ATTR = / d="([^"]*)"/g;
export const fmt = (v) => { const s = v.toFixed(1); return (s.endsWith('.0') ? s.slice(0, -2) : s).replace(/^-0$/, '0'); };
export const mapPaths = (xml, f) => xml.replace(D_ATTR, (_, d) => ` d="${d.replace(PAIR, (__, x, y) => f(+x, +y).map(fmt).join(','))}"`);
export const mapCircles = (xml, f) => xml.replace(/cx="([^"]*)" cy="([^"]*)"/g, (_, x, y) => { const [X, Y] = f(+x, +y); return `cx="${fmt(X)}" cy="${fmt(Y)}"`; });
export const coords = (xml) => [...xml.matchAll(D_ATTR)].flatMap(([, d]) => [...d.matchAll(PAIR)].map((m) => [+m[1], +m[2]]));
