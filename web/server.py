# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
"""HazardFill (HF) - server web locale per elaborare e visualizzare le mappe di pericolosita'.
Avvio:  python server.py --data CARTELLA_DATI [--port 8765] [indirizzi ...]      ->  http://localhost:8765
Dati attesi: CARTELLA_DATI/<area>/**/*.tif  (+ CARTELLA_DATI/<area>/Edifici/*.shp, facoltativo).
Codici nel raster 'con codici': classe + 10*criterio  (1 edifici, 2 zone interne, 3 buffer)
"""
import base64, glob, io, json, os, re, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

_here = os.path.dirname(os.path.abspath(__file__))
for _cand in (os.path.join(_here, "hazardfill"), os.path.join(_here, "..", "plugin", "hazardfill")):
    if os.path.exists(os.path.join(_cand, "core.py")):
        sys.path.insert(0, _cand)
        break
import core
import numpy as np
import rasterio
import rasterio.features
import geopandas as gpd
from scipy import ndimage as ndi
from PIL import Image
from pyproj import Transformer

ROOTS = []                  # [(cartella, suffisso)] valorizzato dalla riga di comando (--data)
WORKSPACE = None            # cartella dei dati caricati dalla pagina (una sottocartella per area)
UPLOAD = True               # caricamento di GeoTIFF ed edifici dalla pagina (--no-upload per disattivarlo)
MAX_RASTER = 3 * 1024 ** 3  # byte
MAX_BUILDINGS = 400 * 1024 ** 2
BLD_EXT = (".shp", ".gpkg", ".geojson", ".json")
HERE = os.path.dirname(os.path.abspath(__file__))
COLORS = {1: (255, 235, 59), 2: (255, 140, 0), 3: (214, 40, 40)}  # basso/medio/alto

CASES = {}

STEP_NAME = {1: "edifici", 2: "zone interne", 3: "buffer"}
LEVEL_NAME = {1: "basso", 2: "medio", 3: "alto"}


code_table, make_qml = core.code_table, core.make_qml




def discover():
    CASES.clear()
    for root, suffix in ROOTS:
        if not os.path.isdir(root):
            continue
        for case in sorted(os.listdir(root)):
            cdir = os.path.join(root, case)
            if not os.path.isdir(cdir):
                continue
            tifs = sorted(f for f in glob.glob(os.path.join(cdir, "**", "*"), recursive=True) if f.lower().endswith((".tif", ".tiff")))
            blds = [f for e in BLD_EXT for f in sorted(glob.glob(os.path.join(cdir, "Edifici", "*" + e)))]
            if not tifs:
                continue
            layers = {os.path.relpath(t, cdir).replace("\\", "/"): t for t in tifs}
            CASES[case + suffix] = dict(layers=layers, buildings=blds[0] if blds else None)


_cache = {}
_lock = threading.Lock()


def load_layer(path):
    with _lock:
        if path in _cache:
            return _cache[path]
        with rasterio.open(path) as r:
            a = r.read(1).astype(np.float32)
            meta = dict(transform=r.transform, crs=r.crs, shape=r.shape, res=r.res[0], bounds=r.bounds)
        a = np.nan_to_num(a, nan=0, neginf=0, posinf=0)
        a = np.where(a < 0.5, 0, np.rint(a)).clip(0, 3).astype(np.uint8)  # nodata (-9999, -3e38) assimilato a 0
        _cache[path] = (a, meta)
        return _cache[path]


