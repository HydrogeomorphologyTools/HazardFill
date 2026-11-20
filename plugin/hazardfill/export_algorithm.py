# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
"""Algoritmo di Processing: esporta la mappa con titolo, legenda, nord e scala (PNG, 150 dpi di default)."""
import datetime
import json
import os
import tempfile

from osgeo import gdal
from qgis.core import (QgsCoordinateTransform, QgsLayoutExporter, QgsLayoutItem, QgsLayoutItemLabel,
                       QgsLayoutItemLegend, QgsLayoutItemMap, QgsLayoutItemPicture, QgsLayoutItemScaleBar,
                       QgsLayoutPoint, QgsLayoutSize, QgsMapLayerLegendUtils, QgsPrintLayout, QgsProcessing,
                       QgsProcessingAlgorithm, QgsProcessingException, QgsProcessingParameterExtent,
                       QgsProcessingParameterBoolean, QgsProcessingParameterFileDestination, QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterNumber, QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterString, QgsProject, QgsRasterLayer, QgsTextFormat, QgsUnitTypes,
                       QgsApplication, QgsFillSymbol, QgsLegendStyle, QgsMapLayerType, QgsSingleSymbolRenderer, QgsWkbTypes)
from qgis.PyQt.QtCore import Qt, QSizeF
from qgis.PyQt.QtGui import QColor, QFont, QIcon

from . import core

HERE = os.path.dirname(__file__)


def raster_tags(path):
    ds = gdal.Open(path)
    md = ds.GetMetadata() if ds is not None else {}
    ds = None
    p = {}
    try:
        p = json.loads(md.get("params", "{}"))
    except Exception:
        pass
    return md.get("variant", "orig"), p


def fills_info(variant, p):
    """(attivi[list di passi 1..3], frase, riga parametri) come nella pagina web."""
    if variant not in ("codes", "clean"):
        return [], "", ""
    steps, where, par = [], [], []
    fm = lambda v: ("%g" % v).replace(".", ",")
    if p.get("bld"):
        steps.append(1)
        where.append("edifici")
        par.append("edifici %s m%s" % (fm(p.get("bm", p.get("bpx", 0))), {1: " (+OSM)", 2: " (solo OSM)"}.get(int(p.get("osm", 0)), "")))
    if p.get("holes"):
        steps.append(2)
        where.append("zone interne alla mappatura")
        a = "tutte" if p.get("all_holes") else "≤ %s m²" % fm(p.get("area", 10))
        gm = p.get("gap_m", 0)
        par.append("zone interne %s%s" % (a, (", varco %s m" % fm(gm)) if gm else ""))
    if p.get("buf"):
        steps.append(3)
        par.append("buffer %s m" % fm(p.get("bufm", p.get("bufpx", 1))))
    if not steps:
        return [], "", ""
    if where:
        sub = "Mappa di pericolosità con riempimenti in corrispondenza di " + " e ".join(where)
        if 3 in steps:
            sub += " e buffer graduato ai margini"
    else:
        sub = "Mappa di pericolosità con buffer graduato ai margini della mappatura"
    return steps, sub, "Parametri: " + " · ".join(par)


def nice_total(extent_w_m, frac=0.22):
    """Lunghezza totale della barra: minimo 100 m, al massimo ~frac della larghezza mappa."""
    best = 100.0
    for o in (100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000):
        if o <= extent_w_m * frac:
            best = float(o)
    return best


