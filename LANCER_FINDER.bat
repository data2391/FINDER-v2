@echo off
setlocal enabledelayedexpansion
title FINDER v2.0 - Data2391
color 0B
cls
echo.
echo  =============================================
echo   FINDER v2.0 - Sonar OSINT by Data2391
echo  =============================================
echo.

set ROOT=%~dp0
if "%ROOT:~-1%"=="\" set ROOT=%ROOT:~0,-1%

set VENVPY=%ROOT%\venv\Scripts\python.exe
set SERVER=%ROOT%\finder\server.py

REM --- Verifier que server.py existe ---
if not exist "%SERVER%" (
    echo ERREUR : finder\server.py introuvable.
    echo Verifie que tu es dans le bon dossier.
    pause
    exit /b 1
)

REM --- Verifier que le venv existe, sinon lancer install ---
if not exist "%VENVPY%" (
    echo AVERT : Environnement virtuel absent.
    echo Lancement de l'installation automatique...
    echo.
    if exist "%ROOT%\install_finder.bat" (
        call "%ROOT%\install_finder.bat"
    ) else (
        echo ERREUR : install_finder.bat introuvable.
        echo Lance install_finder.bat manuellement pour installer FINDER.
        pause
        exit /b 1
    )
)

REM --- Re-verifier apres install ---
if not exist "%VENVPY%" (
    echo ERREUR : Le venv n'a pas pu etre cree.
    echo Relance install_finder.bat en tant qu'administrateur.
    pause
    exit /b 1
)

echo  Demarrage du serveur local...
echo  Le navigateur va s'ouvrir automatiquement.
echo.
echo  NE PAS FERMER CETTE FENETRE pendant l'utilisation.
echo  Pour arreter : ferme cette fenetre.
echo.

timeout /t 2 /nobreak >nul
start http://localhost:8000

"%VENVPY%" "%SERVER%"

echo.
echo  Serveur arrete.
pause
endlocal
