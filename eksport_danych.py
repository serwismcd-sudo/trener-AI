# -*- coding: utf-8 -*-
"""Zrzuca zawartość lokalnej bazy do jednego pliku JSON.

Potrzebne przy przeprowadzce do chmury: ten plik wczytamy do Postgresa,
żeby historia ważeń, plany i profil nie zostały na dysku.
Uruchomienie:  python eksport_danych.py
"""

import json
from datetime import datetime
from pathlib import Path

import database

PLIK = Path(__file__).parent / "dane" / "eksport.json"


def zbierz(plik_bazy=database.PLIK_BAZY):
    dni = [database.wczytaj_dzien(d, plik=plik_bazy)
           for d in database.historia_dni(9999, plik=plik_bazy)]
    tygodnie = [database.wczytaj_tydzien(t, plik=plik_bazy)
                for t in database.historia_tygodni(9999, plik=plik_bazy)]
    return {
        "wyeksportowano": datetime.now().isoformat(timespec="seconds"),
        "profil": database.wczytaj_profil(plik=plik_bazy),
        "waga": [{"data": d, "kg": kg} for d, kg in database.historia_wagi(plik=plik_bazy)],
        "dni": dni,
        "tygodnie": tygodnie,
    }


def zapisz(sciezka=PLIK, plik_bazy=database.PLIK_BAZY):
    dane = zbierz(plik_bazy)
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    sciezka.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
    return sciezka, dane


if __name__ == "__main__":
    plik, dane = zapisz()
    print(f"zapisano: {plik} ({plik.stat().st_size // 1024} KB)\n")
    print(f"  profil:    {len(dane['profil'])} pól")
    print(f"  ważenia:   {len(dane['waga'])} pomiarów"
          + (f" ({dane['waga'][0]['data']} .. {dane['waga'][-1]['data']})" if dane["waga"] else ""))
    print(f"  dni:       {len(dane['dni'])} planów dziennych")
    print(f"  tygodnie:  {len(dane['tygodnie'])} planów tygodniowych")

    # Samosprawdzenie: plik da się odczytać i nic nie zginęło po drodze.
    wczytane = json.loads(plik.read_text(encoding="utf-8"))
    assert len(wczytane["waga"]) == len(database.historia_wagi()), "zgubione ważenia"
    assert wczytane["profil"] == database.wczytaj_profil(), "profil się nie zgadza"
    assert all(d and d.get("plan") for d in wczytane["dni"]), "pusty plan dzienny w eksporcie"
    print("\neksport_danych.py: OK")
