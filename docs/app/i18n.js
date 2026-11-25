// HazardFill (HF) - interfaccia bilingue: inglese (predefinito) / italiano con la bandierina.
// Il testo inglese e' nell'HTML e nel codice; qui ci sono le traduzioni italiane. Condiviso da versione locale e GitHub Pages.
(function () {
  const IT = {
    tag: 'chiusura buchi nelle mappe di pericolosità',
    nodata: 'nodata assimilato a 0', origr: 'i raster sono quelli originali', help: 'Help &ndash; utilizzo',
    disc: 'Ausilio di pre-screening per i gestori del territorio: non è una mappatura di pericolosità né sostituisce la valutazione di esperti.',
    case: 'Caso', upl: 'Carica i tuoi dati',
    upinfo: 'GeoTIFF a una banda, in CRS proiettato (metri), con le sole classi 0-3 (nodata = 0). Edifici (facoltativi): shapefile compresso .zip, GeoPackage o GeoJSON. I file restano sul computer su cui gira il server.',
    folder: 'cartella', raster: 'raster', bldg: 'edifici', dirgo: 'Carica dalla cartella', orfiles: 'oppure scegli i singoli file:',
    aname: 'nome area', aph: 'es. MiaArea', load: 'Carica',
    h_orig: 'Layer originali (visualizza)', opac: 'Opacità', showb: 'edifici (contorni)', h_proc: 'Elaborazione', proclayer: 'Layer da elaborare',
    s0: '0. Edifici', s0d: "l'edificio prende il valore max che lo tocca o che è entro la tolleranza (m) dal bordo", tol: 'tolleranza', source: 'sorgente',
    o0: 'solo edifici forniti', o1: 'forniti + integra da OSM', o2: 'solo OSM',
    osmd: 'OSM: gli edifici vengono scaricati da OpenStreetMap (Overpass) per l\'estensione del raster; quelli già coperti dai tuoi (&ge;20% di sovrapposizione) non vengono aggiunti. La prima volta può richiedere qualche decina di secondi.',
    s1: '1. Chiusura zone interne', s1d: 'zone a 0 interne al dominio (non collegate al bordo del raster), circondate da valori &gt;0, con area ≤ A',
    gap: 'varco sigillabile', gapd: '0 = solo zone non collegate al bordo; &gt;0 = anche zone con aperture strette (&lt; varco) verso l\'esterno',
    allint: 'chiudi TUTTE le zone interne', noarea: '(nessun limite di area)', fillv: 'valore di riempimento',
    hmax: 'massimo del contorno', hmaj: 'maggioranza del contorno', hnear: 'pixel valido più vicino (sfumato)',
    s2: '2. Buffer graduato su classe 0', s2d: 'fascia (m) su classe 0 adiacente a valori validi, con valore −1 grado (min 1); non sovrascrive pixel validi', width: 'larghezza',
    hl: 'evidenzia pixel modificati (tratteggio scuro)', showorig: 'sovrapponi originale (confronto)', busy: 'calcolo…', h_stats: 'Statistiche',
    h_img: 'Esporta mappa (immagine)', imgd: 'PNG con titolo, legenda, freccia del nord e scala, come la vedi ora (base, hillshade, layer, edifici).',
    what: 'cosa', x_screen: 'come a schermo', x_orig: 'solo mappa originale', x_elab: 'solo mappa con riempimenti', xtph: 'titolo (vuoto = automatico)', xpng: 'Scarica immagine PNG',
    h_exp: 'Esporta mappatura', expd: 'Raster (GeoTIFF uint8 nella griglia originale) o vettoriale (GeoPackage) della mappatura elaborata, con i parametri attuali scritti nei metadati.',
    exp1: 'Raster con codici + stile QGIS', exp2: 'Solo classi 0-3 (+ stile)', expv: 'Vettoriale (GeoPackage) con codici',
    gpkgd: 'Il GeoPackage contiene 4 livelli (originale, omogeneizzata, mappa_con_codici, modifiche) con gli stessi codici del raster e lo stile QGIS incorporato; l\'esportazione può richiedere decine di secondi.',
    qmld: 'Il pulsante scarica il raster e il suo stile <code>.qml</code>: salvali nella stessa cartella (lo stesso nome) e QGIS mostra i valori a classi singole, dal giallo al rosso. Il GeoTIFF ha nodata = 0.',
    h_leg: 'Legenda e codici', l_code: 'codice', l_mean: 'significato', l0: 'nodata / nessun pericolo', l1: 'pericolo basso (originale)', l2: 'pericolo medio (originale)', l3: 'pericolo alto (originale)',
    l11: 'valore 1/2/3 assegnato da <b>edifici</b>', l21: 'valore 1/2/3 assegnato da <b>zone interne</b>', l31: 'valore 1/2/3 assegnato da <b>buffer graduato</b>',
    legn: 'Cifra delle decine = passo che ha modificato il pixel; unità = livello di pericolo. In mappa i pixel modificati sono tratteggiati con il colore del codice (più scuro del livello); nel file esportato "con codici" hanno 11–33.',
    // testi dinamici
    n0: 'nodata (0)', n1: '1 basso', n2: '2 medio', n3: '3 alto', st_orig: 'orig.', st_new: 'elab.',
    st_bld: 'edifici modificati: <b>{0}</b> / {1}<br>', st_holes: 'zone interne chiuse: <b>{0}</b><br>', st_buf: 'pixel di buffer: <b>{0}</b> ({1} m²)<br>',
    st_steps: 'pixel modificati per passo (edifici/buchi/buffer): {0}',
    prep_vec: 'preparo vettoriale…', prep_img: 'preparo immagine…', nobase: 'mappa base non inclusa (restrizioni del browser); layer, legenda, nord e scala sì.',
    clickval: 'clic per scrivere il valore',
    m_Hazard: 'Pericolo', m_low: 'basso', m_med: 'medio', m_high: 'alto', m_by: 'Valore assegnato da', m_bld: 'edifici', m_int: 'zone interne', m_buf: 'buffer', m_bout: 'edifici (contorni)',
    m_all: 'tutte', m_gap: ', varco {0} m', m_osmonly: ' (solo OSM)', m_osmplus: ' (+OSM)', p_bld: 'edifici {0} m{1}', p_int: 'zone interne {0}{1}', p_buf: 'buffer {0} m', par: 'Parametri: ',
    w_bld: 'edifici', w_int: 'zone interne alla mappatura', and: ' e ',
    sub1: 'Mappa di pericolosità con riempimenti in corrispondenza di {0}', sub1b: ' e buffer graduato ai margini', sub2: 'Mappa di pericolosità con buffer graduato ai margini della mappatura',
    base: 'Base: ', fn_screen: 'schermo', fn_fills: 'riempimenti',
    pickone: 'scegli almeno un file', needarea: "scrivi il nome dell'area", loading: 'carico {0} ({1} MB)…', pbuilds: ' ({0} edifici)', prepmap: 'preparo la mappa…', err: 'errore: {0}',
    d_none: '(nessuno: edifici solo da OpenStreetMap)', d_gpkg: ' (GeoPackage non supportato online: usa lo zip)', d_found: 'Trovati {0} raster e {1} file di edifici.',
    d_nozip: 'libreria zip non disponibile: comprimi lo shapefile in uno .zip e sceglilo', d_blds: 'carico gli edifici…', d_ok: 'caricato ✔', d_name: 'edifici.zip'
  };
  // errori e avvisi dei backend (scritti in inglese): [espressione, traduzione]
  const MSG = [
    [/^The raster must be a GeoTIFF \(\.tif\)$/, 'Il raster deve essere un GeoTIFF (.tif)'],
    [/^File too large \(maximum (\d+) (GB|MB)\)$/, 'File troppo grande (massimo $1 $2)'],
    [/^Buildings: zipped shapefile \(\.zip\), GeoPackage \(\.gpkg\) or GeoJSON$/, 'Edifici: shapefile compresso (.zip), GeoPackage (.gpkg) o GeoJSON'],
    [/^invalid upload type$/, 'tipo di caricamento non valido'], [/^upload interrupted$/, 'caricamento interrotto'], [/^upload disabled$/, 'caricamento disattivato'],
    [/^the raster must be in a projected coordinate system in metres \(not degrees\): reproject it before loading$/, 'il raster deve essere in un sistema di coordinate proiettato in metri (non in gradi): riproiettalo prima del caricamento'],
    [/^the raster must have a north-up grid, without rotation$/, 'il raster deve avere la griglia con il nord in alto, senza rotazione'],
    [/^the raster has (\d+) bands: the first one is used$/, 'il raster ha $1 bande: si usa la prima'],
    [/^values other than 0-3 \(e\.g\. (.*)\): non-integers are rounded and values >3 are set to 3; if the map uses other codes, reclassify it first$/, 'valori diversi da 0-3 (es. $1): i non interi sono arrotondati e i valori >3 portati a 3; se la mappa usa altri codici riclassificala prima'],
    [/^no shapefile \(\.shp\) found in the zip$/, "nello zip non c'è nessuno shapefile (.shp)"],
    [/^the buildings have no coordinate system \(missing \.prj file\?\)$/, 'gli edifici non hanno un sistema di coordinate (file .prj mancante?)'],
    [/^the buildings layer must contain polygons$/, 'il layer degli edifici deve contenere poligoni'],
    [/^(\d+) buildings with invalid geometry: they are rasterized anyway$/, '$1 edifici con geometria non valida: vengono rasterizzati comunque'],
    [/^coordinate system EPSG:(\d+) not recognised: reproject the raster to UTM \(e\.g\. EPSG:32632\) and try again$/, 'sistema di coordinate EPSG:$1 non riconosciuto: riproietta il raster in UTM (es. EPSG:32632) e riprova'],
    [/^raster too large for the browser \((\d+) million pixels, maximum (\d+)\): crop it or use the QGIS plugin or the local version$/, 'raster troppo grande per il browser ($1 milioni di pixel, massimo $2): ritaglialo oppure usa il plugin QGIS o la versione locale'],
    [/^the file is not a georeferenced GeoTIFF$/, 'il file non è un GeoTIFF georeferenziato'], [/^pixels must be square$/, 'i pixel devono essere quadrati'],
    [/^unrecognised coordinate system \(a projected EPSG code is needed\)$/, 'sistema di coordinate non riconosciuto (serve un codice EPSG proiettato)'],
    [/^buildings: zipped shapefile \(\.zip\) or GeoJSON \(a GeoPackage must first be exported to GeoJSON\)$/, 'edifici: shapefile compresso (.zip) oppure GeoJSON (un GeoPackage va prima esportato in GeoJSON)'],
    [/^the file contains no polygons$/, 'il file non contiene poligoni'],
    [/^building coordinates are not in degrees \(EPSG:4326\): for the shapefile include the \.prj file in the zip; for GeoJSON save as EPSG:4326$/, 'le coordinate degli edifici non sono in gradi (EPSG:4326): per lo shapefile includi il file .prj nello zip; per il GeoJSON salva in EPSG:4326'],
    [/^Overpass unreachable \((.*)\): try again later$/, 'Overpass non raggiungibile ($1): riprova più tardi'],
    [/^Overpass unreachable \((.*)\): try again later or provide the buildings as shapefile\/GeoPackage$/, "Overpass non raggiungibile ($1): riprova più tardi oppure fornisci gli edifici come shapefile/GeoPackage"],
    [/^no response within (\d+) s$/, 'nessuna risposta entro $1 s'],
    [/^area not loaded$/, 'area non caricata'], [/^replaced by a more recent request$/, 'sostituita da una richiesta più recente'],
    [/^load the GeoTIFF first$/, 'carica prima il GeoTIFF'], [/^calculation error: (.*)$/, 'errore nel calcolo: $1']
  ];
  const FLAG_IT = '<svg viewBox="0 0 3 2" width="22" height="15"><rect width="1" height="2" fill="#009246"/><rect x="1" width="1" height="2" fill="#fff"/><rect x="2" width="1" height="2" fill="#ce2b37"/></svg>';
  const FLAG_EN = '<svg viewBox="0 0 60 40" width="22" height="15"><rect width="60" height="40" fill="#012169"/><path d="M0,0 60,40M60,0 0,40" stroke="#fff" stroke-width="8"/><path d="M0,0 60,40M60,0 0,40" stroke="#c8102e" stroke-width="3"/><path d="M30,0V40M0,20H60" stroke="#fff" stroke-width="13"/><path d="M30,0V40M0,20H60" stroke="#c8102e" stroke-width="8"/></svg>';
  let lang = 'it';
  try { const q = new URLSearchParams(location.search).get('lang'); lang = q === 'it' || q === 'en' ? q : (localStorage.getItem('hf_lang') === 'en' ? 'en' : 'it'); } catch (e) {}
  const fmt = (s, a) => s.replace(/\{(\d+)\}/g, (m, i) => a[+i]);
  // T(chiave, testo inglese, ...argomenti)
  window.T = function (k, en, ...a) { const x = lang === 'it' ? (IT[k] !== undefined ? IT[k] : (window.HF_IT_EXTRA || {})[k]) : undefined; return fmt(x !== undefined ? x : en, a); };
  window.trMsg = function (s) {
    s = String(s); if (lang !== 'it') return s;
    for (const [re, it] of MSG) if (re.test(s)) return s.replace(re, it);
    return s;
  };
  window.HF_LANG = () => lang;
  window.HF_DEC = () => (lang === 'it' ? ',' : '.');
  function apply() {
    Object.assign(IT, window.HF_IT_EXTRA || {});
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i]').forEach(el => {
      if (el.dataset.en === undefined) el.dataset.en = el.innerHTML;
      el.innerHTML = lang === 'it' && IT[el.dataset.i] !== undefined ? IT[el.dataset.i] : el.dataset.en;
    });
    document.querySelectorAll('[data-ip]').forEach(el => {
      if (el.dataset.en === undefined) el.dataset.en = el.placeholder;
      el.placeholder = lang === 'it' && IT[el.dataset.ip] !== undefined ? IT[el.dataset.ip] : el.dataset.en;
    });
    const b = document.getElementById('langbtn');
    if (b) b.innerHTML = lang === 'en' ? FLAG_IT + '<span>Italiano</span>' : FLAG_EN + '<span>English</span>';
    const h = document.getElementById('helplink');
    if (h) h.href = h.href.split('?')[0] + '?lang=' + lang;
    const de = document.documentElement; if (de.dataset.t0 === undefined) de.dataset.t0 = document.title;
    document.title = lang === 'it' && window.HF_TITLE_IT ? window.HF_TITLE_IT : de.dataset.t0;
    if (window.onLangChange) window.onLangChange(lang);
  }
  window.setLang = function (l) { lang = l; try { localStorage.setItem('hf_lang', l); } catch (e) {} apply(); };
  window.HF_applyLang = apply;
  document.addEventListener('DOMContentLoaded', () => {
    const b = document.getElementById('langbtn');
    if (b) b.onclick = () => setLang(lang === 'en' ? 'it' : 'en');
    apply();
  });
})();
