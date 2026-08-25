# -*- coding: utf-8 -*-
"""Baza danych: Postgres w chmurze albo lokalny plik SQLite.

Wybór jest automatyczny: jeśli w środowisku (albo w sekretach Streamlita) jest
DATABASE_URL, aplikacja pisze do Supabase i wtedy komputer i telefon widzą te same
dane. Bez tego adresu działa po staremu na pliku trener.db obok skryptów.
"""

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PLIK_BAZY = Path(__file__).parent / "trener.db"


def _adres_chmury():
    """Adres bazy z .env, a na Streamlit Cloud z panelu sekretów."""
    adres = os.getenv("DATABASE_URL")
    if adres:
        return adres
    try:                                   # tylko gdy działamy pod Streamlitem
        import streamlit as st
        return st.secrets.get("DATABASE_URL")
    except Exception:
        return None


CHMURA = bool(_adres_chmury())

SCHEMAT = """
CREATE TABLE IF NOT EXISTS dzien (
    data      TEXT PRIMARY KEY,
    garmin    TEXT,
    plan      TEXT,
    utworzono TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS waga (
    data TEXT PRIMARY KEY,
    kg   REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS ustawienia (
    klucz   TEXT PRIMARY KEY,
    wartosc TEXT
);
CREATE TABLE IF NOT EXISTS tydzien (
    od        TEXT PRIMARY KEY,
    plan      TEXT,
    utworzono TEXT DEFAULT (datetime('now', 'localtime'))
);
"""


def polacz(plik=PLIK_BAZY):
    """Połączenie do bazy. W chmurze parametr `plik` jest pomijany."""
    adres = _adres_chmury()
    if adres:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(adres, row_factory=dict_row, connect_timeout=15)

    # Nowe połączenie na każde wywołanie - Streamlit przerysowuje stronę w innych
    # wątkach, a połączenia sqlite3 nie są współdzielone między wątkami.
    db = sqlite3.connect(plik)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMAT)
    return db


def _sql(zapytanie):
    """SQLite używa znaku ?, psycopg %s. Reszta składni jest wspólna."""
    return zapytanie.replace("?", "%s") if CHMURA else zapytanie


def _json(wartosc):
    """Postgres zwraca kolumny jsonb od razu jako dict, SQLite jako tekst."""
    if wartosc is None:
        return {}
    return wartosc if isinstance(wartosc, (dict, list)) else json.loads(wartosc)


def _wykonaj(zapytanie, parametry=(), plik=PLIK_BAZY):
    with closing(polacz(plik)) as db, db:
        db.execute(_sql(zapytanie), parametry)


def _pobierz(zapytanie, parametry=(), plik=PLIK_BAZY, jeden=False):
    with closing(polacz(plik)) as db, db:
        kursor = db.execute(_sql(zapytanie), parametry)
        return kursor.fetchone() if jeden else kursor.fetchall()


# ----------------------------------------------------------------- plan dnia
def zapisz_dzien(data, garmin, plan, plik=PLIK_BAZY):
    _wykonaj(
        "INSERT INTO dzien (data, garmin, plan) VALUES (?, ?, ?) "
        "ON CONFLICT(data) DO UPDATE SET garmin=excluded.garmin, plan=excluded.plan",
        (data, json.dumps(garmin, ensure_ascii=False), json.dumps(plan, ensure_ascii=False)),
        plik,
    )


def wczytaj_dzien(data, plik=PLIK_BAZY):
    w = _pobierz("SELECT * FROM dzien WHERE data = ?", (data,), plik, jeden=True)
    if not w:
        return None
    return {
        "data": str(w["data"]),
        "garmin": _json(w["garmin"]),
        "plan": _json(w["plan"]),
        "utworzono": str(w["utworzono"]),
    }


def historia_dni(limit=14, plik=PLIK_BAZY):
    return [str(w["data"]) for w in
            _pobierz("SELECT data FROM dzien ORDER BY data DESC LIMIT ?", (limit,), plik)]


# --------------------------------------------------------------------- waga
def zapisz_wage(data, kg, plik=PLIK_BAZY):
    _wykonaj(
        "INSERT INTO waga (data, kg) VALUES (?, ?) "
        "ON CONFLICT(data) DO UPDATE SET kg=excluded.kg",
        (data, float(kg)), plik,
    )


