# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
"""Esempi sintetici per l'help: piccole griglie calcolate con il codice vero (core.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugin", "hazardfill"))
import numpy as np
import core

COL = {0: "#ffffff", 1: "#ffeb3b", 2: "#ff8c00", 3: "#d62828"}
DARK = {1: 0.72, 2: 0.55, 3: 0.38}
STEP_LAB = {1: "edifici", 2: "zone interne", 3: "buffer"}

LANG = "it"
EN = {
    "Prima": "Before",
    "edificio (bordo azzurro): solo la 1ª colonna ha pericolo 2": "building (blue outline): only its 1st column has hazard 2",
    "Dopo, tolleranza 0 m": "After, tolerance 0 m",
    "tutto l'edificio prende il massimo che lo tocca: 2": "the whole building takes the maximum touching it: 2",
    "Dopo, tolleranza 1 m": "After, tolerance 1 m",
    "entra anche la cella a pericolo 3 entro 1 m: tutto 3": "the hazard-3 cell within 1 m is included: all 3",
    "due zone a 0 interne: 4 m² e 12 m² (pixel da 1 m)": "two interior zones at 0: 4 m² and 12 m² (1 m pixels)",
    "Area ≤ 5 m²": "Area ≤ 5 m²",
    "si chiude solo la piccola": "only the small one is closed",
    "Chiudi TUTTE": "Close ALL",
    "si chiudono entrambe": "both are closed",
    "la zona a 0 è collegata all'esterno da un passaggio di 1 cella": "the zone at 0 is linked to the outside by a 1-cell passage",
    "Varco 0 m": "Gap 0 m",
    "zona esterna: non si chiude": "exterior zone: not closed",
    "Varco 3 m": "Gap 3 m",
    "passaggio più stretto del varco: zona interna, si chiude": "passage narrower than the gap: interior zone, closed",
    "contorno: 3 sopra, 1 a sinistra, 2 a destra e sotto": "boundary: 3 above, 1 on the left, 2 on the right and below",
    "massimo del contorno": "boundary maximum",
    "più frequente del contorno": "most frequent boundary value",
    "più vicino (ogni cella prende il suo)": "nearest (each cell takes its own)",
    "il pericolo termina sulla classe 0": "the hazard ends on class 0",
    "Buffer 1 m": "Buffer 1 m",
    "1 cella (1 m) con valore −1 grado (minimo 1)": "1 cell (1 m) with value −1 degree (minimum 1)",
    "Buffer 2 m": "Buffer 2 m",
    "2 celle (2 m), stesso valore (nessun altro grado)": "2 cells (2 m), same value (no further degree)",
}


def _t(s):
    return EN.get(s, s) if LANG == "en" else s



def _dark(hexcol, f):
    r, g, b = (int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def grid(arr, bid=None, code=None, title="", note=""):
    """Tabella HTML: colore = classe; cella modificata = tratteggio nel colore del codice; bordo azzurro = edificio."""
    rows = []
    for y in range(arr.shape[0]):
        cells = []
        for x in range(arr.shape[1]):
            v = int(arr[y, x])
            st = ["background:%s" % COL[v]]
            cls = ""
            if code is not None and code[y, x] > 0 and v > 0:
                d = _dark(COL[v], DARK[int(code[y, x])])
                st = ["background:repeating-linear-gradient(45deg,%s 0 3px,%s 3px 6px)" % (COL[v], d)]
            if bid is not None and bid[y, x] > 0:
                st.append("outline:2px solid #00b8d4;outline-offset:-2px")
            txt = str(v) if code is None or code[y, x] == 0 else str(v + 10 * int(code[y, x]))
            cells.append('<td style="%s">%s</td>' % (";".join(st), txt if v or (code is not None and code[y, x]) else ""))
        rows.append("<tr>%s</tr>" % "".join(cells))
    return '<figure class="ex"><table class="g">%s</table><figcaption><b>%s</b>%s</figcaption></figure>' % (
        "".join(rows), _t(title), ("<br>" + _t(note)) if note else "")


def row(*figs):
    return '<div class="exrow">%s</div>' % "".join(figs)


def ex_buildings():
    h = np.zeros((9, 9), np.uint8)
    h[:, :3] = 1
    h[:, 3] = 3
    bid = np.zeros((9, 9), np.int32)
    bid[3:6, 4:7] = 1           # edificio 3x3
    h[3:6, 4] = 2               # il flusso entra solo nella prima colonna dell'edificio
    out0, m0, _ = core.step_buildings(h, bid, 0)
    out1, m1, _ = core.step_buildings(h, bid, 1)
    c0 = np.where(m0, 1, 0).astype(np.uint8)
    c1 = np.where(m1, 1, 0).astype(np.uint8)
    return (row(grid(h, bid, None, "Prima", "edificio (bordo azzurro): solo la 1ª colonna ha pericolo 2"),
                grid(out0, bid, c0, "Dopo, tolleranza 0 m", "tutto l'edificio prende il massimo che lo tocca: 2"),
                grid(out1, bid, c1, "Dopo, tolleranza 1 m", "entra anche la cella a pericolo 3 entro 1 m: tutto 3")),
            (h, out0, out1, bid))


def ex_holes():
    h = np.zeros((12, 14), np.uint8)
    h[1:11, 1:13] = 2
    h[1:11, 1:3] = 3
    h[3:5, 5:7] = 0          # 4 celle
    h[6:9, 8:12] = 0         # 12 celle
    res = 1.0               # pixel 1 m
    o1, m1, n1 = core.step_holes(h, 5, "max", 0)
    o2, m2, n2 = core.step_holes(h, None, "max", 0)
    return (row(grid(h, None, None, "Prima", "due zone a 0 interne: 4 m² e 12 m² (pixel da 1 m)"),
                grid(o1, None, np.where(m1, 2, 0).astype(np.uint8), "Area ≤ 5 m²", "si chiude solo la piccola"),
                grid(o2, None, np.where(m2, 2, 0).astype(np.uint8), "Chiudi TUTTE", "si chiudono entrambe")),
            (h, o1, o2))


def ex_gap():
    h = np.zeros((11, 11), np.uint8)
    h[1:10, 1:10] = 2
    h[3:8, 3:8] = 0          # zona 5x5 a 0
    h[5, 9] = 0              # varco (1 cella) verso l'esterno: 0 anche sul bordo
    h[5, 8:10] = 0
    o0, m0, _ = core.step_holes(h, None, "max", 0)
    o1, m1, _ = core.step_holes(h, None, "max", 2)
    assert m0.sum() == 0, "senza varco la zona e' collegata all'esterno"
    assert m1.sum() > 0
    return (row(grid(h, None, None, "Prima", "la zona a 0 è collegata all'esterno da un passaggio di 1 cella"),
                grid(o0, None, np.where(m0, 2, 0).astype(np.uint8), "Varco 0 m", "zona esterna: non si chiude"),
                grid(o1, None, np.where(m1, 2, 0).astype(np.uint8), "Varco 3 m", "passaggio più stretto del varco: zona interna, si chiude")),
            (h, o0, o1))


def ex_fillmode():
    h = np.zeros((9, 9), np.uint8)
    h[0:3, :] = 3
    h[3:9, :3] = 1
    h[3:9, 6:] = 2
    h[6:9, 3:6] = 2
    h[3:6, 3:6] = 0          # zona interna 3x3
    outs = []
    figs = [grid(h, None, None, "Prima", "contorno: 3 sopra, 1 a sinistra, 2 a destra e sotto")]
    notes = {"max": "massimo del contorno", "major": "più frequente del contorno", "near": "più vicino (ogni cella prende il suo)"}
    for mode in ("max", "major", "near"):
        o, m, _ = core.step_holes(h, None, mode, 0)
        outs.append(o)
        figs.append(grid(o, None, np.where(m, 2, 0).astype(np.uint8), mode, notes[mode]))
    return row(*figs[:2]) + row(*figs[2:]), (h, outs)


def ex_buffer():
    h = np.zeros((6, 12), np.uint8)
    h[0:2, 0:4] = 3
    h[2:4, 0:4] = 2
    h[4:6, 0:4] = 1
    o1, m1, _ = core.step_buffer(h, 1)
    o2, m2, _ = core.step_buffer(h, 2)
    return (row(grid(h, None, None, "Prima", "il pericolo termina sulla classe 0"),
                grid(o1, None, np.where(m1, 3, 0).astype(np.uint8), "Buffer 1 m", "1 cella (1 m) con valore −1 grado (minimo 1)"),
                grid(o2, None, np.where(m2, 3, 0).astype(np.uint8), "Buffer 2 m", "2 celle (2 m), stesso valore (nessun altro grado)")),
            (h, o1, o2))


def ex_all(lang="it"):
    global LANG
    LANG = lang
    return dict(buildings=ex_buildings()[0], holes=ex_holes()[0], gap=ex_gap()[0], fillmode=ex_fillmode()[0], buffer=ex_buffer()[0])


if __name__ == "__main__":
    # verifiche dei comportamenti descritti nel testo
    _, (h, o0, o1, bid) = ex_buildings()
    assert (o0[bid > 0] == 2).all() and (o1[bid > 0] == 3).all(), (o0[bid > 0], o1[bid > 0])
    print("edifici tol0:", np.unique(o0[bid > 0]), "tol1:", np.unique(o1[bid > 0]))
    _, (h, o1_, o2_) = ex_holes()
    print("zone interne: 0 rimasti piccola/tutte:", int((o1_ == 0).sum() - (h[:0] == 0).sum()), int((o2_ == 0).sum()))
    _, (h, outs) = ex_fillmode()
    print("riempimento max/major/near nella zona 3x3:", [np.unique(o[3:6, 3:6]).tolist() for o in outs])
    _, (h, o1, o2) = ex_buffer()
    print("buffer 1px colonna 4:", o1[:, 4].tolist(), "buffer 2px colonna 5:", o2[:, 5].tolist(), "colonna 6:", o2[:, 6].tolist())
