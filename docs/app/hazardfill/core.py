# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
"""HazardFill - nucleo di calcolo (solo numpy + scipy, nessuna dipendenza GIS).

Condiviso tra il plugin QGIS e il server web di prova.
Convenzioni: raster di pericolo uint8 con 0 = nessun pericolo/nodata, 1 basso, 2 medio, 3 alto.
Codici di modifica nel raster esportato: livello + 10*passo  (passo 1 edifici, 2 zone interne, 3 buffer).
"""
import json
import os
import threading
import time
import urllib.parse
import urllib.request

import numpy as np
from scipy import ndimage as ndi

__version__ = "1.2.1"

COLORS = {1: (255, 235, 59), 2: (255, 140, 0), 3: (214, 40, 40)}
STEP_NAME = {1: "edifici", 2: "zone interne", 3: "buffer"}
LEVEL_NAME = {1: "basso", 2: "medio", 3: "alto"}


# ------------------------------------------------------------------ stili
def code_table(clean):
    """[(valore, (r,g,b,a), etichetta)]"""
    rows = [(0, (0, 0, 0, 0), "nodata / nessun pericolo")]
    for k in (1, 2, 3):
        rows.append((k, COLORS[k] + (255,), "%d pericolo %s" % (k, LEVEL_NAME[k]) + ("" if clean else " (originale)")))
    if not clean:
        for st, f in ((1, 0.72), (2, 0.55), (3, 0.38)):
            for k in (1, 2, 3):
                c = tuple(int(v * f) for v in COLORS[k])
                rows.append((10 * st + k, c + (255,), "%d %s (assegnato da %s)" % (10 * st + k, LEVEL_NAME[k], STEP_NAME[st])))
    return rows


def make_qml(clean):
    ent = "".join('<paletteEntry value="%d" color="#%02x%02x%02x" alpha="%d" label="%s"/>' % (v, c[0], c[1], c[2], c[3], l)
                  for v, c, l in code_table(clean))
    return ('<!DOCTYPE qgis PUBLIC "http://mrcc.com/qgis.dtd" "SYSTEM"><qgis version="3.28.0" styleCategories="AllStyleCategories">'
            '<pipe><rasterrenderer type="paletted" band="1" opacity="1" alphaBand="-1" nodataColor="">'
            '<rasterTransparency/><colorPalette>%s</colorPalette></rasterrenderer>'
            '<brightnesscontrast brightness="0" contrast="0" gamma="1"/><huesaturation colorizeOn="0" saturation="0" grayscaleMode="0"/>'
            '<rasterresampler maxOversampling="2"/></pipe><blendMode>0</blendMode></qgis>' % ent)


# ------------------------------------------------------------------ preparazione
def normalize_hazard(a):
    """Qualsiasi raster numerico -> uint8 0..3 (nodata, NaN e valori <0.5 diventano 0)."""
    a = np.nan_to_num(np.asarray(a, dtype=np.float64), nan=0, neginf=0, posinf=0)
    return np.where(a < 0.5, 0, np.rint(a)).clip(0, 3).astype(np.uint8)


# ------------------------------------------------------------------ edifici
def step_buildings(h, bid, npx):
    """Ogni edificio prende il valore max che lo tocca o entro npx pixel dal suo bordo."""
    if bid.max() == 0:
        return h, np.zeros_like(h, bool), 0
    inside = bid > 0
    dist, (iy, ix) = ndi.distance_transform_edt(~inside, return_indices=True)
    near = bid[iy, ix]
    zone = dist <= npx
    ids = np.arange(1, bid.max() + 1)
    mx = ndi.maximum(np.where(zone, h, 0), labels=np.where(zone, near, 0), index=ids)
    mx = np.concatenate([[0], np.asarray(mx, dtype=np.uint8)])
    newv = mx[bid]
    out = h.copy()
    out[inside] = np.maximum(h[inside], newv[inside])
    mod = out != h
    return out, mod, int(len(np.unique(bid[mod])))


