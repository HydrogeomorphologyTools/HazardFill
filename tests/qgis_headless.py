"""Test del plugin QGIS senza interfaccia grafica.

Esecuzione (Windows):  "C:\\Program Files\\QGIS 3.34.11\\bin\\python-qgis-ltr.bat" tests\\qgis_headless.py
Altri sistemi: python con le librerie di QGIS; imposta QGIS_PREFIX (es. /usr) se serve.
"""
import glob
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "plugin"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if sys.platform.startswith("win"):
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

from qgis.core import QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsCategorizedSymbolRenderer  # noqa: E402

prefix = os.environ.get("QGIS_PREFIX") or (r"C:\Program Files\QGIS 3.34.11\apps\qgis-ltr" if sys.platform.startswith("win") else "/usr")
QgsApplication.setPrefixPath(prefix, True)
app = QgsApplication([], False)
app.initQgis()
sys.path.append(os.path.join(prefix, "python", "plugins"))
import processing  # noqa: E402
from processing.core.Processing import Processing  # noqa: E402
Processing.initialize()

import numpy as np  # noqa: E402
from osgeo import gdal, ogr  # noqa: E402
gdal.UseExceptions()
ogr.UseExceptions()
from hazardfill.provider import HazardFillProvider  # noqa: E402
from hazardfill import core  # noqa: E402

PROV = HazardFillProvider()
QgsApplication.processingRegistry().addProvider(PROV)

tif = os.path.join(ROOT, "examples", "Figna_test", "Mappa_Pericolo_V1.tif")
shp = os.path.join(ROOT, "examples", "Figna_test", "Edifici", "Edifici.shp")
tmp = tempfile.mkdtemp(prefix="hf_qgis_")
results = []


def check(label, cond, extra=""):
    results.append(bool(cond))
    print(("OK   " if cond else "FAIL ") + label, extra)


def arr(p):
    d = gdal.Open(p)
    return d.GetRasterBand(1).ReadAsArray()


rl = QgsRasterLayer(tif, "h")
vl = QgsVectorLayer(shp, "b", "ogr")
check("dati di esempio leggibili", rl.isValid() and vl.isValid())

alg = QgsApplication.processingRegistry().algorithmById("hazardfill:fillhazard")
check("algoritmi registrati", alg is not None and QgsApplication.processingRegistry().algorithmById("hazardfill:exportmap") is not None)
d = {p.name(): p.defaultValue() for p in alg.parameterDefinitions()}
check("valori predefiniti", d["BUILDING_TOLERANCE"] == 0.0 and d["BUFFER_WIDTH"] == 1.0 and d["FILL_MODE"] == 1 and d["APPLY_BUILDINGS"] is True)

# elaborazione completa con raster, vettoriale e confronto con il nucleo
out = os.path.join(tmp, "elab.tif")
clean = os.path.join(tmp, "elab_pulita.tif")
gp = os.path.join(tmp, "elab.gpkg")
processing.run("hazardfill:fillhazard", dict(INPUT=rl, BUILDINGS=vl, OSM=0, APPLY_BUILDINGS=True, BUILDING_TOLERANCE=0.5, APPLY_HOLES=True, AREA=10000.0,
               ALL_HOLES=False, GAP=30.0, FILL_MODE=1, APPLY_BUFFER=True, BUFFER_WIDTH=1.0, OUTPUT=out, OUTPUT_CLEAN=clean, OUTPUT_VECTOR=gp))
a, b = arr(out), arr(clean)
check("raster con codici e raster pulito", set(np.unique(a)) >= {0, 1} and a.max() >= 11 and set(np.unique(b)) <= {0, 1, 2, 3})
check("stile .qml accanto ai raster", os.path.exists(out.replace(".tif", ".qml")) and os.path.exists(clean.replace(".tif", ".qml")))
ds = gdal.Open(out)
check("nodata = 0 e metadati con i parametri", ds.GetRasterBand(1).GetNoDataValue() == 0 and "params" in ds.GetMetadata())

# riferimento: lo stesso calcolo con il nucleo, rasterizzando gli edifici con GDAL
d0 = gdal.Open(tif)
gt = d0.GetGeoTransform()
h = core.normalize_hazard(d0.GetRasterBand(1).ReadAsArray())
mem = gdal.GetDriverByName("MEM").Create("", h.shape[1], h.shape[0], 1, gdal.GDT_Int32)
mem.SetGeoTransform(gt)
mem.SetProjection(d0.GetProjection())
from osgeo import osr  # noqa: E402
sr = osr.SpatialReference(wkt=d0.GetProjection())
src = ogr.Open(shp)
lyr = src.GetLayer(0)
mds = ogr.GetDriverByName("Memory").CreateDataSource("t")
ml = mds.CreateLayer("b", sr, ogr.wkbUnknown)
ml.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))
ct = osr.CoordinateTransformation(lyr.GetSpatialRef(), sr)
for i, f in enumerate(lyr):
    g = f.GetGeometryRef().Clone()
    g.Transform(ct)
    nf = ogr.Feature(ml.GetLayerDefn())
    nf.SetField("id", i + 1)
    nf.SetGeometry(g)
    ml.CreateFeature(nf)
