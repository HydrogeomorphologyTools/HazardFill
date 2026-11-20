# Versione online (GitHub Pages)

**https://hydrogeomorphologytools.github.io/HazardFill/** → pulsante «Prova la versione online».

È la stessa pagina della versione locale, ma **il calcolo avviene nel tuo browser**: non serve installare nulla e i file non vengono inviati a nessun server.

> **Per provare, non per un uso intensivo.** La versione online è pensata per **provare lo strumento con dati non troppo pesanti**, non per un uso massivo o continuo.
> Per lavorare con regolarità, su raster grandi o per produrre i risultati ufficiali, la scelta migliore per il singolo utente è il **plugin QGIS** ([guida](plugin-qgis.md)); in alternativa la [pagina web locale](web-locale.md).

## Come si usa

1. Apri il link e premi **«Prova la versione online»**.
2. Nella sezione **«Carica i tuoi dati»** (già aperta):
   * premi **«Carica l'esempio (Figna_test)»** per provare subito con i dati di prova; oppure
   * scrivi un nome per l'area, scegli il **GeoTIFF** e, se vuoi, gli **edifici** (shapefile compresso `.zip` con il `.prj`, oppure GeoJSON in EPSG:4326) e premi **«Carica»**.
3. Imposta i criteri come nella pagina locale (edifici, zone interne, buffer; valori in metri; sorgente edifici anche da **OpenStreetMap**) e guarda le statistiche e la mappa.
4. Esporta: **raster con codici**, **raster pulito**, **stile QGIS (.qml)** e **immagine PNG** con titolo, legenda, nord e scala.

La prima apertura scarica Python e le librerie scientifiche (qualche decina di MB, poi in cache del browser): può servire fino a un minuto. Poi i calcoli sono rapidi
(circa 1-2 secondi sull'esempio, circa 15 secondi per un raster da 11,6 milioni di pixel con varco di 30 m).

Si può anche aprire la pagina già impostata con i parametri nell'indirizzo (utile per condividere una configurazione):
`…/app/?bld=1&bm=0.5&holes=1&area=10000&gap=30&buf=1&bufm=5&hmode=major`

## Cosa cambia rispetto alla versione locale

| | Online (browser) | Locale / plugin |
|---|---|---|
| Installazione | nessuna | Python o QGIS |
| Dove girano i calcoli | nel tuo browser | sul tuo computer |
| Dimensione dei dati | fino a qualche decina di milioni di pixel (limite: memoria del browser) | limitata dalla RAM del computer |
| Raster | GeoTIFF in CRS proiettato (UTM, Monte Mario/Gauss-Boaga, ETRS89-UTM e altri EPSG) | qualsiasi formato GDAL |
| Edifici | `.zip` (shapefile) o GeoJSON; OpenStreetMap | anche GeoPackage |
| **Vettoriale GeoPackage** | **non disponibile** | **disponibile** |
| Basi | OSM, satellite Esri, OpenTopoMap, hillshade | + Sentinel-2 |

I risultati sono **identici** a quelli della versione locale e del plugin: il calcolo è lo stesso codice Python (`core.py`) eseguito nel browser con [Pyodide](https://pyodide.org). Lo abbiamo verificato pixel per pixel
(stessi conteggi dei pixel modificati e raster esportati uguali) sull'esempio, con edifici forniti, con OpenStreetMap e su un raster di 11,6 milioni di pixel.

## Limiti e avvertenze

* **Uso**: pensata per prove, non per un uso massivo o continuo. Ogni utente calcola sul proprio computer, quindi non c'è un server da sovraccaricare, ma la pagina dipende da servizi di terzi (vedi sotto) che hanno proprie condizioni d'uso.
* **Memoria**: i raster molto grandi possono esaurire la memoria del browser; sopra 60 milioni di pixel il caricamento è rifiutato (ritaglia l'area o usa il plugin).
* **Browser**: funziona con le versioni recenti di Chrome, Edge, Firefox e Safari; serve una connessione internet per scaricare le librerie e le carte.
* **Edifici OpenStreetMap**: scaricati da Overpass, servizio pubblico a volte lento o occupato: l'operazione riprova su più server ed espone un errore chiaro se non riesce.
* **Sistemi di coordinate**: sono riconosciuti i più comuni; per altri codici EPSG la pagina cerca la definizione su epsg.io; in caso di dubbio riproietta il raster in UTM.
* **NoData**: come ovunque, assimilato a 0 (vedi [metodo](metodo.md)).

## Servizi di terzi utilizzati

Librerie da CDN jsDelivr (Pyodide, GeoTIFF.js, proj4js, shpjs) e Leaflet; carte di OpenStreetMap, Esri, OpenTopoMap; DEM Terrarium su AWS Open Data per l'hillshade; Overpass (OpenStreetMap) per gli edifici.
Ognuno ha le proprie condizioni d'uso e attribuzioni (le trovi nella carta e nell'immagine esportata).

## Come è fatta (per chi sviluppa)

* La pagina `docs/app/index.html` è **generata** da `web/index.html` con `python tools/build_pages.py`: la stessa interfaccia parla con un «backend» (il server Python oppure `backend-browser.js`).
* `hf-worker.js` carica Pyodide con numpy e scipy ed esegue `core.py` in un Web Worker (la pagina resta reattiva).
* `backend-browser.js` legge il GeoTIFF (GeoTIFF.js), gestisce le proiezioni (proj4js), rasterizza gli edifici, prepara la visualizzazione in Web Mercator e scrive i GeoTIFF.
* Test: vedi [sviluppo](sviluppo.md).
