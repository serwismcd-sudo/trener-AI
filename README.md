# 🏃 Trener AI — asystent redukcji masy ciała (Garmin + Claude)

Lokalna aplikacja na Twój komputer. Rano pobiera dane z zegarka Garmin
(Forerunner 965), wysyła je do Claude'a razem z Twoim profilem i dostaje
gotowy plan na dziś: ocenę regeneracji, trening dopasowany do zmęczenia
oraz bilans kaloryczny z makroskładnikami. Wszystko zapisuje w lokalnej
bazie SQLite, żeby widzieć postępy w czasie.

Nic nie wychodzi poza Twój komputer poza dwoma połączeniami: do Garmin
Connect (po Twoje dane) i do API Anthropic (po plan).

---

## 1. Czego potrzebujesz

| Co | Skąd |
|---|---|
| Python 3.10 lub nowszy | https://python.org — przy instalacji zaznacz **Add Python to PATH** |
| Konto Garmin Connect | to, z którym sparowany jest Forerunner 965 |
| Klucz API Anthropic | https://console.anthropic.com → **Settings → API Keys → Create Key** |

> **Uwaga o kluczu API:** to osobna, płatna usługa — subskrypcja Claude.ai (Pro/Max)
> **nie** obejmuje API. Trzeba doładować konto w konsoli (minimum to zwykle 5 USD).
> Realny koszt tej aplikacji to jeden zapytanie dziennie, czyli **ok. 0,05–0,15 USD
> za dzień** (~2–5 USD miesięcznie) na modelu `claude-opus-5`. Taniej wyjdzie
> `claude-sonnet-5` — patrz krok 3.

---

## 2. Instalacja

Otwórz PowerShell i przejdź do katalogu aplikacji. Ścieżka zawiera spacje,
więc **musi być w cudzysłowie**:

```bash
cd "D:\programy AI\APLIKACJA TRENINGOWA AI\TrenerAI"
```

Następnie:

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

Środowisko `.venv` trzeba aktywować (`.venv\Scripts\activate`) za każdym razem,
gdy otwierasz nowe okno konsoli.

---

## 3. Klucze i hasła

Skopiuj plik `.env.example` na `.env`:

```bash
copy .env.example .env
```

Otwórz `.env` w notatniku i uzupełnij:

```
ANTHROPIC_API_KEY=sk-ant-...        # klucz z console.anthropic.com
GARMIN_EMAIL=twoj@email.pl          # login do Garmin Connect
GARMIN_PASSWORD=twoje-haslo         # hasło do Garmin Connect
```

Opcjonalnie, jeśli chcesz tańszy model, dopisz:

```
ANTHROPIC_MODEL=claude-sonnet-5
```

Plik `.env` zostaje tylko na Twoim dysku — `.gitignore` pilnuje, żeby nigdy
nie trafił do repozytorium.

---

## Najprostsza droga: dwa pliki do kliknięcia

W katalogu aplikacji są dwa pliki `.bat` — wystarczy je **kliknąć dwa razy**,
nie trzeba otwierać konsoli ani nic wpisywać:

| Plik | Kiedy |
|---|---|
| `1-LOGOWANIE-GARMIN.bat` | **raz na początku** (i ponownie, gdy token wygaśnie po ~roku) |
| `2-URUCHOM-TRENERA.bat` | **codziennie**, żeby uruchomić aplikację |

Na pulpicie i w menu Start jest też skrót **Trener AI** z własną ikoną. Otwiera aplikację
w **prawdziwym oknie systemowym** (`uruchom.py` + pywebview/WebView2) — bez przeglądarki,
paska adresu i okna konsoli. Okno należy do procesu aplikacji, nie do Edge.

Gdyby okno natywne nie było dostępne, program cofa się do okna Edge w trybie aplikacji.
Wtedy powstaje folder `dane\okno` z osobnym profilem przeglądarki — można go skasować,
odtworzy się sam.

**Żeby zamknąć aplikację, zamknij jej okno** — serwer w tle zatrzyma się sam po kilku
sekundach. Plik `2-URUCHOM-TRENERA.bat` robi to samo, ale z widoczną konsolą: użyj go,
gdy coś nie działa i chcesz zobaczyć komunikaty błędów. Gdyby aplikacja nie wystartowała,
pokaże się okienko z błędem, a szczegóły wylądują w `danelad.log`. Możesz go przypiąć do paska
zadań (prawy przycisk → *Przypnij do paska zadań*). Aplikację zamykasz, zamykając
okno konsoli na pasku.