gdal.RasterizeLayer(mem, [1], ml, options=["ATTRIBUTE=id", "ALL_TOUCHED=TRUE"])
bid = mem.GetRasterBand(1).ReadAsArray().astype(np.int32)
o, c, st = core.process(h, bid, abs(gt[1]), dict(bld=True, bm=0.5, holes=True, area=10000.0, hmode="major", gap=int(round(30 / abs(gt[1]) / 2)), buf=True, bufm=1.0))
check("plugin = nucleo, pixel per pixel", (a == core.with_codes(o, c)).all() and (b == o).all(), "(diversi: %d)" % int((a != core.with_codes(o, c)).sum()))

# vettoriale: 4 livelli, geometrie valide, stile categorizzato, aree = pixel
res = abs(gt[1]) ** 2
v = ogr.Open(gp)
names = [v.GetLayer(i).GetName() for i in range(v.GetLayerCount())]
check("GeoPackage con 4 livelli", {"originale", "omogeneizzata", "mappa_con_codici", "modifiche"} <= set(names), str(names))
sq = v.ExecuteSQL("SELECT codice AS k, SUM(area_m2) AS a FROM mappa_con_codici GROUP BY codice")
tot = {int(f.GetField("k")): f.GetField("a") for f in sq}
v.ReleaseResultSet(sq)
codes = core.with_codes(o, c)
check("aree dei poligoni = pixel", all(abs(tot[k] - (codes == k).sum() * res) < max(0.05, 1e-6 * tot[k]) for k in tot))
vv = QgsVectorLayer(gp + "|layername=mappa_con_codici", "v", "ogr")
check("stile incorporato nel GeoPackage", vv.isValid() and isinstance(vv.renderer(), QgsCategorizedSymbolRenderer) and len(vv.renderer().categories()) == 12)

# edifici in un altro CRS (GeoJSON in EPSG:4326)
gj = os.path.join(tmp, "edifici.geojson")
gdal.VectorTranslate(gj, shp, format="GeoJSON", dstSRS="EPSG:4326", reproject=True)
vl4 = QgsVectorLayer(gj, "b4326", "ogr")
out4 = os.path.join(tmp, "e4326.tif")
processing.run("hazardfill:fillhazard", dict(INPUT=rl, BUILDINGS=vl4, OSM=0, APPLY_BUILDINGS=True, BUILDING_TOLERANCE=0.5, APPLY_HOLES=False, BUFFER_WIDTH=1.0, APPLY_BUFFER=False, OUTPUT=out4))
a4 = arr(out4)
check("edifici in un altro CRS (EPSG:4326)", ((a4 > 10).sum() - (a > 10).sum()) is not None and (a4 > 10).sum() > 0)

# errori attesi
try:
    processing.run("hazardfill:fillhazard", dict(INPUT=rl, BUILDINGS=None, OSM=0, OUTPUT=os.path.join(tmp, "x.tif")))
    check("senza edifici ne' OSM: errore", False)
except Exception as e:
    check("senza edifici ne' OSM: errore chiaro", "edifici" in str(e).lower(), str(e).splitlines()[0][:60])
geo = os.path.join(tmp, "geo.tif")
gdal.Warp(geo, tif, dstSRS="EPSG:4326")
try:
    processing.run("hazardfill:fillhazard", dict(INPUT=QgsRasterLayer(geo, "g"), BUILDINGS=vl, OSM=0, OUTPUT=os.path.join(tmp, "y.tif")))
    check("raster in gradi: errore", False)
except Exception as e:
    check("raster in gradi: errore chiaro", "proiettato" in str(e), str(e).splitlines()[0][:60])

# esporta mappa (PNG) con riempimenti e originale
QgsProject.instance().addMapLayers([rl, vl])
el = QgsRasterLayer(out, "elaborata")
QgsProject.instance().addMapLayer(el)
png1 = processing.run("hazardfill:exportmap", dict(HAZARD=el, LAYERS=[el, vl], TITLE="Esempio", WIDTH_MM=200, DPI=100, OUTPUT=os.path.join(tmp, "mappa.png")))["OUTPUT"]
check("PNG con riempimenti (nome con 'riempimenti')", os.path.exists(png1) and "riempimenti" in os.path.basename(png1), os.path.basename(png1))
png2 = processing.run("hazardfill:exportmap", dict(HAZARD=rl, LAYERS=[rl, vl], WIDTH_MM=200, DPI=100, OUTPUT=os.path.join(tmp, "mappa_orig.png")))["OUTPUT"]
check("PNG originale (senza 'riempimenti')", os.path.exists(png2) and "riempimenti" not in os.path.basename(png2))

print("\nTUTTO OK" if all(results) else "\nERRORI: %d su %d" % (results.count(False), len(results)))
sys.stdout.flush()
os._exit(0 if all(results) else 1)     # uscita immediata: evita l'arresto anomalo di QGIS in chiusura
