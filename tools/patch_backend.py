"""Introduce nella pagina un livello 'backend' (server oppure browser). Eseguito una volta sola."""
import os
R = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
p = os.path.join(R, "web", "index.html")
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert a in s, a[:90]
    s = s.replace(a, b, 1)


rep("const $=id=>document.getElementById(id);", '''const $=id=>document.getElementById(id);
// ---- backend: il server Python (predefinito) oppure, nella versione per GitHub Pages, il calcolo nel browser
const serverBackend={
  info:()=>fetch('/api/info').then(r=>r.json()),
  process:async q=>(await fetch('/api/process?'+q)).json(),
  exportRaster:(q,clean)=>{location.href='/api/export?'+q+(clean?'&clean=1':'');},
  exportStyle:(name,clean)=>{location.href='/api/style?name='+encodeURIComponent(name)+'&clean='+(clean?1:0);},
  exportVector:q=>{location.href='/api/export_vector?'+q;},
  version:()=>fetch('/api/version').then(r=>r.json()),
  upload:async(kind,file,area)=>(await fetch('/api/upload_data?kind='+kind+'&area='+encodeURIComponent(area)+'&name='+encodeURIComponent(file.name),{method:'POST',body:file})).json(),
  vector:true
};
const BACKEND=window.HF_BACKEND||serverBackend;''')

rep("return fetch('/api/info').then(r=>r.json()).then(d=>{D=d;", "return BACKEND.info().then(d=>{D=d;")
rep("const r=await (await fetch('/api/process?'+params())).json(); if(my!==reqId) return;", "const r=await BACKEND.process(params().toString()); if(my!==reqId) return;")
rep("$('exp1').onclick=()=>{location.href='/api/export?'+params().toString()};", "$('exp1').onclick=()=>BACKEND.exportRaster(params().toString(),false);")
rep("$('sty').onclick=()=>{const n=$('proc').value.replace(/\\.tif+$/,'').replace(/.*\\//,''); location.href='/api/style?name='+encodeURIComponent(n)+'&clean='+(0)};",
    "$('sty').onclick=()=>{const n=$('proc').value.replace(/\\.tif+$/,'').replace(/.*\\//,''); BACKEND.exportStyle(n,false)};")
rep("$('expv').onclick=()=>{$('expv').textContent='preparo vettoriale…'; location.href='/api/export_vector?'+params().toString(); setTimeout(()=>$('expv').textContent='Vettoriale (GeoPackage) con codici',8000)};",
    "$('expv').onclick=()=>{$('expv').textContent='preparo vettoriale…'; BACKEND.exportVector(params().toString()); setTimeout(()=>$('expv').textContent='Vettoriale (GeoPackage) con codici',8000)};")
rep("$('exp2').onclick=()=>{location.href='/api/export?'+params().toString()+'&clean=1'};", "$('exp2').onclick=()=>BACKEND.exportRaster(params().toString(),true);")
rep("fetch('/api/version').then(r=>r.json()).then(j=>{$('ver').textContent='v'+j.version}).catch(()=>{});", "BACKEND.version().then(j=>{$('ver').textContent='v'+j.version; if(j.vector===false) $('expv').style.display='none';}).catch(()=>{});")
rep("fetch('/api/version').then(r=>r.json()).then(j=>{ if(j.upload) $('updet').style.display='block'; }).catch(()=>{});", "BACKEND.version().then(j=>{ if(j.upload) $('updet').style.display='block'; if(j.openUpload) $('updet').open=true; }).catch(()=>{});")
rep('''async function sendFile(kind,file,area){
  const r=await fetch('/api/upload_data?kind='+kind+'&area='+encodeURIComponent(area)+'&name='+encodeURIComponent(file.name),{method:'POST',body:file});
  return r.json();
}''', '''async function sendFile(kind,file,area){ return BACKEND.upload(kind,file,area); }''')
rep("function update(){\n", "function update(){\n  if(!cur) return;\n")
open(p, "w", encoding="utf-8").write(s)
print("backend ok")
