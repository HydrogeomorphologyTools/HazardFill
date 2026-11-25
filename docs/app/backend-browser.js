/* HazardFill (HF) - backend per il browser (GitHub Pages): tutto il calcolo avviene sul computer dell'utente.
 * Legge GeoTIFF ed edifici, li proietta, esegue il nucleo Python (core.py) in un Web Worker con Pyodide e
 * restituisce alla pagina le stesse strutture del server.
 * Copyright (C) 2026 Stefano Crema, Marco Cavalli, Alessandro Sarretta - CNR-GEO (Istituto di Geoscienze). Licenza GNU GPL v2. */
(function () {
  'use strict';
  const VERSION = '1.2.1';
  const $ = (id) => document.getElementById(id);
  const COLORS = { 1: [255, 235, 59], 2: [255, 140, 0], 3: [214, 40, 40] };
  const FF = { 1: 0.72, 2: 0.55, 3: 0.38 };
  const MAX_PX = 60e6;
  const areas = {};                       // nome area -> dati
  const busy = (t) => { const b = $('busy'); if (b) { b.textContent = t; b.style.display = 'inline'; } };
  const idle = () => { const b = $('busy'); if (b) { b.style.display = 'none'; b.textContent = 'calcolo…'; } };

  // ------------------------------------------------------------------ worker (Python)
  const worker = new Worker('hf-worker.js');
  let seq = 0;
  const pending = {};
  let wReady = false;
  worker.onmessage = (e) => {
    const m = e.data;
    if (m.type === 'status') { busy(m.msg); return; }
    if (m.type === 'ready') { wReady = true; idle(); return; }
    const p = pending[m.id];
    if (!p) return;
    delete pending[m.id];
    if (m.type === 'error') p.rej(new Error(m.error)); else p.res(m);
  };
  worker.onerror = (e) => { busy('errore nel calcolo: ' + (e.message || e)); };
  function call(msg) {
    return new Promise((res, rej) => { const id = ++seq; pending[id] = { res, rej }; worker.postMessage(Object.assign({ id }, msg)); });
  }
  worker.postMessage({ type: 'init', id: 0 });         // avvia subito Pyodide in sottofondo

  // ------------------------------------------------------------------ sistemi di coordinate
  const defCache = {};
  async function crsDef(epsg) {
    if (defCache[epsg]) return defCache[epsg];
    let d = null;
    if (epsg >= 32601 && epsg <= 32660) d = '+proj=utm +zone=' + (epsg - 32600) + ' +datum=WGS84 +units=m +no_defs';
    else if (epsg >= 32701 && epsg <= 32760) d = '+proj=utm +zone=' + (epsg - 32700) + ' +south +datum=WGS84 +units=m +no_defs';
    else if (epsg >= 25828 && epsg <= 25838) d = '+proj=utm +zone=' + (epsg - 25800) + ' +ellps=GRS80 +units=m +no_defs';
    else if (epsg === 3003) d = '+proj=tmerc +lat_0=0 +lon_0=9 +k=0.9996 +x_0=1500000 +y_0=0 +ellps=intl +towgs84=-104.1,-49.1,-9.9,0.971,-2.917,0.714,-11.68 +units=m +no_defs';
    else if (epsg === 3004) d = '+proj=tmerc +lat_0=0 +lon_0=15 +k=0.9996 +x_0=2520000 +y_0=0 +ellps=intl +towgs84=-104.1,-49.1,-9.9,0.971,-2.917,0.714,-11.68 +units=m +no_defs';
    else if (epsg === 3035) d = '+proj=laea +lat_0=52 +lon_0=10 +x_0=4321000 +y_0=3210000 +ellps=GRS80 +units=m +no_defs';
    else if (epsg === 3857) d = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0 +lon_0=0 +x_0=0 +y_0=0 +k=1 +units=m +nadgrids=@null +no_defs';
    else if (epsg === 7791 || epsg === 6707 || epsg === 6708) d = null;
    if (!d) {
      try { d = (await (await fetch('https://epsg.io/' + epsg + '.proj4')).text()).trim(); } catch (e) { d = null; }
      if (!d || d.indexOf('+proj') < 0) throw new Error('sistema di coordinate EPSG:' + epsg + ' non riconosciuto: riproietta il raster in UTM (es. EPSG:32632) e riprova');
    }
    defCache[epsg] = d;
    return d;
  }

  // ------------------------------------------------------------------ lettura GeoTIFF
  function rint(v) {                      // arrotondamento "al pari" come numpy.rint
    const r = Math.round(v);
    return (Math.abs(v % 1) === 0.5 && (r % 2) !== 0) ? r - 1 : r;
  }
  async function readGeoTiff(file) {
    const tiff = await GeoTIFF.fromArrayBuffer(await file.arrayBuffer());
    const img = await tiff.getImage();
    const w = img.getWidth(), h = img.getHeight();
    if (w * h > MAX_PX) throw new Error('raster troppo grande per il browser (' + (w * h / 1e6).toFixed(0) + ' milioni di pixel, massimo ' + (MAX_PX / 1e6) + '): ritaglialo oppure usa il plugin QGIS o la versione locale');
    const fd = img.getFileDirectory();
    const keys = img.getGeoKeys() || {};
    let sx, sy, x0, y0;
    if (fd.ModelTransformation) {
      const t = fd.ModelTransformation;
      if (Math.abs(t[1]) > 1e-12 || Math.abs(t[4]) > 1e-12) throw new Error('il raster deve avere la griglia con il nord in alto, senza rotazione');
      sx = t[0]; sy = -t[5]; x0 = t[3]; y0 = t[7];
    } else if (fd.ModelPixelScale && fd.ModelTiepoint) {
      sx = fd.ModelPixelScale[0]; sy = fd.ModelPixelScale[1];
      x0 = fd.ModelTiepoint[3] - fd.ModelTiepoint[0] * sx; y0 = fd.ModelTiepoint[4] + fd.ModelTiepoint[1] * sy;
    } else throw new Error('il file non è un GeoTIFF georeferenziato');
    if (Math.abs(sx - sy) > 0.01 * sx) throw new Error('i pixel devono essere quadrati');
    if (keys.GTRasterTypeGeoKey === 2) { x0 -= sx / 2; y0 += sy / 2; }          // PixelIsPoint
    const epsg = keys.ProjectedCSTypeGeoKey;
    if (!epsg || epsg === 32767) {
      if (keys.GeographicTypeGeoKey) throw new Error('il raster deve essere in un sistema di coordinate proiettato in metri (non in gradi): riproiettalo prima del caricamento');
      throw new Error('sistema di coordinate non riconosciuto (serve un codice EPSG proiettato)');
    }
    const def = await crsDef(epsg);
    const band = await img.readRasters({ samples: [0], interleave: true });
    const h8 = new Uint8Array(w * h);
    const odd = new Set();
    for (let i = 0; i < band.length; i++) {
      const v = band[i];
      if (!(v >= 0.5)) { h8[i] = 0; continue; }                 // NaN, negativi e < 0,5
      const r = rint(v);
      if (odd.size < 8 && (r > 3 || Math.abs(v - r) > 1e-6)) odd.add(+v.toFixed(3));
      h8[i] = r > 3 ? 3 : r;
    }
    const warnings = [];
    if (odd.size) warnings.push('valori diversi da 0-3 (es. ' + [...odd].slice(0, 6).join(', ') + '): i non interi sono arrotondati e i valori >3 portati a 3; se la mappa usa altri codici riclassificala prima');
    if (fd.SamplesPerPixel > 1) warnings.push('il raster ha ' + fd.SamplesPerPixel + ' bande: si usa la prima');
    return { w, h, res: sx, x0, y0, epsg, def, h8, warnings };
  }

  // ------------------------------------------------------------------ griglia di visualizzazione (Web Mercator)
  const R_E = 6378137;
  const mercLon = (x) => x / R_E * 180 / Math.PI;
  const mercLat = (y) => (2 * Math.atan(Math.exp(y / R_E)) - Math.PI / 2) * 180 / Math.PI;
  function buildDisplay(a) {
    const fwd = proj4(a.def, 'EPSG:3857'), inv = proj4('EPSG:3857', a.def);
    const xs = [a.x0, a.x0 + a.w * a.res], ys = [a.y0 - a.h * a.res, a.y0];
    const cs = [[xs[0], ys[0]], [xs[1], ys[0]], [xs[0], ys[1]], [xs[1], ys[1]]].map((p) => fwd.forward(p));
    const mx0 = Math.min(...cs.map((c) => c[0])), mx1 = Math.max(...cs.map((c) => c[0]));
    const my0 = Math.min(...cs.map((c) => c[1])), my1 = Math.max(...cs.map((c) => c[1]));
    const lat = mercLat((my0 + my1) / 2) * Math.PI / 180;
    const dm = Math.max(a.res / Math.cos(lat), Math.max(mx1 - mx0, my1 - my0) / 3600);
    const W = Math.ceil((mx1 - mx0) / dm), H = Math.ceil((my1 - my0) / dm);
    const B = 8, gx = Math.ceil(W / B) + 2, gy = Math.ceil(H / B) + 2;
    const E = new Float64Array(gx * gy), N = new Float64Array(gx * gy);
    for (let j = 0; j < gy; j++) for (let i = 0; i < gx; i++) {
      const p = inv.forward([mx0 + i * B * dm, my1 - j * B * dm]);
      E[j * gx + i] = p[0]; N[j * gx + i] = p[1];
    }
    const idx = new Int32Array(W * H);
    for (let y = 0; y < H; y++) {
      const j = Math.floor(y / B), fy = y / B - j;
      for (let x = 0; x < W; x++) {
        const i = Math.floor(x / B), fx = x / B - i;
        const o = j * gx + i;
        const e = (1 - fy) * ((1 - fx) * E[o] + fx * E[o + 1]) + fy * ((1 - fx) * E[o + gx] + fx * E[o + gx + 1]);
        const n = (1 - fy) * ((1 - fx) * N[o] + fx * N[o + 1]) + fy * ((1 - fx) * N[o + gx] + fx * N[o + gx + 1]);
        const c = Math.floor((e - a.x0) / a.res), r = Math.floor((a.y0 - n) / a.res);
        idx[y * W + x] = (c >= 0 && c < a.w && r >= 0 && r < a.h) ? r * a.w + c : -1;
      }
    }
    const mx1b = mx0 + W * dm, my0b = my1 - H * dm;
    return { W, H, idx, bounds: [[mercLat(my0b), mercLon(mx0)], [mercLat(my1), mercLon(mx1b)]] };
  }
  function renderPNG(a, arr, code) {
    const { W, H, idx } = a.display;
    const cv = document.createElement('canvas');
    cv.width = W; cv.height = H;
    const ctx = cv.getContext('2d');
    const im = ctx.createImageData(W, H);
    const d = im.data;
    for (let p = 0, y = 0; y < H; y++) {
      for (let x = 0; x < W; x++, p++) {
        const i = idx[p];
        if (i < 0) continue;
        const v = arr[i];
        if (!v) continue;
        let c = COLORS[v];
        const cd = code ? code[i] : 0;
        let r = c[0], g = c[1], b = c[2];
        if (cd > 0 && (cd === 1 ? ((x + y) >> 1) % 2 === 0 : cd === 2 ? (y >> 1) % 2 === 0 : (x >> 1) % 2 === 0)) { const f = FF[cd]; r = Math.trunc(r * f); g = Math.trunc(g * f); b = Math.trunc(b * f); }
        const o = p * 4;
        d[o] = r; d[o + 1] = g; d[o + 2] = b; d[o + 3] = 255;
      }
    }
    ctx.putImageData(im, 0, 0);
    return cv.toDataURL('image/png').split(',')[1];
  }

  // ------------------------------------------------------------------ edifici: rasterizzazione "all touched"
  function supercover(x0, y0, x1, y1, cb) {
    let cx = Math.floor(x0), cy = Math.floor(y0);
    const ex = Math.floor(x1), ey = Math.floor(y1);
    const dx = x1 - x0, dy = y1 - y0;
    const sx = dx > 0 ? 1 : -1, sy = dy > 0 ? 1 : -1;
    let tx = dx !== 0 ? ((dx > 0 ? cx + 1 : cx) - x0) / dx : Infinity;
    let ty = dy !== 0 ? ((dy > 0 ? cy + 1 : cy) - y0) / dy : Infinity;
    const tdx = dx !== 0 ? Math.abs(1 / dx) : Infinity, tdy = dy !== 0 ? Math.abs(1 / dy) : Infinity;
    cb(cx, cy);
    let guard = Math.abs(ex - cx) + Math.abs(ey - cy) + 4;
    while ((cx !== ex || cy !== ey) && guard-- > 0) {
      if (tx < ty) { cx += sx; tx += tdx; } else if (ty < tx) { cy += sy; ty += tdy; } else { cb(cx + sx, cy); cb(cx, cy + sy); cx += sx; cy += sy; tx += tdx; ty += tdy; }
      cb(cx, cy);
    }
  }
  function rasterize(polys, w, h) {                 // polys: [[ring,...], ...] con ring = [[col,row],...] in pixel
    const ids = new Int32Array(w * h);
    polys.forEach((rings, fi) => {
      const id = fi + 1;
      let ymin = Infinity, ymax = -Infinity, xmin = Infinity, xmax = -Infinity;
      for (const r of rings) for (const p of r) { if (p[0] < xmin) xmin = p[0]; if (p[0] > xmax) xmax = p[0]; if (p[1] < ymin) ymin = p[1]; if (p[1] > ymax) ymax = p[1]; }
      if (ymax < 0 || ymin > h || xmax < 0 || xmin > w) return;
      for (let row = Math.max(0, Math.floor(ymin)); row <= Math.min(h - 1, Math.floor(ymax)); row++) {
        const yc = row + 0.5, xsx = [];
        for (const r of rings) for (let i = 0, n = r.length, j = n - 1; i < n; j = i++) {
          const y1 = r[j][1], y2 = r[i][1];
          if ((y1 <= yc && y2 > yc) || (y2 <= yc && y1 > yc)) xsx.push(r[j][0] + (yc - y1) * (r[i][0] - r[j][0]) / (y2 - y1));
        }
        xsx.sort((p, q) => p - q);
        for (let k = 0; k + 1 < xsx.length; k += 2) {
          const c0 = Math.max(0, Math.ceil(xsx[k] - 0.5)), c1 = Math.min(w - 1, Math.ceil(xsx[k + 1] - 0.5) - 1);
          for (let c = c0; c <= c1; c++) ids[row * w + c] = id;
        }
      }
      for (const r of rings) for (let i = 1; i < r.length; i++) {
        supercover(r[i - 1][0], r[i - 1][1], r[i][0], r[i][1], (c, rr) => { if (c >= 0 && c < w && rr >= 0 && rr < h) ids[rr * w + c] = id; });
      }
    });
    return ids;
  }
  function polysToPixels(a, lonlatPolys) {           // [[ring lon/lat,...],...] -> pixel
    const f = proj4('EPSG:4326', a.def);
    return lonlatPolys.map((rings) => rings.map((ring) => ring.map((p) => { const q = f.forward([p[0], p[1]]); return [(q[0] - a.x0) / a.res, (a.y0 - q[1]) / a.res]; })));
  }
  function featuresToPolys(fc) {
    const out = [];
    for (const f of fc.features || []) {
      const g = f.geometry;
      if (!g) continue;
      if (g.type === 'Polygon') out.push(g.coordinates);
      else if (g.type === 'MultiPolygon') for (const p of g.coordinates) out.push(p);
    }
    return out;
  }
  async function readBuildings(file) {
    const name = file.name.toLowerCase();
    let gj;
    if (name.endsWith('.zip')) {
      let r = await shp(await file.arrayBuffer());
      if (Array.isArray(r)) r = { type: 'FeatureCollection', features: [].concat(...r.map((x) => x.features)) };
      gj = r;
    } else if (name.endsWith('.geojson') || name.endsWith('.json')) {
      gj = JSON.parse(await file.text());
    } else throw new Error('edifici: shapefile compresso (.zip) oppure GeoJSON (un GeoPackage va prima esportato in GeoJSON)');
    const polys = featuresToPolys(gj);
    if (!polys.length) throw new Error('il file non contiene poligoni');
    const p0 = polys[0][0][0];
    if (Math.abs(p0[0]) > 180 || Math.abs(p0[1]) > 90) throw new Error('le coordinate degli edifici non sono in gradi (EPSG:4326): per lo shapefile includi il file .prj nello zip; per il GeoJSON salva in EPSG:4326');
    return { gj, polys };
  }

  // ------------------------------------------------------------------ OpenStreetMap (Overpass)
  const OVERPASS = ['https://overpass.kumi.systems/api/interpreter', 'https://overpass-api.de/api/interpreter', 'https://overpass.private.coffee/api/interpreter'];
  async function overpass(query) {
    let last = null;
    for (let k = 0; k < 6; k++) {
      const ctl = new AbortController();
      const timer = setTimeout(() => ctl.abort(), 30000);              // un server che non risponde non blocca gli altri
      try {
        const r = await fetch(OVERPASS[k % OVERPASS.length], { method: 'POST', body: 'data=' + encodeURIComponent(query), headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, signal: ctl.signal });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return await r.json();
      } catch (e) { last = e; await new Promise((s) => setTimeout(s, Math.min(1500 * (k + 1), 8000))); }
      finally { clearTimeout(timer); }
    }
    throw new Error('Overpass non raggiungibile (' + last + '): riprova più tardi');
  }
  async function osmPolys(a) {
    const inv = proj4(a.def, 'EPSG:4326');
    const xs = [a.x0, a.x0 + a.w * a.res], ys = [a.y0 - a.h * a.res, a.y0];
    const ll = [[xs[0], ys[0]], [xs[1], ys[0]], [xs[0], ys[1]], [xs[1], ys[1]]].map((p) => inv.forward(p));
    const west = Math.min(...ll.map((p) => p[0])), east = Math.max(...ll.map((p) => p[0]));
    const south = Math.min(...ll.map((p) => p[1])), north = Math.max(...ll.map((p) => p[1]));
    const step = 0.05, ny = Math.max(1, Math.ceil((north - south) / step)), nx = Math.max(1, Math.ceil((east - west) / step));
    const seen = new Set(), polys = [];
    for (let iy = 0; iy < ny; iy++) for (let ix = 0; ix < nx; ix++) {
      busy('scarico gli edifici da OpenStreetMap: riquadro ' + (iy * nx + ix + 1) + '/' + (nx * ny) + '…');
      const s = south + iy * (north - south) / ny, n = south + (iy + 1) * (north - south) / ny;
      const wv = west + ix * (east - west) / nx, e = west + (ix + 1) * (east - west) / nx;
      const q = '[out:json][timeout:90];(way["building"](' + [s, wv, n, e].join(',') + ');relation["building"](' + [s, wv, n, e].join(',') + '););out geom;';
      const data = await overpass(q);
      for (const el of data.elements || []) {
        const key = el.type + el.id;
        if (seen.has(key)) continue;
        seen.add(key);
        const geoms = [];
        if (el.type === 'way' && el.geometry) geoms.push(el.geometry);
        else if (el.type === 'relation') for (const m of el.members || []) if (m.role === 'outer' && m.geometry) geoms.push(m.geometry);
        for (const g of geoms) {
          const r = g.map((p) => [p.lon, p.lat]);
          if (r.length >= 4 && r[0][0] === r[r.length - 1][0] && r[0][1] === r[r.length - 1][1]) polys.push([r]);
        }
      }
    }
    return polys;
  }
  async function ensureOsm(a) {
    if (a.bo) return;
    const polys = await osmPolys(a);
    a.bo = rasterize(polysToPixels(a, polys), a.w, a.h);
    a.osmCount = polys.length;
  }

  // ------------------------------------------------------------------ calcolo
  function parseQ(q) {
    const u = new URLSearchParams(q), g = (k) => u.get(k);
    return { case: g('case'), layer: g('layer'), bld: g('bld') === '1', bm: +g('bm') || 0, osm: +g('osm') || 0, holes: g('holes') === '1',
             area: +g('area'), hmode: g('hmode') || 'major', gap: Math.round(+g('gap') || 0), buf: g('buf') === '1', bufm: +g('bufm') || 0, hl: g('hl') === '1' };
  }
  let lastKey = null, lastRes = null;
  async function compute(q) {
    const P = parseQ(q);
    const a = areas[P.case];
    if (!a) throw new Error('area non caricata');
    const noHl = q.replace(/&?hl=\d/, '');
    if (lastKey === noHl && lastRes) return lastRes;
    if (P.bld && P.osm && !a.bo) await ensureOsm(a);
    busy('calcolo…');
    const pj = JSON.stringify({ bld: P.bld, bm: P.bm, holes: P.holes, area: P.area, all_holes: P.area >= 1e9, hmode: P.hmode, gap: P.gap, buf: P.buf, bufm: P.bufm });
    const r = await call({ type: 'process', h: a.h8, bu: a.bu, bo: a.bo, w: a.w, hh: a.h, res: a.res, params: pj, key: a.name + '|' + P.osm, osm: P.osm });
    lastKey = noHl; lastRes = { P, a, out: r.out, code: r.code, stats: r.stats, pj };
    return lastRes;
  }
  let running = false, nextJob = null;
  function process(q) {
    return new Promise((res) => {
      const start = async (qq, rr) => {
        running = true;
        try {
          const c = await compute(qq);
          const png = renderPNG(c.a, c.out, c.P.hl ? c.code : null);
          rr({ png, stats: c.stats });
        } catch (e) { rr({ error: String(e.message || e) }); }
        running = false; idle();
        if (nextJob) { const j = nextJob; nextJob = null; start(j.q, j.res); }
      };
      if (running) { if (nextJob) nextJob.res({ error: 'sostituita da una richiesta più recente' }); nextJob = { q, res }; } else start(q, res);
    });
  }

  // ------------------------------------------------------------------ GeoTIFF in scrittura (uint8, non compresso)
  function writeGeoTiff(arr, a, description) {
    const w = a.w, h = a.h;
    const rps = Math.max(1, Math.min(h, Math.floor(65536 / w)));
    const nstrips = Math.ceil(h / rps);
    const desc = new TextEncoder().encode(description + '\0');
    const nod = new TextEncoder().encode('0\0');
    const geokeys = [1, 1, 0, 3, 1024, 0, 1, 1, 1025, 0, 1, 1, 3072, 0, 1, a.epsg];
    const tags = [];                                    // {tag,type,count,value(bytes)|number}
    const T = { SHORT: 3, LONG: 4, ASCII: 2, DOUBLE: 12 };
    const ifdEntries = 15;
    const ifdSize = 2 + ifdEntries * 12 + 4;
    let off = 8 + ifdSize;
    const extra = [];                                   // blocchi dati esterni
    const place = (bytes) => { const o = off; extra.push([o, bytes]); off += bytes.length + (bytes.length % 2); return o; };
    const u16 = (arr2) => { const b = new Uint8Array(arr2.length * 2); const dv = new DataView(b.buffer); arr2.forEach((v, i) => dv.setUint16(i * 2, v, true)); return b; };
    const u32 = (arr2) => { const b = new Uint8Array(arr2.length * 4); const dv = new DataView(b.buffer); arr2.forEach((v, i) => dv.setUint32(i * 4, v, true)); return b; };
    const f64 = (arr2) => { const b = new Uint8Array(arr2.length * 8); const dv = new DataView(b.buffer); arr2.forEach((v, i) => dv.setFloat64(i * 8, v, true)); return b; };
    const entry = (tag, type, count, bytesOrNum) => tags.push({ tag, type, count, v: bytesOrNum });
    // dati dell'immagine
    const dataStart = off;
    const stripOff = [], stripCnt = [];
    let pos = dataStart;
    for (let s = 0; s < nstrips; s++) { const rows = Math.min(rps, h - s * rps); stripOff.push(pos); stripCnt.push(rows * w); pos += rows * w; }
    off = pos + (pos % 2);
    entry(256, T.LONG, 1, w); entry(257, T.LONG, 1, h); entry(258, T.SHORT, 1, 8); entry(259, T.SHORT, 1, 1); entry(262, T.SHORT, 1, 1);
    entry(270, T.ASCII, desc.length, desc.length > 4 ? place(desc) : desc);
    entry(273, T.LONG, nstrips, nstrips > 1 ? place(u32(stripOff)) : stripOff[0]);
    entry(277, T.SHORT, 1, 1); entry(278, T.LONG, 1, rps);
    entry(279, T.LONG, nstrips, nstrips > 1 ? place(u32(stripCnt)) : stripCnt[0]);
    entry(284, T.SHORT, 1, 1);
    entry(33550, T.DOUBLE, 3, place(f64([a.res, a.res, 0])));
    entry(33922, T.DOUBLE, 6, place(f64([0, 0, 0, a.x0, a.y0, 0])));
    entry(34735, T.SHORT, geokeys.length, place(u16(geokeys)));
    entry(42113, T.ASCII, nod.length, nod.length > 4 ? place(nod) : nod);
    if (tags.length !== ifdEntries) throw new Error('GeoTIFF: numero di tag inatteso');
    const total = off;
    const buf = new Uint8Array(total);
    const dv = new DataView(buf.buffer);
    buf[0] = 0x49; buf[1] = 0x49; dv.setUint16(2, 42, true); dv.setUint32(4, 8, true);
    dv.setUint16(8, ifdEntries, true);
    tags.forEach((t, i) => {
      const o = 10 + i * 12;
      dv.setUint16(o, t.tag, true); dv.setUint16(o + 2, t.type, true); dv.setUint32(o + 4, t.count, true);
      if (typeof t.v === 'number') { if (t.type === T.SHORT && t.count === 1) dv.setUint16(o + 8, t.v, true); else dv.setUint32(o + 8, t.v, true); }
      else if (t.v instanceof Uint8Array) { buf.set(t.v, o + 8); }
    });
    dv.setUint32(10 + ifdEntries * 12, 0, true);
    for (const [o, bytes] of extra) buf.set(bytes, o);
    buf.set(arr, dataStart);
    return new Blob([buf], { type: 'image/tiff' });
  }
  function download(blob, name) {
    const u = URL.createObjectURL(blob);
    const l = document.createElement('a');
    l.href = u; l.download = name; document.body.appendChild(l); l.click();
    setTimeout(() => { URL.revokeObjectURL(u); l.remove(); }, 1500);
  }
  const base = (n) => n.replace(/\.tiff?$/i, '');

  // ------------------------------------------------------------------ interfaccia verso la pagina (stessa del server)
  const backend = {
    vector: false,
    async version() { return { version: VERSION, upload: true, vector: false, openUpload: true }; },
    async info() {
      const D = {};
      for (const [name, a] of Object.entries(areas)) {
        if (!a.png) a.png = renderPNG(a, a.h8, null);
        D[name] = { layers: [{ name: a.layer, bounds: a.display.bounds, res: a.res, png: a.png }], buildings: a.gj || null, default: a.layer, bounds: a.display.bounds };
      }
      return D;
    },
    process,
    async exportRaster(q, clean) {
      busy('preparo il raster…');
      try {
        const c = await compute(q);
        const arr = clean ? c.out : c.out.map((v, i) => (c.code[i] > 0 ? v + 10 * c.code[i] : v));
        const codes = 'codes=0=nodata/zero;1-3=pericolo originale;1x=modificato da edifici;2x=da zone interne;3x=da buffer (x=livello 1-3)';
        const desc = 'HazardFill ' + VERSION + ' | source=' + c.a.layer + ' | params=' + c.pj + ' | ' + (clean ? 'codes=0=nodata/zero;1=basso;2=medio;3=alto' : codes);
        download(writeGeoTiff(arr instanceof Uint8Array ? arr : Uint8Array.from(arr), c.a, desc), base(c.a.layer) + (clean ? '_elaborata_pulita.tif' : '_elaborata_codici.tif'));
      } catch (e) { alert('Esportazione non riuscita: ' + (e.message || e)); }
      idle();
    },
    async exportStyle(name, clean) {
      const m = await call({ type: 'qml', clean: clean ? 1 : 0 });
      download(new Blob([m.text], { type: 'application/xml' }), name + (clean ? '_elaborata_pulita.qml' : '_elaborata_codici.qml'));
    },
    exportVector() { alert('Il vettoriale (GeoPackage) è disponibile nel plugin QGIS e nella versione locale della pagina.'); },
    async upload(kind, file, area) {
      try {
        busy('leggo ' + file.name + '…');
        if (kind === 'raster') {
          const a = await readGeoTiff(file);
          a.name = area; a.layer = file.name; a.bu = null; a.bo = null; a.gj = null; a.png = null;
          busy('preparo la visualizzazione…');
          await new Promise((r) => setTimeout(r, 20));
          a.display = buildDisplay(a);
          areas[area] = a; lastKey = null; lastRes = null;
          idle();
          return { ok: true, case: area, warnings: a.warnings, info: { width: a.w, height: a.h, res: +a.res.toFixed(4), crs: 'EPSG:' + a.epsg } };
        }
        const a = areas[area];
        if (!a) return { error: 'carica prima il GeoTIFF' };
        const { gj, polys } = await readBuildings(file);
        busy('rasterizzo gli edifici…');
        await new Promise((r) => setTimeout(r, 20));
        a.bu = rasterize(polysToPixels(a, polys), a.w, a.h);
        a.bo = null; lastKey = null; lastRes = null;
        const [[s, w0], [n, e]] = a.display.bounds;
        a.gj = { type: 'FeatureCollection', features: gj.features.filter((f) => { const g = f.geometry; if (!g) return false; const c = (g.type === 'Polygon' ? g.coordinates[0][0] : g.coordinates[0][0][0]); return c[0] >= w0 - 0.01 && c[0] <= e + 0.01 && c[1] >= s - 0.01 && c[1] <= n + 0.01; }).map((f) => ({ type: 'Feature', properties: {}, geometry: f.geometry })) };
        idle();
        return { ok: true, case: area, warnings: [], info: { features: polys.length } };
      } catch (e) { idle(); return { error: String(e.message || e) }; }
    },
    _areas: areas, _compute: compute,
  };
  window.HF_BACKEND = backend;

  // ------------------------------------------------------------------ esempio Spona_test
  document.addEventListener('DOMContentLoaded', () => {
    const go = $('upgo');
    if (!go) return;
    const sm = document.querySelector('#updet .box small');
    if (sm) sm.innerHTML = 'GeoTIFF a una banda, in CRS proiettato (metri), con le sole classi 0-3 (nodata = 0). Edifici (facoltativi): shapefile compresso .zip (con .prj) oppure GeoJSON in EPSG:4326. <b>Tutto il calcolo avviene nel tuo browser: i file non vengono inviati a nessun server.</b>';
    // il pulsante dell'esempio compare solo se i dati di prova sono presenti sul sito
    fetch('example/Mappa_Pericolo_Spona.tif', { method: 'HEAD' }).then(r => { if (r.ok) addExample(); }).catch(() => {});
    function addExample() {
    const b = document.createElement('button');
    b.id = 'upex'; b.textContent = 'Carica l\'esempio (Spona_test)'; b.style.marginLeft = '6px';
    go.parentNode.appendChild(b);
    b.onclick = async () => {
      b.disabled = true;
      const msg = $('upmsg'); msg.style.color = '#666'; msg.textContent = 'scarico l\'esempio…';
      try {
        const t = await (await fetch('example/Mappa_Pericolo_Spona.tif')).blob();
        const e = await (await fetch('example/Edifici.geojson')).blob();
        const r1 = await backend.upload('raster', new File([t], 'Mappa_Pericolo_Spona.tif'), 'Spona_test');
        if (r1.error) throw new Error(r1.error);
        const r2 = await backend.upload('buildings', new File([e], 'Edifici.geojson'), 'Spona_test');
        if (r2.error) throw new Error(r2.error);
        msg.textContent = 'preparo la mappa…';
        await window.loadInfo('Spona_test');
        msg.style.color = '#080'; msg.innerHTML = 'Spona_test caricato (dati di prova) ✔';
      } catch (err) { msg.style.color = '#b00'; msg.textContent = String(err.message || err); }
      b.disabled = false;
    };
    }
  });
})();