def merge_building_ids(bid_user, bid_osm, min_overlap=0.2):
    """Integra gli edifici OSM in quelli forniti: un edificio OSM viene aggiunto solo se meno del
    `min_overlap` dei suoi pixel cade su edifici gia' presenti. Restituisce (ids, n_osm_aggiunti)."""
    if bid_osm is None or bid_osm.max() == 0:
        return bid_user, 0
    n = int(bid_osm.max())
    tot = np.bincount(bid_osm.ravel(), minlength=n + 1)
    ov = np.bincount(bid_osm[bid_user > 0], minlength=n + 1)
    keep = (tot > 0) & (ov < min_overlap * np.maximum(tot, 1))
    keep[0] = False
    add = keep[bid_osm] & (bid_user == 0)
    base = int(bid_user.max())
    new_id = np.zeros(n + 1, np.int32)
    new_id[keep] = base + 1 + np.arange(int(keep.sum()))
    out = bid_user.copy()
    out[add] = new_id[bid_osm[add]]
    return out, int(keep.sum())


# ------------------------------------------------------------------ OSM
OVERPASS = ["https://overpass.kumi.systems/api/interpreter",
            "https://overpass-api.de/api/interpreter",
            "https://overpass.private.coffee/api/interpreter"]


class Cancelled(Exception):
    """L'utente ha annullato l'operazione."""


def _sleep(seconds, is_canceled=None):
    end = time.time() + seconds
    while time.time() < end:
        if is_canceled and is_canceled():
            raise Cancelled()
        time.sleep(min(0.2, max(0.0, end - time.time())))


