# Plugin QGIS

Compatibile con **QGIS 3.22 o successivo** (provato con 3.34 LTR). Richiede solo numpy e scipy, già inclusi in QGIS (installatore standalone per Windows, pacchetti ufficiali per Linux e macOS).

## Installazione

**Da ZIP (consigliato)**
1. Scarica `HazardFill_plugin_<versione>.zip` dalle [release](https://github.com/HydrogeomorphologyTools/HazardFill/releases).
2. *Plugin → Gestisci e installa plugin → Installa da ZIP* → seleziona il file → *Installa*.

**Dai sorgenti**: copia la cartella `plugin/hazardfill` in quella dei plugin del tuo profilo QGIS
(`%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins` su Windows; `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins` su Linux), riavvia QGIS e attiva **HazardFill (HF)** in *Gestisci e installa plugin → Installati*.

## Dove si trova

* Menu **Raster → HazardFill**: *Apri cartella di dati…* (sceglie una cartella, trova raster ed edifici, fa scegliere su quali lavorare con due menù a tendina, li carica nel progetto e apre l'algoritmo già compilato), *Elabora mappa di pericolosità…*, *Esporta mappa con legenda, nord e scala (PNG)…*, *Aggiungi basi cartografiche…*, *Help – utilizzo*.
* Pannello **Processing**, gruppo *HazardFill → Mappe di pericolosità*: gli stessi algoritmi, quindi utilizzabili in **batch**, nei **modelli grafici** e da riga di comando.

## Algoritmo «Chiusura buchi nella mappa di pericolosità» (`hazardfill:fillhazard`)

| Parametro | Nome (Processing) | Valore di partenza |
|---|---|---|
| Mappa di pericolosità (classi 0-3) | `INPUT` | — |
| Edifici (poligoni, facoltativi con OSM) | `BUILDINGS` | — |
| Sorgente edifici: 0 forniti · 1 forniti + OpenStreetMap · 2 solo OpenStreetMap | `OSM` | 0 |
| 0. Applica criterio edifici | `APPLY_BUILDINGS` | sì |
| Edifici: tolleranza dal bordo (m) | `BUILDING_TOLERANCE` | 0 |
| 1. Chiudi zone interne | `APPLY_HOLES` | sì |
| Zone interne: area massima da chiudere (m², fino a 100 000) | `AREA` | 10 |
| Chiudi TUTTE le zone interne | `ALL_HOLES` | no |
| Varco sigillabile (m, 0 = solo zone chiuse) | `GAP` | 0 |
| Valore di riempimento: 0 massimo · 1 maggioranza · 2 più vicino | `FILL_MODE` | 1 |
| 2. Buffer graduato su classe 0 | `APPLY_BUFFER` | sì |
| Buffer: larghezza (m) | `BUFFER_WIDTH` | 1 |
| **Raster con codici** | `OUTPUT` | (obbligatorio) |
| Crea anche il raster pulito (0-3, `<nome>_pulito.tif`) | `CREATE_CLEAN` | no |
| Vettoriale GeoPackage con codici (4 livelli) | `OUTPUT_VECTOR` | facoltativo |

* Gli edifici sono letti direttamente dal layer, senza il filtro di QGIS sulle geometrie non valide.
* Di default si crea **un solo raster** (con codici), mostrato a **classi singole** dal giallo al rosso: lo stile è applicato al caricamento (anche per i file temporanei) e salvato come `.qml` accanto al file. Nel GeoPackage i poligoni modificati hanno un **retino** per criterio (edifici oblique, zone interne orizzontali, buffer verticali). Il GeoPackage ha lo stile incorporato; i suoi livelli sono aggiunti al progetto a fine elaborazione.
* In «Registro» compaiono il numero di edifici modificati, i pixel modificati per criterio e il conteggio dei pixel per classe prima e dopo.

## Algoritmo «Esporta mappa con legenda, nord e scala (PNG)» (`hazardfill:exportmap`)

Crea un'immagine con **titolo, legenda, freccia del nord e scala** (layout di stampa di QGIS, 150 dpi di partenza).

| Parametro | Nome | Note |
|---|---|---|
| Raster di pericolo (originale o elaborato) | `HAZARD` | quello da descrivere in legenda; se è elaborato, titolo e legenda riportano i criteri applicati (letti dai metadati del file) |
| Estensione della mappa | `EXTENT` | facoltativa, anche «calcola dal canvas»; vuota = estensione del raster |
| Layer da mostrare | `LAYERS` | vuoto = i layer visibili del progetto, nell'ordine del pannello Layer (basi, hillshade, edifici…) |
| Titolo | `TITLE` | vuoto = nome del raster |
| Larghezza della mappa (mm) | `WIDTH_MM` | 250 |
| Risoluzione (dpi) | `DPI` | 150 |
| Edifici (layer poligonali): solo contorno azzurro | `BUILDING_OUTLINE` | sì |
| Immagine PNG | `OUTPUT` | se i riempimenti sono attivi, `_riempimenti` è aggiunto al nome |

La legenda contiene le classi 1-3 e **solo i codici dei criteri applicati**; la scala ha lunghezza minima 100 m.

## Basi cartografiche

*Raster → HazardFill → Aggiungi basi cartografiche* inserisce in fondo al pannello Layer il gruppo **Basi HazardFill** con satellite Esri, hillshade Esri, Sentinel-2 (EOX), OpenTopoMap e OpenStreetMap (visibile solo la prima).
Ogni base appartiene al suo fornitore e va usata nel rispetto delle condizioni d'uso; mantieni le attribuzioni quando pubblichi le mappe.

## Uso da riga di comando

Con `qgis_process` (installato con QGIS):

```bash
qgis_process plugins enable hazardfill
qgis_process run hazardfill:fillhazard -- INPUT=mappa.tif BUILDINGS=edifici.shp \
    BUILDING_TOLERANCE=0.5 AREA=10000 GAP=30 FILL_MODE=1 BUFFER_WIDTH=5 \
    OUTPUT=elaborata.tif CREATE_CLEAN=true OUTPUT_VECTOR=elaborata.gpkg
```

## Problemi frequenti

| Messaggio | Causa | Rimedio |
|---|---|---|
| «Il raster deve essere in un CRS proiettato in metri» | raster in gradi (EPSG:4326) | riproietta il raster (*Raster → Proiezioni → Riproietta*) |
| «Nessun vettore di edifici indicato…» | né edifici né sorgente OSM | indica un layer di edifici oppure scegli una sorgente OpenStreetMap |
| «Overpass non raggiungibile» | nessuna connessione o servizio sovraccarico | riprova più tardi: i riquadri già scaricati sono in cache |
| Memoria insufficiente | raster molto grande | ritaglia l'area (*Raster → Estrazione → Ritaglia*) o aumenta la RAM |
| Legenda con codici non desiderati | passi attivi nell'elaborazione | la legenda riporta i criteri che erano attivi quando il raster è stato creato |
