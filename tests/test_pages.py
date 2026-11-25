"""La versione per GitHub Pages (docs/app) deve restare coerente con il resto del repository."""
import json
import os
import pytest
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
APP = os.path.join(ROOT, "docs", "app")


def read(*p):
    return open(os.path.join(ROOT, *p), encoding="utf-8").read()


def test_core_copy_is_in_sync():
    assert read("docs", "app", "hazardfill", "core.py") == read("plugin", "hazardfill", "core.py")


def test_app_page_is_derived_from_web_page():
    app, web = read("docs", "app", "index.html"), read("web", "index.html")
    assert "backend-browser.js" in app and "backend-browser.js" not in web
    for key in ("BACKEND.process(", "BACKEND.info()", "BACKEND.upload(", "BACKEND.exportRaster("):
        assert key in web and key in app
    assert "/tile/eox/" not in app and "Sentinel-2 EOX" not in app.split("L.control.layers")[1][:400]
    assert 'href="/logo.svg"' not in app and 'href="/help"' not in app


def test_versions_are_aligned():
    core = re.search(r'__version__ = "([^"]+)"', read("plugin", "hazardfill", "core.py")).group(1)
    assert re.search(r"^version=" + re.escape(core) + r"$", read("plugin", "hazardfill", "metadata.txt"), re.M)
    assert "const VERSION = '%s'" % core in read("docs", "app", "backend-browser.js")
    assert "version: " + core in read("CITATION.cff")


@pytest.mark.skipif(not os.path.exists(os.path.join(APP, "example", "Mappa_Pericolo_Spona.tif")), reason="dati di prova non presenti")
def test_example_files_for_pages():
    ex = os.path.join(APP, "example")
    gj = json.load(open(os.path.join(ex, "Edifici.geojson"), encoding="utf-8"))
    assert len(gj["features"]) == 186
    assert os.path.getsize(os.path.join(ex, "Mappa_Pericolo_Spona.tif")) == os.path.getsize(os.path.join(ROOT, "examples", "Spona_test", "Mappa_Pericolo_Spona.tif"))
    assert os.path.exists(os.path.join(ROOT, "docs", ".nojekyll"))


def test_landing_page_links_to_app_and_has_disclaimer():
    s = read("docs", "index.html")
    assert 'href="app/"' in s and "pre-screening" in s and "plugin QGIS" in s and "uso intensivo" in s