def _fetch_json(url, query, timeout, is_canceled=None):
    """Una richiesta POST in un thread separato: si puo' annullare subito e non dura mai piu' di ~1,5 x timeout."""
    box = {}

    def work():
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": query}).encode(),
                                         headers={"User-Agent": "HazardFill-QGIS/%s" % __version__, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                box["data"] = json.loads(r.read().decode("utf-8"))
        except Exception as e:                      # noqa: BLE001
            box["err"] = e

    th = threading.Thread(target=work, daemon=True)
    th.start()
    t0 = time.time()
    while th.is_alive():
        th.join(0.2)
        if is_canceled and is_canceled():
            raise Cancelled()
        if time.time() - t0 > timeout * 1.5:
            raise TimeoutError("nessuna risposta entro %d s" % int(timeout * 1.5))
    if "err" in box:
        raise box["err"]
    return box["data"]


def _overpass(query, tries=6, timeout=30, mirrors=None, is_canceled=None, log=None):
    """Interroga Overpass provando i server a turno: ogni richiesta ha un tempo massimo (`timeout`, secondi),
    un server che non risponde non blocca gli altri e `is_canceled()` permette di annullare subito."""
    mirrors = mirrors or OVERPASS
    last = None
    for k in range(tries):
        if is_canceled and is_canceled():
            raise Cancelled()
        url = mirrors[k % len(mirrors)]
        host = urllib.parse.urlparse(url).netloc
        if log:
            log("OSM: richiesta a %s (tentativo %d/%d, massimo %d s)..." % (host, k + 1, tries, timeout))
        try:
            return _fetch_json(url, query, timeout, is_canceled)
        except Cancelled:
            raise
        except Exception as e:           # server occupato / timeout: prossimo server dopo una breve attesa
            last = e
            if log:
                log("OSM: %s non risponde (%s)" % (host, str(e)[:80]))
            _sleep(min(1.5 * (k + 1), 6), is_canceled)
    raise RuntimeError("Overpass non raggiungibile (%s): riprova piu' tardi oppure fornisci gli edifici come shapefile/GeoPackage" % last)


def osm_buildings(south, west, north, east, cache_dir=None, step=0.05, log=None, is_canceled=None):
    """Poligoni degli edifici OSM nel bbox WGS84 -> lista di anelli [(lon, lat), ...].
    Interroga a riquadri di `step` gradi; cache su disco opzionale. Le relazioni multipoligono
    vengono usate solo per gli anelli esterni gia' chiusi (i cortili interni sono ignorati).
    `is_canceled` (facoltativo) e' una funzione che restituisce True se l'utente ha annullato (solleva Cancelled)."""
    rings, seen = [], set()
    ny = max(1, int(np.ceil((north - south) / step)))
    nx = max(1, int(np.ceil((east - west) / step)))
    for iy in range(ny):
        for ix in range(nx):
            if is_canceled and is_canceled():
                raise Cancelled()
            s, n = south + iy * (north - south) / ny, south + (iy + 1) * (north - south) / ny
            w, e = west + ix * (east - west) / nx, west + (ix + 1) * (east - west) / nx
            fn = os.path.join(cache_dir, "osm_%.5f_%.5f_%.5f_%.5f.json" % (s, w, n, e)) if cache_dir else None
            if fn and os.path.exists(fn):
                with open(fn, encoding="utf-8") as f:
                    data = json.load(f)
            else:
                if log:
                    log("OSM: riquadro %d/%d ..." % (iy * nx + ix + 1, nx * ny))
                q = ('[out:json][timeout:90];(way["building"](%f,%f,%f,%f);relation["building"](%f,%f,%f,%f););out geom;'
                     % (s, w, n, e, s, w, n, e))
                data = _overpass(q, is_canceled=is_canceled, log=log)
                if fn:
                    os.makedirs(cache_dir, exist_ok=True)
                    with open(fn, "w", encoding="utf-8") as f:
                        json.dump(data, f)
            for el in data.get("elements", []):
                key = (el["type"], el["id"])
                if key in seen:
                    continue
                seen.add(key)
                geoms = []
                if el["type"] == "way" and el.get("geometry"):
                    geoms.append(el["geometry"])
                elif el["type"] == "relation":
                    for m in el.get("members", []):
                        if m.get("role") == "outer" and m.get("geometry"):
                            geoms.append(m["geometry"])
                for g in geoms:
                    r = [(p["lon"], p["lat"]) for p in g]
                    if len(r) >= 4 and r[0] == r[-1]:
                        rings.append(r)
    return rings


# ------------------------------------------------------------------ zone interne
def _flood(mk, mask):
    """Espansione simultanea dei marcatori dentro `mask` (4-connessione, a fronte): equivale a un
    watershed su immagine piatta, senza dipendere da scikit-image."""
    H, W = mask.shape
    lab = np.where(mask, mk, 0).astype(np.int32).ravel()
    m = mask.ravel()
    front = np.flatnonzero(lab)
    offs = ((-W, lambda y, x: y > 0), (W, lambda y, x: y < H - 1),
            (-1, lambda y, x: x > 0), (1, lambda y, x: x < W - 1))
    while front.size:
        y, x = np.divmod(front, W)
        new = []
        for off, ok in offs:
            sel = ok(y, x)
            src = front[sel]
            cand = src + off
            go = m[cand] & (lab[cand] == 0)
            lab[cand[go]] = lab[src[go]]
            new.append(cand[go])
        front = np.unique(np.concatenate(new)) if new else front[:0]
    return lab.reshape(H, W)


def _interior_one(z, r):
    """Zone a 0 'interne' a UNA scala r (pixel). r=0: non collegate al bordo del raster.
    r>0: i varchi piu' stretti di 2r pixel contano come chiusi."""
    if r <= 0:
        lab, n = ndi.label(z)
        border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        return z & ~np.isin(lab, border[border > 0])
    d = ndi.distance_transform_edt(z)
    core = d > r
    lab, n = ndi.label(core)
    mk = lab.astype(np.int32)
    EXT = n + 1
    ext_ids = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist()) - {0}
    fr = np.zeros(z.shape, bool)
    fr[0] = fr[-1] = True
    fr[:, 0] = fr[:, -1] = True
    mk[fr & z & (mk == 0)] = EXT
    ext_ids.add(EXT)
    ws = _flood(mk, z)
    return z & ~np.isin(ws, list(ext_ids))


