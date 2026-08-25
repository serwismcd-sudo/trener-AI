# -*- coding: utf-8 -*-
"""Z eksportu JSON robi dwa pliki SQL do wklejenia w edytorze SQL Supabase.

Dzięki temu baza powstaje bez podawania komukolwiek hasła - wszystko dzieje się
w panelu Supabase, do którego logujesz się sam.
"""

import json
from pathlib import Path

KATALOG = Path(__file__).parent / "dane"
EKSPORT = KATALOG / "eksport.json"

SCHEMAT = """-- Trener AI: struktura bazy
-- Wklej całość w Supabase -> SQL Editor -> Run

create table if not exists ustawienia (
    klucz   text primary key,
    wartosc jsonb
);

create table if not exists waga (
    data date primary key,
    kg    real not null
);

create table if not exists dzien (
    data      date primary key,
    garmin    jsonb,
    plan      jsonb,
    utworzono timestamptz default now()
);

create table if not exists tydzien (
    od        date primary key,
    plan      jsonb,
    utworzono timestamptz default now()
);

-- WAŻNE dla bezpieczeństwa: Supabase wystawia tabele ze schematu public przez
-- publiczne API. Klucz "anon" jest jawny, więc bez tego każdy mógłby odczytać
-- Twoją wagę i plany. Włączenie RLS bez żadnej polityki blokuje ten dostęp,
-- a aplikacja i tak łączy się rolą postgres, której RLS nie dotyczy.
alter table ustawienia enable row level security;
alter table waga       enable row level security;
alter table dzien      enable row level security;
alter table tydzien    enable row level security;
"""


def _json(wartosc):
    """Literał JSON w dolarowym cudzysłowie - odporny na apostrofy w tekście."""
    return "$j$" + json.dumps(wartosc, ensure_ascii=False) + "$j$"


def zrob_import(dane):
    w = ["-- Trener AI: Twoje dane z lokalnej bazy",
         "-- Wklej w Supabase -> SQL Editor -> Run (po utworzeniu tabel)", ""]

    if dane.get("profil"):
        w.append("insert into ustawienia (klucz, wartosc) values "
                 f"('profil', {_json(dane['profil'])}::jsonb) "
                 "on conflict (klucz) do update set wartosc = excluded.wartosc;")
        w.append("")

    if dane.get("waga"):
        w.append("insert into waga (data, kg) values")
        wiersze = [f"  ('{p['data']}', {p['kg']})" for p in dane["waga"]]
        w.append(",\n".join(wiersze))
        w.append("on conflict (data) do update set kg = excluded.kg;")
        w.append("")

    for d in dane.get("dni", []):
        w.append(f"insert into dzien (data, garmin, plan) values ('{d['data']}', "
                 f"{_json(d['garmin'])}::jsonb, {_json(d['plan'])}::jsonb) "
                 "on conflict (data) do update set garmin = excluded.garmin, plan = excluded.plan;")
    if dane.get("dni"):
        w.append("")

    for t in dane.get("tygodnie", []):
        w.append(f"insert into tydzien (od, plan) values ('{t['od']}', {_json(t['plan'])}::jsonb) "
                 "on conflict (od) do update set plan = excluded.plan;")

    return "\n".join(w) + "\n"


if __name__ == "__main__":
    assert EKSPORT.exists(), "najpierw uruchom: python eksport_danych.py"
    dane = json.loads(EKSPORT.read_text(encoding="utf-8"))

    p1 = KATALOG / "1-tabele.sql"
    p2 = KATALOG / "2-dane.sql"
    p1.write_text(SCHEMAT, encoding="utf-8")
    p2.write_text(zrob_import(dane), encoding="utf-8")

    # Kontrola: czy nic nie zginęło i czy nie ma niedomkniętych literałów.
    tresc = p2.read_text(encoding="utf-8")
    assert tresc.count("$j$") % 2 == 0, "niedomknięty literał JSON"
    assert tresc.count("insert into waga") == 1
    assert all(p["data"] in tresc for p in dane["waga"]), "brakuje któregoś ważenia"
    print(f"{p1.name}: {p1.stat().st_size} B")
    print(f"{p2.name}: {p2.stat().st_size // 1024} KB "
          f"({len(dane['waga'])} ważeń, {len(dane['dni'])} dni, {len(dane['tygodnie'])} tygodni)")
    print("\nzrob_sql.py: OK")
