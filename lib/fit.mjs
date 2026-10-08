// Deformazione "thin-plate spline" 2D: porta i punti `src` sui punti `dst` e deforma in modo morbido tutto il resto.
// Serve ad adattare i vestiti, disegnati su un corpo di riferimento, ai corpi delle varie sagome.

/** Risolve A·x = b (Gauss con pivot parziale); A è n×n, modifica le copie. */
function solve(A, b) {
  const n = b.length;
  const M = A.map((row, i) => [...row, b[i]]);
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    if (Math.abs(M[p][c]) < 1e-12) throw new Error('fit: punti di riferimento degeneri');
    [M[c], M[p]] = [M[p], M[c]];
    for (let r = c + 1; r < n; r++) {
      const f = M[r][c] / M[c][c];
      for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k];
    }
  }
  const x = new Array(n).fill(0);
  for (let r = n - 1; r >= 0; r--) {
    let s = M[r][n];
    for (let k = r + 1; k < n; k++) s -= M[r][k] * x[k];
    x[r] = s / M[r][r];
  }
  return x;
}

/**
 * @param {number[][]} src  punti di partenza [[x, y], …]
 * @param {number[][]} dst  punti di arrivo, stesso ordine
 * @param {number} lambda   rigidità (0 = i punti coincidono esattamente; più alto = deformazione più dolce)
 * @returns {(x: number, y: number) => number[]} funzione che deforma un punto
 */
export function makeTps(src, dst, lambda = 0) {
  const n = src.length;
  // coordinate centrate e scalate: il sistema resta ben condizionato
  const cx = src.reduce((t, p) => t + p[0], 0) / n, cy = src.reduce((t, p) => t + p[1], 0) / n;
  const sc = Math.sqrt(src.reduce((t, p) => t + (p[0] - cx) ** 2 + (p[1] - cy) ** 2, 0) / n) || 1;
  const P = src.map(([x, y]) => [(x - cx) / sc, (y - cy) / sc]);
  const U = (r2) => (r2 === 0 ? 0 : 0.5 * r2 * Math.log(r2));   // r² ln r

  const N = n + 3;
  const A = Array.from({ length: N }, () => new Array(N).fill(0));
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) A[i][j] = U((P[i][0] - P[j][0]) ** 2 + (P[i][1] - P[j][1]) ** 2) + (i === j ? lambda : 0);
    A[i][n] = A[n][i] = 1;
    A[i][n + 1] = A[n + 1][i] = P[i][0];
    A[i][n + 2] = A[n + 2][i] = P[i][1];
  }
  const wx = solve(A, [...dst.map((p) => p[0]), 0, 0, 0]);
  const wy = solve(A, [...dst.map((p) => p[1]), 0, 0, 0]);

  return (x, y) => {
    const px = (x - cx) / sc, py = (y - cy) / sc;
    let fx = wx[n] + wx[n + 1] * px + wx[n + 2] * py;
    let fy = wy[n] + wy[n + 1] * px + wy[n + 2] * py;
    for (let i = 0; i < n; i++) {
      const u = U((px - P[i][0]) ** 2 + (py - P[i][1]) ** 2);
      fx += wx[i] * u;
      fy += wy[i] * u;
    }
    return [fx, fy];
  };
}
