# -*- coding: utf-8 -*-
"""Prognoza spadku wagi tydzień po tygodniu. Czysta arytmetyka, bez udziału AI.

Kluczowa rzecz: tempo NIE jest stałe. Wraz ze spadkiem masy maleje podstawowa
przemiana materii, więc przy tej samej diecie deficyt się kurczy i chudnięcie
zwalnia. Dlatego zapotrzebowanie przeliczamy od nowa na każdy tydzień.
"""

from datetime import date, timedelta

KCAL_NA_KG = 7700          # przyjęta wartość energetyczna 1 kg tkanki tłuszczowej
MIN_WAGA = 40              # zabezpieczenie, żeby pętla nie schodziła w absurd

AKTYWNOSC = {
    "siedzący tryb życia, bez treningów": 1.2,
    "praca siedząca, 1-3 treningi w tygodniu": 1.375,
    "praca siedząca, 4-5 treningów w tygodniu": 1.45,
    "praca fizyczna albo 6-7 treningów": 1.6,
}


def bmr(waga_kg, wzrost_cm, wiek, plec):
    """Podstawowa przemiana materii wg wzoru Mifflin-St Jeor."""
    podstawa = 10 * waga_kg + 6.25 * wzrost_cm - 5 * wiek
    return podstawa + (5 if str(plec).lower().startswith("m") else -161)


MIN_KCAL = {"m": 1500, "k": 1200}   # te same progi, których pilnuje prompt systemowy


def prognoza(waga_start, wzrost_cm, wiek, plec, kalorie_dziennie=None,
             wspolczynnik=1.45, tygodni=52, od=None, deficyt_procent=None):
    """Lista tygodni: (data, waga, tdee, deficyt_dzienny, ubytek_w_tygodniu).

    Dwa tryby:
    - kalorie_dziennie: jesz stale tyle samo. Tempo samo zwalnia, bo maleje
      zapotrzebowanie. Tak wyjdzie, jeśli raz ustalisz jadłospis i go nie ruszasz.
    - deficyt_procent (np. 0.20): plan przeliczany co tydzień pod aktualną wagę.
      Tak działa ta aplikacja, gdy regularnie generujesz nowy plan.
    """
    od = od or date.today()
    prog = MIN_KCAL["m" if str(plec).lower().startswith("m") else "k"]
    waga = float(waga_start)
    wynik = []
    for tydzien in range(1, tygodni + 1):
        tdee = bmr(waga, wzrost_cm, wiek, plec) * wspolczynnik
        kalorie = max(tdee * (1 - deficyt_procent), prog) if deficyt_procent else kalorie_dziennie
        deficyt = tdee - kalorie
        ubytek = max(0.0, deficyt * 7 / KCAL_NA_KG)   # nadwyżka kalorii nie tuczy w tym modelu
        waga = max(waga - ubytek, MIN_WAGA)
        wynik.append((od + timedelta(weeks=tydzien), round(waga, 1),
                      round(tdee), round(deficyt), round(ubytek, 2)))
    return wynik


def kiedy_cel(prognoza_tygodni, cel_kg):
    """Pierwszy tydzień, w którym waga schodzi do celu. None, jeśli nie w tym zakresie."""
    for nr, (data, waga, *_) in enumerate(prognoza_tygodni, start=1):
        if waga <= cel_kg:
            return nr, data
    return None


if __name__ == "__main__":
    # Samosprawdzenie: profil użytkownika, 2250 kcal, praca siedząca + 4 treningi.
    p = prognoza(114.0, 176, 48, "mężczyzna", 2250, 1.45, tygodni=52)

    assert len(p) == 52
    wagi = [w for _, w, *_ in p]
    assert wagi == sorted(wagi, reverse=True), "waga musi maleć monotonicznie"

    pierwszy, ostatni = p[0][4], p[-1][4]
    assert pierwszy > ostatni, f"tempo ma zwalniać, a mamy {pierwszy} -> {ostatni} kg/tydz."
    print(f"ubytek w 1. tygodniu: {pierwszy} kg, w 52. tygodniu: {ostatni} kg (zwalnia)")

    cel = kiedy_cel(p, 79)
    print(f"cel 79 kg: {'tydzień ' + str(cel[0]) + ', ' + cel[1].isoformat() if cel else 'poza rokiem'}")
    print(f"po roku: {wagi[-1]} kg (start 114 kg, razem {round(114 - wagi[-1], 1)} kg)")

    # Przy jedzeniu na poziomie zapotrzebowania waga stoi.
    stoi = prognoza(114.0, 176, 48, "mężczyzna", 99999, 1.45, tygodni=4)
    assert all(w == 114.0 for _, w, *_ in stoi), "bez deficytu waga nie może spadać"
    print("brak deficytu = brak spadku: OK")

    # Tryb drugi: plan korygowany co tydzień, stały deficyt 20%.
    k = prognoza(114.0, 176, 48, "mężczyzna", wspolczynnik=1.45, tygodni=52, deficyt_procent=0.20)
    print(f"\nkorygowany co tydzień (-20%): po roku {k[-1][1]} kg, "
          f"razem {round(114 - k[-1][1], 1)} kg")
    assert k[-1][1] < p[-1][1], "korygowanie planu powinno dawać lepszy wynik niż stała podaż"

    dlugi = prognoza(114.0, 176, 48, "mężczyzna", wspolczynnik=1.45, tygodni=200, deficyt_procent=0.20)
    c = kiedy_cel(dlugi, 79)
    print(f"cel 79 kg przy korygowanym planie: tydzień {c[0]} ({c[1].isoformat()}), "
          f"czyli ok. {round(c[0]/4.33)} miesięcy")

    dlugi_staly = prognoza(114.0, 176, 48, "mężczyzna", 2250, 1.45, tygodni=300)
    cs = kiedy_cel(dlugi_staly, 79)
    print(f"cel 79 kg przy stałych 2250 kcal: tydzień {cs[0]}, czyli ok. {round(cs[0]/4.33)} miesięcy")

    print("\nprognoza.py: OK")
