# -*- coding: utf-8 -*-
"""Lista zakupów i jadłospis jako PDF do wydruku.

Okno natywne aplikacji nie obsługuje pobierania plików przez przeglądarkę,
więc PDF zapisujemy wprost na dysk i otwieramy domyślnym czytnikiem.
"""

import os
from pathlib import Path

from fpdf import FPDF

KATALOG = Path(__file__).parent
CZCIONKI = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"


class _Pdf(FPDF):
    def header(self):
        self.set_font("PL", "B", 9)
        self.set_text_color(130)
        self.cell(0, 6, self.title, align="R")
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("PL", size=8)
        self.set_text_color(150)
        self.cell(0, 6, f"strona {self.page_no()}", align="C")


def _czcionki(pdf):
    """Polskie znaki wymagają czcionki TrueType - wbudowane w PDF jej nie mają."""
    zwykla = CZCIONKI / "arial.ttf"
    pogrubiona = CZCIONKI / "arialbd.ttf"
    if not zwykla.exists():                       # awaryjnie, gdyby Arial zniknął
        zwykla = pogrubiona = CZCIONKI / "segoeui.ttf"
    pdf.add_font("PL", "", str(zwykla))
    pdf.add_font("PL", "B", str(pogrubiona if pogrubiona.exists() else zwykla))


def zapisz_pdf(plan, od, katalog=None):
    """Zapisuje PDF z listą zakupów i jadłospisem. Zwraca ścieżkę do pliku."""
    pdf = _Pdf()
    pdf.set_title(f"Trener AI - tydzień od {od}")
    pdf.set_auto_page_break(True, margin=18)
    _czcionki(pdf)
    pdf.add_page()

    pdf.set_font("PL", "B", 18)
    pdf.set_text_color(20)
    pdf.cell(0, 10, "Lista zakupów na tydzień", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("PL", size=10)
    pdf.set_text_color(110)
    podsumowanie = f"Tydzień od {od}"
    if plan.get("kcal_dzienne"):
        podsumowanie += f"   ·   {plan['kcal_dzienne']} kcal i {plan.get('bialko_dzienne_g', '?')} g białka dziennie"
    pdf.cell(0, 6, podsumowanie, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    zakupy = plan.get("lista_zakupow", [])
    for kategoria in dict.fromkeys(z.get("kategoria", "Inne") for z in zakupy):
        pdf.set_font("PL", "B", 12)
        pdf.set_text_color(20)
        pdf.ln(2)
        pdf.cell(0, 7, kategoria, new_x="LMARGIN", new_y="NEXT")
        for z in (x for x in zakupy if x.get("kategoria", "Inne") == kategoria):
            ilosc = z.get("ilosc", 0)
            ilosc = int(ilosc) if float(ilosc).is_integer() else ilosc
            pdf.set_font("PL", size=11)
            pdf.set_text_color(20)
            pdf.cell(7, 6, "")                                  # miejsce na kratkę
            kratka_x, kratka_y = pdf.get_x() - 6, pdf.get_y() + 1
            pdf.rect(kratka_x, kratka_y, 3.5, 3.5)              # pole do odhaczenia
            pdf.cell(0, 6, f"{z.get('produkt', '')} - {ilosc} {z.get('jednostka', '')}",
                     new_x="LMARGIN", new_y="NEXT")
            if z.get("uwaga"):
                pdf.set_font("PL", size=9)
                pdf.set_text_color(120)
                pdf.cell(7, 5, "")
                pdf.multi_cell(0, 5, z["uwaga"], new_x="LMARGIN", new_y="NEXT")

    dni = plan.get("dni", [])
    if dni:
        pdf.add_page()
        pdf.set_font("PL", "B", 18)
        pdf.set_text_color(20)
        pdf.cell(0, 10, "Jadłospis na 7 dni", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        for d in dni:
            pdf.set_font("PL", "B", 12)
            pdf.set_text_color(20)
            pdf.ln(3)
            pdf.cell(0, 7, f"{d.get('dzien', '')} - {d.get('kcal_razem', '?')} kcal, "
                           f"{d.get('bialko_razem_g', '?')} g białka",
                     new_x="LMARGIN", new_y="NEXT")
            for pos in d.get("posilki", []):
                pdf.set_font("PL", "B", 10)
                pdf.set_text_color(60)
                pdf.multi_cell(0, 5, f"{pos.get('nazwa', '')} "
                                     f"({pos.get('kcal', '?')} kcal, {pos.get('bialko_g', '?')} g B)",
                               new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("PL", size=10)
                pdf.set_text_color(20)
                pdf.multi_cell(0, 5, pos.get("opis", ""), new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)

    if plan.get("uwagi"):
        pdf.add_page()
        pdf.set_font("PL", "B", 14)
        pdf.set_text_color(20)
        pdf.cell(0, 9, "Uwagi", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("PL", size=10)
        pdf.multi_cell(0, 5, plan["uwagi"], new_x="LMARGIN", new_y="NEXT")

    katalog = Path(katalog) if katalog else KATALOG / "dane"
    katalog.mkdir(parents=True, exist_ok=True)
    plik = katalog / f"zakupy-{od}.pdf"
    pdf.output(str(plik))
    return plik


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(KATALOG))
    import database
    from datetime import date, timedelta

    pon = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    zapis = database.wczytaj_tydzien(pon)
    assert zapis, "brak planu tygodniowego w bazie - najpierw wygeneruj go w aplikacji"
    p = zapisz_pdf(zapis["plan"], pon)
    assert p.exists() and p.stat().st_size > 5000, "PDF wyszedł podejrzanie mały"
    print(f"raport.py: OK -> {p} ({p.stat().st_size // 1024} KB)")