def building_ids(case, meta, osm=0):
    """osm: 0 = solo edifici forniti, 1 = forniti + integrazione OSM, 2 = solo OSM."""
    key = ("bld", case, meta["shape"], meta["transform"], osm)
    with _lock:
        if key in _cache:
            return _cache[key]
    shp = CASES[case]["buildings"]
    user = np.zeros(meta["shape"], np.int32)
    if shp and osm != 2:
        g = gpd.read_file(shp).to_crs(meta["crs"])
        shapes = [(geom, i + 1) for i, geom in enumerate(g.geometry) if geom is not None and not geom.is_empty]
        user = rasterio.features.rasterize(shapes, out_shape=meta["shape"], transform=meta["transform"],
                                           fill=0, dtype="int32", all_touched=True)
    out = user
    if osm:
        from shapely.geometry import Polygon
        b = meta["bounds"]
        t = Transformer.from_crs(meta["crs"], 4326, always_xy=True)
        xs, ys = t.transform([b.left, b.right, b.left, b.right], [b.bottom, b.bottom, b.top, b.top])
        rings = core.osm_buildings(min(ys), min(xs), max(ys), max(xs), cache_dir=os.path.join(HERE, "osm_cache"))
        t2 = Transformer.from_crs(4326, meta["crs"], always_xy=True)
        shapes = []
        for i, r in enumerate(rings):
            X, Y = t2.transform([p[0] for p in r], [p[1] for p in r])
            shapes.append((Polygon(list(zip(X, Y))).buffer(0), i + 1))
        shapes = [(g, v) for g, v in shapes if not g.is_empty]
        bo = rasterio.features.rasterize(shapes, out_shape=meta["shape"], transform=meta["transform"],
                                         fill=0, dtype="int32", all_touched=True)
        out, nadd = core.merge_building_ids(user, bo)
        print("OSM: %d edifici nel riquadro, %d aggiunti" % (len(shapes), nadd), flush=True)
    with _lock:
        _cache[key] = out
    return out


# ----------------------------------------------------------------- criteri (in core.py)
_icache = {}


def process(case, layer, p):
    path = CASES[case]["layers"][layer]
    h, meta = load_layer(path)
    bid = building_ids(case, meta, p.get("osm", 0)) if p["bld"] else None
    return core.process(h, bid, meta["res"], dict(p, all_holes=p["area"] >= 1e9), cache=_icache,
                        key=(layer, p.get("osm", 0)))


def export_vector(case, layer, p):
    """GeoPackage con 4 livelli: originale, omogeneizzata, mappa_con_codici, modifiche (stessi codici del raster)."""
    import tempfile
    from shapely.geometry import shape
    from shapely import make_valid
    out, code, stats = process(case, layer, p)
    h, meta = load_layer(CASES[case]["layers"][layer])
    codes = core.with_codes(out, code)

    def to_gdf(arr, with_codes_cols):
        recs = []
        for geom, v in rasterio.features.shapes(arr, mask=arr > 0, transform=meta["transform"], connectivity=4):
            g = shape(geom)
            if not g.is_valid:
                g = make_valid(g)
            v = int(v)
            r = {"classe": core.classe_of(v), "area_m2": round(g.area, 3), "geometry": g}
            if with_codes_cols:
                r = {"codice": v, "classe": core.classe_of(v), "criterio": core.criterio_of(v), "area_m2": round(g.area, 3), "geometry": g}
            recs.append(r)
        cols = ["codice", "classe", "criterio", "area_m2", "geometry"] if with_codes_cols else ["classe", "area_m2", "geometry"]
        return gpd.GeoDataFrame(recs, columns=cols, geometry="geometry", crs=meta["crs"])

    layers = {"originale": to_gdf(h, False), "omogeneizzata": to_gdf(out, False)}
    cod = to_gdf(codes, True)
    layers["mappa_con_codici"] = cod
    layers["modifiche"] = cod[cod["codice"] >= 10].copy()
    fd, path = tempfile.mkstemp(suffix=".gpkg")
    os.close(fd)
    os.remove(path)
    for i, (name, gdf) in enumerate(layers.items()):
        gdf.to_file(path, layer=name, driver="GPKG", mode="w" if i == 0 else "a")
    core.add_gpkg_styles(path, core.vector_styles())
    with open(path, "rb") as f:
        body = f.read()
    os.remove(path)
    info = {k: len(v) for k, v in layers.items()}
    print("export vettoriale:", info, flush=True)
    return body



from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.crs import CRS
_wcache = {}


def warp_grid(meta):
    key = (meta["shape"], meta["transform"])
    if key not in _wcache:
        h, w = meta["shape"]
        lat = np.radians(46.0)
        res = meta["res"] / np.cos(lat)          # stesso dettaglio a terra in Web Mercator
        tr, dw, dh = calculate_default_transform(meta["crs"], CRS.from_epsg(3857), w, h,
                                                 *meta["bounds"], resolution=res)
        _wcache[key] = (tr, dh, dw)
    return _wcache[key]


def warp(arr, meta):
    tr, dh, dw = warp_grid(meta)
    dst = np.zeros((dh, dw), np.uint8)
    reproject(arr, dst, src_transform=meta["transform"], src_crs=meta["crs"],
              dst_transform=tr, dst_crs=CRS.from_epsg(3857), resampling=Resampling.nearest,
              src_nodata=None, dst_nodata=0)
    return dst