_SCALES = (0, 5, 10, 15, 30, 45, 60, 90, 120, 150)


def interior_mask(z, gap, cache=None, key=None):
    """Interno se sigillabile a QUALSIASI scala di varco <= gap (unione sulle scale)."""
    scales = sorted({r for r in _SCALES if r <= gap} | {int(gap)})
    out = np.zeros(z.shape, bool)
    for r in scales:
        k = (key, r)
        if cache is not None and key is not None and k in cache:
            m = cache[k]
        else:
            m = _interior_one(z, r)
            if cache is not None and key is not None:
                if len(cache) > 24:
                    cache.pop(next(iter(cache)))
                cache[k] = m
        out |= m
    return out


def step_holes(h, area_px, mode, gap_px=0, cache=None, key=None):
    """Chiude le zone interne (0) con area<=area_px (None = tutte). Valore: max / maggioranza del
    contorno ('max','major') oppure pixel valido piu' vicino ('near')."""
    z = h == 0
    inter = interior_mask(z, gap_px, cache, key)
    lab, n = ndi.label(inter)
    if n == 0:
        return h, np.zeros_like(z), 0
    area = np.bincount(lab.ravel(), minlength=n + 1)
    ok = (area <= area_px) if area_px is not None else np.ones(n + 1, bool)
    ok[0] = False
    if not ok.any():
        return h, np.zeros_like(z), 0
    cnt = np.zeros((4, n + 1), np.int64)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a = h[max(dy, 0):h.shape[0] + min(dy, 0), max(dx, 0):h.shape[1] + min(dx, 0)]
        l = lab[max(-dy, 0):h.shape[0] + min(-dy, 0), max(-dx, 0):h.shape[1] + min(-dx, 0)]
        m = (l > 0) & (a > 0)
        for k in (1, 2, 3):
            cnt[k] += np.bincount(l[m & (a == k)], minlength=n + 1)
    ok &= cnt[1:].sum(0) > 0
    mod = ok[lab] & inter
    out = h.copy()
    if mode == "near":
        _, (iy, ix) = ndi.distance_transform_edt(h == 0, return_indices=True)
        out[mod] = h[iy, ix][mod]
    else:
        val = cnt[1:].argmax(0) + 1 if mode == "major" else np.where(cnt[3] > 0, 3, np.where(cnt[2] > 0, 2, 1))
        out[mod] = np.where(ok, val, 0).astype(np.uint8)[lab[mod]]
    return out, mod, int(ok.sum())


def step_buffer(h, npx):
    """Fascia di npx pixel sulla classe 0 adiacente a pixel validi: valore del valido piu' vicino -1 (min 1)."""
    valid = h > 0
    if not valid.any():
        return h, np.zeros_like(valid), 0
    dist, (iy, ix) = ndi.distance_transform_edt(~valid, return_indices=True)
    new = np.maximum(h[iy, ix].astype(np.int16) - 1, 1).astype(np.uint8)
    mod = (~valid) & (dist <= npx)
    out = h.copy()
    out[mod] = new[mod]
    return out, mod, int(mod.sum())


DEFAULTS = dict(bld=True, bm=0.0, holes=True, area=10.0, all_holes=False, hmode="major", gap=0, buf=True, bufm=1.0)


