# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
"""Lingua del plugin: inglese (predefinito) o italiano. La scelta e' nelle impostazioni di QGIS (HazardFill/lang);
fuori da QGIS si puo' usare la variabile d'ambiente HAZARDFILL_LANG=it. Il testo inglese e' nel codice, qui l'italiano."""
import os


def lang():
    env = os.environ.get("HAZARDFILL_LANG")
    if env in ("it", "en"):
        return env
    try:
        from qgis.PyQt.QtCore import QSettings
        return "en" if QSettings().value("HazardFill/lang", "it") == "en" else "it"
    except Exception:
        return "it"


def set_lang(code):
    from qgis.PyQt.QtCore import QSettings
    QSettings().setValue("HazardFill/lang", "it" if code == "it" else "en")


def tr(text):
    """Traduce il testo inglese `text` (o una chiave 'help_*') nella lingua scelta."""
    if lang() == "it":
        return IT.get(text, text)
    return EN.get(text, text)


EN = {
    'help_fill': '<p><i>Pre-screening aid for land managers in the final assessment of hazard mapping: it does not produce hazard maps and does not replace expert assessment.</i></p><p>Corrects classified hazard maps (<b>0</b> no hazard/nodata, <b>1</b> low, <b>2</b> medium, <b>3</b> high) by removing unrealistic islands of no hazard. Default values are <i>starting examples</i>, not definitive parameters.</p><p><b>Inputs</b>: single-band raster in a projected CRS (metres) with <b>only</b> these classes (nodata and negatives = 0); polygon buildings in any CRS (optional if OpenStreetMap is used).</p><h4>The steps, with examples (1 m pixels)</h4><p><b>0 Buildings.</b> Each building takes the <i>maximum</i> value that touches it or lies within the tolerance (m) of its edge. E.g. a 3×3 building with only its first column at hazard 2 &rarr; with tolerance 0 m the whole building is 2; if there is a cell at 3 next to it and the tolerance is 1 m &rarr; all 3. Distances in metres are converted to pixels with the raster resolution.</p><p><b>1 Interior zones.</b> Fills zones at 0 surrounded by hazard (not connected to the raster edge) with area &le; A m². E.g. two holes of 4 m² and 12 m² &rarr; with A=5 only the first is closed; with &laquo;Close ALL&raquo; both.</p><p><b>Sealable gap</b> (m): with 0 only completely enclosed interiors count; with 3 m a zone connected to the outside through a passage narrower than 3 m is considered interior (e.g. an embankment with a single opening).</p><p><b>Fill value</b>: most frequent boundary value (default), maximum (cautious), or nearest. E.g. boundary with 3 above, 1 on the left and 2 elsewhere &rarr; most frequent = 2, maximum = 3, nearest = mixed 1/2/3.</p><p><b>2 Buffer.</b> Band of given width (m) on class 0 adjacent to valid pixels with the value of the nearest one &minus;1 degree (min 1). E.g. edge at 3 &rarr; buffer 2; edge at 2 &rarr; 1; edge at 1 &rarr; 1. It does not overwrite valid pixels.</p><h4>Outputs</h4><p>Raster with codes: tens = step (1 buildings, 2 interior zones, 3 buffer), units = assigned level (e.g. <b>23</b> = high hazard assigned by an interior zone); and, if requested, a clean 0-3 raster. Each with a .qml style.</p><p>For the image with legend, north and scale use the &laquo;Export map&raquo; algorithm. Full help with figures: menu Raster &rarr; HazardFill &rarr; Help.</p>',
    'help_export': "<p>Creates a PNG image of the map with <b>title, legend, north arrow and scale</b> (150 dpi). Same graphics as the web page.</p><p><b>Hazard raster</b>: the raster to describe in the legend (the original or the one processed by HazardFill). If processed, the title and legend report the fills and <i>only</i> the codes of the selected steps (11-13 buildings, 21-23 interior zones, 31-33 buffer).</p><p><b>Layers to show</b>: if empty, the visible layers of the project (basemaps, hillshade, buildings) in the Layers panel order; the hazard raster is given the HazardFill style.</p><p><b>Extent</b>: framing (for example 'calculate from canvas'); empty = raster extent.</p><p>Scale: minimum 100 m, unit written once. If fills are active, the file name automatically contains the word <i>fills</i> (<i>riempimenti</i>).</p>",
}

