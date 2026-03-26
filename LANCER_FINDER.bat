@echo off
title FINDER v2.0 - Data2391
color 0B
cls
echo.
echo  =============================================
echo   FINDER v2.0 - Sonar OSINT by Data2391
echo  =============================================
echo.
echo  Demarrage du serveur local...
echo  Le navigateur va s'ouvrir automatiquement.
echo.
echo  NE PAS FERMER CETTE FENETRE pendant l'utilisation.
echo  Pour arreter : ferme cette fenetre.
echo.
cd /d "%~dp0"
timeout /t 2 /nobreak >nul
start http://localhost:8000
venv\Scripts\python.exe finder\server.py
echo.
echo  Serveur arrete.
pause