def process(h, bid, res, p, cache=None, key=None):
    """Applica i passi in ordine. h: uint8 0..3, bid: id edifici (int32) o None, res: lato pixel (m).
    Ritorna (out, code, stats) con code = passo che ha modificato il pixel (0/1/2/3)."""
    given = p
    p = {**DEFAULTS, **p}
    if "bpx" in given and "bm" not in given:         # compatibilita': tolleranze date in pixel
        p["bm"] = given["bpx"] * res
    if "bufpx" in given and "bufm" not in given:
        p["bufm"] = given["bufpx"] * res
    bpx = int(round(p["bm"] / res))                  # metri -> pixel (arrotondati con la risoluzione del raster)
    bufpx = max(1, int(round(p["bufm"] / res))) if p["bufm"] > 0 else 0
    out = h.copy()
    code = np.zeros(h.shape, np.uint8)
    stats = dict(res=res, bld_px=bpx, buf_px_width=bufpx)
    if p["bld"] and bid is not None:
        out, mod, nb = step_buildings(out, bid, bpx)
        code[mod] = 1
        stats["bld_changed"], stats["bld_total"] = nb, int(bid.max())
    if p["holes"]:
        area_px = None if p["all_holes"] else max(1, int(round(p["area"] / res ** 2)))
        out, mod, nh = step_holes(out, area_px, p["hmode"], p["gap"], cache, (key, p["bld"], bpx))
        code[mod & (code == 0)] = 2
        stats["holes_closed"] = nh
    if p["buf"] and bufpx > 0:
        out, mod, nm = step_buffer(out, bufpx)
        code[mod & (code == 0)] = 3
        stats["buf_px"] = nm
    stats["orig"] = [int((h == k).sum()) for k in (0, 1, 2, 3)]
    stats["new"] = [int((out == k).sum()) for k in (0, 1, 2, 3)]
    stats["mod_by_step"] = [int((code == k).sum()) for k in (1, 2, 3)]
    stats["px_area"] = res ** 2
    return out, code, stats


def with_codes(out, code):
    return np.where(code > 0, out + 10 * code, out).astype(np.uint8)


# ------------------------------------------------------------------ export vettoriale (GeoPackage)
VECTOR_LAYERS = ("originale", "omogeneizzata", "mappa_con_codici", "modifiche")


