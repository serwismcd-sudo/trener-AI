"""Silnik AI: profil + swieze dane z Garmina -> plan dnia od Claude'a (walidowany JSON)."""

import json
import os

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")

SYSTEM = """Jesteś doświadczonym trenerem personalnym i dietetykiem klinicznym.
Prowadzisz jedną osobę przez długą redukcję masy ciała (cel: -35 kg).

Zasady, których trzymasz się bezwzględnie:
- Bezpieczne tempo redukcji to 0,5-1% masy ciała tygodniowo. Nie przyspieszaj tego głodówką.
- Deficyt kaloryczny 15-25% poniżej dziennego wydatku. NIGDY nie schodzisz poniżej
  1500 kcal u mężczyzn i 1200 kcal u kobiet, nawet jeśli użytkownik o to prosi.
- Wysoka podaż białka chroniąca mięśnie: 1,6-2,2 g na kg docelowej (nie aktualnej) masy ciała.
- Trening dobierasz do STANU REGENERACJI z Garmina, nie do ambicji:
  niskie Body Battery (<40), krótki lub słaby sen, podwyższone tętno spoczynkowe
  albo status "overreaching" oznaczają spacer, strefę 2 albo pełny odpoczynek.
  Nie planuj interwałów na zmęczonym organizmie.
- Przy dużej nadwadze oszczędzasz stawy: preferuj marsz, rower, orbitrek, basen
  zamiast długiego biegania.
- Siła 2-3 razy w tygodniu jest obowiązkowym elementem ochrony mięśni w deficycie.
- Jeśli dane z Garmina są niepełne (pola null), powiedz to wprost i planuj zachowawczo.
- Bezpieczeństwo żywności jest ważniejsze niż wygoda jadłospisu. NIGDY nie proponujesz
  surowego mięsa, surowych jaj ani surowej ryby, nawet jeśli użytkownik prosi o dietę
  bez gotowania - to ryzyko salmonelli, listerii i pasożytów. Przy diecie bez gotowania
  białko bierzesz z produktów gotowych do spożycia: nabiał (skyr, twaróg, serek wiejski,
  jogurt grecki, kefir, ser), ryby wędzone i z puszki, dobrej jakości wędliny, odżywka
  białkowa, strączki z puszki, orzechy i nasiona. Jajka tylko jako gotowe ugotowane.
  Jeśli przy danym ograniczeniu nie da się bezpiecznie dobić do celu białkowego,
  powiedz to wprost i podaj, ile realnie wychodzi.

Jesteś asystentem, nie lekarzem. Przy niepokojących sygnałach (długotrwale wysokie
tętno spoczynkowe, skrajne zmęczenie, ból) zalecasz kontakt z lekarzem.
Piszesz po polsku, konkretnie, bez lania wody. Podajesz liczby, nie ogólniki."""


class PlanDnia(BaseModel):
    ocena_regeneracji: str = Field(
        description="2-4 zdania: jak organizm się zregenerował, na podstawie snu, Body Battery, tętna spoczynkowego i wczorajszego obciążenia."
    )
    gotowosc_do_wysilku: int = Field(
        ge=0, le=100, description="Ocena gotowości do wysiłku 0-100."
    )
    trening_typ: str = Field(
        description="Krótka etykieta, np. 'Strefa 2 - marszobieg 45 min', 'Siłownia - góra ciała', 'Pełny odpoczynek'."
    )
    trening_szczegoly: str = Field(
        description="Plan treningu w Markdown: rozgrzewka, część główna z zakresami tętna lub strefami, schłodzenie. Jeśli odpoczynek - napisz dlaczego i co wolno robić."
    )
    kalorie: int = Field(description="Docelowa podaż kaloryczna na dzisiaj (kcal).")
    bialko_g: int = Field(description="Białko w gramach na dzisiaj.")
    tluszcz_g: int = Field(description="Tłuszcz w gramach na dzisiaj.")
    wegle_g: int = Field(description="Węglowodany w gramach na dzisiaj.")
    uzasadnienie_bilansu: str = Field(
        description="1-3 zdania: skąd ta liczba kalorii, jaki deficyt względem szacowanego wydatku."
    )
    propozycja_posilkow: str = Field(
        description="Konkretne posiłki na dziś w Markdown (śniadanie/obiad/kolacja/przekąska) z orientacyjnymi kaloriami i białkiem."
    )
    uwagi: str = Field(
        description="Nawodnienie, sen, sygnały ostrzegawcze, ewentualne zalecenie kontaktu z lekarzem."
    )


