# -*- coding: utf-8 -*-
"""Uruchamia Trenera AI w prawdziwym oknie systemowym.

Streamlit startuje w tle jako serwer lokalny, a jego strona pokazuje się w oknie
natywnym (pywebview / WebView2) - bez przeglądarki, paska adresu i zakładek.
Zamknięcie okna zatrzymuje serwer.

Gdyby okno natywne nie było dostępne, program cofa się do okna Edge w trybie
aplikacji (--app), które wygląda podobnie, ale jest już przeglądarką.
"""

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

KATALOG = Path(__file__).parent
IKONA = KATALOG / "trener.ico"
PORT = 8501
URL = f"http://localhost:{PORT}"

PRZEGLADARKI = [
    r"{pf86}\Microsoft\Edge\Application\msedge.exe",
    r"{pf}\Microsoft\Edge\Application\msedge.exe",
    r"{pf}\Google\Chrome\Application\chrome.exe",
    r"{pf86}\Google\Chrome\Application\chrome.exe",
    r"{lad}\Google\Chrome\Application\chrome.exe",
]


def port_otwarty(port=PORT):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def czekaj_na_serwer(sekundy=60):
    koniec = time.time() + sekundy
    while time.time() < koniec:
        if port_otwarty():
            return True
        time.sleep(0.5)
    return False


def wystartuj_serwer():
    """Zwraca proces Streamlita albo None, jeśli aplikacja już działa."""
    if port_otwarty():
        print("Trener AI już działa - otwieram okno.")
        return None
    print("Uruchamiam Trenera AI...")
    serwer = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.headless", "true", "--server.port", str(PORT)],
        cwd=KATALOG,
    )
    if not czekaj_na_serwer():
        serwer.terminate()
        raise RuntimeError("Serwer Streamlit nie wystartował w ciągu 60 sekund.")
    return serwer


def okno_natywne():
    """Prawdziwe okno systemowe. Blokuje aż użytkownik je zamknie.

    Zwraca False, jeśli pywebview nie jest dostępny - wtedy wołający używa Edge.
    """
    try:
        import webview
    except Exception as e:
        print(f"Okno natywne niedostępne ({e}) - używam okna przeglądarki.")
        return False

    webview.create_window("Trener AI", URL, width=1500, height=950, min_size=(900, 600))
    webview.start(icon=str(IKONA) if IKONA.exists() else None)
    return True


def znajdz_przegladarke():
    sciezki = {
        "pf": os.environ.get("PROGRAMFILES", r"C:\Program Files"),
        "pf86": os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
        "lad": os.environ.get("LOCALAPPDATA", ""),
    }
    for wzor in PRZEGLADARKI:
        p = Path(wzor.format(**sciezki))
        if p.exists():
            return p
    return None


def zamknij_stare_okna(profil):
    """Zamyka przeglądarki wiszące na naszym profilu okna aplikacji.

    Bez tego zostaje pułapka: jeśli dla tego profilu działa już jakaś instancja,
    Edge przekazuje jej sterowanie, a proces który właśnie uruchomiliśmy kończy się
    od razu - program bierze to za "użytkownik zamknął okno" i gasi serwer sekundę
    po starcie (w oknie widać wtedy ERR_CONNECTION_REFUSED).
    """
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe' OR Name='chrome.exe'\" | "
        f"Where-Object {{ $_.CommandLine -like '*{profil}*' }} | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                       capture_output=True, timeout=25,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        time.sleep(1.5)
    except Exception as e:
        print(f"Nie udało się zamknąć starych okien ({e}) - próbuję mimo to.")


def okno_przegladarki(serwer):
    """Zapasowa droga: Edge/Chrome w trybie aplikacji. Blokuje do zamknięcia okna."""
    przegladarka = znajdz_przegladarke()
    if not przegladarka:
        print("Nie znaleziono Edge ani Chrome - otwieram w domyślnej przeglądarce.")
        webbrowser.open(URL)
        if serwer is not None:
            serwer.wait()
        return

    profil = KATALOG / "dane" / "okno"
    profil.mkdir(parents=True, exist_ok=True)
    if serwer is not None:
        # Sprzątamy tylko wtedy, gdy to my właśnie postawiliśmy serwer. Przy ponownym
        # kliknięciu ikony zabicie starego okna wywołałoby ten sam błąd od drugiej strony.
        zamknij_stare_okna(profil)

    okno = subprocess.Popen([
        str(przegladarka), f"--app={URL}", f"--user-data-dir={profil}",
        "--window-size=1500,950", "--no-first-run", "--no-default-browser-check",
    ])
    start = time.monotonic()
    okno.wait()
    if time.monotonic() - start < 15 and serwer is not None:
        # Okno zniknęło za szybko, żeby użytkownik zdążył je zamknąć - sterowanie
        # przejęła inna instancja. Nie wolno teraz ubić serwera.
        print("Okno przekazane innej instancji - zamknij to okno konsoli, żeby zatrzymać.")
        serwer.wait()


def zatrzymaj(serwer):
    if serwer is not None and serwer.poll() is None:
        serwer.terminate()
        try:
            serwer.wait(timeout=10)
        except subprocess.TimeoutExpired:
            serwer.kill()


def main():
    serwer = wystartuj_serwer()
    print(f"\nTrener AI działa pod adresem {URL}")
    try:
        if not okno_natywne():
            okno_przegladarki(serwer)
    except KeyboardInterrupt:
        pass
    finally:
        zatrzymaj(serwer)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Uruchamiani przez pythonw.exe nie mamy konsoli, więc błąd nie miałby się gdzie
        # pokazać - aplikacja po prostu nie wstałaby w ciszy. Zapisujemy ślad i mówimy o tym.
        import ctypes
        import traceback

        log = KATALOG / "dane" / "blad.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(traceback.format_exc(), encoding="utf-8")
        ctypes.windll.user32.MessageBoxW(
            None, f"Trener AI nie wystartował.\n\nSzczegóły zapisano w pliku:\n{log}",
            "Trener AI", 0x10)
        sys.exit(1)
