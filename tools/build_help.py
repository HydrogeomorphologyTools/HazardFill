# HazardFill (HF) - chiusura delle aree prive di valore nelle mappe di pericolosita'.
# Copyright (C) 2026  Stefano Crema, Marco Cavalli, Alessandro Sarretta
#                     CNR-GEO (Istituto di Geoscienze)
#
# Questo programma e' software libero: puoi ridistribuirlo e/o modificarlo secondo i termini
# della GNU General Public License versione 2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
# Il programma e' distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA.
"""Costruisce l'help bilingue (EN predefinito, IT con la bandierina) in plugin/hazardfill/help/help_utilizzo.html."""
import base64, os, re
import examples

here = os.path.dirname(os.path.abspath(__file__))
rd = lambda n: open(os.path.join(here, n), encoding="utf-8").read()
ver = re.search(r'__version__\s*=\s*"([^"]+)"', open(os.path.join(here, "..", "plugin", "hazardfill", "core.py"), encoding="utf-8").read()).group(1)

FLAG_IT = '<svg viewBox="0 0 3 2"><rect width="1" height="2" fill="#009246"/><rect x="1" width="1" height="2" fill="#fff"/><rect x="2" width="1" height="2" fill="#ce2b37"/></svg>'
FLAG_EN = ('<svg viewBox="0 0 60 40"><rect width="60" height="40" fill="#012169"/><path d="M0,0 60,40M60,0 0,40" stroke="#fff" stroke-width="8"/>'
           '<path d="M0,0 60,40M60,0 0,40" stroke="#c8102e" stroke-width="3"/><path d="M30,0V40M0,20H60" stroke="#fff" stroke-width="13"/>'
           '<path d="M30,0V40M0,20H60" stroke="#c8102e" stroke-width="8"/></svg>')
LANGBAR = ('<div id="langbar"><button id="langbtn" type="button" title="Italiano / English">%s<span>English</span></button></div>' % FLAG_EN)
LANGJS = """<script>
(function(){
 var FI='%s', FE='%s';
 function get(){try{var q=new URLSearchParams(location.search).get('lang'); if(q==='it'||q==='en') return q; return localStorage.getItem('hf_lang')==='en'?'en':'it';} catch(e){return 'it'}}
 function set(l){document.documentElement.lang=l; try{localStorage.setItem('hf_lang',l)}catch(e){}
  var b=document.getElementById('langbtn'); b.innerHTML=(l==='en'?FI+'<span>Italiano</span>':FE+'<span>English</span>'); document.title=l==='en'?'HazardFill - Help':'HazardFill - Help \u00b7 utilizzo';}
 document.getElementById('langbtn').onclick=function(){set(document.documentElement.lang==='en'?'it':'en')};
 set(get());
})();
</script>""" % (FLAG_IT.replace("'", "\'"), FLAG_EN.replace("'", "\'"))

svg = open(os.path.join(here, "..", "plugin", "hazardfill", "icon.svg"), "rb").read()
logo = "data:image/svg+xml;base64," + base64.b64encode(svg).decode()
out = rd("help_src.html").replace("{{LANGBAR}}", LANGBAR).replace("{{LANGJS}}", LANGJS)
for lang in ("en", "it"):
    body = rd("help_body_%s.html" % lang)
    for k, v in examples.ex_all(lang).items():
        body = body.replace("{{EX_%s}}" % k.upper(), v)
    out = out.replace("{{BODY_%s}}" % lang.upper(), body)
out = out.replace("{{LOGO}}", logo).replace("{{VER}}", ver)
assert "{{" not in out
dst = os.path.join(here, "..", "plugin", "hazardfill", "help", "help_utilizzo.html")
open(dst, "w", encoding="utf-8").write(out)
print("help scritto:", os.path.normpath(dst), len(out))
