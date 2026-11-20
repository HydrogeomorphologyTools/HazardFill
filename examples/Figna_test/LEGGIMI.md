# Figna_test — dati di prova

> **Questi sono dati di prova.** Non rappresentano mappature di pericolosità reali né ufficiali e **non vanno usati per alcuna valutazione o decisione**:
> servono soltanto a mostrare come funziona HazardFill (HF).

| File | Contenuto |
|---|---|
| `Mappa_Pericolo_V1.tif` | raster di pericolosità di prova, 0,5 m, EPSG:32632, classi 0 (nodata), 1 basso, 2 medio, 3 alto |
| `Edifici/Edifici.shp` (+ `.shx`, `.dbf`, `.prj`, `.cpg`) | poligoni degli edifici dell'area (802 edifici, EPSG:4326) |
| `Edifici_Figna_test.zip` | gli stessi edifici in uno **shapefile compresso**, comodo da scaricare (QGIS lo apre direttamente; la pagina web lo accetta così com'è) |
| `Edifici_Figna_test.gpkg` | gli stessi edifici in **GeoPackage** |

Origine: risultati di una simulazione preliminare per l'area di Figna, riprodotti qui a solo scopo dimostrativo.

Come usarli: [`docs/esempio-figna-test.md`](../../docs/esempio-figna-test.md).