class ExportMapAlgorithm(QgsProcessingAlgorithm):
    HAZARD, EXTENT, LAYERS, TITLE, WIDTH, DPI, OUT = "HAZARD", "EXTENT", "LAYERS", "TITLE", "WIDTH_MM", "DPI", "OUTPUT"
    OUTLINE = "BUILDING_OUTLINE"

    def name(self):
        return "exportmap"

    def displayName(self):
        return "Esporta mappa con legenda, nord e scala (PNG)"

    def group(self):
        return "Mappe di pericolosità"

    def groupId(self):
        return "hazard"

    def icon(self):
        return QIcon(os.path.join(HERE, "icon.svg"))

    def createInstance(self):
        return ExportMapAlgorithm()

    def helpUrl(self):
        return "file:///" + os.path.join(HERE, "help", "help_utilizzo.html").replace("\\", "/")

    def shortHelpString(self):
        return (
            "<p>Crea un'immagine PNG della mappa con <b>titolo, legenda, freccia del nord e scala</b> (150 dpi). "
            "Stessa grafica della pagina web.</p>"
            "<p><b>Raster di pericolo</b>: il raster da descrivere in legenda (quello originale oppure quello elaborato "
            "da HazardFill). Se è elaborato, titolo e legenda riportano i riempimenti e <i>solo</i> i codici dei passi "
            "selezionati (11-13 edifici, 21-23 zone interne, 31-33 buffer).</p>"
            "<p><b>Layer da mostrare</b>: se vuoto, i layer visibili del progetto (basi, hillshade, edifici) nell'ordine del pannello Layer; "
            "il raster di pericolo viene messo in stile HazardFill.</p>"
            "<p><b>Estensione</b>: inquadratura (ad esempio 'calcola dal canvas'); vuota = estensione del raster.</p>"
            "<p>Scala: minimo 100 m, unità scritta una sola volta. Se i riempimenti sono attivi, il nome file contiene "
            "automaticamente la parola <i>riempimenti</i>.</p>")

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.HAZARD, "Raster di pericolo (originale o elaborato)"))
        self.addParameter(QgsProcessingParameterExtent(self.EXTENT, "Estensione della mappa", optional=True))
        self.addParameter(QgsProcessingParameterMultipleLayers(self.LAYERS, "Layer da mostrare (vuoto = layer visibili del progetto)", QgsProcessing.TypeMapLayer, optional=True))
        self.addParameter(QgsProcessingParameterString(self.TITLE, "Titolo (vuoto = nome del raster)", optional=True))
        self.addParameter(QgsProcessingParameterNumber(self.WIDTH, "Larghezza della mappa (mm)", QgsProcessingParameterNumber.Double, 250, minValue=80, maxValue=1000))
        self.addParameter(QgsProcessingParameterNumber(self.DPI, "Risoluzione (dpi)", QgsProcessingParameterNumber.Integer, 150, minValue=72, maxValue=600))
        self.addParameter(QgsProcessingParameterBoolean(self.OUTLINE, "Edifici (layer poligonali): solo contorno azzurro", True))
        self.addParameter(QgsProcessingParameterFileDestination(self.OUT, "Immagine PNG", "PNG (*.png)"))

    # ------------------------------------------------------------------
    def processAlgorithm(self, parameters, context, feedback):
        hazard = self.parameterAsRasterLayer(parameters, self.HAZARD, context)
        crs = hazard.crs()
        variant, p = raster_tags(hazard.source())
        steps, sub, parline = fills_info(variant, p)
        clean = variant != "codes"

        # clone con lo stile HazardFill (palette 0-3 oppure con codici)
        qml = os.path.join(tempfile.gettempdir(), "hazardfill_style_%s.qml" % ("clean" if clean else "codes"))
        with open(qml, "w", encoding="utf-8") as f:
            f.write(core.make_qml(clean))
        hz = QgsRasterLayer(hazard.source(), hazard.name())
        hz.loadNamedStyle(qml)

        # layer della mappa: scelti dall'utente oppure visibili nel progetto
        sel = self.parameterAsLayerList(parameters, self.LAYERS, context)
        if not sel:
            prj = context.project() or QgsProject.instance()
            root = prj.layerTreeRoot()
            sel = [l for l in root.layerOrder() if root.findLayer(l.id()) and root.findLayer(l.id()).isVisible()]
        layers = []
        placed = False
        for l in sel:
            if l.source() == hazard.source() or l.id() == hazard.id():
                if not placed:
                    layers.append(hz)
                    placed = True
            else:
                layers.append(l)
        if not placed:
            layers.insert(0, hz)

        bld_layers = []
        if self.parameterAsBool(parameters, self.OUTLINE, context):
            for i, l in enumerate(layers):
                if l is not hz and l.type() == QgsMapLayerType.VectorLayer and QgsWkbTypes.geometryType(l.wkbType()) == QgsWkbTypes.PolygonGeometry:
                    c = l.clone()
                    c.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple(
                        {"color": "0,0,0,0", "outline_color": "0,229,255", "outline_width": "0.3", "style": "no"})))
                    layers[i] = c
                    bld_layers.append(c)

        ext = self.parameterAsExtent(parameters, self.EXTENT, context, crs)
        if ext.isNull() or ext.isEmpty():
            ext = hazard.extent()
        W = self.parameterAsDouble(parameters, self.WIDTH, context)
        dpi = self.parameterAsInt(parameters, self.DPI, context)
        Hm = W * ext.height() / ext.width()
        TOP, BOT = 26.0, 7.0

        lay = QgsPrintLayout(QgsProject.instance())
        lay.initializeDefaults()
        lay.pageCollection().page(0).setPageSize(QgsLayoutSize(W, Hm + TOP + BOT))

        title = self.parameterAsString(parameters, self.TITLE, context).strip() or os.path.splitext(hazard.name())[0]
        lab = QgsLayoutItemLabel(lay)
        lab.setText(title)
        lab.setFont(QFont("Arial", 16, QFont.Bold))
        lab.attemptMove(QgsLayoutPoint(2, 1.5, QgsUnitTypes.LayoutMillimeters))
        lab.attemptResize(QgsLayoutSize(W - 4, 8))
        lay.addLayoutItem(lab)
        if sub:
            l2 = QgsLayoutItemLabel(lay)
            l2.setText(sub)
            l2.setFont(QFont("Arial", 10))
            l2.attemptMove(QgsLayoutPoint(2, 10, QgsUnitTypes.LayoutMillimeters))
            l2.attemptResize(QgsLayoutSize(W - 4, 6))
            lay.addLayoutItem(l2)
            l3 = QgsLayoutItemLabel(lay)
            l3.setText(parline)
            l3.setFont(QFont("Arial", 8))
            l3.setFontColor(QColor(100, 100, 100))
            l3.attemptMove(QgsLayoutPoint(2, 16.5, QgsUnitTypes.LayoutMillimeters))
            l3.attemptResize(QgsLayoutSize(W - 4, 5))
            lay.addLayoutItem(l3)

        m = QgsLayoutItemMap(lay)
        m.attemptMove(QgsLayoutPoint(0, TOP, QgsUnitTypes.LayoutMillimeters))
        m.attemptResize(QgsLayoutSize(W, Hm))
        m.setCrs(crs)
        m.setLayers(layers)
        m.setKeepLayerSet(True)
        m.setExtent(ext)
        m.setFrameEnabled(True)
        lay.addLayoutItem(m)

        # nord
        north = QgsLayoutItemPicture(lay)
        for cand in (os.path.join(QgsApplication.pkgDataPath(), "svg", "arrows", "NorthArrow_02.svg"),
                     ":/images/north_arrows/layout_default_north_arrow.svg"):
            if cand.startswith(":") or os.path.exists(cand):
                north.setPicturePath(cand)
                break
        north.setLinkedMap(m)
        north.attemptResize(QgsLayoutSize(14, 18))
        north.attemptMove(QgsLayoutPoint(W - 17, TOP + 3, QgsUnitTypes.LayoutMillimeters))
        north.setBackgroundEnabled(True)
        north.setBackgroundColor(QColor(255, 255, 255, 225))
        lay.addLayoutItem(north)

        # legenda: classi 1-3 e codici dei soli passi selezionati
        leg = QgsLayoutItemLegend(lay)
        leg.setLinkedMap(m)
        leg.setAutoUpdateModel(False)
        root = leg.model().rootGroup()
        root.clear()
        node = root.addLayer(hz)
        names = [r[0] for r in core.code_table(clean)]
        want = [1, 2, 3] + ([10 * s + k for s in steps for k in (1, 2, 3)] if not clean else [])
        nodes = leg.model().layerLegendNodes(node, True)
        shift = 1 if len(nodes) == len(names) + 1 else 0      # eventuale nodo di intestazione
        order = [names.index(v) + shift for v in want if v in names]
        QgsMapLayerLegendUtils.setLegendNodeOrder(node, order)
        node.setCustomProperty("legend/title-style", "hidden")
        node.setName("Pericolo")
        leg.model().refreshLayerLegend(node)
        for c in bld_layers:
            nb = root.addLayer(c)
            nb.setName("Edifici (contorni)")
            nb.setCustomProperty("legend/title-style", "hidden")
        leg.setTitle("")
        for sty, size, bold in ((QgsLegendStyle.Subgroup, 13, True), (QgsLegendStyle.SymbolLabel, 12, False)):
            fmt = QgsTextFormat()
            fmt.setFont(QFont("Arial", size, QFont.Bold if bold else QFont.Normal))
            fmt.setSize(size)
            leg.rstyle(sty).setTextFormat(fmt)
        leg.setSymbolWidth(10)
        leg.setSymbolHeight(6)
        leg.setBackgroundEnabled(True)
        leg.setBackgroundColor(QColor(255, 255, 255, 235))
        leg.setFrameEnabled(True)
        lay.addLayoutItem(leg)
        leg.adjustBoxSize()
        leg.setReferencePoint(QgsLayoutItem.LowerRight)
        leg.attemptMove(QgsLayoutPoint(W - 3, TOP + Hm - 3, QgsUnitTypes.LayoutMillimeters))

        # scala (doppia dimensione, minimo 100 m)
        ext_w_m = ext.width() * QgsUnitTypes.fromUnitToUnitFactor(crs.mapUnits(), QgsUnitTypes.DistanceMeters)
        total = nice_total(ext_w_m)
        sb = QgsLayoutItemScaleBar(lay)
        sb.setLinkedMap(m)
        sb.setStyle("Single Box")
        sb.setNumberOfSegmentsLeft(0)
        sb.setNumberOfSegments(2)
        if total >= 1000:
            sb.setUnits(QgsUnitTypes.DistanceKilometers)
            sb.setUnitLabel("km")
            sb.setUnitsPerSegment(total / 2000.0)
        else:
            sb.setUnits(QgsUnitTypes.DistanceMeters)
            sb.setUnitLabel("m")
            sb.setUnitsPerSegment(total / 2.0)
        fmt = QgsTextFormat()
        fmt.setFont(QFont("Arial", 12))
        fmt.setSize(12)
        sb.setTextFormat(fmt)
        sb.setBackgroundEnabled(True)
        sb.setBackgroundColor(QColor(255, 255, 255, 225))
        lay.addLayoutItem(sb)
        sb.attemptMove(QgsLayoutPoint(3, TOP + Hm - 16, QgsUnitTypes.LayoutMillimeters))

        foot = QgsLayoutItemLabel(lay)
        others = [l.name() for l in layers if l is not hz]
        foot.setText(("Layer: " + ", ".join(others) + " · " if others else "") + "HazardFill %s · %s" % (core.__version__, datetime.date.today().strftime("%d/%m/%Y")))
        foot.setFont(QFont("Arial", 7))
        foot.setFontColor(QColor(90, 90, 90))
        foot.attemptMove(QgsLayoutPoint(2, TOP + Hm + 1, QgsUnitTypes.LayoutMillimeters))
        foot.attemptResize(QgsLayoutSize(W - 4, 5))
        lay.addLayoutItem(foot)

        out = self.parameterAsFileOutput(parameters, self.OUT, context)
        base, ext_f = os.path.splitext(out)
        if steps and "riempiment" not in os.path.basename(base).lower():
            out = base + "_riempimenti" + (ext_f or ".png")
            feedback.pushInfo("Nome file con i riempimenti: %s" % out)
        settings = QgsLayoutExporter.ImageExportSettings()
        settings.dpi = dpi
        res = QgsLayoutExporter(lay).exportToImage(out, settings)
        if res != QgsLayoutExporter.Success:
            raise QgsProcessingException("Esportazione immagine non riuscita (codice %s)." % res)
        feedback.pushInfo("Immagine scritta: %s (%d dpi)" % (out, dpi))
        return {self.OUT: out}