IT = {
    'Cannot open the raster %s': 'Impossibile aprire il raster %s',
    'The raster must have a regular north-up grid (no rotation).': 'Il raster deve avere griglia regolare con nord in alto (senza rotazione).',
    'The raster must be in a projected CRS in metres (not degrees).': 'Il raster deve essere in un CRS proiettato in metri (non gradi).',
    'Fill holes in the hazard map': 'Chiusura buchi nella mappa di pericolosità',
    'Hazard maps': 'Mappe di pericolosità',
    'Hazard map (classes 0-3)': 'Mappa di pericolosità (classi 0-3)',
    'Buildings (polygons)': 'Edifici (poligoni)',
    'Buildings source': 'Sorgente edifici',
    'provided buildings only': 'solo edifici forniti',
    'provided + add from OpenStreetMap': 'forniti + integra da OpenStreetMap',
    'OpenStreetMap only': 'solo OpenStreetMap',
    '0. Apply buildings criterion': '0. Applica criterio edifici',
    '   Buildings: tolerance from the edge (m)': '   Edifici: tolleranza dal bordo (m)',
    '1. Close interior zones': '1. Chiudi zone interne',
    '   Interior zones: maximum area to close (m²)': '   Zone interne: area massima da chiudere (m²)',
    '   Close ALL interior zones (ignore the area)': "   Chiudi TUTTE le zone interne (ignora l'area)",
    '   Sealable gap (m, 0 = closed zones only)': '   Varco sigillabile (m, 0 = solo zone chiuse)',
    '   Fill value': '   Valore di riempimento',
    'boundary maximum': 'massimo del contorno',
    'most frequent boundary value (majority)': 'più frequente del contorno (maggioranza)',
    'nearest': 'più vicino',
    '2. Graded buffer on class 0': '2. Buffer graduato su classe 0',
    '   Buffer: width (m)': '   Buffer: larghezza (m)',
    'Processed raster (with modification codes)': 'Raster elaborato (con codici di modifica)',
    'Also create the clean raster (classes 0-3 only, no codes)': 'Crea anche il raster pulito (solo classi 0-3, senza codici)',
    'Clean raster (0-3 only)': 'Raster pulito (solo 0-3)',
    'GeoPackage vector with codes (4 layers)': 'Vettoriale GeoPackage con codici (4 livelli)',
    'No buildings vector given: choose a vector or an OpenStreetMap source.': 'Nessun vettore di edifici indicato: scegli un vettore oppure una sorgente OpenStreetMap.',
    'Reading raster...': 'Lettura raster...',
    'Rasterizing provided buildings...': 'Rasterizzazione edifici forniti...',
    '  %d buildings provided': '  %d edifici forniti',
    'Downloading buildings from OpenStreetMap...': 'Download edifici da OpenStreetMap...',
    '(you can cancel at any time; if the service is slow you can provide the buildings as shapefile/GeoPackage)': "(puoi annullare in qualsiasi momento; se il servizio e' lento puoi fornire gli edifici come shapefile/GeoPackage)",
    'Operation cancelled.': 'Operazione annullata.',
    '  %d OSM buildings in the area, %d added': "  %d edifici OSM nell'area, %d aggiunti",
    'Processing (%d x %d pixels, %.2f m)...': 'Elaborazione (%d x %d pixel, %.2f m)...',
    'Buildings modified: %d / %d': 'Edifici modificati: %d / %d',
    'Modified pixels per step (buildings / interior zones / buffer): %s': 'Pixel modificati per passo (edifici / zone interne / buffer): %s',
    'Pixels per class 0/1/2/3 before: %s  after: %s': 'Pixel per classe 0/1/2/3 prima: %s  dopo: %s',
    'Clean raster (0-3)': 'Raster pulito (0-3)',
    'Polygonizing (GeoPackage with 4 layers)...': 'Poligonizzazione (GeoPackage con 4 livelli)...',
    'Layers written: %s': 'Livelli scritti: %s',
    '%s (%d polygons)': '%s (%d poligoni)',
    'Vector - ': 'Vettoriale - ',
    '_clean.tif': '_pulito.tif',
    'Export map with legend, north and scale (PNG)': 'Esporta mappa con legenda, nord e scala (PNG)',
    'Hazard raster (original or processed)': 'Raster di pericolo (originale o elaborato)',
    'Map extent': 'Estensione della mappa',
    'Layers to show (empty = visible project layers)': 'Layer da mostrare (vuoto = layer visibili del progetto)',
    'Title (empty = raster name)': 'Titolo (vuoto = nome del raster)',
    'Map width (mm)': 'Larghezza della mappa (mm)',
    'Resolution (dpi)': 'Risoluzione (dpi)',
    'Buildings (polygon layers): light-blue outline only': 'Edifici (layer poligonali): solo contorno azzurro',
    'PNG image': 'Immagine PNG',
    'Hazard': 'Pericolo',
    'Buildings (outlines)': 'Edifici (contorni)',
    'File name with fills: %s': 'Nome file con i riempimenti: %s',
    'Image export failed (code %s).': 'Esportazione immagine non riuscita (codice %s).',
    'Image written: %s (%d dpi)': 'Immagine scritta: %s (%d dpi)',
    'Layers: ': 'Layer: ',
    'buildings': 'edifici',
    ' (+OSM)': ' (+OSM)',
    ' (OSM only)': ' (solo OSM)',
    'zones inside the mapping': 'zone interne alla mappatura',
    'all': 'tutte',
    'buildings %s m%s': 'edifici %s m%s',
    'interior zones %s%s': 'zone interne %s%s',
    ', gap %s m': ', varco %s m',
    'buffer %s m': 'buffer %s m',
    'Hazard map with fills at ': 'Mappa di pericolosità con riempimenti in corrispondenza di ',
    ' and ': ' e ',
    ' and graded buffer at the edges': ' e buffer graduato ai margini',
    'Hazard map with graded buffer at the edges of the mapping': 'Mappa di pericolosità con buffer graduato ai margini della mappatura',
    'Parameters: ': 'Parametri: ',
    '_fills': '_riempimenti',
    'HazardFill - filling holes in hazard maps': 'HazardFill - chiusura buchi nelle mappe di pericolosità',
    'HazardFill - open data folder': 'HazardFill - apri cartella di dati',
    'Choose the folder: hazard rasters (.tif) and buildings (.shp, .gpkg, .geojson, .zip) are searched for, also in subfolders.': 'Scegli la cartella: vengono cercati i raster di pericolosità (.tif) e gli edifici (.shp, .gpkg, .geojson, .zip) anche nelle sottocartelle.',
    'Browse…': 'Sfoglia…',
    'Hazard map': 'Mappa di pericolosità',
    'Buildings': 'Edifici',
    'Load and open the algorithm': "Carica e apri l'algoritmo",
    'Data folder': 'Cartella dei dati',
    'Found %d rasters and %d building files.': 'Trovati %d raster e %d file di edifici.',
    '(none: buildings from OpenStreetMap only)': '(nessuno: edifici solo da OpenStreetMap)',
    'Process hazard map…': 'Elabora mappa di pericolosità…',
    'Open data folder…': 'Apri cartella di dati…',
    'Export map with legend, north and scale (PNG)…': 'Esporta mappa con legenda, nord e scala (PNG)…',
    'Add basemaps (satellite, hillshade, ...)': 'Aggiungi basi cartografiche (satellite, hillshade, ...)',
    'Help – usage': 'Help – utilizzo',
    "Basemaps added: %d (group 'HazardFill basemaps'; only one is visible).": "Basi aggiunte: %d (gruppo 'Basi HazardFill'; ne è visibile una sola).",
    'help_fill': "<p><i>Ausilio di pre-screening per i gestori del territorio nella fase di valutazione finale della mappatura del pericolo: non produce mappe di pericolosità e non sostituisce la valutazione di esperti.</i></p><p>Corregge le mappe di pericolosità a classi (<b>0</b> nessun pericolo/nodata, <b>1</b> basso, <b>2</b> medio, <b>3</b> alto) eliminando le isole di assenza di pericolo non realistiche. I valori predefiniti sono <i>esempi di partenza</i>, non parametri definitivi.</p><p><b>Ingressi</b>: raster a una banda in CRS proiettato (metri) con <b>solo</b> queste classi (nodata e negativi = 0); edifici poligonali in qualsiasi CRS (opzionali se si usa OpenStreetMap).</p><h4>I passi, con esempi (pixel da 1 m)</h4><p><b>0 Edifici.</b> Ogni edificio prende il valore <i>massimo</i> che lo tocca o che è entro la tolleranza (m) dal bordo. Es.: edificio 3×3 con solo la prima colonna a pericolo 2 &rarr; con tolleranza 0 m tutto l'edificio vale 2; se accanto c'è una cella a 3 e la tolleranza è 1 m &rarr; tutto 3. Le distanze in metri sono convertite in pixel con la risoluzione del raster.</p><p><b>1 Zone interne.</b> Riempie le zone a 0 circondate da pericolo (non collegate al bordo del raster) con area &le; A m². Es.: due buchi di 4 m² e 12 m² &rarr; con A=5 si chiude solo il primo; con «Chiudi TUTTE» entrambi.</p><p><b>Varco sigillabile</b> (m): con 0 conta solo l'interno completamente chiuso; con 3 m una zona collegata all'esterno da un passaggio più stretto di 3 m è considerata interna (es. argine con una sola apertura).</p><p><b>Valore di riempimento</b>: più frequente del contorno (predefinito), massimo (prudente), oppure più vicino. Es.: contorno con 3 sopra, 1 a sinistra e 2 altrove &rarr; più frequente = 2, massimo = 3, più vicino = misto 1/2/3.</p><p><b>2 Buffer.</b> Fascia di larghezza data (m) sulla classe 0 adiacente a pixel validi con valore del più vicino &minus;1 grado (min 1). Es.: bordo a 3 &rarr; buffer 2; bordo a 2 &rarr; 1; bordo a 1 &rarr; 1. Non sovrascrive pixel validi.</p><h4>Uscite</h4><p>Raster con codici: decine = passo (1 edifici, 2 zone interne, 3 buffer), unità = livello assegnato (es. <b>23</b> = pericolo alto assegnato da zona interna); e, se richiesto, raster pulito 0-3. Ciascuno con stile .qml.</p><p>Per l'immagine con legenda, nord e scala usa l'algoritmo «Esporta mappa». Help completo con figure: menu Raster &rarr; HazardFill &rarr; Help &ndash; utilizzo.</p>",
    'help_export': "<p>Crea un'immagine PNG della mappa con <b>titolo, legenda, freccia del nord e scala</b> (150 dpi). Stessa grafica della pagina web.</p><p><b>Raster di pericolo</b>: il raster da descrivere in legenda (quello originale oppure quello elaborato da HazardFill). Se è elaborato, titolo e legenda riportano i riempimenti e <i>solo</i> i codici dei passi selezionati (11-13 edifici, 21-23 zone interne, 31-33 buffer).</p><p><b>Layer da mostrare</b>: se vuoto, i layer visibili del progetto (basi, hillshade, edifici) nell'ordine del pannello Layer; il raster di pericolo viene messo in stile HazardFill.</p><p><b>Estensione</b>: inquadratura (ad esempio 'calcola dal canvas'); vuota = estensione del raster.</p><p>Scala: minimo 100 m, unità scritta una sola volta. Se i riempimenti sono attivi, il nome file contiene automaticamente la parola <i>riempimenti</i>.</p>",
}
