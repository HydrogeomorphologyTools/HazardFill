# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
"""Algoritmo di Processing: HazardFill."""
import json
import os
import tempfile

import numpy as np
from osgeo import gdal, ogr, osr
from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeatureRequest, QgsGeometry,
                       QgsProcessing, QgsProcessingAlgorithm, QgsProcessingException, QgsProcessingParameterBoolean,
                       QgsProcessingContext, QgsProcessingParameterEnum, QgsProcessingParameterFeatureSource, QgsProcessingParameterFileDestination,
                       QgsProcessingParameterNumber, QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterRasterLayer, QgsProject, QgsWkbTypes)
from qgis.PyQt.QtGui import QIcon

from . import core, vector_export

HERE = os.path.dirname(__file__)
HMODES = ["max", "major", "near"]


def read_raster(layer):
    ds = gdal.Open(layer.source())
    if ds is None:
        raise QgsProcessingException("Impossibile aprire il raster %s" % layer.source())
    gt = ds.GetGeoTransform()
    if abs(gt[2]) > 1e-12 or abs(gt[4]) > 1e-12 or gt[5] > 0:
        raise QgsProcessingException("Il raster deve avere griglia regolare con nord in alto (senza rotazione).")
    crs = layer.crs()
    if not crs.isValid() or crs.isGeographic():
        raise QgsProcessingException("Il raster deve essere in un CRS proiettato in metri (non gradi).")
    arr = ds.GetRasterBand(1).ReadAsArray()
    return core.normalize_hazard(arr), gt, crs


def rasterize_polys(wkt_list, shape, gt, wkt_crs):
    """Rasterizza poligoni (WKT nel CRS del raster) in un array int32 di id (1..n), all_touched."""
    mem = gdal.GetDriverByName("MEM").Create("", shape[1], shape[0], 1, gdal.GDT_Int32)
    mem.SetGeoTransform(gt)
    mem.SetProjection(wkt_crs)
    mem.GetRasterBand(1).Fill(0)
    if wkt_list:
        drv = ogr.GetDriverByName("Memory")
        src = drv.CreateDataSource("x")
        srs = osr.SpatialReference()
        srs.ImportFromWkt(wkt_crs)
        lyr = src.CreateLayer("b", srs, ogr.wkbUnknown)
        lyr.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))
        for i, w in enumerate(wkt_list):
            g = ogr.CreateGeometryFromWkt(w)
            if g is None:
                continue
            f = ogr.Feature(lyr.GetLayerDefn())
            f.SetField("id", i + 1)
            f.SetGeometry(g)
            lyr.CreateFeature(f)
        gdal.RasterizeLayer(mem, [1], lyr, options=["ATTRIBUTE=id", "ALL_TOUCHED=TRUE"])
    return mem.GetRasterBand(1).ReadAsArray().astype(np.int32)


def write_tif(path, arr, gt, crs, tags):
    drv = gdal.GetDriverByName("GTiff")
    ds = drv.Create(path, arr.shape[1], arr.shape[0], 1, gdal.GDT_Byte, options=["COMPRESS=LZW"])
    ds.SetGeoTransform(gt)
    ds.SetProjection(crs.toWkt())
    b = ds.GetRasterBand(1)
    b.WriteArray(arr)
    b.SetNoDataValue(0)
    ds.SetMetadata(tags)
    ds.FlushCache()
    ds = None
    with open(os.path.splitext(path)[0] + ".qml", "w", encoding="utf-8") as f:
        f.write(core.make_qml("clean" in tags.get("variant", "")))


def vector_export_layers():
    return core.VECTOR_LAYERS


