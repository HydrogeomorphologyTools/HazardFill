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

from .provider import HazardFillProvider

HERE = os.path.dirname(__file__)
MANUAL = os.path.join(HERE, "help", "help_utilizzo.html")

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
    grp = root.findGroup("Basi HazardFill") or root.addGroup("Basi HazardFill")
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

    def initGui(self):
        self.provider = HazardFillProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)
        run = self._act("Elabora mappa di pericolosità…", lambda: self._dlg("hazardfill:fillhazard"))
        self._act("Esporta mappa con legenda, nord e scala (PNG)…", lambda: self._dlg("hazardfill:exportmap"))
        self._act("Aggiungi basi cartografiche (satellite, hillshade, ...)", self.basemaps)
        self._act("Help – utilizzo", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(MANUAL)))
        self.iface.addToolBarIcon(run)

    def _dlg(self, alg):
        import processing
        processing.execAlgorithmDialog(alg)

    def basemaps(self):
        n = add_basemaps()
        self.iface.messageBar().pushInfo("HazardFill", "Basi aggiunte: %d (gruppo 'Basi HazardFill'; ne è visibile una sola)." % n)

    def unload(self):
        for a in self.actions:
            self.iface.removePluginRasterMenu("HazardFill", a)
        if self.actions:
            self.iface.removeToolBarIcon(self.actions[0])
        self.actions = []
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
