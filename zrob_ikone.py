# -*- coding: utf-8 -*-
"""Generuje ikonę aplikacji (trener.ico). Uruchom raz: python zrob_ikone.py"""

from pathlib import Path

from PIL import Image, ImageDraw

S = 1024          # rysujemy w duzej skali i zmniejszamy - daje gladkie krawedzie
PLIK = Path(__file__).parent / "trener.ico"

OD, DO = (34, 197, 94), (13, 148, 136)   # zielen -> morski, gradient po przekatnej
BIALY = (255, 255, 255, 255)


def gradient(rozmiar, od, do):
    """Gradient po przekatnej - piksel po pikselu byłby wolny, więc robimy go
    z pionowego przejscia obroconego o 45 stopni."""
    g = Image.new("RGB", (rozmiar, rozmiar))
    rys = ImageDraw.Draw(g)
    for i in range(rozmiar * 2):
        t = i / (rozmiar * 2 - 1)
        kolor = tuple(round(a + (b - a) * t) for a, b in zip(od, do))
        rys.line([(i, 0), (0, i)], fill=kolor, width=2)
    return g


def zrob():
    tlo = gradient(S, OD, DO).convert("RGBA")

    # zaokraglone rogi w stylu ikon Windows 11
    maska = Image.new("L", (S, S), 0)
    ImageDraw.Draw(maska).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=255)
    ikona = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ikona.paste(tlo, (0, 0), maska)

    rys = ImageDraw.Draw(ikona)

    # opadajaca linia wagi - czytelna nawet w 16 px, bo gruba i o duzym spadku
    punkty = [(0.18, 0.34), (0.38, 0.48), (0.58, 0.42), (0.82, 0.72)]
    xy = [(x * S, y * S) for x, y in punkty]
    rys.line(xy, fill=BIALY, width=int(S * 0.075), joint="curve")
    for p in xy:                                   # zaokraglenie zalaman i koncow
        r = S * 0.037
        rys.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=BIALY)

    # kropka "tu jesteś" na koncu linii, z zielona obwodka dla kontrastu
    kon = xy[-1]
    r = S * 0.085
    rys.ellipse([kon[0] - r, kon[1] - r, kon[0] + r, kon[1] + r], fill=BIALY)
    r2 = S * 0.042
    rys.ellipse([kon[0] - r2, kon[1] - r2, kon[0] + r2, kon[1] + r2], fill=(13, 148, 136, 255))

    # podkreslenie u dolu - "poziom docelowy"
    y = S * 0.85
    rys.line([(S * 0.18, y), (S * 0.82, y)], fill=(255, 255, 255, 110), width=int(S * 0.028))

    rozmiary = [(r, r) for r in (256, 128, 64, 48, 32, 16)]
    ikona.resize((256, 256), Image.LANCZOS).save(PLIK, sizes=rozmiary)
    return PLIK


if __name__ == "__main__":
    p = zrob()
    print(f"zapisano: {p} ({p.stat().st_size} bajtow)")
    with Image.open(p) as im:
        print("rozmiary w pliku:", sorted(im.info.get("sizes", [])))