def criterio_of(code):
    """Nome del criterio che ha assegnato il valore: 'originale' per i codici 0-3."""
    return "originale" if code < 10 else STEP_NAME.get(code // 10, "?")


def classe_of(code):
    return code % 10 if code >= 10 else code


HATCH_ANGLE = {1: 45, 2: 0, 3: 90}      # retino per criterio: edifici diagonale, zone interne orizzontale, buffer verticale


def make_vector_qml(field, clean=False):
    """Stile QGIS categorizzato (stessi colori del raster) per il campo `field` (codice o classe).
    Per i codici di modifica (11-33) si aggiunge un retino di linee che dipende dal criterio."""
    rows = [r for r in code_table(clean) if r[0] != 0]
    cats, syms = "", ""
    ddp = ('<data_defined_properties><Option type="Map"><Option name="name" value="" type="QString"/>'
           '<Option name="properties"/><Option name="type" value="collection" type="QString"/></Option></data_defined_properties>')
    for i, (v, c, l) in enumerate(rows):
        cats += '<category value="%d" label="%s" symbol="%d" render="true"/>' % (v, l, i)
        layers = ('<layer class="SimpleFill" enabled="1" locked="0" pass="0"><Option type="Map">'
                  '<Option name="color" value="%d,%d,%d,255" type="QString"/>'
                  '<Option name="outline_style" value="no" type="QString"/>'
                  '<Option name="style" value="solid" type="QString"/></Option></layer>') % (c[0], c[1], c[2])
        if v >= 10:
            d = tuple(int(x * 0.55) for x in c[:3])
            layers += ('<layer class="LinePatternFill" enabled="1" locked="0" pass="0"><Option type="Map">'
                       '<Option name="angle" value="%d" type="QString"/><Option name="clip_mode" value="during_render" type="QString"/>'
                       '<Option name="coordinate_reference" value="feature" type="QString"/>'
                       '<Option name="distance" value="1.1" type="QString"/><Option name="distance_unit" value="MM" type="QString"/>'
                       '</Option><symbol type="line" name="@%d@1" alpha="1" clip_to_extent="1" force_rhr="0">%s'
                       '<layer class="SimpleLine" enabled="1" locked="0" pass="0"><Option type="Map">'
                       '<Option name="line_color" value="%d,%d,%d,255" type="QString"/>'
                       '<Option name="line_width" value="0.2" type="QString"/><Option name="line_width_unit" value="MM" type="QString"/>'
                       '<Option name="capstyle" value="flat" type="QString"/></Option></layer></symbol></layer>'
                       ) % (HATCH_ANGLE[v // 10], i, ddp, d[0], d[1], d[2])
        syms += '<symbol type="fill" name="%d" alpha="1" clip_to_extent="1" force_rhr="0">%s%s</symbol>' % (i, ddp, layers)
    return ('<!DOCTYPE qgis PUBLIC "http://mrcc.com/qgis.dtd" "SYSTEM"><qgis version="3.28.0" styleCategories="Symbology">'
            '<renderer-v2 type="categorizedSymbol" attr="%s" forceraster="0" symbollevels="0" enableorderby="0">'
            '<categories>%s</categories><symbols>%s</symbols></renderer-v2></qgis>' % (field, cats, syms))


def vector_styles():
    """{nome livello: qml} per i quattro livelli del GeoPackage."""
    return {"originale": make_vector_qml("classe", True), "omogeneizzata": make_vector_qml("classe", True),
            "mappa_con_codici": make_vector_qml("codice", False), "modifiche": make_vector_qml("codice", False)}


def add_gpkg_styles(path, styles, geom_col="geom"):
    """Scrive gli stili nella tabella layer_styles del GeoPackage (formato QGIS: stile predefinito del livello)."""
    import sqlite3
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS layer_styles(id INTEGER PRIMARY KEY AUTOINCREMENT, f_table_catalog TEXT(256), "
                "f_table_schema TEXT(256), f_table_name TEXT(256), f_geometry_column TEXT(256), styleName TEXT(30), "
                "styleQML TEXT, styleSLD TEXT, useAsDefault BOOLEAN, description TEXT, owner TEXT(30), ui TEXT(30), "
                "update_time DATETIME DEFAULT CURRENT_TIMESTAMP)")
    for name, qml in styles.items():
        gc = con.execute("SELECT column_name FROM gpkg_geometry_columns WHERE table_name=?", (name,)).fetchone()
        con.execute("DELETE FROM layer_styles WHERE f_table_name=?", (name,))
        con.execute("INSERT INTO layer_styles(f_table_catalog,f_table_schema,f_table_name,f_geometry_column,styleName,styleQML,"
                    "styleSLD,useAsDefault,description) VALUES('','',?,?,?,?, '',1,'HazardFill')",
                    (name, gc[0] if gc else geom_col, name, qml))
    con.commit()
    con.close()


# ------------------------------------------------------------------ ricerca dei dati in una cartella
RASTER_EXT = (".tif", ".tiff")
VECTOR_EXT = (".shp", ".gpkg", ".geojson", ".json", ".zip")


def scan_folder(root, max_depth=4):
    """Cerca in una cartella (e sottocartelle) i raster di pericolosita' (.tif) e i vettoriali degli edifici
    (.shp, .gpkg, .geojson, .zip con shapefile). Restituisce {'rasters': [...], 'buildings': [...]} con percorsi
    completi; i file il cui percorso richiama gli edifici ('edific', 'building') sono messi in testa."""
    root = os.path.abspath(root)
    base = root.rstrip(os.sep).count(os.sep)
    rasters, vectors = [], []
    for d, dirs, files in os.walk(root):
        if d.rstrip(os.sep).count(os.sep) - base >= max_depth:
            dirs[:] = []
        for f in files:
            low = f.lower()
            full = os.path.join(d, f)
            if low.endswith(RASTER_EXT):
                rasters.append(full)
            elif low.endswith(VECTOR_EXT):
                vectors.append(full)

    def hinted(p):
        q = p.lower()
        return 0 if ("edific" in q or "building" in q) else 1
    return {"rasters": sorted(rasters), "buildings": sorted(vectors, key=lambda p: (hinted(p), p))}
