@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Uruchamiam Trenera AI... okno aplikacji otworzy sie za chwile.
echo Aby zamknac aplikacje - zamknij to okno.
echo.
".venv\Scripts\python.exe" uruchom.py
echo.
pause
