#!/usr/bin/env sh
# HazardFill (HF) - avvio della pagina web locale (Linux/macOS)
# Metti le aree in "dati" (una sottocartella per area) oppure passa --data altra_cartella.
cd "$(dirname "$0")" && python3 server.py "$@"