Skrót wskazuje na konkretną ścieżkę — po przeniesieniu folderu trzeba go utworzyć na nowo.
Ikonę generuje `zrob_ikone.py` (`python zrob_ikone.py`), jeśli plik `trener.ico` zaginie.

Reszta tego rozdziału opisuje to samo z poziomu konsoli — dla tych, którzy wolą.

---

## 4. Pierwsze logowanie do Garmina (jednorazowo)

Garmin często prosi o kod MFA (dwuskładnikowe logowanie), a okno przeglądarki
Streamlita nie ma jak o niego zapytać. Dlatego pierwsze logowanie robisz
raz, w konsoli:

```bash
python garmin_sync.py
```

Skrypt zaloguje się danymi z `.env`, w razie potrzeby poprosi o **kod MFA**
(przyjdzie mailem lub w aplikacji Garmin), a potem zapisze token sesji
w `C:\Users\<Ty>\.garminconnect`. Na koniec wypisze świeżo pobrane dane —
to potwierdzenie, że wszystko działa.

Token jest ważny około roku. Jeśli kiedyś wygaśnie, aplikacja wyświetli
komunikat i wystarczy powtórzyć tę jedną komendę.

---

## 5. Uruchomienie aplikacji

```bash
streamlit run app.py
```

Przeglądarka otworzy `http://localhost:8501`.

**Zanim klikniesz cokolwiek innego — uzupełnij panel boczny:**

1. **⚖️ Waga** — wpisz dzisiejszą wagę i zapisz. Bez tego AI nie wie, od czego zaczynamy.
2. **👤 Profil** — wiek, płeć, wzrost, **waga docelowa** (np. aktualna minus 35 kg),
   dostępny sprzęt, preferencje żywieniowe, kontuzje i choroby. Im konkretniej,
   tym lepszy plan.

Potem kliknij **🔄 Synchronizuj z Garminem i pobierz dzisiejszy plan od AI**.
Po kilkunastu sekundach zobaczysz plan na dziś.

---

## 6. Codzienne użycie

Rano, po przebudzeniu i zsynchronizowaniu zegarka z aplikacją Garmin Connect
w telefonie:

1. `streamlit run app.py`
2. Wpisz wagę w panelu bocznym (najlepiej mierzoną na czczo, codziennie o tej samej porze).
3. Kliknij duży przycisk synchronizacji.

### Zakładka „Tydzień i zakupy"

Przycisk **🛒 Ułóż jadłospis na tydzień i listę zakupów** generuje jadłospis na 7 dni
oraz **jedną zbiorczą listę zakupów** — każdy produkt raz, z ilością zsumowaną ze
wszystkich dni i podpowiedzią, w jakich opakowaniach go kupić. Listę można pobrać jako
**PDF z polami do odhaczania** — przycisk *Zapisz listę zakupów w PDF* tworzy plik
w folderze `dane` i od razu go otwiera. Nie używamy pobierania przez przeglądarkę,
bo okno natywne aplikacji go nie obsługuje.

To dłuższe zapytanie niż plan dzienny: trwa **około 3 minut** i kosztuje więcej
(rząd 0,50 USD). Wystarczy raz w tygodniu — plan zapisuje się pod datą poniedziałku.

### Zakładka „Postępy i prognoza"

Wykres historii wagi oraz **prognoza na 52 tygodnie do przodu**. Liczona lokalnie,
bez udziału AI: zapotrzebowanie wg wzoru Mifflin-St Jeor przeliczane co tydzień pod
aktualną wagę, 1 kg tłuszczu = 7700 kcal. Dzięki temu tempo w prognozie zwalnia —
im mniej ważysz, tym mniej spalasz i tym mniejszy jest deficyt przy tej samej diecie.

Dwa warianty do porównania: dieta korygowana co tydzień (tak działa ta aplikacja)
oraz stała podaż kalorii bez korekt. Różnica po roku to kilka kilogramów.

### Zakładka „Dzisiaj"

Rozwijana lista **Dzień** pozwala wrócić do planów z poprzednich dni —
wszystko zostaje w bazie. Wykres **📉 Postępy** pokazuje trend wagi
i zieloną linię celu.

---

## Dostęp z telefonu

Aplikacja działa na komputerze, ale możesz ją otworzyć **w przeglądarce telefonu**,
gdy oba urządzenia są w tej samej sieci domowej. W panelu bocznym jest sekcja
**📱 Otwórz na telefonie** z adresem i kodem QR do zeskanowania.

