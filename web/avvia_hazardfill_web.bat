@echo off
rem HazardFill (HF) - avvio della pagina web locale (Windows)
rem Metti le aree in "dati" (una sottocartella per area) oppure passa --data altra_cartella.
rem Senza dati compare comunque l'esempio Spona_test (se presente) e puoi caricare i tuoi file dalla pagina.
cd /d "%~dp0"
python server.py %*
pause