class Posilek(BaseModel):
    nazwa: str = Field(description="Nazwa posiłku, np. 'Śniadanie', 'Obiad', 'Przekąska'.")
    opis: str = Field(
        description="Składniki z konkretną gramaturą, np. '200 g skyru, 60 g płatków owsianych, 100 g malin'. Bez opisu przygotowania, jeśli dieta jest bez gotowania."
    )
    kcal: int = Field(description="Kalorie tego posiłku.")
    bialko_g: int = Field(description="Białko tego posiłku w gramach.")


class DzienTygodnia(BaseModel):
    dzien: str = Field(description="Nazwa dnia po polsku, np. 'Poniedziałek'.")
    posilki: list[Posilek] = Field(description="Posiłki tego dnia, 4-5 pozycji.")
    kcal_razem: int = Field(description="Suma kalorii z posiłków tego dnia.")
    bialko_razem_g: int = Field(description="Suma białka z posiłków tego dnia.")


class Zakup(BaseModel):
    produkt: str = Field(description="Nazwa produktu tak, jak szuka się go w sklepie, np. 'Skyr naturalny', 'Tuńczyk w sosie własnym'.")
    ilosc: float = Field(description="ŁĄCZNA ilość na cały tydzień, zsumowana ze wszystkich siedmiu dni.")
    jednostka: str = Field(description="Jednostka zakupowa: 'kg', 'g', 'l', 'szt' albo 'opak'.")
    uwaga: str = Field(description="Praktyczna podpowiedź przy zakupie, np. '7 kubków po 200 g' albo 'puszki 4 x 145 g'. Pusty tekst, jeśli zbędna.")
    kategoria: str = Field(description="Dział sklepu: 'Nabiał', 'Mięso i ryby', 'Warzywa i owoce', 'Pieczywo', 'Suche i konserwy', 'Inne'.")


class PlanTygodniowy(BaseModel):
    dni: list[DzienTygodnia] = Field(description="Dokładnie 7 dni, od poniedziałku do niedzieli.")
    lista_zakupow: list[Zakup] = Field(
        description="Zbiorcza lista zakupów na cały tydzień. Każdy produkt WYSTĘPUJE TYLKO RAZ, z ilością zsumowaną ze wszystkich dni."
    )
    kcal_dzienne: int = Field(description="Docelowa dzienna podaż kaloryczna przyjęta w tym planie.")
    bialko_dzienne_g: int = Field(description="Docelowa dzienna podaż białka w gramach.")
    uwagi: str = Field(description="Uwagi: przechowywanie, co przygotować z wyprzedzeniem, czego nie kupować na zapas.")


def zbuduj_prompt(profil, garmin, waga_kg=None, historia_wagi=None):
    """Sklada wiadomosc uzytkownika: kim jest, gdzie jest, co pokazal Garmin."""
    czesci = ["## Profil użytkownika", json.dumps(profil, ensure_ascii=False, indent=2)]

    if waga_kg:
        cel = profil.get("waga_docelowa_kg")
        linie = [f"Aktualna waga: {waga_kg} kg"]
        if cel:
            linie.append(f"Waga docelowa: {cel} kg (do zrzucenia: {round(waga_kg - cel, 1)} kg)")
        if historia_wagi and len(historia_wagi) > 1:
            # Historia z wagi Garmin siega lat wstecz i bywa nieciagla, dlatego podajemy
            # zakres i ostatnie pomiary zamiast roznicy "od pierwszego wpisu" - ta ostatnia
            # myli, gdy najstarszy pomiar pochodzi z innego okresu zycia.
            naj = max(historia_wagi, key=lambda x: x[1])
            naj_niz = min(historia_wagi, key=lambda x: x[1])
            linie.append(f"Historia ważeń: {len(historia_wagi)} pomiarów, "
                         f"od {historia_wagi[0][0]} do {historia_wagi[-1][0]}")
            linie.append(f"Najwyższa waga: {naj[1]} kg ({naj[0]}), najniższa: {naj_niz[1]} kg ({naj_niz[0]})")
            linie.append("Ostatnie pomiary: " + ", ".join(f"{d}: {kg} kg" for d, kg in historia_wagi[-7:]))
        czesci += ["\n## Waga", "\n".join(linie)]

    czesci += [
        "\n## Świeże dane z zegarka Garmin (pola null = brak pomiaru)",
        json.dumps(garmin, ensure_ascii=False, indent=2),
        "\nPrzygotuj plan na dzisiaj: ocenę regeneracji, trening dopasowany do tego stanu "
        "oraz bilans kaloryczny i makroskładniki.",
    ]
    return "\n".join(czesci)


