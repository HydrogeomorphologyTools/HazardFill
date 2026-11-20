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
