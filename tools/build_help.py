# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
import base64, os
import examples

here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, "help_src.html"), encoding="utf-8").read()
for k, v in examples.ex_all().items():
    src = src.replace("{{EX_%s}}" % k.upper(), v)
svg = open(os.path.join(here, "..", "plugin", "hazardfill", "icon.svg"), "rb").read()
src = src.replace("{{LOGO}}", "data:image/svg+xml;base64," + base64.b64encode(svg).decode())
assert "{{" not in src
out = os.path.join(here, "..", "plugin", "hazardfill", "help", "help_utilizzo.html")
open(out, "w", encoding="utf-8").write(src)
print("help scritto:", os.path.normpath(out), len(src))