def plan_dnia(profil, garmin, waga_kg=None, historia_wagi=None, model=None):
    """Zwraca plan jako slownik (walidowany schematem PlanDnia)."""
    klient = anthropic.Anthropic()  # klucz z ANTHROPIC_API_KEY w .env
    odpowiedz = klient.messages.parse(
        model=model or MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": zbuduj_prompt(profil, garmin, waga_kg, historia_wagi)}],
        output_format=PlanDnia,
    )
    if odpowiedz.stop_reason == "refusal":
        raise RuntimeError(f"Model odmówił odpowiedzi: {odpowiedz.stop_details}")
    if odpowiedz.parsed_output is None:
        raise RuntimeError(f"Nie udało się sparsować odpowiedzi (stop_reason={odpowiedz.stop_reason})")
    return odpowiedz.parsed_output.model_dump()


def plan_tygodniowy(profil, waga_kg=None, historia_wagi=None, model=None):
    """Jadłospis na 7 dni plus zbiorcza lista zakupów. Nie korzysta z danych Garmina -
    plan żywieniowy na tydzień układa się z profilu i wagi, a nie ze snu z jednej nocy."""
    czesci = ["## Profil użytkownika", json.dumps(profil, ensure_ascii=False, indent=2)]
    if waga_kg:
        cel = profil.get("waga_docelowa_kg")
        czesci += ["\n## Waga", f"Aktualna: {waga_kg} kg" +
                   (f", docelowa: {cel} kg (do zrzucenia {round(waga_kg - cel, 1)} kg)" if cel else "")]
    if historia_wagi and len(historia_wagi) > 1:
        czesci.append("Ostatnie pomiary: " +
                      ", ".join(f"{d}: {kg} kg" for d, kg in historia_wagi[-5:]))
    czesci += [
        "\nUłóż jadłospis na 7 dni (poniedziałek-niedziela) oraz JEDNĄ zbiorczą listę "
        "zakupów na cały tydzień.\n"
        "Wymagania dla listy zakupów:\n"
        "- każdy produkt występuje na liście dokładnie raz, z ilością zsumowaną ze wszystkich dni,\n"
        "- ilości podawaj w jednostkach zakupowych: kg lub g, litry, sztuki, opakowania,\n"
        "- zaokrąglaj w górę do tego, co realnie kupi się w sklepie,\n"
        "- pogrupuj produkty po działach sklepu.\n"
        "Jadłospis ma być powtarzalny i prosty: nie wymyślaj siedmiu zupełnie różnych śniadań, "
        "lepiej 2-3 warianty na zmianę, żeby lista zakupów była krótka i nic się nie zmarnowało.",
    ]

    klient = anthropic.Anthropic()
    # Jadłospis na 7 dni z listą zakupów to długa odpowiedź. Przy takim max_tokens SDK
    # wymaga streamingu, bo zwykłe żądanie mogłoby przekroczyć limit czasu połączenia.
    with klient.messages.stream(
        model=model or MODEL,
        max_tokens=32000,
        system=SYSTEM,
        messages=[{"role": "user", "content": "\n".join(czesci)}],
        output_format=PlanTygodniowy,
    ) as strumien:
        odpowiedz = strumien.get_final_message()
    if odpowiedz.stop_reason == "refusal":
        raise RuntimeError(f"Model odmówił odpowiedzi: {odpowiedz.stop_details}")
    if odpowiedz.parsed_output is None:
        raise RuntimeError(f"Nie udało się sparsować odpowiedzi (stop_reason={odpowiedz.stop_reason})")
    return odpowiedz.parsed_output.model_dump()


if __name__ == "__main__":
    # Samosprawdzenie bez wywolania API (bez kosztow): czy prompt zbiera wszystkie dane.
    p = zbuduj_prompt(
        {"wiek": 48, "plec": "mężczyzna", "wzrost_cm": 176, "waga_docelowa_kg": 79},
        {"sen_godziny": 6.0, "body_battery": 45, "tetno_spoczynkowe": 62, "wczoraj_aktywnosci": []},
        waga_kg=114.0,
        # historia z luka: stare pomiary z innego okresu nie moga udawac biezacego postepu
        historia_wagi=[("2023-08-23", 101.8), ("2026-01-08", 92.8), ("2026-08-22", 114.0)],
    )
    for oczekiwane in ("waga_docelowa_kg", "114.0 kg", "do zrzucenia: 35.0 kg",
                       "Najwyższa waga: 114.0 kg", "najniższa: 92.8 kg", "body_battery", "45"):
        assert oczekiwane in p, f"brak w promptcie: {oczekiwane}"
    assert set(PlanDnia.model_fields) >= {"kalorie", "bialko_g", "trening_szczegoly"}
    print(p)
    print("\nclaude_agent.py: OK (prompt zbudowany, API nie bylo wolane)")