class FillHazardAlgorithm(QgsProcessingAlgorithm):
    INPUT, BUILDINGS, OSM = "INPUT", "BUILDINGS", "OSM"
    BLD, BPX = "APPLY_BUILDINGS", "BUILDING_TOLERANCE"
    HOLES, AREA, ALL, GAP, HMODE = "APPLY_HOLES", "AREA", "ALL_HOLES", "GAP", "FILL_MODE"
    BUF, BUFPX = "APPLY_BUFFER", "BUFFER_WIDTH"
    OUT, OUT_CLEAN, OUT_VECTOR = "OUTPUT", "OUTPUT_CLEAN", "OUTPUT_VECTOR"

    def name(self):
        return "fillhazard"

    def displayName(self):
        return "Chiusura buchi nella mappa di pericolosità"

    def group(self):
        return "Mappe di pericolosità"

    def groupId(self):
        return "hazard"

    def icon(self):
        return QIcon(os.path.join(HERE, "icon.svg"))

    def createInstance(self):
        return FillHazardAlgorithm()

    def helpUrl(self):
        return "file:///" + os.path.join(HERE, "help", "help_utilizzo.html").replace("\\", "/")

    def shortHelpString(self):
        return (
            "<p><i>Ausilio di pre-screening per i gestori del territorio nella fase di valutazione finale della mappatura del pericolo: "
            "non produce mappe di pericolosità e non sostituisce la valutazione di esperti.</i></p>"
            "<p>Corregge le mappe di pericolosità a classi (<b>0</b> nessun pericolo/nodata, <b>1</b> basso, "
            "<b>2</b> medio, <b>3</b> alto) eliminando le isole di assenza di pericolo non realistiche. "
            "I valori predefiniti sono <i>esempi di partenza</i>, non parametri definitivi.</p>"
            "<p><b>Ingressi</b>: raster a una banda in CRS proiettato (metri) con <b>solo</b> queste classi "
            "(nodata e negativi = 0); edifici poligonali in qualsiasi CRS (opzionali se si usa OpenStreetMap).</p>"
            "<h4>I passi, con esempi (pixel da 1 m)</h4>"
            "<p><b>0 Edifici.</b> Ogni edificio prende il valore <i>massimo</i> che lo tocca o che è entro la tolleranza (m) dal bordo. "
            "Es.: edificio 3×3 con solo la prima colonna a pericolo 2 &rarr; con tolleranza 0 m tutto l'edificio vale 2; "
            "se accanto c'è una cella a 3 e la tolleranza è 1 m &rarr; tutto 3. Le distanze in metri sono convertite in pixel con la risoluzione del raster.</p>"
            "<p><b>1 Zone interne.</b> Riempie le zone a 0 circondate da pericolo (non collegate al bordo del raster) con area &le; A m². "
            "Es.: due buchi di 4 m² e 12 m² &rarr; con A=5 si chiude solo il primo; con «Chiudi TUTTE» entrambi.</p>"
            "<p><b>Varco sigillabile</b> (m): con 0 conta solo l'interno completamente chiuso; con 3 m una zona collegata all'esterno "
            "da un passaggio più stretto di 3 m è considerata interna (es. argine con una sola apertura).</p>"
            "<p><b>Valore di riempimento</b>: più frequente del contorno (predefinito), massimo (prudente), oppure più vicino. "
            "Es.: contorno con 3 sopra, 1 a sinistra e 2 altrove &rarr; più frequente = 2, massimo = 3, più vicino = misto 1/2/3.</p>"
            "<p><b>2 Buffer.</b> Fascia di larghezza data (m) sulla classe 0 adiacente a pixel validi con valore del più vicino &minus;1 grado (min 1). "
            "Es.: bordo a 3 &rarr; buffer 2; bordo a 2 &rarr; 1; bordo a 1 &rarr; 1. Non sovrascrive pixel validi.</p>"
            "<h4>Uscite</h4>"
            "<p>Raster con codici: decine = passo (1 edifici, 2 zone interne, 3 buffer), unità = livello assegnato "
            "(es. <b>23</b> = pericolo alto assegnato da zona interna); e, se richiesto, raster pulito 0-3. Ciascuno con stile .qml.</p>"
            "<p>Per l'immagine con legenda, nord e scala usa l'algoritmo «Esporta mappa». "
            "Help completo con figure: menu Raster &rarr; HazardFill &rarr; Help &ndash; utilizzo.</p>")

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Mappa di pericolosità (classi 0-3)"))
        self.addParameter(QgsProcessingParameterFeatureSource(self.BUILDINGS, "Edifici (poligoni)", [QgsProcessing.TypeVectorPolygon], optional=True))
        self.addParameter(QgsProcessingParameterEnum(self.OSM, "Sorgente edifici", ["solo edifici forniti", "forniti + integra da OpenStreetMap", "solo OpenStreetMap"], defaultValue=0))
        self.addParameter(QgsProcessingParameterBoolean(self.BLD, "0. Applica criterio edifici", True))
        self.addParameter(QgsProcessingParameterNumber(self.BPX, "   Edifici: tolleranza dal bordo (m)", QgsProcessingParameterNumber.Double, 0.0, minValue=0, maxValue=100))
        self.addParameter(QgsProcessingParameterBoolean(self.HOLES, "1. Chiudi zone interne", True))
        self.addParameter(QgsProcessingParameterNumber(self.AREA, "   Zone interne: area massima da chiudere (m²)", QgsProcessingParameterNumber.Double, 10.0, minValue=0))
        self.addParameter(QgsProcessingParameterBoolean(self.ALL, "   Chiudi TUTTE le zone interne (ignora l'area)", False))
        self.addParameter(QgsProcessingParameterNumber(self.GAP, "   Varco sigillabile (m, 0 = solo zone chiuse)", QgsProcessingParameterNumber.Double, 0.0, minValue=0))
        self.addParameter(QgsProcessingParameterEnum(self.HMODE, "   Valore di riempimento", ["massimo del contorno", "più frequente del contorno (maggioranza)", "più vicino"], defaultValue=1))
        self.addParameter(QgsProcessingParameterBoolean(self.BUF, "2. Buffer graduato su classe 0", True))
        self.addParameter(QgsProcessingParameterNumber(self.BUFPX, "   Buffer: larghezza (m)", QgsProcessingParameterNumber.Double, 1.0, minValue=0.1, maxValue=1000))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUT, "Raster elaborato (con codici di modifica)"))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUT_CLEAN, "Raster elaborato pulito (solo 0-3)", optional=True, createByDefault=False))
        self.addParameter(QgsProcessingParameterFileDestination(self.OUT_VECTOR, "Vettoriale GeoPackage con codici (4 livelli)", "GeoPackage (*.gpkg)", optional=True, createByDefault=False))

    # ------------------------------------------------------------------
    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        # gli edifici si leggono direttamente dal layer: senza il filtro di QGIS sulle geometrie non valide
        # (che ferma l'algoritmo), perche' la rasterizzazione le gestisce comunque
        src = self.parameterAsVectorLayer(parameters, self.BUILDINGS, context)
        if src is None:
            src = self.parameterAsSource(parameters, self.BUILDINGS, context)
        osm = self.parameterAsEnum(parameters, self.OSM, context)
        p = dict(bld=self.parameterAsBool(parameters, self.BLD, context),
                 bm=self.parameterAsDouble(parameters, self.BPX, context),
                 holes=self.parameterAsBool(parameters, self.HOLES, context),
                 area=self.parameterAsDouble(parameters, self.AREA, context),
                 all_holes=self.parameterAsBool(parameters, self.ALL, context),
                 hmode=HMODES[self.parameterAsEnum(parameters, self.HMODE, context)],
                 buf=self.parameterAsBool(parameters, self.BUF, context),
                 bufm=self.parameterAsDouble(parameters, self.BUFPX, context))
        out_path = self.parameterAsOutputLayer(parameters, self.OUT, context)
        clean_path = self.parameterAsOutputLayer(parameters, self.OUT_CLEAN, context) if self.OUT_CLEAN in parameters and parameters[self.OUT_CLEAN] else None
        vec_path = self.parameterAsFileOutput(parameters, self.OUT_VECTOR, context) if self.OUT_VECTOR in parameters and parameters[self.OUT_VECTOR] else None

        feedback.pushInfo("Lettura raster...")
        h, gt, crs = read_raster(layer)
        res = abs(gt[1])
        p["gap"] = int(round(self.parameterAsDouble(parameters, self.GAP, context) / res / 2))
        shape = h.shape
        wkt = crs.toWkt()
        ext_xmin, ext_ymax = gt[0], gt[3]
        ext_xmax, ext_ymin = gt[0] + gt[1] * shape[1], gt[3] + gt[5] * shape[0]
        from qgis.core import QgsRectangle
        rect = QgsRectangle(ext_xmin, ext_ymin, ext_xmax, ext_ymax)

        bid = None
        if p["bld"]:
            user = np.zeros(shape, np.int32)
            if osm != 2:
                if src is None:
                    if osm == 0:
                        raise QgsProcessingException("Nessun vettore di edifici indicato: scegli un vettore oppure una sorgente OpenStreetMap.")
                else:
                    feedback.pushInfo("Rasterizzazione edifici forniti...")
                    xf = QgsCoordinateTransform(crs, src.sourceCrs(), context.transformContext())
                    req = QgsFeatureRequest().setFilterRect(xf.transformBoundingBox(rect))
                    xf2 = QgsCoordinateTransform(src.sourceCrs(), crs, context.transformContext())
                    wl = []
                    for f in src.getFeatures(req):
                        g = QgsGeometry(f.geometry())
                        if g.isNull() or g.isEmpty() or QgsWkbTypes.geometryType(g.wkbType()) != QgsWkbTypes.PolygonGeometry:
                            continue
                        g.transform(xf2)
                        wl.append(g.asWkt())
                    user = rasterize_polys(wl, shape, gt, wkt)
                    feedback.pushInfo("  %d edifici forniti" % len(wl))
            bid = user
            if osm:
                feedback.pushInfo("Download edifici da OpenStreetMap...")
                to_ll = QgsCoordinateTransform(crs, QgsCoordinateReferenceSystem("EPSG:4326"), context.transformContext())
                bb = to_ll.transformBoundingBox(rect)
                cache = os.path.join(tempfile.gettempdir(), "hazardfill_osm_cache")
                rings = core.osm_buildings(bb.yMinimum(), bb.xMinimum(), bb.yMaximum(), bb.xMaximum(), cache_dir=cache, log=feedback.pushInfo)
                from_ll = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), crs, context.transformContext())
                wl = []
                for r in rings:
                    g = QgsGeometry.fromWkt("POLYGON((%s))" % ",".join("%.8f %.8f" % pt for pt in r))
                    g.transform(from_ll)
                    wl.append(g.asWkt())
                bo = rasterize_polys(wl, shape, gt, wkt)
                bid, nadd = core.merge_building_ids(user, bo)
                feedback.pushInfo("  %d edifici OSM nell'area, %d aggiunti" % (len(wl), nadd))
            if feedback.isCanceled():
                return {}

        feedback.pushInfo("Elaborazione (%d x %d pixel, %.2f m)..." % (shape[1], shape[0], res))
        out, code, st = core.process(h, bid, res, p)
        if "bld_total" in st:
            feedback.pushInfo("Edifici modificati: %d / %d" % (st["bld_changed"], st["bld_total"]))
        feedback.pushInfo("Pixel modificati per passo (edifici / zone interne / buffer): %s" % st["mod_by_step"])
        feedback.pushInfo("Pixel per classe 0/1/2/3 prima: %s  dopo: %s" % (st["orig"], st["new"]))

        params = json.dumps(dict(p, osm=osm, gap_m=self.parameterAsDouble(parameters, self.GAP, context)))
        base = dict(source=layer.source(), params=params, software="HazardFill %s" % core.__version__)
        write_tif(out_path, core.with_codes(out, code), gt, crs, dict(base, variant="codes",
                  codes="0=nodata/zero;1-3=pericolo originale;1x=modificato da edifici;2x=da zone interne;3x=da buffer (x=livello 1-3)"))
        res_d = {self.OUT: out_path}
        if clean_path:
            write_tif(clean_path, out, gt, crs, dict(base, variant="clean", codes="0=nodata/zero;1=basso;2=medio;3=alto"))
            res_d[self.OUT_CLEAN] = clean_path
        if vec_path:
            feedback.pushInfo("Poligonizzazione (GeoPackage con 4 livelli)...")
            info = vector_export.write_gpkg(vec_path, h, out, core.with_codes(out, code), gt, wkt)
            feedback.pushInfo("Livelli scritti: %s" % ", ".join("%s (%d poligoni)" % kv for kv in info.items()))
            for name in vector_export_layers():
                context.addLayerToLoadOnCompletion("%s|layername=%s" % (vec_path, name),
                                                   QgsProcessingContext.LayerDetails("Vettoriale - " + name, context.project(), self.OUT_VECTOR))
            res_d[self.OUT_VECTOR] = vec_path
        return res_d
