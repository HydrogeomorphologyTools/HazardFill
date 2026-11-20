# Pagina web locale

Una pagina web con il suo piccolo server **Python che gira sul tuo computer**: i dati non lasciano la macchina (tranne gli edifici OpenStreetMap, se li richiedi, e le tessere delle basi cartografiche).

## Installazione

Serve **Python 3.10 o successivo**. Su Windows è comodo installare i pacchetti con `pip` oppure con conda (`conda install -c conda-forge numpy scipy rasterio geopandas pyogrio shapely pyproj pillow`).

```bash
git clone https://github.com/HydrogeomorphologyTools/HazardFill.git
cd HazardFill/web
pip install -r requirements.txt
```

In alternativa scarica `HazardFill_web_<versione>.zip` dalle [release](https://github.com/HydrogeomorphologyTools/HazardFill/releases): contiene il server, la pagina, il nucleo di calcolo, l'help e l'esempio `Figna_test`.

## Avvio

```bash
python server.py                                  # esempio Figna_test (e dati in web/dati) -> http://localhost:8765
python server.py --data /percorso/aree            # una sottocartella per area
python server.py --data aree1 --data aree2=" (prove)"   # più cartelle, con un suffisso nel nome
python server.py --port 8800                      # altra porta
python server.py 192.168.1.20                     # ascolta anche su un altro indirizzo (es. IP VPN)
python server.py --workspace /cartella/lavoro     # dove salvare i file caricati dalla pagina
python server.py --no-upload                      # disattiva il caricamento dalla pagina
```

Su Windows puoi fare doppio clic su `avvia_hazardfill_web.bat` (Linux/macOS: `avvia_hazardfill_web.sh`). La prima volta il server prepara le immagini delle aree (da qualche secondo a un minuto).

## Come mettere i dati

**1. Cartella di dati** (`--data`, oppure `web/dati`): una sottocartella per area.

```
dati/
  MiaArea/
    Mappa_Pericolo.tif          (uno o più GeoTIFF)
    Edifici/
      edifici.shp               (facoltativo: .shp, .gpkg o .geojson)
```

**2. Dal computer, con la pagina**: apri **«Carica i tuoi dati»** sotto la scelta del caso, scrivi il nome dell'area, scegli il **GeoTIFF** e, se vuoi, gli **edifici** (shapefile compresso `.zip`, GeoPackage o GeoJSON) e premi *Carica*.
I file sono controllati (CRS proiettato, griglia con nord in alto, classi, geometrie) con avvisi chiari e salvati nella cartella di lavoro (`web/caricati` di partenza, area con suffisso «(caricati)»).

## La pagina

* **Caso** e **layer originali**: scelta dell'area, visualizzazione dei raster con opacità regolabile, contorni degli edifici.
* **Elaborazione**: i tre criteri con i loro slider (in **metri**; clic sul numero per **scriverlo a mano**, anche oltre il massimo dello slider). Accanto ai metri compare l'equivalente in pixel.
  *Evidenzia pixel modificati* mostra il tratteggio dei pixel cambiati; *sovrapponi originale* serve al confronto.
* **Statistiche**: m² per classe prima e dopo, edifici modificati, zone chiuse, pixel di buffer, pixel modificati per criterio.
* **Esporta mappa (immagine)**: PNG con titolo, legenda, nord e scala, a 150 dpi; scelta *come a schermo / solo originale / solo con riempimenti*; titolo libero.
* **Esporta mappatura**: raster con codici, raster pulito, stile QGIS `.qml`, **GeoPackage vettoriale** (4 livelli).
* **Basi**: OSM, satellite Esri, Sentinel-2 EOX, OpenTopoMap, **hillshade** calcolato dal DEM (Terrarium) e hillshade Esri.
* **Help – utilizzo**: link in alto, con esempi sintetici.

### Configurazione da URL
Puoi aprire la pagina già impostata (utile per condividere una configurazione):
`http://localhost:8765/?bld=1&bm=0.5&holes=1&area=10000&gap=30&buf=1&bufm=5&hmode=major`
(`bm` tolleranza edifici in m, `area` in m², `gap` in m, `bufm` buffer in m, `hmode` = `max` | `major` | `near`, `all=1` chiude tutte le zone, `osm=0|1|2`).

## Sicurezza e rete

* Il server **non ha autenticazione**. Ascolta solo su `127.0.0.1` a meno che tu non indichi altri indirizzi: non esporlo su internet.
* Se lo rendi raggiungibile da altri (VPN, rete locale), chi accede può **caricare file** nella cartella di lavoro: usa `--no-upload` per impedirlo.
* Il caricamento accetta solo GeoTIFF, `.zip` con shapefile, GeoPackage e GeoJSON, ha limiti di dimensione (3 GB raster, 400 MB edifici), pulisce i nomi dei file e non scrive fuori dalla cartella di lavoro.

## Problemi frequenti

| Sintomo | Causa / rimedio |
|---|---|
| «Nessuna area trovata» | indica `--data CARTELLA` o carica un GeoTIFF dalla pagina |
| La pagina è lenta alla prima apertura | il server prepara le immagini delle aree; dopo la prima volta restano in cache finché il server resta acceso |
| Sul calcolo con OSM passa molto tempo | il primo scaricamento da Overpass può richiedere decine di secondi (poi è in cache) |
| Raster rifiutato | controlla che sia in un CRS proiettato in metri, con nord in alto e classi 0-3 |
| Il browser non carica la pagina da un altro computer | avvia il server con l'indirizzo di quel computer e controlla il firewall |
