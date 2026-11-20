/* HazardFill (HF) - calcolo nel browser: esegue il nucleo Python (core.py, solo numpy + scipy) con Pyodide in un Web Worker.
 * Copyright (C) 2026 Stefano Crema, Marco Cavalli, Alessandro Sarretta - CNR-GEO (Istituto di Geoscienze). Licenza GNU GPL v2. */
importScripts('https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js');

let py = null;
let ready = null;

function init() {
  if (ready) return ready;
  ready = (async () => {
    postMessage({ type: 'status', msg: 'carico Python nel browser (la prima volta può richiedere qualche decina di secondi)…' });
    py = await loadPyodide();
    postMessage({ type: 'status', msg: 'carico numpy e scipy…' });
    await py.loadPackage(['numpy', 'scipy']);
    const core = await (await fetch('hazardfill/core.py')).text();
    py.FS.writeFile('/home/pyodide/core.py', core);
    await py.runPythonAsync(`
import sys, json
sys.path.insert(0, '/home/pyodide')
import numpy as np
import core

_cache = {}

def _arr(buf, dtype, hh, w):
    return np.frombuffer(buf.to_py(), dtype=dtype).reshape(hh, w)

def run(h, bu, bo, w, hh, res, params_json, key, osm):
    p = json.loads(params_json)
    H = _arr(h, np.uint8, hh, w)
    bid = None
    if p.get('bld'):
        U = _arr(bu, np.int32, hh, w) if bu is not None else np.zeros((hh, w), np.int32)
        O = _arr(bo, np.int32, hh, w) if bo is not None else None
        if osm == 2 and O is not None:
            bid, _ = core.merge_building_ids(np.zeros((hh, w), np.int32), O)     # come il server: rinumera gli edifici presenti nel raster
        elif osm == 1 and O is not None:
            bid, _ = core.merge_building_ids(U, O)
        else:
            bid = U.copy()
    out, code, st = core.process(H, bid, res, p, cache=_cache, key=key)
    return out.astype(np.uint8).tobytes(), code.astype(np.uint8).tobytes(), json.dumps(st)

def qml(clean):
    return core.make_qml(bool(clean))

def version():
    return core.__version__
`);
    postMessage({ type: 'ready', version: py.globals.get('version')() });
  })();
  return ready;
}

onmessage = async (e) => {
  const m = e.data;
  try {
    await init();
    if (m.type === 'process') {
      const t0 = performance.now();
      const r = py.globals.get('run')(m.h, m.bu, m.bo, m.w, m.hh, m.res, m.params, m.key, m.osm);
      const arr = r.toJs();
      r.destroy();
      const out = new Uint8Array(arr[0]);
      const code = new Uint8Array(arr[1]);
      postMessage({ type: 'result', id: m.id, out, code, stats: JSON.parse(arr[2]), ms: performance.now() - t0 }, [out.buffer, code.buffer]);
    } else if (m.type === 'qml') {
      postMessage({ type: 'qml', id: m.id, text: py.globals.get('qml')(m.clean) });
    } else if (m.type === 'init') {
      /* solo inizializzazione */
    }
  } catch (err) {
    postMessage({ type: 'error', id: m.id, error: String(err && err.message ? err.message : err) });
  }
};
