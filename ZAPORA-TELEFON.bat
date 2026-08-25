@echo off
chcp 65001 >nul
title Trener AI - dostep z telefonu

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo ============================================================
  echo   POTRZEBNE UPRAWNIENIA ADMINISTRATORA
  echo ============================================================
  echo.
  echo   Zamknij to okno, kliknij ten plik PRAWYM przyciskiem
  echo   i wybierz "Uruchom jako administrator".
  echo.
  echo   Regula w zaporze wymaga uprawnien administratora -
  echo   bez nich Windows odmawia dostepu (blad 5^).
  echo.
  pause
  exit /b 1
)

echo Dodaje regule zapory dla portu 8501 (tylko siec domowa)...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | Select-Object -First 1).IPAddress;" ^
  "$podsiec = ($ip -replace '\.\d+$', '.0') + '/24';" ^
  "Get-NetFirewallRule -DisplayName 'Trener AI (siec domowa)' -ErrorAction SilentlyContinue | Remove-NetFirewallRule;" ^
  "New-NetFirewallRule -DisplayName 'Trener AI (siec domowa)' -Direction Inbound -Protocol TCP -LocalPort 8501 -RemoteAddress $podsiec -Action Allow | Out-Null;" ^
  "Write-Host ''; Write-Host ('  Gotowe. Adres dla telefonu: http://' + $ip + ':8501');" ^
  "Write-Host ('  Dopuszczono wylacznie urzadzenia z sieci ' + $podsiec)"

echo.
echo   Teraz uruchom Trenera AI i zeskanuj kod QR z panelu bocznego.
echo.
pause
