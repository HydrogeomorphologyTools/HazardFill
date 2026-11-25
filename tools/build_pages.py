# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
"""Costruisce la versione per GitHub Pages in docs/app (la pagina dell'app e' derivata da web/index.html).

Servono geopandas e shapely (solo per preparare l'esempio). Esecuzione:  python tools/build_pages.py
"""
import os
import re
import shutil

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
APP = os.path.join(ROOT, "docs", "app")
os.makedirs(os.path.join(APP, "hazardfill"), exist_ok=True)
os.makedirs(os.path.join(APP, "example"), exist_ok=True)

NOTE = ('<small style="display:block;margin-top:6px;padding:5px 7px;background:#fff3cd;border-left:3px solid #f5b400;color:#664d03">'
        '<b>Versione online di prova.</b> Il calcolo avviene nel tuo browser, quindi serve per <b>provare lo strumento con dati non troppo pesanti</b> '
        '(raster fino a qualche milione di pixel); non è pensata per un uso intensivo o massivo. Per lavorare con regolarità o su dati grandi '
        'usa il <b>plugin QGIS</b> (la scelta migliore per il singolo utente) o la versione locale. '
        'Il vettoriale (GeoPackage) è disponibile solo nel plugin e nella versione locale.</small>')


def build_app():
    s = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
    s = s.replace('href="/logo.svg"', 'href="logo.svg"').replace('src="/logo.svg"', 'src="logo.svg"').replace('href="/help"', 'href="help.html"')
    # niente Sentinel-2 EOX: il server delle tessere non permette l'esportazione dell'immagine dal browser
    s = re.sub(r"const s2=L\.tileLayer\('/tile/eox/[^\n]*\n", "", s)
    assert "'Sentinel-2 EOX':s2," in s
    s = s.replace("'Sentinel-2 EOX':s2,", "")
    s = s.replace("</head>", ('<script src="https://cdn.jsdelivr.net/npm/proj4@2.9.0/dist/proj4.js"></script>\n'
                              '<script src="https://cdn.jsdelivr.net/npm/geotiff@2.1.3/dist-browser/geotiff.js"></script>\n'
                              '<script src="https://cdn.jsdelivr.net/npm/shpjs@4.0.4/dist/shp.min.js"></script>\n'
                              '<script src="backend-browser.js"></script>\n</head>'), 1)
    marker = "non è una mappatura di pericolosità né sostituisce la valutazione di esperti.</small>"
    assert marker in s
    s = s.replace(marker, marker + NOTE, 1)
    s = s.replace("<title>HazardFill (HF) – chiusura buchi nelle mappe di pericolosità</title>", "<title>HazardFill (HF) – versione online di prova</title>", 1)
    open(os.path.join(APP, "index.html"), "w", encoding="utf-8").write(s)
    shutil.copy(os.path.join(ROOT, "plugin", "hazardfill", "core.py"), os.path.join(APP, "hazardfill", "core.py"))
    shutil.copy(os.path.join(ROOT, "plugin", "hazardfill", "icon.svg"), os.path.join(APP, "logo.svg"))
    shutil.copy(os.path.join(ROOT, "plugin", "hazardfill", "help", "help_utilizzo.html"), os.path.join(APP, "help.html"))


def build_example():
    import geopandas as gpd
    ex = os.path.join(ROOT, "examples", "Spona_test")
    shutil.copy(os.path.join(ex, "Mappa_Pericolo_Spona.tif"), os.path.join(APP, "example", "Mappa_Pericolo_Spona.tif"))
    g = gpd.read_file(os.path.join(ex, "Edifici", "Edifici.shp")).to_crs(4326)
    g = g[["geometry"]]
    out = os.path.join(APP, "example", "Edifici.geojson")
    g.to_file(out, driver="GeoJSON", COORDINATE_PRECISION=9)
    print("esempio: %d edifici, %d KB" % (len(g), os.path.getsize(out) // 1024))


if __name__ == "__main__":
    build_app()
    build_example()
    open(os.path.join(ROOT, "docs", ".nojekyll"), "w").close()
    print("sito costruito in", APP)
