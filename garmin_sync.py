"""Pobieranie danych z chmury Garmin Connect (Forerunner 965).

Pierwsze logowanie (obsluguje kod MFA) uruchamiasz recznie:  python garmin_sync.py
Potem aplikacja korzysta juz z zapisanego tokenu i nie pyta o haslo.
"""

import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin

load_dotenv()

# Token sesji Garmina (wazny ok. roku). Nie trzymamy hasla w aplikacji.
# GARMINTOKENS to nazwa uzywana takze przez sama biblioteke garminconnect.
# W wersji przenosnej (pendrive) obok aplikacji istnieje folder dane\garmin i token
# ma tam zostac, zeby jechal razem z pendrivem zamiast zostawac w profilu na obcym
# komputerze. Na zwyklej instalacji tego folderu nie ma i token idzie do katalogu domowego.
_LOKALNY_TOKEN = Path(__file__).parent / "dane" / "garmin"
KATALOG_TOKENOW = os.getenv("GARMINTOKENS") or str(
    _LOKALNY_TOKEN if _LOKALNY_TOKEN.is_dir() else Path.home() / ".garminconnect"
)


def _mfa_w_aplikacji():
    # Wywolywane tylko wtedy, gdy Garmin zada kodu MFA w trakcie pracy aplikacji.
    # Streamlit nie ma jak zapytac o kod w watku roboczym, wiec odsylamy do konsoli.
    raise RuntimeError(
        "Garmin zada kodu MFA. Uruchom w konsoli: python garmin_sync.py i podaj kod."
    )


def _g(obiekt, *klucze, domyslnie=None):
    """Bezpieczne zejscie w zagniezdzony JSON od Garmina - brak klucza to None, nie wyjatek."""
    for k in klucze:
        if not isinstance(obiekt, dict):
            return domyslnie
        obiekt = obiekt.get(k)
    return domyslnie if obiekt is None else obiekt


def _sprobuj(fn, *a, **kw):
    """Jeden padniety endpoint Garmina nie moze wywrocic calej synchronizacji."""
    try:
        return fn(*a, **kw)
    except Exception as e:
        print(f"[garmin] {getattr(fn, '__name__', fn)} nie odpowiedzialo: {e}")
        return None


def _pierwsza_wartosc(mapa):
    """Garmin zwraca czesc metryk jako slownik {id_urzadzenia: dane}."""
    if isinstance(mapa, dict) and mapa:
        return next(iter(mapa.values()))
    return None


def klient():
    """Klient Garmina: najpierw zapisany token, w razie potrzeby ponowne logowanie z .env.

    Odswiezony token zapisuje sie sam - o haslo nie pytamy juz nigdy,
    chyba ze Garmin zazada kodu MFA (wtedy: python garmin_sync.py).
    """
    g = Garmin(
        email=os.getenv("GARMIN_EMAIL"),
        password=os.getenv("GARMIN_PASSWORD"),
        prompt_mfa=_mfa_w_aplikacji,
    )
    g.login(KATALOG_TOKENOW)
    return g


def zaloguj_haslem(kod_mfa=None):
    """Pierwsze logowanie e-mailem i haslem z .env. Obsluguje MFA. Do uruchomienia z konsoli."""
    email = (os.getenv("GARMIN_EMAIL") or "").strip()
    haslo = (os.getenv("GARMIN_PASSWORD") or "").strip()
    if not email or not haslo:
        raise RuntimeError("Brak GARMIN_EMAIL / GARMIN_PASSWORD w pliku .env")
    # Najczestsza pomylka: uzytkownik dopisuje dane OBOK tekstu z szablonu zamiast go zastapic.
    # Bez tej kontroli Garmin odpowiada tylko "401 Invalid Username or Password".
    if haslo.lower().startswith("twoje-") or email.lower().startswith("twoj@"):
        raise RuntimeError(
            "W pliku .env zostal tekst z szablonu ('twoje-' albo 'twoj@').\n"
            "Otworz .env i zostaw w linii SAMA wartosc, bez podpowiedzi z szablonu:\n"
            "  GARMIN_EMAIL=adres@example.com\n"
            "  GARMIN_PASSWORD=TwojePrawdziweHaslo"
        )

    g = Garmin(email=email, password=haslo, return_on_mfa=True)
    wynik, stan = g.login()
    if wynik == "needs_mfa":
        kod = kod_mfa or input("Kod MFA z maila / aplikacji Garmin: ").strip()
        g.resume_login(stan, kod)
    g.client.dump(KATALOG_TOKENOW)  # zapis tokenu na dysk (0600)
    return g


def pobierz_wagi(od, do=None, g=None):
    """Wazenia z wagi Garmin Index — lista (data, kg) rosnaco.

    Garmin trzyma wage w gramach, a na jeden dzien moze przypasc kilka pomiarow
    (bierzemy ostatni z dnia, tak jak pokazuje to aplikacja Garmin Connect).
    """
    do = do or date.today()
    g = g or klient()
    dane = _sprobuj(g.get_weigh_ins, od.isoformat(), do.isoformat()) or {}

    wynik = []
    for dzien in dane.get("dailyWeightSummaries", []):
        gramy = (dzien.get("latestWeight") or {}).get("weight")
        data = dzien.get("summaryDate")
        if gramy and data:
            wynik.append((data, round(gramy / 1000, 1)))
    return sorted(wynik)


