# Documentazione di HazardFill (HF)

> **Avvertenza.** HazardFill è un ausilio di pre-screening per i gestori del territorio nella fase di valutazione finale della mappatura del pericolo,
> per una scelta e una gestione più consapevoli del vincolo da apporre sul territorio. Non produce mappe di pericolosità e non sostituisce
> la modellazione né la valutazione di esperti.

| Documento | Contenuto |
|---|---|
| [Metodo](metodo.md) | cosa fa ciascun criterio, come si decide «interno/esterno», ordine dei passi, esempi sintetici, limiti |
| [Plugin QGIS](plugin-qgis.md) | installazione, algoritmi, parametri, uso da Processing/riga di comando, basi cartografiche |
| [Pagina web locale](web-locale.md) | installazione, avvio, cartella dei dati, caricamento file, esportazioni, uso da altri computer |
| [Versione online](versione-online.md) | la pagina su GitHub Pages: uso, limiti, differenze dalla versione locale |
| [Formati e codici](formati-e-codici.md) | dati in ingresso, uscite, codici dei pixel modificati, metadati |
| [Esempio Spona_test](esempio-spona-test.md) | passo-passo sui dati di prova, con immagini |
| [Sviluppo e test](sviluppo.md) | struttura del repository, test, costruzione delle release |

Lo strumento contiene anche una pagina **Help – utilizzo** (menu del plugin; link nella pagina web) con gli stessi esempi.

## In una pagina

1. Prepara la mappa di pericolosità con **solo le classi 0, 1, 2, 3** (0 = nessun pericolo/nodata) in un CRS proiettato in metri, e, se li hai, gli edifici.
2. Scegli i criteri: **edifici**, **zone interne**, **buffer sul margine**. I valori proposti sono esempi di partenza.
3. Guarda dove la mappa è cambiata (i pixel modificati hanno un codice proprio) e regola i parametri.
4. Esporta: raster con codici, raster pulito, vettoriale GeoPackage, mappa PNG con legenda, nord e scala.
5. La scelta finale dei parametri e del vincolo resta al decisore.
