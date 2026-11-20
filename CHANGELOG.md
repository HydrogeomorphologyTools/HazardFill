# Changelog

## 1.1.0 — 2026-11-20
* **Versione online (GitHub Pages)**: la pagina funziona interamente nel browser (Pyodide con numpy/scipy, GeoTIFF.js, proj4js, shpjs): caricamento di GeoTIFF ed edifici (zip shapefile o GeoJSON), edifici OpenStreetMap, esportazione di raster con codici, raster pulito, stile QGIS e immagine PNG. Risultati identici a quelli del server e del plugin. Pensata per prove con dati non troppo pesanti; il vettoriale resta nel plugin e nella versione locale.
* La pagina web parla con un «backend» (server Python oppure browser); aggiunta la configurazione da URL.
* Correzioni: i file ausiliari `.tif.aux.xml` non sono più scambiati per raster; il plugin è utilizzabile da `qgis_process`.

## 1.0.0 — 2026-11-20
Prima versione stabile. Plugin QGIS e pagina web locale con lo stesso nucleo di calcolo.

* **Criteri**: edifici (tolleranza in metri, 0 m di partenza), zone interne (area, tutte, varco sigillabile; riempimento per maggioranza di partenza, massimo o più vicino), buffer graduato sul margine (larghezza in metri, 1 m di partenza).
* **Edifici**: forniti (shapefile, GeoPackage, GeoJSON), integrati o ricavati da OpenStreetMap.
* **Tracciabilità**: codici `classe + 10 × criterio` nei raster e nei vettoriali.
* **Esporta mappatura**: raster con codici, raster pulito, stile QGIS, GeoPackage vettoriale a 4 livelli con stile incorporato.
* **Esporta mappa**: PNG a 150 dpi con titolo, legenda dei soli criteri applicati, nord e scala.
* **Pagina web**: basi cartografiche e hillshade, statistiche, confronto con l'originale, caricamento di GeoTIFF ed edifici dal computer, configurazione da URL.
* **Plugin**: algoritmi di Processing (batch, modelli grafici, `qgis_process`), basi cartografiche, Help – utilizzo.
* Esempio **Figna_test** (dati di prova) e documentazione.
