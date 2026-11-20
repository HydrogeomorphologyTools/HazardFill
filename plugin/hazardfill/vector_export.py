# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
"""Export vettoriale (GeoPackage) del plugin: poligonizza con GDAL i raster elaborati, con gli stessi 4 livelli
e gli stessi codici della pagina web (originale, omogeneizzata, mappa_con_codici, modifiche)."""
import os

import numpy as np
from osgeo import gdal, ogr, osr

from . import core


def _mem(arr, gt, wkt, dtype):
    ds = gdal.GetDriverByName("MEM").Create("", arr.shape[1], arr.shape[0], 1, dtype)
    ds.SetGeoTransform(gt)
    ds.SetProjection(wkt)
    ds.GetRasterBand(1).WriteArray(arr)
    return ds


def _poly_layer(gpkg, name, arr, mask, gt, wkt, with_codes):
    src = _mem(arr.astype(np.int16), gt, wkt, gdal.GDT_Int16)
    msk = _mem(mask.astype(np.uint8), gt, wkt, gdal.GDT_Byte)
    srs = osr.SpatialReference()
    srs.ImportFromWkt(wkt)
    lyr = gpkg.CreateLayer(name, srs, ogr.wkbPolygon)
    first = "codice" if with_codes else "classe"
    lyr.CreateField(ogr.FieldDefn(first, ogr.OFTInteger))
    if with_codes:
        lyr.CreateField(ogr.FieldDefn("classe", ogr.OFTInteger))
        lyr.CreateField(ogr.FieldDefn("criterio", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("area_m2", ogr.OFTReal))
    gdal.Polygonize(src.GetRasterBand(1), msk.GetRasterBand(1), lyr, 0, [])   # 4-connesso (predefinito GDAL)
    lyr.StartTransaction()
    n = 0
    f = lyr.GetNextFeature()
    while f is not None:
        g = f.GetGeometryRef()
        if not g.IsValid():
            f.SetGeometry(g.Buffer(0))
            g = f.GetGeometryRef()
        v = f.GetField(first)
        if with_codes:
            f.SetField("classe", core.classe_of(v))
            f.SetField("criterio", core.criterio_of(v))
        f.SetField("area_m2", round(g.GetArea(), 3))
        lyr.SetFeature(f)
        n += 1
        f = lyr.GetNextFeature()
    lyr.CommitTransaction()
    return n


def write_gpkg(path, original, clean, codes, gt, crs_wkt):
    """original/clean/codes: array 0-3 / 0-3 / 0-33. Ritorna {livello: n_poligoni}."""
    if os.path.exists(path):
        os.remove(path)
    ds = ogr.GetDriverByName("GPKG").CreateDataSource(path)
    info = {}
    info["originale"] = _poly_layer(ds, "originale", original, original > 0, gt, crs_wkt, False)
    info["omogeneizzata"] = _poly_layer(ds, "omogeneizzata", clean, clean > 0, gt, crs_wkt, False)
    info["mappa_con_codici"] = _poly_layer(ds, "mappa_con_codici", codes, codes > 0, gt, crs_wkt, True)
    info["modifiche"] = _poly_layer(ds, "modifiche", codes, codes >= 10, gt, crs_wkt, True)
    ds = None                                   # chiude e scrive il file
    core.add_gpkg_styles(path, core.vector_styles())
    return info