def historia_wagi(plik=PLIK_BAZY):
    """[(data, kg), ...] rosnąco po dacie."""
    return [(str(w["data"]), w["kg"]) for w in
            _pobierz("SELECT data, kg FROM waga ORDER BY data", (), plik)]


def ostatnia_waga(plik=PLIK_BAZY):
    w = _pobierz("SELECT kg FROM waga ORDER BY data DESC LIMIT 1", (), plik, jeden=True)
    return w["kg"] if w else None


# ---------------------------------------------------------------- plan tygodnia
def zapisz_tydzien(od, plan, plik=PLIK_BAZY):
    _wykonaj(
        "INSERT INTO tydzien (od, plan) VALUES (?, ?) "
        "ON CONFLICT(od) DO UPDATE SET plan=excluded.plan",
        (od, json.dumps(plan, ensure_ascii=False)), plik,
    )


def wczytaj_tydzien(od, plik=PLIK_BAZY):
    w = _pobierz("SELECT * FROM tydzien WHERE od = ?", (od,), plik, jeden=True)
    if not w:
        return None
    return {"od": str(w["od"]), "plan": _json(w["plan"]), "utworzono": str(w["utworzono"])}


def historia_tygodni(limit=12, plik=PLIK_BAZY):
    return [str(w["od"]) for w in
            _pobierz("SELECT od FROM tydzien ORDER BY od DESC LIMIT ?", (limit,), plik)]


# -------------------------------------------------------------------- profil
def zapisz_profil(profil, plik=PLIK_BAZY):
    _wykonaj(
        "INSERT INTO ustawienia (klucz, wartosc) VALUES ('profil', ?) "
        "ON CONFLICT(klucz) DO UPDATE SET wartosc=excluded.wartosc",
        (json.dumps(profil, ensure_ascii=False),), plik,
    )


def wczytaj_profil(plik=PLIK_BAZY):
    w = _pobierz("SELECT wartosc FROM ustawienia WHERE klucz = 'profil'", (), plik, jeden=True)
    return _json(w["wartosc"]) if w else {}


if __name__ == "__main__":
    import os as _os
    import tempfile

    print("tryb:", "Postgres (chmura)" if CHMURA else "SQLite (plik lokalny)")

    if CHMURA:
        print(f"ważeń w bazie: {len(historia_wagi())}")
        print(f"ostatnia waga: {ostatnia_waga()} kg")
        print(f"profil: {len(wczytaj_profil())} pól")
        print(f"dni: {len(historia_dni(9999))}, tygodni: {len(historia_tygodni(9999))}")
        print("\ndatabase.py: OK (odczyt z chmury)")
    else:
        p = Path(tempfile.gettempdir()) / "trener_test.db"
        p.unlink(missing_ok=True)

        zapisz_dzien("2026-08-22", {"sen_h": 6.2}, {"kalorie": 2100}, plik=p)
        zapisz_dzien("2026-08-22", {"sen_h": 7.0}, {"kalorie": 2000}, plik=p)  # nadpisanie
        d = wczytaj_dzien("2026-08-22", plik=p)
        assert d["garmin"]["sen_h"] == 7.0 and d["plan"]["kalorie"] == 2000, d
        assert wczytaj_dzien("2000-01-01", plik=p) is None

        zapisz_wage("2026-08-20", 130.5, plik=p)
        zapisz_wage("2026-08-22", 129.8, plik=p)
        assert historia_wagi(plik=p) == [("2026-08-20", 130.5), ("2026-08-22", 129.8)]
        assert ostatnia_waga(plik=p) == 129.8

        zapisz_tydzien("2026-08-24", {"dni": [{"dzien": "Poniedziałek"}]}, plik=p)
        assert wczytaj_tydzien("2026-08-24", plik=p)["plan"]["dni"][0]["dzien"] == "Poniedziałek"
        assert historia_tygodni(plik=p) == ["2026-08-24"]

        zapisz_profil({"cel_kg": 95}, plik=p)
        assert wczytaj_profil(plik=p)["cel_kg"] == 95
        assert historia_dni(plik=p) == ["2026-08-22"]

        _os.remove(p)
        print("database.py: OK (plik lokalny)")
