# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
"""Figure sintetiche per la documentazione: piccole griglie calcolate con il codice vero (core.py)."""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import examples  # noqa: E402
import core  # noqa: E402

OUT = os.path.join(here, "..", "docs", "images")
os.makedirs(OUT, exist_ok=True)
COL = {0: "#ffffff", 1: "#ffeb3b", 2: "#ff8c00", 3: "#d62828"}
F = {1: .72, 2: .55, 3: .38}


def shade(c, f):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) / 255 * f for i in (0, 2, 4))


def panel(ax, arr, title, note="", bid=None, code=None):
    ny, nx = arr.shape
    for y in range(ny):
        for x in range(nx):
            v = int(arr[y, x])
            c = int(code[y, x]) if code is not None else 0
            ax.add_patch(Rectangle((x, ny - 1 - y), 1, 1, facecolor=COL[v], edgecolor="#bbbbbb", linewidth=.6))
            if c > 0 and v > 0:
                ax.add_patch(Rectangle((x, ny - 1 - y), 1, 1, facecolor=shade(COL[v], F[c]), edgecolor="none", hatch="////", alpha=.55))
            if v:
                ax.text(x + .5, ny - 1 - y + .5, str(v + 10 * c if c else v), ha="center", va="center", fontsize=6.5, color="#222")
            if bid is not None and bid[y, x] > 0:
                ax.add_patch(Rectangle((x + .06, ny - 1 - y + .06), .88, .88, facecolor="none", edgecolor="#00b8d4", linewidth=1.6))
    ax.set_xlim(0, nx)
    ax.set_ylim(0, ny)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=10, fontweight="bold", loc="left")
    if note:
        ax.text(0, -1.0, note, fontsize=8, va="top", color="#444", wrap=True)


def fig(name, panels, w=4.0):
    f, axs = plt.subplots(1, len(panels), figsize=(w * len(panels), w * .78 + .6))
    axs = np.atleast_1d(axs)
    for ax, p in zip(axs, panels):
        panel(ax, **p)
    f.tight_layout()
    f.savefig(os.path.join(OUT, name), dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(f)
    print("scritta", name)


def mk(codearr):
    return np.where(codearr, codearr, 0).astype(np.uint8)


# ---- edifici
_, (h, o0, o1, bid) = examples.ex_buildings()
fig("esempio_edifici.png", [
    dict(arr=h, title="Prima", note="edificio (bordo azzurro): solo la 1ª colonna\nha pericolo 2", bid=bid),
    dict(arr=o0, title="Tolleranza 0 m", note="tutto l'edificio prende il massimo\nche lo tocca: 2", bid=bid, code=(o0 != h).astype(np.uint8)),
    dict(arr=o1, title="Tolleranza 1 m", note="entra anche la cella a 3 entro 1 m:\ntutto 3", bid=bid, code=(o1 != h).astype(np.uint8)),
])
# ---- zone interne
_, (h, o1, o2) = examples.ex_holes()
fig("esempio_zone_interne.png", [
    dict(arr=h, title="Prima", note="due zone a 0 interne:\n4 m² e 12 m² (pixel da 1 m)"),
    dict(arr=o1, title="Area ≤ 5 m²", note="si chiude solo la piccola", code=2 * (o1 != h).astype(np.uint8)),
    dict(arr=o2, title="Chiudi TUTTE", note="si chiudono entrambe", code=2 * (o2 != h).astype(np.uint8)),
])
# ---- varco
_, (h, o0, o1) = examples.ex_gap()
fig("esempio_varco.png", [
    dict(arr=h, title="Prima", note="zona a 0 collegata all'esterno\nda un passaggio di 1 cella"),
    dict(arr=o0, title="Varco 0 m", note="zona esterna: non si chiude", code=2 * (o0 != h).astype(np.uint8)),
    dict(arr=o1, title="Varco 3 m", note="passaggio più stretto del varco:\nzona interna, si chiude", code=2 * (o1 != h).astype(np.uint8)),
])
# ---- valore di riempimento
_, (h, outs) = examples.ex_fillmode()
fig("esempio_riempimento.png", [
    dict(arr=h, title="Prima", note="contorno: 3 sopra, 1 a sinistra,\n2 a destra e sotto"),
    dict(arr=outs[0], title="Massimo", note="prudente: 3", code=2 * (outs[0] != h).astype(np.uint8)),
    dict(arr=outs[1], title="Maggioranza (predefinito)", note="il valore più frequente: 2", code=2 * (outs[1] != h).astype(np.uint8)),
    dict(arr=outs[2], title="Più vicino", note="ogni cella prende il valore\ndella cella valida più vicina", code=2 * (outs[2] != h).astype(np.uint8)),
], w=3.3)
# ---- buffer
_, (h, o1, o2) = examples.ex_buffer()
fig("esempio_buffer.png", [
    dict(arr=h, title="Prima", note="il pericolo termina sulla classe 0"),
    dict(arr=o1, title="Buffer 1 m", note="1 cella con valore −1 grado\n(minimo 1)", code=3 * (o1 != h).astype(np.uint8)),
    dict(arr=o2, title="Buffer 2 m", note="2 celle, stesso valore\n(nessun altro grado)", code=3 * (o2 != h).astype(np.uint8)),
])

# ---- tavola dei codici
f, ax = plt.subplots(figsize=(7.2, 2.6))
ax.axis("off")
rows = core.code_table(False)
ax.set_xlim(0, 8)
ax.set_ylim(0, 5)
ax.text(0, 4.8, "Codici del raster «con codici»  (decine = criterio, unità = classe assegnata)", fontsize=10, fontweight="bold", va="top")
for j, (name, steps) in enumerate((("originale", (0,)), ("edifici", (1,)), ("zone interne", (2,)), ("buffer", (3,)))):
    x = j * 2.0
    ax.text(x, 4.0, name, fontsize=9, fontweight="bold", va="top")
    for i, k in enumerate((1, 2, 3)):
        c = steps[0]
        v = k + 10 * c
        col = COL[k] if c == 0 else shade(COL[k], F[c])
        ax.add_patch(Rectangle((x, 3.0 - i * .85), .55, .6, facecolor=col, edgecolor="#555"))
        ax.text(x + .7, 3.3 - i * .85, "%d  %s" % (v, {1: "basso", 2: "medio", 3: "alto"}[k]), fontsize=9, va="center")
f.savefig(os.path.join(OUT, "codici.png"), dpi=130, bbox_inches="tight", facecolor="white")
plt.close(f)
print("scritta codici.png")
