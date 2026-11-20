"""Test del nucleo di calcolo (solo numpy + scipy): comportamento dei tre criteri su piccole griglie."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugin", "hazardfill"))
import core  # noqa: E402


def test_normalize_hazard():
    a = np.array([[-9999, np.nan, 0.2, 0.6, 1.4, 2.5, 7, 3]], dtype="float64")
    assert core.normalize_hazard(a).tolist() == [[0, 0, 0, 1, 1, 2, 3, 3]]


def _building_case():
    h = np.zeros((9, 9), np.uint8)
    h[:, :3] = 1
    h[:, 3] = 3
    bid = np.zeros((9, 9), np.int32)
    bid[3:6, 4:7] = 1
    h[3:6, 4] = 2                   # il flusso entra solo nella prima colonna dell'edificio
    return h, bid


def test_buildings_take_max_inside_footprint():
    h, bid = _building_case()
    out, mod, n = core.step_buildings(h, bid, 0)
    assert (out[bid > 0] == 2).all() and n == 1
    assert (out[bid == 0] == h[bid == 0]).all()           # fuori dall'edificio non cambia nulla


def test_buildings_tolerance_ring():
    h, bid = _building_case()
    out, _, _ = core.step_buildings(h, bid, 1)
    assert (out[bid > 0] == 3).all()                      # entra anche la cella a 3 entro 1 pixel


def test_buildings_never_lower_existing_values():
    h, bid = _building_case()
    h[3, 5] = 3
    out, _, _ = core.step_buildings(h, bid, 0)
    assert out[3, 5] == 3 and (out[bid > 0] >= 2).all() and (out[bid > 0] == 3).all()


def test_buildings_without_valid_values_are_not_assigned():
    h = np.zeros((6, 6), np.uint8)
    bid = np.zeros((6, 6), np.int32)
    bid[2:4, 2:4] = 1
    out, mod, n = core.step_buildings(h, bid, 0)
    assert n == 0 and not out.any()


def _holes_case():
    h = np.zeros((12, 14), np.uint8)
    h[1:11, 1:13] = 2
    h[1:11, 1:3] = 3
    h[3:5, 5:7] = 0         # 4 celle
    h[6:9, 8:12] = 0        # 12 celle
    return h


def test_holes_area_threshold_and_all():
    h = _holes_case()
    out, mod, n = core.step_holes(h, 5, "max", 0)
    assert mod.sum() == 4 and n == 1 and (out[3:5, 5:7] == 3).all() or (out[3:5, 5:7] > 0).all()
    assert (out[6:9, 8:12] == 0).all()                    # la grande resta
    out2, mod2, n2 = core.step_holes(h, None, "max", 0)
    assert mod2.sum() == 16 and (out2[1:11, 1:13] > 0).all()


def test_holes_do_not_close_zones_connected_to_the_border():
    h = np.full((10, 10), 2, np.uint8)
    h[4:6, 4:6] = 0
    h[4:6, 6:] = 0                                         # collegata al bordo destro
    out, mod, n = core.step_holes(h, None, "max", 0)
    assert mod.sum() == 0


def test_gap_closes_narrow_openings():
    h = np.zeros((11, 11), np.uint8)
    h[1:10, 1:10] = 2
    h[3:8, 3:8] = 0
    h[5, 8:10] = 0                                         # varco di 1 cella verso l'esterno
    assert core.step_holes(h, None, "max", 0)[1].sum() == 0
    assert core.step_holes(h, None, "max", 2)[1].sum() > 0


def test_fill_modes():
    h = np.zeros((9, 9), np.uint8)
    h[0:3, :] = 3
    h[3:9, :3] = 1
    h[3:9, 6:] = 2
    h[6:9, 3:6] = 2
    outs = {m: core.step_holes(h, None, m, 0)[0][3:6, 3:6] for m in ("max", "major", "near")}
    assert (outs["max"] == 3).all()
    assert (outs["major"] == 2).all()
    assert set(np.unique(outs["near"])) == {1, 2, 3}


def test_buffer_is_one_grade_lower_and_never_overwrites():
    h = np.zeros((6, 12), np.uint8)
    h[0:2, 0:4] = 3
    h[2:4, 0:4] = 2
    h[4:6, 0:4] = 1
    out, mod, n = core.step_buffer(h, 2)
    assert out[:, 4].tolist() == [2, 2, 1, 1, 1, 1] and out[:, 5].tolist() == [2, 2, 1, 1, 1, 1]
    assert (out[:, 6:] == 0).all() and (out[:, :4] == h[:, :4]).all()


def test_process_codes_and_priority():
    h, bid = _building_case()
    out, code, st = core.process(h, bid, 1.0, dict(bld=True, bm=1.0, holes=True, area=50, buf=True, bufm=1.0))
    assert set(np.unique(code)) <= {0, 1, 2, 3}
    assert (code[bid > 0] <= 1).all()                      # i pixel degli edifici portano il codice 1 (o 0)
    assert st["mod_by_step"][0] == int((code == 1).sum())
    coded = core.with_codes(out, code)
    assert coded[code == 1].min() >= 11 and (coded[code == 0] == out[code == 0]).all()


def test_metres_are_converted_with_resolution():
    h, bid = _building_case()
    a = core.process(h, bid, 0.5, dict(bld=True, bm=0.5, holes=False, buf=False))        # 0,5 m a 0,5 m/px = 1 px
    b = core.process(h, bid, 1.0, dict(bld=True, bm=1.0, holes=False, buf=False))        # 1 m a 1 m/px = 1 px
    assert (a[0] == b[0]).all()
    assert a[2]["bld_px"] == 1 and b[2]["bld_px"] == 1


def test_defaults():
    d = core.DEFAULTS
    assert d["bm"] == 0.0 and d["hmode"] == "major" and d["bufm"] == 1.0 and d["bld"] is True


def test_merge_building_ids():
    user = np.zeros((10, 10), np.int32)
    user[1:4, 1:4] = 1
    osm = np.zeros((10, 10), np.int32)
    osm[1:4, 1:4] = 1                     # duplicato di quello fornito
    osm[6:9, 6:9] = 2                     # nuovo
    out, n = core.merge_building_ids(user, osm)
    assert n == 1 and out.max() == 2 and (out[6:9, 6:9] == 2).all() and (out[1:4, 1:4] == 1).all()


def test_code_helpers_and_styles():
    assert core.criterio_of(1) == "originale" and core.criterio_of(23) == "zone interne" and core.criterio_of(31) == "buffer"
    assert core.classe_of(23) == 3 and core.classe_of(2) == 2
    assert [r[0] for r in core.code_table(False)] == [0, 1, 2, 3, 11, 12, 13, 21, 22, 23, 31, 32, 33]
    assert 'attr="codice"' in core.make_vector_qml("codice")
    assert set(core.vector_styles()) == set(core.VECTOR_LAYERS)


def test_flood_matches_skimage_watershed_when_available():
    skseg = pytest.importorskip("skimage.segmentation")
    from scipy import ndimage as ndi
    rng = np.random.default_rng(1)
    z = ndi.binary_closing(rng.random((120, 160)) > 0.6, iterations=3)
    lab, _ = ndi.label(ndi.distance_transform_edt(z) > 3)
    a = core._flood(lab, z)
    b = skseg.watershed(np.zeros(z.shape, np.uint8), markers=lab, mask=z)
    assert (a != b).sum() <= 0.01 * z.sum()


# ------------------------------------------------------------------ download OSM (Overpass)
def _fake_overpass():
    import json
    import threading
    import time as _t
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path == "/hang":
                _t.sleep(5)                                   # un server che non risponde
            body = json.dumps({"elements": []}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


def test_overpass_moves_on_when_a_server_does_not_answer():
    import time
    srv, base = _fake_overpass()
    try:
        t = time.time()
        r = core._overpass("q", tries=3, timeout=1, mirrors=[base + "/hang", base + "/ok"])
        assert r == {"elements": []} and time.time() - t < 4.5      # 1 s di attesa + pausa, non 5 s
    finally:
        srv.shutdown()


def test_overpass_can_be_cancelled():
    import time
    srv, base = _fake_overpass()
    try:
        t0 = time.time()
        with pytest.raises(core.Cancelled):
            core._overpass("q", tries=6, timeout=1, mirrors=[base + "/hang"], is_canceled=lambda: time.time() - t0 > 1.2)
        assert time.time() - t0 < 5
    finally:
        srv.shutdown()


def test_overpass_gives_a_clear_error_when_all_servers_fail():
    with pytest.raises(RuntimeError) as e:
        core._overpass("q", tries=2, timeout=1, mirrors=["http://127.0.0.1:9/x"])
    assert "shapefile" in str(e.value)


def test_osm_buildings_uses_the_cache_without_network(tmp_path):
    import json
    south, west, north, east = 46.0, 10.0, 46.01, 10.01
    data = {"elements": [{"type": "way", "id": 1, "geometry": [{"lat": 46.001, "lon": 10.001}, {"lat": 46.001, "lon": 10.002},
                                                                  {"lat": 46.002, "lon": 10.002}, {"lat": 46.001, "lon": 10.001}]}]}
    name = "osm_%.5f_%.5f_%.5f_%.5f.json" % (south, west, north, east)
    (tmp_path / name).write_text(json.dumps(data), encoding="utf-8")
    rings = core.osm_buildings(south, west, north, east, cache_dir=str(tmp_path), is_canceled=lambda: False)
    assert len(rings) == 1 and rings[0][0] == rings[0][-1]
    with pytest.raises(core.Cancelled):
        core.osm_buildings(south, west, north, east, cache_dir=str(tmp_path), is_canceled=lambda: True)