Warunek: zapora Windows musi przepuszczać port 8501. Kliknij plik
**`ZAPORA-TELEFON.bat`** *prawym* przyciskiem i wybierz **„Uruchom jako administrator"**.
Bez tego Windows odmawia dostępu (błąd 5) — regułę w zaporze może dodać tylko administrator.

Skrypt sam wykrywa Twój adres w sieci i dopuszcza wyłącznie urządzenia z tej samej
podsieci, na tym jednym porcie.

Potem na telefonie otwórz adres z kodu QR i dodaj go do ekranu głównego — będzie
wyglądał jak zwykła aplikacja.

**Ograniczenia:** komputer musi być włączony z uruchomioną aplikacją, działa to tylko
w domowej sieci, i **nie ma hasła** — każdy, kto jest w Twoim Wi-Fi, zobaczy te dane
i może wygenerować plan (czyli wydać Twoje środki na API). W domu zwykle bez znaczenia,
ale warto o tym wiedzieć.

## 7. Co gdzie leży

| Plik | Rola |
|---|---|
| `app.py` | interfejs Streamlit: przyciski, widok dnia, wykresy |
| `garmin_sync.py` | logowanie do Garmin Connect i pobieranie danych; uruchamiany też ręcznie do pierwszego logowania |
| `claude_agent.py` | prompt systemowy i wywołanie API Claude, walidacja odpowiedzi |
| `database.py` | baza SQLite: dni, waga, profil |
| `trener.db` | Twoja baza danych — **to jest cała historia, zrób sobie kopię** |
| `.env` | klucze i hasła (nie commituj) |
| `.streamlit/config.toml` | wyłącza pytanie o e-mail i telemetrię Streamlita |
| `*.bat` | skróty do klikania zamiast konsoli |
| `trener.ico`, `zrob_ikone.py` | ikona aplikacji i skrypt, który ją generuje |
| `uruchom.py` | start we własnym oknie (bez paska adresu) — na to wskazuje skrót |

Każdy moduł da się uruchomić osobno, żeby sprawdzić czy działa:

```bash
python database.py
```

```bash
python claude_agent.py
```

(`claude_agent.py` uruchomiony samodzielnie tylko buduje i wypisuje prompt —
nie wywołuje API, więc nic nie kosztuje.)

---

## 8. Jakie dane trafiają do Claude'a

Tylko to, co potrzebne do ułożenia planu:

- **regeneracja z dzisiaj:** długość i ocena snu, sen głęboki i REM, Body Battery,
  tętno spoczynkowe, poziom stresu, Training Readiness,
- **wczoraj:** kalorie całkowite i aktywne, kroki, lista aktywności (typ, czas, kcal, tętno),
- **obciążenie treningowe:** status treningowy, obciążenie ostre i przewlekłe,
- **Twój profil i historia wagi** z panelu bocznego.

Bez imienia, nazwiska, e-maila i bez danych GPS.

---

## 9. Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| `Garmin: ...` przy synchronizacji | Token wygasł lub go nie ma — w konsoli: `python garmin_sync.py` |
| Prośba o kod MFA w aplikacji | To samo — kod da się podać tylko w konsoli |
| `Claude: authentication_error` | Zły lub pusty `ANTHROPIC_API_KEY` w `.env` |
| `Claude: credit balance is too low` | Doładuj konto w console.anthropic.com |
| Puste pola w danych z Garmina (`-`) | Zegarek nie zsynchronizował się z telefonem albo nie miał danego pomiaru tej nocy. AI dostaje wtedy informację o braku i planuje zachowawczo |
| `streamlit: nie znaleziono polecenia` | Nie aktywowałeś środowiska: `.venv\Scripts\activate` |

---

## 10. Zastrzeżenie

Aplikacja jest narzędziem wspierającym, **nie zastępuje lekarza ani dietetyka**.
Przy redukcji o 35 kg — zwłaszcza z chorobami towarzyszącymi, lekami lub
problemami z sercem i stawami — skonsultuj plan z lekarzem, zanim zaczniesz.
Prompt systemowy pilnuje bezpiecznych granic (tempo 0,5–1% masy ciała na tydzień,
minimum kaloryczne, odpoczynek przy słabej regeneracji), ale model AI może się mylić.
Jeśli coś w planie wygląda niepokojąco — nie wykonuj tego.
