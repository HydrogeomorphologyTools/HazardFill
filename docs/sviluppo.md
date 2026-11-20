# Sviluppo e test

## Struttura del repository

```
HazardFill/
├── plugin/hazardfill/      plugin QGIS (provider e algoritmi di Processing, export mappa, vettoriale)
│   ├── core.py             nucleo di calcolo (solo numpy + scipy), condiviso con la pagina web
│   ├── algorithm.py        algoritmo «Chiusura buchi nella mappa di pericolosità»
│   ├── export_algorithm.py algoritmo «Esporta mappa con legenda, nord e scala (PNG)»
│   ├── vector_export.py    poligonizzazione con GDAL e stili nel GeoPackage
│   ├── help/               pagina «Help – utilizzo» (generata da tools/)
│   └── metadata.txt
├── web/                    server Python + pagina (index.html) e script di avvio
├── examples/Figna_test/    dati di prova
├── docs/                   documentazione e immagini
├── tests/                  test automatici (pytest) e test del plugin con QGIS
└── tools/                  generazione di help, figure e release
```

## Test

Test automatici (nucleo e server web; richiedono i pacchetti di `web/requirements.txt` e `pytest`):

```bash
pip install -r web/requirements.txt pytest
python -m pytest tests -q
```

Test del plugin con QGIS (senza interfaccia grafica), con il Python di QGIS:

```bat
"C:\Program Files\QGIS 3.34.11\bin\python-qgis-ltr.bat" tests\qgis_headless.py
```

Il test confronta il plugin con il nucleo pixel per pixel, controlla il GeoPackage (livelli, geometrie, stile, aree), gli errori attesi e l'esportazione della mappa.
Su altri sistemi imposta `QGIS_PREFIX` (es. `/usr`).

I test su GitHub (`.github/workflows/tests.yml`) eseguono la parte con pytest.

## Help e figure

L'Help è un unico HTML generato dal codice (gli esempi sono **calcolati con `core.py`**, così non possono contraddire il comportamento reale):

```bash
python tools/build_help.py          # sorgente tools/help_src.html -> plugin/hazardfill/help/help_utilizzo.html
python tools/make_figures.py        # figure sintetiche in docs/images
```

`tools/make_plugin_figure.py` genera con QGIS l'immagine di esempio dell'esportazione del plugin.

## Release

```bash
python tools/build_help.py
python tools/build_release.py       # crea dist/HazardFill_plugin_<v>.zip e dist/HazardFill_web_<v>.zip
```

1. Aggiorna `__version__` in `plugin/hazardfill/core.py`, `version=` in `plugin/hazardfill/metadata.txt`, `CITATION.cff` e `CHANGELOG.md`.
2. Esegui i test, costruisci la release, crea un tag (`v1.0.0`) e una release su GitHub allegando i due zip.

## Note di progetto

* Mantieni **`core.py` privo di dipendenze GIS** (solo numpy/scipy): è ciò che garantisce plugin e web identici.
* Nuovi criteri o parametri vanno aggiunti prima in `core.process`, poi esposti in plugin e pagina, con test in `tests/test_core.py`.
* I valori predefiniti sono esempi di partenza: cambiali con cautela e riportalo nel `CHANGELOG`.

## Licenza

GNU GPL v2. Aggiungendo un file Python inserisci l'intestazione di licenza usata negli altri.
