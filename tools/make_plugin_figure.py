# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
"""Genera con il plugin (QGIS senza interfaccia) l'immagine di esempio dell'export della mappa.
Esecuzione:  "C:\\Program Files\\QGIS 3.34.11\\bin\\python-qgis-ltr.bat" tools\\make_plugin_figure.py
"""
import os
import shutil
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "plugin"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if sys.platform.startswith("win"):
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
from qgis.core import QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer  # noqa: E402

prefix = os.environ.get("QGIS_PREFIX") or (r"C:\Program Files\QGIS 3.34.11\apps\qgis-ltr" if sys.platform.startswith("win") else "/usr")
QgsApplication.setPrefixPath(prefix, True)
app = QgsApplication([], False)
app.initQgis()
sys.path.append(os.path.join(prefix, "python", "plugins"))
import processing  # noqa: E402
from processing.core.Processing import Processing  # noqa: E402
Processing.initialize()
from hazardfill.provider import HazardFillProvider  # noqa: E402
PROV = HazardFillProvider()
QgsApplication.processingRegistry().addProvider(PROV)

tmp = os.path.join(ROOT, "tests", "_out")
os.makedirs(tmp, exist_ok=True)
rl = QgsRasterLayer(os.path.join(ROOT, "examples", "Figna_test", "Mappa_Pericolo_V1.tif"), "Figna_test")
vl = QgsVectorLayer(os.path.join(ROOT, "examples", "Figna_test", "Edifici", "Edifici.shp"), "Edifici", "ogr")
out = os.path.join(tmp, "figna_elaborata.tif")
processing.run("hazardfill:fillhazard", dict(INPUT=rl, BUILDINGS=vl, OSM=0, APPLY_BUILDINGS=True, BUILDING_TOLERANCE=0.5, APPLY_HOLES=True,
               AREA=10000.0, ALL_HOLES=False, GAP=30.0, FILL_MODE=1, APPLY_BUFFER=True, BUFFER_WIDTH=5.0, OUTPUT=out))
el = QgsRasterLayer(out, "Figna_test elaborata")
QgsProject.instance().addMapLayers([el, vl])
png = processing.run("hazardfill:exportmap", dict(HAZARD=el, LAYERS=[el, vl], TITLE="Figna_test (dati di prova)", WIDTH_MM=220, DPI=130,
                     OUTPUT=os.path.join(tmp, "plugin_export.png")))["OUTPUT"]
dest = os.path.join(ROOT, "docs", "images", "plugin_export_esempio.png")
shutil.copy(png, dest)
print("scritta", dest)
sys.stdout.flush()
os._exit(0)
