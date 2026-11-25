# Spona_test — dati di prova

> **Questi sono dati di prova.** Non rappresentano mappature di pericolosità ufficiali né valutazioni reali: sono un caso test **derivato da idrogrammi non «calati» nel contesto locale**, usato in un corso, e servono **soltanto a provare HazardFill (HF)**. Non vanno usati per alcuna valutazione o decisione.

| File | Contenuto |
|---|---|
| `Mappa_Pericolo_Spona.tif` | raster di pericolosità «grezzo» di prova, 1 m, EPSG:32632, classi 0 (nodata), 1 basso, 2 medio, 3 alto |
| `Edifici/Edifici.shp` (+ `.shx`, `.dbf`, `.prj`, `.cpg`) | poligoni degli edifici (186, EPSG:32632) |
| `Edifici_Spona_test.zip` | gli stessi edifici in uno **shapefile compresso**, comodo da scaricare |
| `Edifici_Spona_test.gpkg` | gli stessi edifici in **GeoPackage** |

**Un edificio è stato volutamente tolto** dallo shapefile ma è presente nel modello digitale del terreno usato: scegliendo la sorgente edifici **«forniti + OpenStreetMap»** HazardFill lo recupera da OpenStreetMap (è l'esempio dell'integrazione con OSM; il primo scaricamento può richiedere qualche decina di secondi).

Come usarli: [`docs/esempio-spona-test.md`](../../docs/esempio-spona-test.md).