def to_png(arr, code=None, hilite=False, meta=None):
    if meta is not None:
        arr = warp(arr, meta)
        if code is not None:
            code = warp(code, meta)
    rgba = np.zeros(arr.shape + (4,), np.uint8)
    for k, c in COLORS.items():
        m = arr == k
        rgba[m, :3] = c
        rgba[m, 3] = 255
    if hilite and code is not None:
        yy, xx = np.indices(arr.shape)
        stripes = {1: ((yy + xx) // 2) % 2 == 0,                 # edifici: diagonale
                   2: (yy // 2) % 2 == 0,                         # zone interne: orizzontale
                   3: (xx // 2) % 2 == 0}                         # buffer: verticale
        for st, f in ((1, 0.72), (2, 0.55), (3, 0.38)):          # stessi colori dello stile QGIS
            for k in (1, 2, 3):
                m = (code == st) & (arr == k) & stripes[st]
                rgba[m, :3] = tuple(int(v * f) for v in COLORS[k])
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "PNG", optimize=False, compress_level=3)
    return base64.b64encode(buf.getvalue()).decode()


def latlon_bounds(meta):
    # estensione della griglia Web Mercator di visualizzazione (esatta per Leaflet)
    tr, dh, dw = warp_grid(meta)
    t = Transformer.from_crs(3857, 4326, always_xy=True)
    x0, y1 = tr * (0, 0); x1, y0 = tr * (dw, dh)
    lo0, la0 = t.transform(x0, y0); lo1, la1 = t.transform(x1, y1)
    return [[la0, lo0], [la1, lo1]]


def info_case(case):
    c = CASES[case]
    layers = []
    for name, path in c["layers"].items():
        h, meta = load_layer(path)
        layers.append(dict(name=name, bounds=latlon_bounds(meta), res=meta["res"], png=to_png(h, meta=meta)))
    gj = None
    if c["buildings"]:
        g = gpd.read_file(c["buildings"]).to_crs(4326)
        lb = [l["bounds"] for l in layers]
        bb = [[min(b[0][0] for b in lb), min(b[0][1] for b in lb)], [max(b[1][0] for b in lb), max(b[1][1] for b in lb)]]
        g = g.cx[bb[0][1]:bb[1][1], bb[0][0]:bb[1][0]]   # edifici nell'unione delle estensioni dei layer
        gj = json.loads(g[["geometry"]].to_json())
    default = "Mappa_Pericolo_V1.tif" if "Mappa_Pericolo_V1.tif" in c["layers"] else next(iter(c["layers"]))
    return dict(layers=layers, buildings=gj, default=default, bounds=layers[0]["bounds"])


_info_cases = {}
_lock2 = threading.Lock()


def INFO():
    """JSON con tutte le aree; ogni area e' calcolata una volta sola e tenuta in cache."""
    with _lock2:
        parts = []
        for case in list(CASES):
            if case not in _info_cases:
                _info_cases[case] = json.dumps(info_case(case))
            parts.append(json.dumps(case) + ":" + _info_cases[case])
        return ("{" + ",".join(parts) + "}").encode()


def reset_caches():
    with _lock:
        _cache.clear()
    _icache.clear()
    _wcache.clear()
    with _lock2:
        _info_cases.clear()


def _safe(name, default="file", maxlen=80):
    n = re.sub(r"[^\w.\- ()+]", "_", os.path.basename(name or "")).strip(" .")
    return (n or default)[:maxlen]


def receive_upload(handler, q):
    """Riceve un file (corpo della richiesta) in streaming e lo salva nella cartella dei dati caricati.
    kind=raster: GeoTIFF a una banda in CRS proiettato; kind=buildings: .zip (shapefile), .gpkg, .geojson."""
    import zipfile
    import shutil
    kind = q.get("kind", "")
    n = int(handler.headers.get("Content-Length", 0))
    name = _safe(q.get("name"), "file")
    area = _safe(q.get("area") or os.path.splitext(name)[0], "area")
    ext = os.path.splitext(name)[1].lower()
    if kind == "raster":
        if ext not in (".tif", ".tiff"):
            return dict(error="Il raster deve essere un GeoTIFF (.tif)")
        if n > MAX_RASTER:
            return dict(error="File troppo grande (massimo %d GB)" % (MAX_RASTER // 1024 ** 3))
        dest_dir = os.path.join(WORKSPACE, area)
    elif kind == "buildings":
        if ext not in (".zip", ".gpkg", ".geojson", ".json"):
            return dict(error="Edifici: shapefile compresso (.zip), GeoPackage (.gpkg) o GeoJSON")
        if n > MAX_BUILDINGS:
            return dict(error="File troppo grande (massimo %d MB)" % (MAX_BUILDINGS // 1024 ** 2))
        dest_dir = os.path.join(WORKSPACE, area, "Edifici")
    else:
        return dict(error="tipo di caricamento non valido")
    os.makedirs(dest_dir, exist_ok=True)
    tmp = os.path.join(dest_dir, "_in_arrivo" + ext)
    left = n
    with open(tmp, "wb") as f:
        while left > 0:
            chunk = handler.rfile.read(min(1 << 20, left))
            if not chunk:
                break
            f.write(chunk)
            left -= len(chunk)
    if left:
        os.remove(tmp)
        return dict(error="caricamento interrotto")
    warn = []
    try:
        if kind == "raster":
            with rasterio.open(tmp) as r:
                if r.crs is None or not r.crs.is_projected:
                    raise ValueError("il raster deve essere in un sistema di coordinate proiettato in metri (non in gradi): riproiettalo prima del caricamento")
                if r.transform.b != 0 or r.transform.d != 0:
                    raise ValueError("il raster deve avere la griglia con il nord in alto, senza rotazione")
                if r.count > 1:
                    warn.append("il raster ha %d bande: si usa la prima" % r.count)
                a = r.read(1)
                vals = np.unique(a[np.isfinite(a)])
                info = dict(width=r.width, height=r.height, res=round(r.res[0], 4), crs=str(r.crs.to_string()))
            extra = [float(v) for v in vals if v >= 0.5 and (abs(v - round(v)) > 1e-6 or v > 3)]
            if extra:
                warn.append("valori diversi da 0-3 (es. %s): i non interi sono arrotondati e i valori >3 portati a 3; se la mappa usa altri codici riclassificala prima" % ", ".join("%g" % v for v in extra[:6]))
            dest = os.path.join(dest_dir, name if ext in (".tif", ".tiff") else name + ".tif")
            if os.path.exists(dest):
                os.remove(dest)
            os.replace(tmp, dest)
        else:
            if ext == ".zip":
                for old in glob.glob(os.path.join(dest_dir, "*")):
                    if os.path.isfile(old) and not old.endswith("_in_arrivo.zip"):
                        os.remove(old)
                with zipfile.ZipFile(tmp) as z:
                    for m in z.infolist():
                        base = _safe(m.filename)
                        if base.lower().endswith((".shp", ".shx", ".dbf", ".prj", ".cpg", ".qix")) and m.file_size < 400 * 1024 ** 2:
                            with z.open(m) as src, open(os.path.join(dest_dir, base), "wb") as out:
                                shutil.copyfileobj(src, out)
                os.remove(tmp)
                shp = glob.glob(os.path.join(dest_dir, "*.shp"))
                if not shp:
                    raise ValueError("nello zip non c'e' nessuno shapefile (.shp)")
                path = shp[0]
            else:
                for old in glob.glob(os.path.join(dest_dir, "*")):
                    if os.path.isfile(old) and not old.endswith("_in_arrivo" + ext):
                        os.remove(old)
                path = os.path.join(dest_dir, name)
                os.replace(tmp, path)
            g = gpd.read_file(path)
            if g.crs is None:
                raise ValueError("gli edifici non hanno un sistema di coordinate (file .prj mancante?)")
            gt = g.geometry.geom_type.value_counts()
            if not any("Polygon" in t for t in gt.index):
                raise ValueError("il layer degli edifici deve contenere poligoni")
            info = dict(features=int(len(g)), crs=str(g.crs.to_string()))
            if (~g.geometry.is_valid).any():
                warn.append("%d edifici con geometria non valida: vengono rasterizzati comunque" % int((~g.geometry.is_valid).sum()))
    except Exception as e:
        for f in glob.glob(os.path.join(dest_dir, "_in_arrivo*")):
            os.remove(f)
        if kind == "raster" and not glob.glob(os.path.join(dest_dir, "*")):
            os.rmdir(dest_dir)
        return dict(error=str(e))
    reset_caches()
    discover()
    suffix = [sf for r, sf in ROOTS if os.path.abspath(r) == os.path.abspath(WORKSPACE)]
    return dict(ok=True, area=area, case=area + (suffix[0] if suffix else ""), warnings=warn, info=info)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        u = urlparse(self.path)
        try:
            if u.path == "/api/upload_data":
                if not UPLOAD or WORKSPACE is None:
                    return self._send(403, json.dumps(dict(error="caricamento disattivato")).encode(), "application/json")
                q = {k: v[0] for k, v in parse_qs(u.query).items()}
                return self._send(200, json.dumps(receive_upload(self, q)).encode(), "application/json")
            self._send(404, b"not found", "text/plain")
        except Exception as e:
            self._send(500, json.dumps(dict(error=str(e))).encode(), "application/json")

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                with open(os.path.join(HERE, "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if u.path.startswith("/tile/eox/"):          # proxy tile Sentinel-2 EOX (il server originale non invia CORS)
                z, y, x = u.path[len("/tile/eox/"):].replace(".jpg", "").split("/")
                key = ("eox", z, y, x)
                with _lock:
                    body = _cache.get(key)
                if body is None:
                    import urllib.request
                    url = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/g/%d/%d/%d.jpg" % (int(z), int(y), int(x))
                    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "HazardFill-test"}), timeout=20) as r:
                        body = r.read()
                    with _lock:
                        _cache[key] = body
                return self._send(200, body, "image/jpeg")
            if u.path == "/api/version":
                return self._send(200, json.dumps(dict(version=core.__version__, upload=bool(UPLOAD and WORKSPACE))).encode(), "application/json")
            if u.path == "/logo.svg":
                with open(os.path.join(os.path.dirname(core.__file__), "icon.svg"), "rb") as f:
                    return self._send(200, f.read(), "image/svg+xml")
            if u.path in ("/help", "/manuale"):
                with open(os.path.join(os.path.dirname(core.__file__), "help", "help_utilizzo.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if u.path == "/api/info":
                return self._send(200, INFO(), "application/json")
            if u.path == "/api/style":
                clean = q.get("clean") == "1"
                body = make_qml(clean).encode("utf-8")
                name = q.get("name", "stile") + ("_elaborata_pulita.qml" if clean else "_elaborata_codici.qml")
                self.send_response(200)
                self.send_header("Content-Type", "application/xml")
                self.send_header("Content-Disposition", 'attachment; filename="%s"' % name)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if u.path == "/api/export_vector":
                p = dict(bld=q.get("bld") == "1", bm=float(q.get("bm", 0)),
                         holes=q.get("holes") == "1", area=float(q.get("area", 10)), hmode=q.get("hmode", "major"),
                         gap=int(q.get("gap", 0)), osm=int(q.get("osm", 0)),
                         buf=q.get("buf") == "1", bufm=float(q.get("bufm", 1)))
                body = export_vector(q["case"], q["layer"], p)
                name = os.path.splitext(os.path.basename(q["layer"]))[0] + "_elaborata_vettoriale.gpkg"
                self.send_response(200)
                self.send_header("Content-Type", "application/geopackage+sqlite3")
                self.send_header("Content-Disposition", 'attachment; filename="%s"' % name)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if u.path == "/api/export":
                from rasterio.io import MemoryFile
                p = dict(bld=q.get("bld") == "1", bm=float(q.get("bm", 0)),
                         holes=q.get("holes") == "1", area=float(q.get("area", 10)), hmode=q.get("hmode", "major"),
                         gap=int(q.get("gap", 0)), osm=int(q.get("osm", 0)),
                         buf=q.get("buf") == "1", bufm=float(q.get("bufm", 1)))
                out, code, stats = process(q["case"], q["layer"], p)
                _, meta = load_layer(CASES[q["case"]]["layers"][q["layer"]])
                clean = q.get("clean") == "1"
                arr = out if clean else np.where(code > 0, out + 10 * code, out).astype(np.uint8)
                tags = dict(source=q["layer"], case=q["case"], params=json.dumps({k: p[k] for k in p}),
                            codes="0=nodata/zero;1-3=pericolo originale;1x=modificato da edifici;2x=da zone interne;3x=da buffer (x=livello 1-3)"
                                  if not clean else "0=nodata/zero;1=basso;2=medio;3=alto (elaborato, senza codici di modifica)")
                with MemoryFile() as mf:
                    with mf.open(driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1, dtype="uint8",
                                 crs=meta["crs"], transform=meta["transform"], compress="lzw", nodata=0) as dst:
                        dst.write(arr, 1)
                        pass   # niente tavolozza incorporata (256 voci nere in QGIS): i colori sono nello .qml   # tavolozza incorporata: QGIS la legge da solo
                        dst.update_tags(**tags)
                    body = mf.read()
                name = os.path.splitext(os.path.basename(q["layer"]))[0] + ("_elaborata_pulita.tif" if clean else "_elaborata_codici.tif")
                self.send_response(200)
                self.send_header("Content-Type", "image/tiff")
                self.send_header("Content-Disposition", 'attachment; filename="%s"' % name)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if u.path == "/api/process":
                p = dict(bld=q.get("bld") == "1", bm=float(q.get("bm", 0)),
                         holes=q.get("holes") == "1", area=float(q.get("area", 10)), hmode=q.get("hmode", "major"), gap=int(q.get("gap", 0)), osm=int(q.get("osm", 0)),
                         buf=q.get("buf") == "1", bufm=float(q.get("bufm", 1)))
                out, code, stats = process(q["case"], q["layer"], p)
                body = json.dumps(dict(png=to_png(out, code, q.get("hl") == "1", meta=load_layer(CASES[q["case"]]["layers"][q["layer"]])[1]), stats=stats)).encode()
                return self._send(200, body, "application/json")
            self._send(404, b"not found", "text/plain")
        except Exception as e:
            import traceback; traceback.print_exc()
            self._send(500, json.dumps(dict(error=str(e))).encode(), "application/json")


def parse_args(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="HazardFill (HF) - server web locale")
    ap.add_argument("hosts", nargs="*", help="indirizzi aggiuntivi su cui ascoltare (es. IP ZeroTier); 127.0.0.1 e' sempre incluso")
    ap.add_argument("--data", action="append", default=[], metavar="CARTELLA[=suffisso]",
                    help="cartella con le aree (una sottocartella per area); ripetibile; opzionale suffisso del nome, es. --data prove=' (test)'")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--workspace", default=None, metavar="CARTELLA", help="dove salvare i dati caricati dalla pagina (predefinita: ./caricati)")
    ap.add_argument("--no-upload", action="store_true", help="disattiva il caricamento di GeoTIFF ed edifici dalla pagina")
    return ap.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    UPLOAD = not args.no_upload
    for d in args.data:
        path, _, suffix = d.partition("=")
        ROOTS.append((os.path.abspath(path), suffix))
    if UPLOAD:
        WORKSPACE = os.path.abspath(args.workspace or os.path.join(HERE, "caricati"))
        os.makedirs(WORKSPACE, exist_ok=True)
        ROOTS.append((WORKSPACE, " (caricati)"))
    if not [r for r in ROOTS if r[0] != WORKSPACE]:      # nessun --data: ./dati oppure, nel repository, gli esempi
        for cand in (os.path.join(HERE, "dati"), os.path.join(HERE, "..", "examples")):
            if os.path.isdir(cand):
                ROOTS.append((os.path.abspath(cand), ""))
    discover()
    if not CASES and not UPLOAD:
        print("Nessuna area trovata. Indicare la cartella dei dati con --data CARTELLA (una sottocartella per area, con i .tif e, se ci sono, Edifici/*.shp).", flush=True)
        sys.exit(1)
    if not CASES:
        print("Nessuna area ancora presente: carica un GeoTIFF dalla pagina (oppure indica --data CARTELLA).", flush=True)
    print("HazardFill %s - aree:" % core.__version__, {k: len(v["layers"]) for k, v in CASES.items()}, "| caricamento:", "attivo" if UPLOAD else "disattivato", flush=True)
    threading.Thread(target=INFO, daemon=True).start()   # pre-calcolo layer all'avvio
    hosts = ["127.0.0.1"] + [a for a in args.hosts if a != "127.0.0.1"]   # es. indirizzi ZeroTier
    servers = []
    for hst in hosts:
        try:
            servers.append(ThreadingHTTPServer((hst, args.port), H))
            print("in ascolto su http://%s:%d" % (hst, args.port), flush=True)
        except OSError as e:
            print("non riesco ad ascoltare su", hst, e, flush=True)
    if not servers:
        sys.exit(1)
    for sv in servers[1:]:
        threading.Thread(target=sv.serve_forever, daemon=True).start()
    servers[0].serve_forever()
