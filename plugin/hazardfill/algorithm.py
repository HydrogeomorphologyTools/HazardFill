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
from qgis.core import QgsProcessingLayerPostProcessorInterface, QgsProcessingOutputRasterLayer, QgsRasterLayer

from . import core, vector_export
from .i18n import lang, tr

HERE = os.path.dirname(__file__)
HMODES = ["max", "major", "near"]


def _qml_file(clean):
    core.LANG = lang()
    """File .qml con la tavolozza dei codici (nella cartella temporanea)."""
    path = os.path.join(tempfile.gettempdir(), "hazardfill_style_%s.qml" % ("clean" if clean else "codes"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(core.make_qml(clean))
    return path


def read_raster(layer):
    ds = gdal.Open(layer.source())
    if ds is None:
        raise QgsProcessingException(tr("Cannot open the raster %s") % layer.source())
    gt = ds.GetGeoTransform()
    if abs(gt[2]) > 1e-12 or abs(gt[4]) > 1e-12 or gt[5] > 0:
        raise QgsProcessingException(tr("The raster must have a regular north-up grid (no rotation)."))
    crs = layer.crs()
    if not crs.isValid() or crs.isGeographic():
        raise QgsProcessingException(tr("The raster must be in a projected CRS in metres (not degrees)."))
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


class StylePostProcessor(QgsProcessingLayerPostProcessorInterface):
    """Applica lo stile a classi singole (con la tavolozza dei codici) al layer caricato in QGIS,
    anche quando il raster e' un file temporaneo (dove il file .qml accanto non viene letto)."""
    keep = []

    def __init__(self, qml):
        super().__init__()
        self.qml = qml
        StylePostProcessor.keep.append(self)

    def postProcessLayer(self, layer, context, feedback):
        if isinstance(layer, QgsRasterLayer):
            layer.loadNamedStyle(self.qml)
            layer.triggerRepaint()


def vector_export_layers():
    return core.VECTOR_LAYERS


class FillHazardAlgorithm(QgsProcessingAlgorithm):
    INPUT, BUILDINGS, OSM = "INPUT", "BUILDINGS", "OSM"
    BLD, BPX = "APPLY_BUILDINGS", "BUILDING_TOLERANCE"
    HOLES, AREA, ALL, GAP, HMODE = "APPLY_HOLES", "AREA", "ALL_HOLES", "GAP", "FILL_MODE"
    BUF, BUFPX = "APPLY_BUFFER", "BUFFER_WIDTH"
    OUT, OUT_CLEAN, OUT_VECTOR, CREATE_CLEAN = "OUTPUT", "OUTPUT_CLEAN", "OUTPUT_VECTOR", "CREATE_CLEAN"

    def name(self):
        return "fillhazard"

    def displayName(self):
        return tr("Fill holes in the hazard map")

    def group(self):
        return tr("Hazard maps")

    def groupId(self):
        return "hazard"

    def icon(self):
        return QIcon(os.path.join(HERE, "icon.svg"))

    def createInstance(self):
        return FillHazardAlgorithm()

    def helpUrl(self):
        return "file:///" + os.path.join(HERE, "help", "help_utilizzo.html").replace("\\", "/")

    def shortHelpString(self):
        return tr("help_fill")

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, tr("Hazard map (classes 0-3)")))
        self.addParameter(QgsProcessingParameterFeatureSource(self.BUILDINGS, tr("Buildings (polygons)"), [QgsProcessing.TypeVectorPolygon], optional=True))
        self.addParameter(QgsProcessingParameterEnum(self.OSM, tr("Buildings source"), [tr("provided buildings only"), tr("provided + add from OpenStreetMap"), tr("OpenStreetMap only")], defaultValue=0))
        self.addParameter(QgsProcessingParameterBoolean(self.BLD, tr("0. Apply buildings criterion"), True))
        self.addParameter(QgsProcessingParameterNumber(self.BPX, tr("   Buildings: tolerance from the edge (m)"), QgsProcessingParameterNumber.Double, 0.0, minValue=0, maxValue=100))
        self.addParameter(QgsProcessingParameterBoolean(self.HOLES, tr("1. Close interior zones"), True))
        self.addParameter(QgsProcessingParameterNumber(self.AREA, tr("   Interior zones: maximum area to close (m²)"), QgsProcessingParameterNumber.Double, 10.0, minValue=0, maxValue=100000))
        self.addParameter(QgsProcessingParameterBoolean(self.ALL, tr("   Close ALL interior zones (ignore the area)"), False))
        self.addParameter(QgsProcessingParameterNumber(self.GAP, tr("   Sealable gap (m, 0 = closed zones only)"), QgsProcessingParameterNumber.Double, 0.0, minValue=0))
        self.addParameter(QgsProcessingParameterEnum(self.HMODE, tr("   Fill value"), [tr("boundary maximum"), tr("most frequent boundary value (majority)"), tr("nearest")], defaultValue=1))
        self.addParameter(QgsProcessingParameterBoolean(self.BUF, tr("2. Graded buffer on class 0"), True))
        self.addParameter(QgsProcessingParameterNumber(self.BUFPX, tr("   Buffer: width (m)"), QgsProcessingParameterNumber.Double, 1.0, minValue=0.1, maxValue=1000))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUT, tr("Processed raster (with modification codes)")))
        self.addParameter(QgsProcessingParameterBoolean(self.CREATE_CLEAN, tr("Also create the clean raster (classes 0-3 only, no codes)"), False))
        self.addOutput(QgsProcessingOutputRasterLayer(self.OUT_CLEAN, tr("Clean raster (0-3 only)")))
        self.addParameter(QgsProcessingParameterFileDestination(self.OUT_VECTOR, tr("GeoPackage vector with codes (4 layers)"), "GeoPackage (*.gpkg)", optional=True, createByDefault=False))

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
        make_clean = self.parameterAsBool(parameters, self.CREATE_CLEAN, context)
        vec_path = self.parameterAsFileOutput(parameters, self.OUT_VECTOR, context) if self.OUT_VECTOR in parameters and parameters[self.OUT_VECTOR] else None

        feedback.pushInfo(tr("Reading raster..."))
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
                        raise QgsProcessingException(tr("No buildings vector given: choose a vector or an OpenStreetMap source."))
                else:
                    feedback.pushInfo(tr("Rasterizing provided buildings..."))
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
                    feedback.pushInfo(tr("  %d buildings provided") % len(wl))
            bid = user
            if osm:
                feedback.pushInfo(tr("Downloading buildings from OpenStreetMap..."))
                to_ll = QgsCoordinateTransform(crs, QgsCoordinateReferenceSystem("EPSG:4326"), context.transformContext())
                bb = to_ll.transformBoundingBox(rect)
                cache = os.path.join(tempfile.gettempdir(), "hazardfill_osm_cache")
                feedback.pushInfo(tr("(you can cancel at any time; if the service is slow you can provide the buildings as shapefile/GeoPackage)"))
                try:
                    rings = core.osm_buildings(bb.yMinimum(), bb.xMinimum(), bb.yMaximum(), bb.xMaximum(), cache_dir=cache, log=feedback.pushInfo,
                                               is_canceled=feedback.isCanceled)
                except core.Cancelled:
                    feedback.pushInfo(tr("Operation cancelled."))
                    return {}
                except RuntimeError as e:
                    raise QgsProcessingException(str(e))
                from_ll = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), crs, context.transformContext())
                wl = []
                for r in rings:
                    g = QgsGeometry.fromWkt("POLYGON((%s))" % ",".join("%.8f %.8f" % pt for pt in r))
                    g.transform(from_ll)
                    wl.append(g.asWkt())
                bo = rasterize_polys(wl, shape, gt, wkt)
                bid, nadd = core.merge_building_ids(user, bo)
                feedback.pushInfo(tr("  %d OSM buildings in the area, %d added") % (len(wl), nadd))
            if feedback.isCanceled():
                return {}

        feedback.pushInfo(tr("Processing (%d x %d pixels, %.2f m)...") % (shape[1], shape[0], res))
        out, code, st = core.process(h, bid, res, p)
        if "bld_total" in st:
            feedback.pushInfo(tr("Buildings modified: %d / %d") % (st["bld_changed"], st["bld_total"]))
        feedback.pushInfo(tr("Modified pixels per step (buildings / interior zones / buffer): %s") % st["mod_by_step"])
        feedback.pushInfo(tr("Pixels per class 0/1/2/3 before: %s  after: %s") % (st["orig"], st["new"]))

        params = json.dumps(dict(p, osm=osm, gap_m=self.parameterAsDouble(parameters, self.GAP, context)))
        base = dict(source=layer.source(), params=params, software="HazardFill %s" % core.__version__)
        write_tif(out_path, core.with_codes(out, code), gt, crs, dict(base, variant="codes",
                  codes="0=nodata/zero;1-3=original hazard;1x=modified by buildings;2x=by interior zones;3x=by buffer (x=level 1-3)"))
        res_d = {self.OUT: out_path}
        if context.willLoadLayerOnCompletion(out_path):                     # stile a classi singole sul raster caricato
            context.layerToLoadOnCompletionDetails(out_path).setPostProcessor(StylePostProcessor(_qml_file(False)))
        if make_clean:
            clean_path = os.path.splitext(out_path)[0] + tr("_clean.tif")
            write_tif(clean_path, out, gt, crs, dict(base, variant="clean", codes="0=nodata/zero;1=low;2=medium;3=high"))
            res_d[self.OUT_CLEAN] = clean_path
            det = QgsProcessingContext.LayerDetails(tr("Clean raster (0-3)"), context.project(), self.OUT_CLEAN)
            det.setPostProcessor(StylePostProcessor(_qml_file(True)))
            context.addLayerToLoadOnCompletion(clean_path, det)
        if vec_path:
            feedback.pushInfo(tr("Polygonizing (GeoPackage with 4 layers)..."))
            info = vector_export.write_gpkg(vec_path, h, out, core.with_codes(out, code), gt, wkt)
            feedback.pushInfo(tr("Layers written: %s") % ", ".join(tr("%s (%d polygons)") % kv for kv in info.items()))
            for name in vector_export_layers():
                context.addLayerToLoadOnCompletion("%s|layername=%s" % (vec_path, name),
                                                   QgsProcessingContext.LayerDetails(tr("Vector - ") + name, context.project(), self.OUT_VECTOR))
            res_d[self.OUT_VECTOR] = vec_path
        return res_d
