"""Trener AI - lokalny asystent treningowy i dietetyczny (Garmin + Claude).

Uruchomienie:  streamlit run app.py
"""

import hmac
import os
from datetime import date, timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import claude_agent
import database
import garmin_sync
import prognoza
import raport

st.set_page_config(page_title="Trener AI", page_icon="🏃", layout="wide")


def _sekret(nazwa):
    """Wartość ze zmiennych środowiskowych albo z panelu sekretów Streamlit Cloud."""
    wartosc = os.getenv(nazwa)
    if wartosc:
        return wartosc
    try:
        return st.secrets.get(nazwa)
    except Exception:
        return None


def brama():
    """Ekran logowania. W chmurze OBOWIĄZKOWY - aplikacja stoi pod publicznym
    adresem, a trzyma wagę, dane zdrowotne i klucz API, za który płacisz."""
    haslo = _sekret("HASLO_APLIKACJI")
    w_chmurze = Path("/mount/src").exists()          # tak wygląda Streamlit Cloud

    if not haslo:
        if w_chmurze:
            # Celowo nie wpuszczamy nikogo zamiast po cichu wystawić dane publicznie.
            st.error("Brak hasła w konfiguracji (HASLO_APLIKACJI). "
                     "Ustaw je w panelu sekretów, zanim aplikacja zacznie działać.")
            st.stop()
        return                                        # lokalnie hasło zbędne

    if st.session_state.get("zalogowany"):
        return

    st.title("🏃 Trener AI")
    podane = st.text_input("Hasło", type="password")
    if podane:
        if hmac.compare_digest(podane, haslo):        # porównanie odporne na pomiar czasu
            st.session_state["zalogowany"] = True
            st.rerun()
        else:
            st.error("Nieprawidłowe hasło.")
    st.stop()


brama()


