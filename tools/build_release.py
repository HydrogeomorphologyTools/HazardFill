# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
"""Compone i file di una release in dist/: plugin QGIS (zip) e pagina web (zip, con esempio)."""
import os
import shutil
import sys
import zipfile

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.normpath(os.path.join(here, ".."))
plug = os.path.join(root, "plugin", "hazardfill")
sys.path.insert(0, plug)
import core  # noqa: E402

V = core.__version__
dist = os.path.join(root, "dist")
os.makedirs(dist, exist_ok=True)


def clean_pycache(path):
    for d, dirs, _ in os.walk(path):
        for x in list(dirs):
            if x == "__pycache__":
                shutil.rmtree(os.path.join(d, x))
                dirs.remove(x)


def add_tree(z, src, arc):
    for d, _, fs in os.walk(src):
        for f in fs:
            full = os.path.join(d, f)
            z.write(full, os.path.join(arc, os.path.relpath(full, src)))


# --- plugin QGIS
clean_pycache(plug)
zp = os.path.join(dist, "HazardFill_plugin_%s.zip" % V)
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    add_tree(z, plug, "hazardfill")

# --- pagina web (con il nucleo di calcolo, l'help e l'esempio)
zw = os.path.join(dist, "HazardFill_web_%s.zip" % V)
with zipfile.ZipFile(zw, "w", zipfile.ZIP_DEFLATED) as z:
    web = os.path.join(root, "web")
    for f in ("server.py", "index.html", "requirements.txt", "avvia_hazardfill_web.bat", "avvia_hazardfill_web.sh"):
        z.write(os.path.join(web, f), os.path.join("HazardFill_web", f))
    z.write(os.path.join(web, "dati", "LEGGIMI.txt"), os.path.join("HazardFill_web", "dati", "LEGGIMI.txt"))
    for f in ("core.py", "icon.svg"):
        z.write(os.path.join(plug, f), os.path.join("HazardFill_web", "hazardfill", f))
    z.write(os.path.join(plug, "help", "help_utilizzo.html"), os.path.join("HazardFill_web", "hazardfill", "help", "help_utilizzo.html"))
    add_tree(z, os.path.join(root, "examples"), os.path.join("HazardFill_web", "dati"))
    z.write(os.path.join(root, "LICENSE"), os.path.join("HazardFill_web", "LICENSE"))
print("release %s:" % V)
for f in sorted(os.listdir(dist)):
    print("  ", f, os.path.getsize(os.path.join(dist, f)) // 1024, "KB")
