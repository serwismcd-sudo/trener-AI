@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ================================================
echo  Logowanie do Garmin Connect (jednorazowe)
echo ================================================
echo.
echo  Jesli Garmin poprosi o kod MFA - sprawdz maila
echo  albo aplikacje Garmin Connect w telefonie,
echo  wpisz kod tutaj i nacisnij Enter.
echo.
".venv\Scripts\python.exe" garmin_sync.py
echo.
echo ================================================
pause
