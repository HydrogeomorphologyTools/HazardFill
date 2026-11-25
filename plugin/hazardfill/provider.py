# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
import os

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .i18n import tr
from .algorithm import FillHazardAlgorithm
from .export_algorithm import ExportMapAlgorithm


class HazardFillProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(FillHazardAlgorithm())
        self.addAlgorithm(ExportMapAlgorithm())

    def id(self):
        return "hazardfill"

    def name(self):
        return "HazardFill"

    def longName(self):
        return tr("HazardFill - filling holes in hazard maps")

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "icon.svg"))
