# Formati e codici

## Dati in ingresso

### Mappa di pericolosità (raster)
* GeoTIFF (o altro formato GDAL nel plugin), **una banda**, griglia regolare con **nord in alto** (senza rotazione).
* **CRS proiettato in metri** (es. EPSG:32632). I CRS geografici (gradi) sono rifiutati.
* Classi ammesse: **0** nessun pericolo / fuori dal dominio / nodata, **1** basso, **2** medio, **3** alto.
* Il NoData (anche −9999, NaN) e i negativi diventano 0; i non interi sono arrotondati; i valori > 3 sono portati a 3 (la pagina web avvisa quando carichi un raster con valori fuori scala).

### Edifici (facoltativi)
* Poligoni in shapefile, GeoPackage o GeoJSON, **qualsiasi CRS** (sono riproiettati nel CRS del raster). Non servono attributi.
* Nella pagina web lo shapefile si carica come `.zip` con `.shp`, `.shx`, `.dbf`, `.prj`.
* Le geometrie non valide sono accettate (la rasterizzazione le tratta comunque).
* In alternativa o in aggiunta: edifici da OpenStreetMap (vedi [metodo](metodo.md)).

## Uscite

| Uscita | Formato | Contenuto |
|---|---|---|
| **Raster con codici** | GeoTIFF uint8, LZW, nodata = 0, stessa griglia dell'originale | valori 0-3 (non modificato) e 11-13, 21-23, 31-33 (modificato); stile `.qml` con lo stesso nome |
| **Raster pulito** | GeoTIFF uint8 | solo 0-3 (versione omogeneizzata da usare), stile `.qml` |
| **Vettoriale** | GeoPackage | 4 livelli (sotto), geometrie valide, stile categorizzato incorporato |
| **Immagine della mappa** | PNG 150 dpi | titolo, legenda, nord, scala |

### Codici

La cifra delle **decine** è il criterio che ha modificato il pixel, l'**unità** la classe assegnata:

| Codice | Significato |
|---|---|
| 0 | nodata / nessun pericolo |
| 1, 2, 3 | pericolo originale basso, medio, alto (non modificato) |
| 11, 12, 13 | classe 1/2/3 assegnata dal criterio **edifici** |
| 21, 22, 23 | classe 1/2/3 assegnata dal criterio **zone interne** |
| 31, 32, 33 | classe 1/2/3 assegnata dal criterio **buffer** |

Esempio: **23** = pericolo alto (3) assegnato da una zona interna (2).

### Metadati del GeoTIFF
Nei tag (*Proprietà → Informazioni* in QGIS): `source` (file di origine), `params` (parametri usati, in JSON), `codes` (legenda dei codici), `software`, `variant` (`codes` o `clean`).

### GeoPackage vettoriale

| Livello | Contenuto | Campi |
|---|---|---|
| `originale` | classi 1-3 della mappa di partenza | `classe`, `area_m2` |
| `omogeneizzata` | classi 1-3 dopo i riempimenti | `classe`, `area_m2` |
| `mappa_con_codici` | tutti i codici (1-3 e 11-33) | `codice`, `classe`, `criterio`, `area_m2` |
| `modifiche` | solo i poligoni modificati (11-33) | `codice`, `classe`, `criterio`, `area_m2` |

`criterio` vale `originale`, `edifici`, `zone interne` o `buffer`. I poligoni nascono dalla poligonizzazione dei pixel (pixel adiacenti con lo stesso valore uniti, 4-connessi):
geometrie valide, senza sovrapposizioni né vuoti, bordi a gradini; la somma delle aree di ogni codice coincide con quella dei pixel del raster.

### Immagine della mappa
Titolo (automatico o scelto), sotto — se ci sono riempimenti — una frase che indica dove sono stati applicati (es. «con riempimenti in corrispondenza di edifici e zone interne alla mappatura») e i parametri usati;
legenda con le classi e, **solo per i criteri selezionati**, i codici; freccia del nord; scala (minimo 100 m, unità scritta una sola volta). Il nome file contiene la parola **riempimenti** quando i riempimenti sono attivi.