def adres_lan():
    """Adres tego komputera w sieci domowej. Gniazdo nic nie wysyła - służy tylko
    do tego, żeby system wskazał interfejs używany do wyjścia na zewnątrz."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except OSError:
            return "localhost"


DZIS = date.today().isoformat()
PLCIE = ["mężczyzna", "kobieta"]
profil = database.wczytaj_profil()

# Streamlit nie ma parametru na szerokość panelu bocznego, a domyślne ~340 px jest
# za ciasne na akapity w polach profilu.
st.markdown(
    "<style>section[data-testid='stSidebar'] { width: 420px !important; }</style>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- panel boczny
with st.sidebar:
    st.header("⚖️ Waga")
    with st.form("waga"):
        d = st.date_input("Data pomiaru", value=date.today())
        kg = st.number_input(
            "Waga (kg)", 30.0, 300.0, float(database.ostatnia_waga() or 100.0), 0.1
        )
        if st.form_submit_button("Zapisz wagę", use_container_width=True):
            database.zapisz_wage(d.isoformat(), kg)
            st.success("Zapisano")

    if st.button("⬇️ Pobierz ważenia z wagi Garmin", use_container_width=True):
        try:
            with st.spinner("Pobieram historię ważeń..."):
                wagi = garmin_sync.pobierz_wagi(date.today() - timedelta(days=3 * 365))
            for data_w, kg_w in wagi:
                database.zapisz_wage(data_w, kg_w)
            st.success(f"Zaimportowano pomiarów: {len(wagi)}")
            st.rerun()
        except Exception as e:
            st.error(f"Garmin: {e}")

    st.header("👤 Profil")
    with st.form("profil"):
        nowy = {
            "wiek": st.number_input("Wiek", 14, 100, profil.get("wiek", 40)),
            "plec": st.selectbox(
                "Płeć", PLCIE,
                index=PLCIE.index(profil.get("plec")) if profil.get("plec") in PLCIE else 0,
            ),
            "wzrost_cm": st.number_input("Wzrost (cm)", 120, 230, profil.get("wzrost_cm", 178)),
            "waga_docelowa_kg": st.number_input(
                "Waga docelowa (kg)", 40.0, 250.0, float(profil.get("waga_docelowa_kg", 95.0)), 0.5
            ),
            "dni_treningowe": st.slider("Dni treningowe w tygodniu", 1, 7, profil.get("dni_treningowe", 4)),
            "praca": st.text_input("Charakter pracy", profil.get("praca", "siedząca")),
            # Wysokość wpisana na sztywno: te pola zawierają całe akapity (ograniczenia
            # sprzętowe z datami, wykluczenia żywieniowe), a domyślne 68 px pokazuje
            # dwie linijki i resztę trzeba przewijać.
            "sprzet": st.text_area("Dostępny sprzęt / siłownia", profil.get("sprzet", ""),
                                   height=170),
            "dieta": st.text_area("Preferencje i wykluczenia żywieniowe", profil.get("dieta", ""),
                                  height=200),
            "ograniczenia": st.text_area("Kontuzje, choroby, leki", profil.get("ograniczenia", ""),
                                         height=120),
            "priorytet": st.text_area("Priorytet i podejście do treningu", profil.get("priorytet", ""),
                                      height=170),
        }
        if st.form_submit_button("Zapisz profil", use_container_width=True):
            database.zapisz_profil(nowy)
            st.success("Zapisano")
            st.rerun()

    with st.expander("📱 Otwórz na telefonie"):
        st.caption("Ten sam program w przeglądarce telefonu, gdy komputer jest włączony "
                   "i podłączony do domowego Wi-Fi.")
        adres = f"http://{adres_lan()}:8501"
        st.code(adres, language=None)
        try:
            import io
            import qrcode
            bufor = io.BytesIO()
            qrcode.make(adres).save(bufor, format="PNG")
            st.image(bufor.getvalue(), width=200, caption="Zeskanuj aparatem telefonu")
        except Exception:
            st.caption("Wpisz adres ręcznie w przeglądarce telefonu.")
        st.caption("Jeśli telefon nie może się połączyć, brakuje reguły w zaporze — "
                   "instrukcja w README, rozdział „Dostęp z telefonu”.")


# ------------------------------------------------------------------- naglowek
st.title("🏃 Trener AI")

waga = database.ostatnia_waga()
historia = database.historia_wagi()
cel = profil.get("waga_docelowa_kg")

# Postep liczymy od pierwszego wazenia z ostatnich 90 dni, nie od najstarszego w bazie.
# Po imporcie historii z wagi Garmin najstarszy pomiar moze byc sprzed lat i pokazywalby
# "postep" z zupelnie innego okresu zycia.
biezace = [(d, kg) for d, kg in historia if d >= (date.today() - timedelta(days=90)).isoformat()]
postep = round(waga - biezace[0][1], 1) if waga and len(biezace) > 1 else None

k1, k2, k3 = st.columns(3)
k1.metric("Aktualna waga", f"{waga} kg" if waga else "-",
          delta=f"{postep} kg (90 dni)" if postep is not None else None,
          delta_color="inverse")
k2.metric("Cel", f"{cel} kg" if cel else "-")
k3.metric("Do celu", f"{round(waga - cel, 1)} kg" if waga and cel else "-")

zakladka_dzis, zakladka_tydzien, zakladka_postepy = st.tabs(
    ["📅 Dzisiaj", "🛒 Tydzień i zakupy", "📉 Postępy i prognoza"]
)

# ============================================================ ZAKŁADKA: DZISIAJ
with zakladka_dzis:
  if st.button("🔄 Synchronizuj z Garminem i pobierz dzisiejszy plan od AI",
               type="primary", use_container_width=True):
      try:
          with st.spinner("Pobieram dane z Garmin Connect..."):
              dane = garmin_sync.pobierz()
      except Exception as e:
          st.error(f"Garmin: {e}")
          st.info("Jeśli to pierwsze uruchomienie albo token wygasł, wykonaj w konsoli: `python garmin_sync.py`")
          st.stop()

      # Garmin zwraca komplet pól nawet dla dnia bez pomiarów — same nulle.
      # Bez tego ostrzeżenia użytkownik dostałby plan "z powietrza", nie wiedząc o tym.
      if all(dane.get(k) in (None, 0) for k in
             ("sen_godziny", "body_battery", "tetno_spoczynkowe", "wczoraj_kalorie_aktywne")):
          st.warning(
              "Garmin nie ma pomiarów za ten dzień. Zsynchronizuj zegarek z aplikacją "
              "Garmin Connect w telefonie i sprawdź, czy jest sparowany z tym samym kontem. "
              "Plan powstanie, ale bez danych o regeneracji będzie ogólny."
          )

      # Formularz profilu pokazuje wartosci domyslne dla pol, ktorych nie ma w bazie.
      # Bez tej kontroli plan powstaje na zalozeniach (np. "ma silownie"), a uzytkownik
      # widzi wypelniony formularz i nie ma pojecia, ze te dane nigdy nie zostaly zapisane.
      braki = [n for n, k in (("sprzęt", "sprzet"), ("dieta", "dieta"),
                              ("kontuzje/choroby", "ograniczenia"), ("charakter pracy", "praca"))
               if not profil.get(k)]
      if braki:
          st.warning(
              "Profil nie ma zapisanych pól: " + ", ".join(braki) + ". "
              "Uzupełnij je w panelu bocznym i kliknij „Zapisz profil” — inaczej AI zgaduje "
              "(np. założy, że masz siłownię)."
          )
      try:
          with st.spinner("Claude układa plan na dzisiaj..."):
              plan = claude_agent.plan_dnia(profil, dane, waga, historia)
      except Exception as e:
          st.error(f"Claude: {e}")
          st.stop()

      database.zapisz_dzien(DZIS, dane, plan)
      st.rerun()

  # ------------------------------------------------------------- widok dnia
  dni = database.historia_dni(30)
  wybrany = st.selectbox("Dzień", dni, index=0) if dni else None
  zapis = database.wczytaj_dzien(wybrany) if wybrany else None

  if not zapis:
      st.info("Brak planu. Kliknij przycisk powyżej, żeby pobrać dane z zegarka i plan od AI.")
  else:
      g, plan = zapis["garmin"], zapis["plan"]

      st.subheader("📊 Dane z Garmina")
      c = st.columns(5)
      c[0].metric("Sen", f"{g.get('sen_godziny')} h" if g.get("sen_godziny") else "-",
                  f"ocena {g['sen_ocena']}" if g.get("sen_ocena") else None, delta_color="off")
      c[1].metric("Body Battery", g.get("body_battery") or "-")
      c[2].metric("Tętno spoczynkowe", f"{g['tetno_spoczynkowe']} bpm" if g.get("tetno_spoczynkowe") else "-")
      c[3].metric("Gotowość (Garmin)", g.get("gotowosc_score") or "-", g.get("gotowosc_opis"), delta_color="off")
      c[4].metric("Kalorie wczoraj", g.get("wczoraj_kalorie_razem") or "-",
                  f"aktywne {g['wczoraj_kalorie_aktywne']}" if g.get("wczoraj_kalorie_aktywne") else None,
                  delta_color="off")

      if g.get("wczoraj_aktywnosci"):
          st.caption("Wczorajsze aktywności")
          st.dataframe(pd.DataFrame(g["wczoraj_aktywnosci"]), hide_index=True, use_container_width=True)
      if g.get("status_treningowy") or g.get("obciazenie_ocena"):
          st.caption(f"Status treningowy: {g.get('status_treningowy') or '-'} | "
                     f"obciążenie: {g.get('obciazenie_ocena') or '-'}")

      st.divider()
      lewo, prawo = st.columns(2)

      with lewo:
          st.subheader("🔋 Regeneracja")
          st.progress(plan.get("gotowosc_do_wysilku", 0) / 100,
                      text=f"Gotowość do wysiłku: {plan.get('gotowosc_do_wysilku')}/100")
          st.write(plan.get("ocena_regeneracji", ""))

          st.subheader(f"🏋️ Trening: {plan.get('trening_typ', '')}")
          st.markdown(plan.get("trening_szczegoly", ""))

      with prawo:
          st.subheader("🍽️ Bilans na dziś")
          m = st.columns(4)
          m[0].metric("kcal", plan.get("kalorie", "-"))
          m[1].metric("Białko", f"{plan.get('bialko_g', '-')} g")
          m[2].metric("Tłuszcz", f"{plan.get('tluszcz_g', '-')} g")
          m[3].metric("Węgle", f"{plan.get('wegle_g', '-')} g")
          st.caption(plan.get("uzasadnienie_bilansu", ""))
          st.markdown(plan.get("propozycja_posilkow", ""))

      if plan.get("uwagi"):
          st.info(plan["uwagi"])
      st.caption(f"Plan wygenerowany: {zapis['utworzono']}")


# ============================================================ ZAKŁADKA: TYDZIEŃ
with zakladka_tydzien:
    # Plan zapisujemy pod data poniedzialku, zeby jeden tydzien mial jeden wpis
    # niezaleznie od tego, w ktorym dniu klikniesz przycisk.
    poniedzialek = (date.today() - timedelta(days=date.today().weekday())).isoformat()

    if st.button("🛒 Ułóż jadłospis na tydzień i listę zakupów",
                 type="primary", use_container_width=True):
        if not profil.get("dieta"):
            st.warning("Profil nie ma zapisanych preferencji żywieniowych — jadłospis będzie ogólny.")
        try:
            with st.spinner("Claude układa 7 dni i przelicza zakupy — to trwa około 3 minut."):
                tyg = claude_agent.plan_tygodniowy(profil, waga, historia)
        except Exception as e:
            st.error(f"Claude: {e}")
            st.stop()
        database.zapisz_tydzien(poniedzialek, tyg)
        st.rerun()

    tygodnie = database.historia_tygodni()
    wybrany_t = st.selectbox("Tydzień od", tygodnie) if tygodnie else None
    zapis_t = database.wczytaj_tydzien(wybrany_t) if wybrany_t else None

    if not zapis_t:
        st.info("Brak planu tygodniowego. Kliknij przycisk powyżej — dostaniesz jadłospis "
                "na 7 dni i jedną listę zakupów z ilościami policzonymi na cały tydzień.")
    else:
        tp = zapis_t["plan"]
        m = st.columns(3)
        m[0].metric("Kalorie dziennie", tp.get("kcal_dzienne", "-"))
        m[1].metric("Białko dziennie", f"{tp.get('bialko_dzienne_g', '-')} g")
        m[2].metric("Produktów do kupienia", len(tp.get("lista_zakupow", [])))

        kol_jadlospis, kol_zakupy = st.columns([3, 2])

        with kol_jadlospis:
            st.subheader("🍽️ Jadłospis na 7 dni")
            for d in tp.get("dni", []):
                naglowek = f"{d['dzien']} — {d['kcal_razem']} kcal, {d['bialko_razem_g']} g białka"
                with st.expander(naglowek):
                    for pos in d.get("posilki", []):
                        st.markdown(
                            f"**{pos['nazwa']}** · {pos['kcal']} kcal · {pos['bialko_g']} g białka  \n"
                            f"{pos['opis']}"
                        )

        with kol_zakupy:
            st.subheader("🛒 Zakupy na cały tydzień")
            zak = tp.get("lista_zakupow", [])
            for kat in dict.fromkeys(z["kategoria"] for z in zak):
                st.markdown(f"**{kat}**")
                for z in (x for x in zak if x["kategoria"] == kat):
                    ile = int(z["ilosc"]) if float(z["ilosc"]).is_integer() else z["ilosc"]
                    wiersz = f"- {z['produkt']} — **{ile} {z['jednostka']}**"
                    if z.get("uwaga"):
                        wiersz += f"  \n&nbsp;&nbsp;&nbsp;<small>{z['uwaga']}</small>"
                    st.markdown(wiersz, unsafe_allow_html=True)
            if st.button("📄 Zapisz listę zakupów w PDF", use_container_width=True,
                         type="secondary"):
                try:
                    sciezka = raport.zapisz_pdf(tp, wybrany_t)
                except Exception as e:
                    st.error(f"Nie udało się zapisać PDF: {e}")
                else:
                    st.success(f"Zapisano: {sciezka}")
                    # Okno natywne nie obsługuje pobierania plików przez przeglądarkę,
                    # więc otwieramy PDF domyślnym czytnikiem systemu.
                    try:
                        os.startfile(sciezka)
                    except Exception:
                        st.info("Otwórz plik ręcznie ze wskazanej ścieżki.")

        if tp.get("uwagi"):
            st.info(tp["uwagi"])
        st.caption(f"Plan wygenerowany: {zapis_t['utworzono']}")


# =================================================== ZAKŁADKA: POSTĘPY I PROGNOZA
with zakladka_postepy:
    st.subheader("📉 Historia wagi")
    if len(historia) > 1:
        df = pd.DataFrame(historia, columns=["data", "kg"])
        df["data"] = pd.to_datetime(df["data"])
        # zero=False: przy spadku 114 -> 111 kg oś od zera spłaszczyłaby cały postęp
        wykres = (
            alt.Chart(df)
            .mark_line(point=True)
            .encode(
                x=alt.X("data:T", title="Data"),
                y=alt.Y("kg:Q", title="Waga (kg)", scale=alt.Scale(zero=False)),
                tooltip=["data:T", "kg:Q"],
            )
        )
        if cel:
            wykres += alt.Chart(pd.DataFrame({"cel": [cel]})).mark_rule(
                color="green", strokeDash=[6, 4]
            ).encode(y="cel:Q")
        st.altair_chart(wykres, use_container_width=True)
    else:
        st.caption("Dodaj co najmniej dwa pomiary wagi, żeby zobaczyć wykres.")

    st.divider()
    st.subheader("🔮 Prognoza na rok")

    if not (waga and profil.get("wzrost_cm") and profil.get("wiek")):
        st.info("Uzupełnij wagę i profil (wiek, wzrost), żeby policzyć prognozę.")
    else:
        ost_tydzien = database.wczytaj_tydzien(database.historia_tygodni(1)[0]) \
            if database.historia_tygodni(1) else None
        domyslne_kcal = (ost_tydzien or {}).get("plan", {}).get("kcal_dzienne") or 2250

        u1, u2 = st.columns(2)
        with u1:
            aktywnosc_opis = st.selectbox("Poziom aktywności", list(prognoza.AKTYWNOSC),
                                          index=2)
        with u2:
            tryb = st.radio(
                "Sposób prowadzenia diety",
                ["Plan przeliczany co tydzień (deficyt 20%)",
                 f"Stała podaż {domyslne_kcal} kcal, bez korekt"],
                help="Aplikacja przelicza plan przy każdym generowaniu, więc pierwszy "
                     "wariant jest bliższy temu, co faktycznie robisz.",
            )

        korygowany = tryb.startswith("Plan przeliczany")
        p = prognoza.prognoza(
            waga, profil["wzrost_cm"], profil["wiek"], profil.get("plec", "mężczyzna"),
            kalorie_dziennie=None if korygowany else domyslne_kcal,
            wspolczynnik=prognoza.AKTYWNOSC[aktywnosc_opis],
            tygodni=52,
            deficyt_procent=0.20 if korygowany else None,
        )

        po_roku = p[-1][1]
        m = st.columns(3)
        m[0].metric("Za rok", f"{po_roku} kg", f"{round(po_roku - waga, 1)} kg",
                    delta_color="inverse")
        m[1].metric("Tempo na starcie", f"{p[0][4]} kg/tydz.")
        m[2].metric("Tempo po roku", f"{p[-1][4]} kg/tydz.")

        if cel:
            trafienie = prognoza.kiedy_cel(p, cel)
            if trafienie:
                nr, kiedy = trafienie
                st.success(f"Cel **{cel} kg** osiągniesz w okolicach **{kiedy.strftime('%d.%m.%Y')}** "
                           f"(za {nr} tygodni).")
            else:
                dluga = prognoza.prognoza(
                    waga, profil["wzrost_cm"], profil["wiek"], profil.get("plec", "mężczyzna"),
                    kalorie_dziennie=None if korygowany else domyslne_kcal,
                    wspolczynnik=prognoza.AKTYWNOSC[aktywnosc_opis],
                    tygodni=260,
                    deficyt_procent=0.20 if korygowany else None,
                )
                dalej = prognoza.kiedy_cel(dluga, cel)
                if dalej:
                    st.info(f"Cel **{cel} kg** wypada poza rokiem: około "
                            f"**{dalej[1].strftime('%m.%Y')}**, czyli za {dalej[0]} tygodni "
                            f"(~{round(dalej[0] / 4.33)} miesięcy).")
                else:
                    st.warning("Przy tych założeniach cel nie zostanie osiągnięty — "
                               "deficyt jest za mały albo dieta schodzi do progu minimum.")

        df_p = pd.DataFrame([(d, w) for d, w, *_ in p], columns=["data", "kg"])
        df_p["data"] = pd.to_datetime(df_p["data"])
        df_p["seria"] = "prognoza"
        df_h = pd.DataFrame(historia, columns=["data", "kg"])
        df_h["data"] = pd.to_datetime(df_h["data"])
        df_h["seria"] = "pomiary"
        razem = pd.concat([df_h[df_h["data"] >= pd.Timestamp(date.today() - timedelta(days=120))], df_p])

        w = (
            alt.Chart(razem)
            .mark_line()
            .encode(
                x=alt.X("data:T", title="Data"),
                y=alt.Y("kg:Q", title="Waga (kg)", scale=alt.Scale(zero=False)),
                color=alt.Color("seria:N", title=""),
                strokeDash=alt.StrokeDash("seria:N", title=""),
                tooltip=["data:T", "kg:Q", "seria:N"],
            )
        )
        if cel:
            w += alt.Chart(pd.DataFrame({"cel": [cel]})).mark_rule(
                color="green", strokeDash=[6, 4]).encode(y="cel:Q")
        st.altair_chart(w, use_container_width=True)

        with st.expander("Tabela tydzień po tygodniu"):
            tab = pd.DataFrame(p, columns=["data", "waga_kg", "zapotrzebowanie_kcal",
                                           "deficyt_kcal", "ubytek_kg"])
            tab.insert(0, "tydzień", range(1, len(tab) + 1))
            st.dataframe(tab, hide_index=True, use_container_width=True)

        st.caption(
            "Jak to policzone: zapotrzebowanie wg wzoru Mifflin-St Jeor przeliczane "
            "co tydzień pod aktualną wagę, 1 kg tkanki tłuszczowej = 7700 kcal. "
            "Dlatego tempo zwalnia — im mniej ważysz, tym mniej spalasz. "
            "To arytmetyka, nie obietnica: w rzeczywistości dochodzą wahania wody, "
            "adaptacja metabolizmu i tygodnie, w których waga stoi mimo trzymania diety. "
            "Traktuj to jako kierunek, a nie rozkład jazdy."
        )
