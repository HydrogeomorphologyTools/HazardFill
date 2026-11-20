# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
"""Finestra «Apri cartella di dati»: sceglie una cartella, trova raster ed edifici e fa scegliere su quali lavorare."""
import os

from qgis.PyQt.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                                 QLineEdit, QPushButton, QVBoxLayout)

from . import core

NONE = "(nessuno: edifici solo da OpenStreetMap)"


class FolderDialog(QDialog):
    def __init__(self, parent=None, folder=""):
        super().__init__(parent)
        self.setWindowTitle("HazardFill - apri cartella di dati")
        self.setMinimumWidth(560)
        self.found = {"rasters": [], "buildings": []}
        self.root = ""
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Scegli la cartella: vengono cercati i raster di pericolosità (.tif) e gli edifici (.shp, .gpkg, .geojson, .zip) anche nelle sottocartelle."))
        row = QHBoxLayout()
        self.path = QLineEdit(folder)
        btn = QPushButton("Sfoglia…")
        btn.clicked.connect(self.browse)
        row.addWidget(self.path)
        row.addWidget(btn)
        lay.addLayout(row)
        form = QFormLayout()
        self.cb_raster = QComboBox()
        self.cb_build = QComboBox()
        form.addRow("Mappa di pericolosità", self.cb_raster)
        form.addRow("Edifici", self.cb_build)
        lay.addLayout(form)
        self.info = QLabel("")
        lay.addWidget(self.info)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Carica e apri l'algoritmo")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        self.path.editingFinished.connect(self.scan)
        if folder:
            self.scan()

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, "Cartella dei dati", self.path.text() or "")
        if d:
            self.path.setText(d)
            self.scan()

    def scan(self):
        folder = self.path.text().strip()
        self.cb_raster.clear()
        self.cb_build.clear()
        self.root = folder
        if not folder or not os.path.isdir(folder):
            self.found = {"rasters": [], "buildings": []}
            self.info.setText("")
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
            return
        self.found = core.scan_folder(folder)
        rel = lambda p: os.path.relpath(p, folder)       # noqa: E731
        for p in self.found["rasters"]:
            self.cb_raster.addItem(rel(p), p)
        self.cb_build.addItem(NONE, None)
        for p in self.found["buildings"]:
            self.cb_build.addItem(rel(p), p)
        if self.found["buildings"]:
            self.cb_build.setCurrentIndex(1)
        self.info.setText("Trovati %d raster e %d file di edifici." % (len(self.found["rasters"]), len(self.found["buildings"])))
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(bool(self.found["rasters"]))

    def selection(self):
        """(percorso del raster, percorso degli edifici o None)"""
        return self.cb_raster.currentData(), self.cb_build.currentData()
