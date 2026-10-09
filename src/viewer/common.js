// Codice comune alle sezioni della pagina (umani e alieni): piccole utilità, tavolozze dei colori rapidi, export
// e il cambio di sezione. Ogni sezione ha il suo file (human.js, alien.js) e non dipende dall'altra.

const SVG_NS = 'http://www.w3.org/2000/svg';
const XML_HEAD = '<?xml version="1.0" encoding="UTF-8"?>\n';

// ---- utilità ------------------------------------------------------------
const $ = (id) => document.getElementById(id);

let toastTimer;
function toast(msg) {
  const el = $('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 1800);
}

const rnd = (list) => list[Math.floor(Math.random() * list.length)];
const lum = (hex) => { const n = parseInt(hex.slice(1), 16); return 0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255); };

// Colori rapidi: toni della pelle, capelli (naturali e di fantasia), tessuti, inchiostri per contorno e occhi.
const PALETTES = {
  skin:   ['#fde3cf', '#fec39c', '#f1c27d', '#e0ac69', '#c68642', '#a0662f', '#8d5524', '#5c3a21'],
  hair:   ['#1f1a17', '#3b2a20', '#5d3523', '#8a4b2a', '#b5562a', '#d8b062', '#ecd8a0', '#a8a39c', '#e8e4dc', '#c2457a', '#3f6fd8', '#3e9b6a'],
  fabric: ['#f5f1ee', '#d9d4cc', '#8a8580', '#3d3d3d', '#1f2a44', '#3a5f9a', '#7aa0c8', '#5ec2b7', '#2f6b4f', '#7d8a4e',
           '#c8a26b', '#8b5a3c', '#b23a3a', '#e07a5f', '#f2c14e', '#f4a6b8', '#9b7bc4', '#6b3a6b'],
  ink:    ['#15100c', '#3b2a20', '#1f2a44', '#4a2330', '#5a5a5a'],
  sole:   ['#f5f1ee', '#e3d9c8', '#8a8580', '#3d3d3d', '#5f483a'],
};
const swatchRow = (keys, palette, label) => `<div class="swatches">${PALETTES[palette].map(c =>
  `<button type="button" class="swatch" data-keys="${keys.join(',')}" data-color="${c}" style="background:${c}" title="${c}" aria-label="${label}: ${c}"></button>`).join('')}</div>`;

// ---- export ------------------------------------------------------------
function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement('a'), { href: url, download: filename });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function svgToPngBlob(svgText, scale, width, height) {
  const url = URL.createObjectURL(new Blob([svgText], { type: 'image/svg+xml' }));
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    const canvas = document.createElement('canvas');
    canvas.width = width * scale;
    canvas.height = height * scale;
    canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
    return await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
  } finally {
    URL.revokeObjectURL(url);
  }
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = Object.assign(document.createElement('textarea'), { value: text });
    document.body.append(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
  }
}

function setPressed(container, attr, value) {
  for (const b of container.querySelectorAll('button')) b.setAttribute('aria-pressed', String(b.dataset[attr] === value));
}

const HEX = /^#[0-9a-f]{6}$/i;

// ---- sezioni della pagina ------------------------------------------------------
// Una scheda per tipo di sagoma (umani, alieni): ogni sezione ha il suo markup (human.html, alien.html), il suo script e i
// suoi dati. Si passa da una all'altra con le schede o con l'indirizzo (#umani, #alieni). Sono sempre nella pagina: quella
// nascosta mantiene il suo stato (personaggio scelto, colori).
const SECTIONS = { human: '#umani', alien: '#alieni' };
const sectionActive = (id) => !$(`section-${id}`).hidden;
function showSection(id, remember = true) {
  for (const key of Object.keys(SECTIONS)) {
    $(`section-${key}`).hidden = key !== id;
    const tab = $(`tab-${key}`);
    tab.setAttribute('aria-selected', String(key === id));
    tab.tabIndex = key === id ? 0 : -1;
  }
  if (remember) try { history.replaceState(null, '', SECTIONS[id]); } catch { /* da file: l'indirizzo resta com'è */ }
}
$('section-tabs').addEventListener('click', (e) => {
  const tab = e.target.closest('button[data-section]');
  if (tab) showSection(tab.dataset.section);
});
$('section-tabs').addEventListener('keydown', (e) => {
  const keys = Object.keys(SECTIONS), now = keys.findIndex(k => sectionActive(k));
  const next = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
  if (!next) return;
  const id = keys[(now + next + keys.length) % keys.length];
  showSection(id);
  $(`tab-${id}`).focus();
});
const fromHash = () => Object.keys(SECTIONS).find(k => SECTIONS[k] === location.hash) ?? 'human';
window.addEventListener('hashchange', () => showSection(fromHash(), false));
showSection(fromHash(), false);
