@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title FINDER v2.0 - Installation
color 0B
mode con: cols=80 lines=50

set ROOT=%~dp0
if "%ROOT:~-1%"=="\" set ROOT=%ROOT:~0,-1%
set FINDERDIR=%ROOT%
set SERVERPY=%FINDERDIR%\finder\server.py
set VENVDIR=%ROOT%\venv
set VENVPY=%VENVDIR%\Scripts\python.exe
set VENVPIP=%VENVDIR%\Scripts\pip.exe
set PYTHON=

cls
echo.
echo  =============================================
echo   FINDER v2.0 - Installeur Windows
echo   by Data2391
echo  =============================================
echo.
echo  Installation entierement automatique.
echo  Ne ferme pas cette fenetre !
echo.

if not exist "%SERVERPY%" (
    echo ERREUR : finder\server.py introuvable.
    echo Place ce script dans le dossier qui contient finder\
    pause
    exit /b 1
)
echo OK : Projet FINDER detecte.
echo.

echo ----------------------------------------------------------
echo  1/8 - Verification de Python 3.8+...
echo ----------------------------------------------------------
for %%c in (python python3 py) do (
    if "!PYTHON!"=="" (
        %%c --version >nul 2>&1
        if not errorlevel 1 set PYTHON=%%c
    )
)
if "!PYTHON!"=="" (
    echo INFO : Python absent. Installation via winget...
    winget install --id Python.Python.3.12 -e --silent --accept-source-agreements --accept-package-agreements
    set PYTHON=python
)
echo OK : Python detecte : !PYTHON!
echo.

echo ----------------------------------------------------------
echo  2/8 - Environnement virtuel Python (venv)...
echo ----------------------------------------------------------
if exist "%VENVPY%" (
    echo OK : Venv deja present.
    goto step3
)
call !PYTHON! -m venv "%VENVDIR%"
if not exist "%VENVPY%" (
    echo ERREUR : Impossible de creer le venv.
    pause & exit /b 1
)
echo OK : Venv cree.

:step3
echo ----------------------------------------------------------
echo  3/8 - Mise a jour de pip...
echo ----------------------------------------------------------
"%VENVPY%" -m pip install --upgrade pip --quiet 2>nul
echo OK : pip mis a jour.
echo.

echo ----------------------------------------------------------
echo  4/8 - Installation de Flask...
echo ----------------------------------------------------------
"%VENVPY%" -c "import flask" >nul 2>&1
if not errorlevel 1 (
    echo OK : Flask deja installe.
    goto step5
)
"%VENVPY%" -m pip install flask --quiet
echo OK : Flask installe.

:step5
echo ----------------------------------------------------------
echo  5/8 - Installation de Playwright...
echo ----------------------------------------------------------
"%VENVPY%" -c "import playwright" >nul 2>&1
if not errorlevel 1 (
    echo OK : Playwright deja installe.
    goto step6
)
"%VENVPY%" -m pip install playwright --quiet
echo OK : Playwright installe.

:step6
echo ----------------------------------------------------------
echo  6/8 - Navigateur Chromium Playwright...
echo ----------------------------------------------------------
set PWCACHE=%LOCALAPPDATA%\ms-playwright
set CHROMEFOUND=0
if exist "%PWCACHE%" (
    for /r "%PWCACHE%" %%f in (chrome.exe) do if exist "%%f" set CHROMEFOUND=1
)
if "!CHROMEFOUND!"=="1" (
    echo OK : Playwright Chromium deja installe.
    goto step7
)
echo INFO : Telechargement Chromium... (150 MB, patience)
"%VENVPY%" -m playwright install chromium
echo OK : Chromium installe.

:step7
echo ----------------------------------------------------------
echo  7/8 - Test d'operabilite...
echo ----------------------------------------------------------
"%VENVPY%" -c "import flask,playwright,asyncio,json,re,urllib,threading,queue,uuid;print('ALLOK')" > "%TEMP%\test.txt" 2>&1
set /p IMPORTRES=<"%TEMP%\test.txt"
del "%TEMP%\test.txt" >nul 2>&1
if "!IMPORTRES!"=="ALLOK" (
    echo OK : Tous les modules Python sont operationnels.
) else (
    echo AVERT : !IMPORTRES!
)

echo.

:step8
echo ----------------------------------------------------------
echo  8/8 - Creation des raccourcis...
echo ----------------------------------------------------------
set BATLOCAL=%ROOT%\LANCER_FINDER.bat
if not exist "%BATLOCAL%" (
    echo @echo off > "%BATLOCAL%"
    echo title FINDER v2.0 - Data2391 >> "%BATLOCAL%"
    echo color 0B >> "%BATLOCAL%"
    echo cls >> "%BATLOCAL%"
    echo cd /d "%%~dp0" >> "%BATLOCAL%"
    echo timeout /t 2 /nobreak ^>nul >> "%BATLOCAL%"
    echo start http://localhost:8000 >> "%BATLOCAL%"
    echo venv\Scripts\python.exe finder\server.py >> "%BATLOCAL%"
    echo pause >> "%BATLOCAL%"
)
echo OK : Lanceur LANCER_FINDER.bat cree.

echo.
echo  =============================================
echo   FINDER v2.0 EST PRET !
echo  =============================================
echo.
echo  Pour lancer : double-clic sur LANCER_FINDER.bat
echo  Interface : http://localhost:8000
echo.
set /p LAUNCHNOW=" Lancer FINDER maintenant ? [O/N] : "
if /i "!LAUNCHNOW!"=="O" start "" "%BATLOCAL%"
echo.
pause
endlocal
