# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
import os

from qgis.core import QgsApplication, QgsProject, QgsRasterLayer
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import QAction

from .i18n import lang, set_lang, tr
from .provider import HazardFillProvider

HERE = os.path.dirname(__file__)
MANUAL = os.path.join(HERE, "help", "help_utilizzo.html")
FLAGS = {"it": os.path.join(HERE, "flag_it.svg"), "en": os.path.join(HERE, "flag_en.svg")}

# basi cartografiche (come nella pagina web); (nome, url XYZ, zmax, visibile)
BASEMAPS = [
    ("Satellite Esri", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", 19, True),
    ("Hillshade Esri", "https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}", 15, False),
    ("Sentinel-2 EOX (cloudless 2021)", "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/g/{z}/{y}/{x}.jpg", 14, False),
    ("OpenTopoMap", "https://tile.opentopomap.org/{z}/{x}/{y}.png", 17, False),
    ("OpenStreetMap", "https://tile.openstreetmap.org/{z}/{x}/{y}.png", 19, False),
]


def add_basemaps():
    """Aggiunge le basi XYZ in un gruppo in fondo al pannello Layer. Ritorna il numero di layer aggiunti."""
    prj = QgsProject.instance()
    root = prj.layerTreeRoot()
    grp = root.findGroup("HazardFill basemaps") or root.findGroup("Basi HazardFill") or root.addGroup("HazardFill basemaps")
    n = 0
    have = {c.name() for c in grp.children()}
    for name, url, zmax, vis in BASEMAPS:
        if name in have:
            continue
        uri = "type=xyz&url=%s&zmax=%d&zmin=0" % (url.replace("{", "%7B").replace("}", "%7D"), zmax)
        lyr = QgsRasterLayer(uri, name, "wms")
        if not lyr.isValid():
            continue
        prj.addMapLayer(lyr, False)
        node = grp.addLayer(lyr)
        node.setItemVisibilityChecked(vis)
        n += 1
    # il gruppo in fondo, sotto ai dati
    clone = grp.clone()
    root.insertChildNode(len(root.children()), clone)
    root.removeChildNode(grp)
    return n


class HazardFillPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.actions = []

    def _act(self, text, slot, icon=True):
        a = QAction(QIcon(os.path.join(HERE, "icon.svg")) if icon else QIcon(), text, self.iface.mainWindow())
        a.triggered.connect(slot)
        self.iface.addPluginToRasterMenu("HazardFill", a)
        self.actions.append(a)
        return a

    def initProcessing(self):
        """Registra gli algoritmi di Processing (anche per qgis_process, senza interfaccia grafica)."""
        if self.provider is None:
            self.provider = HazardFillProvider()
            QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()
        run = self._act(tr("Process hazard map…"), lambda: self._dlg("hazardfill:fillhazard"))
        self._act(tr("Open data folder…"), self.open_folder)
        self._act(tr("Export map with legend, north and scale (PNG)…"), lambda: self._dlg("hazardfill:exportmap"))
        self._act(tr("Add basemaps (satellite, hillshade, ...)"), self.basemaps)
        self._act(tr("Help – usage"), self.open_help)
        other = "it" if lang() == "en" else "en"
        a = QAction(QIcon(FLAGS[other]), "Italiano" if other == "it" else "English", self.iface.mainWindow())
        a.triggered.connect(self.toggle_language)
        self.iface.addPluginToRasterMenu("HazardFill", a)
        self.actions.append(a)
        self.iface.addToolBarIcon(run)

    def open_help(self):
        url = QUrl.fromLocalFile(MANUAL)
        url.setQuery("lang=" + lang())
        QDesktopServices.openUrl(url)

    def toggle_language(self):
        """Inglese <-> italiano: menu, algoritmi e help seguono la scelta (salvata nelle impostazioni di QGIS)."""
        set_lang("it" if lang() == "en" else "en")
        self.unload()
        self.initGui()
        self.iface.messageBar().pushInfo("HazardFill", "Language: English" if lang() == "en" else "Lingua: italiano")

    def _dlg(self, alg):
        import processing
        processing.execAlgorithmDialog(alg)

    def open_folder(self):
        """Sceglie una cartella, carica raster ed edifici trovati e apre l'algoritmo gia' compilato."""
        import processing
        from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer
        from .folder_dialog import FolderDialog
        dlg = FolderDialog(self.iface.mainWindow())
        if not dlg.exec_():
            return
        rpath, bpath = dlg.selection()
        if not rpath:
            return
        rl = QgsRasterLayer(rpath, os.path.splitext(os.path.basename(rpath))[0])
        params = {}
        if rl.isValid():
            QgsProject.instance().addMapLayer(rl)
            params["INPUT"] = rl.id()
        if bpath:
            vl = QgsVectorLayer(bpath, os.path.splitext(os.path.basename(bpath))[0], "ogr")
            if vl.isValid():
                QgsProject.instance().addMapLayer(vl)
                params["BUILDINGS"] = vl.id()
        else:
            params["OSM"] = 2
        processing.execAlgorithmDialog("hazardfill:fillhazard", params)

    def basemaps(self):
        n = add_basemaps()
        self.iface.messageBar().pushInfo("HazardFill", tr("Basemaps added: %d (group 'HazardFill basemaps'; only one is visible).") % n)

    def unload(self):
        for a in self.actions:
            self.iface.removePluginRasterMenu("HazardFill", a)
        if self.actions:
            self.iface.removeToolBarIcon(self.actions[0])
        self.actions = []
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