def pobierz(dzien=None, g=None):
    """Regeneracja z dzisiaj + podsumowanie i aktywnosci z dnia poprzedniego."""
    dzien = dzien or date.today()
    wczoraj = dzien - timedelta(days=1)
    d, w = dzien.isoformat(), wczoraj.isoformat()
    g = g or klient()

    dzis_sum = _sprobuj(g.get_stats, d) or {}
    wczoraj_sum = _sprobuj(g.get_stats, w) or {}
    sen = _sprobuj(g.get_sleep_data, d) or {}
    status = _sprobuj(g.get_training_status, d) or {}
    gotowosc = _sprobuj(g.get_training_readiness, d) or []
    aktywnosci = _sprobuj(g.get_activities_by_date, w, w) or []

    obciazenie = _pierwsza_wartosc(
        _g(status, "mostRecentTrainingLoadBalance", "metricsTrainingLoadBalanceDTOMap") or {}
    ) or {}
    status_tren = _pierwsza_wartosc(
        _g(status, "mostRecentTrainingStatus", "latestTrainingStatusData") or {}
    ) or {}
    gotowosc = gotowosc[0] if isinstance(gotowosc, list) and gotowosc else {}

    sen_s = _g(sen, "dailySleepDTO", "sleepTimeSeconds")

    return {
        "data": d,
        # --- regeneracja (dzis rano) ---
        "sen_godziny": round(sen_s / 3600, 1) if sen_s else None,
        "sen_ocena": _g(sen, "dailySleepDTO", "sleepScores", "overall", "value"),
        "sen_gleboki_min": round(_g(sen, "dailySleepDTO", "deepSleepSeconds", domyslnie=0) / 60) or None,
        "sen_rem_min": round(_g(sen, "dailySleepDTO", "remSleepSeconds", domyslnie=0) / 60) or None,
        "body_battery": _g(dzis_sum, "bodyBatteryMostRecentValue")
        or _g(dzis_sum, "bodyBatteryHighestValue"),
        "tetno_spoczynkowe": _g(dzis_sum, "restingHeartRate"),
        "stres_sredni": _g(dzis_sum, "averageStressLevel"),
        "gotowosc_score": _g(gotowosc, "score"),
        "gotowosc_opis": _g(gotowosc, "feedbackShort"),
        # --- wczoraj ---
        "wczoraj_data": w,
        "wczoraj_kalorie_razem": _g(wczoraj_sum, "totalKilocalories"),
        "wczoraj_kalorie_aktywne": _g(wczoraj_sum, "activeKilocalories"),
        "wczoraj_kroki": _g(wczoraj_sum, "totalSteps"),
        "wczoraj_aktywnosci": [
            {
                "typ": _g(a, "activityType", "typeKey"),
                "nazwa": a.get("activityName"),
                "minuty": round(a.get("duration", 0) / 60),
                "kcal": a.get("calories"),
                "srednie_tetno": a.get("averageHR"),
            }
            for a in aktywnosci
        ],
        # --- obciazenie treningowe ---
        "status_treningowy": _g(status_tren, "trainingStatusFeedbackPhrase"),
        "obciazenie_ostre": _g(obciazenie, "acwrPercent") or _g(obciazenie, "dailyTrainingLoadAcute"),
        "obciazenie_przewlekle": _g(obciazenie, "dailyTrainingLoadChronic"),
        "obciazenie_ocena": _g(obciazenie, "trainingBalanceFeedbackPhrase"),
    }


def _komunikat(e):
    """Zamienia techniczny wyjatek Garmina na zdanie, z ktorym wiadomo co zrobic."""
    t = str(e)
    if "429" in t or "TooManyRequests" in t or "rate limited" in t.lower():
        return ("Garmin chwilowo blokuje logowania z Twojego adresu IP (kod 429).\n"
                "Odczekaj 15-30 minut i sprobuj ponownie. Kolejne proby w tym czasie\n"
                "tylko przedluzaja blokade.")
    if "401" in t or "Invalid Username or Password" in t:
        return ("Garmin odrzucil dane logowania (401).\n"
                "Sprawdz w pliku .env, czy GARMIN_EMAIL i GARMIN_PASSWORD sa dokladnie\n"
                "takie, jak przy logowaniu na connect.garmin.com - bez cudzyslowow,\n"
                "bez spacji i bez resztek tekstu z szablonu.")
    return t


if __name__ == "__main__":
    import json
    import sys

    print(f"Token zostanie zapisany w: {KATALOG_TOKENOW}")
    try:
        g = Garmin()
        g.login(KATALOG_TOKENOW)
        print("Zalogowano na istniejacym tokenie.")
    except Exception:
        print("Brak waznego tokenu - loguje sie haslem z pliku .env...")
        try:
            g = zaloguj_haslem()
        except Exception as e:
            print("\n--- LOGOWANIE NIEUDANE ---")
            print(_komunikat(e))
            sys.exit(1)
        print("Token zapisany. Aplikacja nie bedzie juz pytac o haslo.")

    print(json.dumps(pobierz(g=g), indent=2, ensure_ascii=False))
    print("\nGotowe. Mozesz uruchomic 2-URUCHOM-TRENERA.bat")
