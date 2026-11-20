"""Test di integrazione del server web: avvia il server sui dati di esempio e prova gli endpoint."""
import glob
import io
import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer

import pytest

rasterio = pytest.importorskip("rasterio")
gpd = pytest.importorskip("geopandas")
pytest.importorskip("pyogrio")

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "web"))
import server  # noqa: E402

EXAMPLE = os.path.join(ROOT, "examples")


@pytest.fixture(scope="module")
def base():
    ws = tempfile.mkdtemp(prefix="hf_ws_")
    server.ROOTS[:] = [(EXAMPLE, ""), (ws, " (caricati)")]
    server.WORKSPACE, server.UPLOAD = ws, True
    server.discover()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:%d" % srv.server_address[1]
    srv.shutdown()


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=300) as r:
        return r.status, r.read(), r.headers


def post(base, path, data):
    req = urllib.request.Request(base + path, data=data, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=300).read())


PARAMS = dict(case="Figna_test", layer="Mappa_Pericolo_V1.tif", bld=1, bm=0, osm=0, holes=1, area=10000, gap=30, hmode="major", buf=1, bufm=1)


def test_basic_pages(base):
    assert get(base, "/")[0] == 200
    assert b"Help" in get(base, "/help")[1]
    assert get(base, "/logo.svg")[2]["Content-Type"] == "image/svg+xml"
    v = json.loads(get(base, "/api/version")[1])
    assert v["version"] and v["upload"] is True


def test_dev_endpoints_are_gone(base):
    for p in ("/upload",):
        with pytest.raises(urllib.error.HTTPError) as e:
            get(base, p)
        assert e.value.code == 404


def test_auxiliary_files_are_not_rasters(base):
    aux = os.path.join(EXAMPLE, "Figna_test", "Mappa_Pericolo_V1.tif.aux.xml")
    open(aux, "w").write("<PAMDataset/>")
    try:
        server.discover()
        assert list(server.CASES["Figna_test"]["layers"]) == ["Mappa_Pericolo_V1.tif"]
    finally:
        os.remove(aux)
        server.discover()


def test_info_and_process(base):
    info = json.loads(get(base, "/api/info")[1])
    assert "Figna_test" in info and info["Figna_test"]["buildings"]
    d = json.loads(get(base, "/api/process?" + urllib.parse.urlencode(dict(PARAMS, hl=1)))[1])
    st = d["stats"]
    assert d["png"] and st["bld_total"] > 0 and sum(st["mod_by_step"]) > 0
    assert st["new"][0] < st["orig"][0]                    # i riempimenti riducono i pixel a 0


def test_export_raster_codes_and_clean(base):
    q = urllib.parse.urlencode(PARAMS)
    codes = get(base, "/api/export?" + q)[1]
    clean = get(base, "/api/export?" + q + "&clean=1")[1]
    with rasterio.MemoryFile(codes) as m, m.open() as r:
        a = r.read(1)
        assert r.nodata == 0 and set(map(int, set(a.ravel()))) <= {0, 1, 2, 3, 11, 12, 13, 21, 22, 23, 31, 32, 33}
        assert a.max() >= 11
    with rasterio.MemoryFile(clean) as m, m.open() as r:
        assert set(map(int, set(r.read(1).ravel()))) <= {0, 1, 2, 3}


def test_export_vector_geopackage(base):
    body = get(base, "/api/export_vector?" + urllib.parse.urlencode(PARAMS))[1]
    path = os.path.join(tempfile.mkdtemp(), "v.gpkg")
    open(path, "wb").write(body)
    import pyogrio
    layers = {r[0] for r in pyogrio.list_layers(path)}
    assert {"originale", "omogeneizzata", "mappa_con_codici", "modifiche"} <= layers
    g = gpd.read_file(path, layer="mappa_con_codici")
    assert g.geometry.is_valid.all() and {"codice", "classe", "criterio", "area_m2"} <= set(g.columns)
    # le aree dei poligoni coincidono con i pixel del raster
    out, code, st = server.process("Figna_test", "Mappa_Pericolo_V1.tif", dict(bld=True, bm=0.0, osm=0, holes=True, area=10000.0, hmode="major", gap=30, buf=True, bufm=1.0))
    h, meta = server.load_layer(server.CASES["Figna_test"]["layers"]["Mappa_Pericolo_V1.tif"])
    codes = server.core.with_codes(out, code)
    for v in g.codice.unique():
        tot = (codes == v).sum() * meta["res"] ** 2
        assert abs(g.loc[g.codice == v, "area_m2"].sum() - tot) < max(0.05, 1e-6 * tot)
    m = gpd.read_file(path, layer="modifiche")
    assert m.codice.min() >= 11


def test_upload_valid_and_invalid(base):
    tif = os.path.join(EXAMPLE, "Figna_test", "Mappa_Pericolo_V1.tif")
    r = post(base, "/api/upload_data?kind=raster&area=Mia&name=prova.tif", open(tif, "rb").read())
    assert r["ok"] and r["case"] == "Mia (caricati)" and r["info"]["res"] == 0.5
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for f in glob.glob(os.path.join(EXAMPLE, "Figna_test", "Edifici", "Edifici.*")):
            z.write(f, os.path.basename(f))
    r = post(base, "/api/upload_data?kind=buildings&area=Mia&name=e.zip", buf.getvalue())
    assert r["ok"] and r["info"]["features"] > 100
    info = json.loads(get(base, "/api/info")[1])
    assert "Mia (caricati)" in info and info["Mia (caricati)"]["buildings"]
    # rifiuti
    assert "error" in post(base, "/api/upload_data?kind=raster&area=X&name=a.exe", b"abc")
    badzip = io.BytesIO()
    with zipfile.ZipFile(badzip, "w") as z:
        z.writestr("leggimi.txt", "x")
    assert "error" in post(base, "/api/upload_data?kind=buildings&area=Mia&name=v.zip", badzip.getvalue())
    # nome pericoloso: nessuna scrittura fuori dalla cartella di lavoro
    r = post(base, "/api/upload_data?kind=raster&area=..%2F..%2Fevil&name=..%5C..%5Cx.tif", open(tif, "rb").read())
    assert r["ok"] and ".." not in r["area"]
    assert not os.path.exists(os.path.join(server.WORKSPACE, "..", "evil"))
