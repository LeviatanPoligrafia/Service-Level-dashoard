import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
import pandas as pd

# Konfiguracja strony
st.set_page_config(page_title="Kalkulator Service Level (SL*)", layout="wide")

st.title("📊 Kalkulator Optymalnego Service Level (SL*)")
st.markdown("""
To narzędzie pomaga wyznaczyć **ekonomicznie uzasadniony** poziom dostępności towaru.
Balansuje koszt utraconej marży (X) z kosztem magazynowania (Y).
""")

# --- SIDEBAR: DANE WEJŚCIOWE ---
st.sidebar.header("1. Parametry Produktu")
nazwa_sku = st.sidebar.text_input("Nazwa SKU", value="Przykładowy Produkt (Standard)")
cena_zakupu = st.sidebar.number_input("Cena Zakupu (PLN)", value=10.0, step=1.0)
cena_sprzedazy = st.sidebar.number_input("Cena Sprzedaży (PLN)", value=30.0, step=1.0)

st.sidebar.header("2. Parametry Strategiczne (X)")
mnoznik_braku = st.sidebar.slider(
    "Mnożnik Kosztu Braku", 
    min_value=1.0, 
    max_value=5.0, 
    value=1.5, 
    step=0.1,
    help="1.0 = Tracimy tylko marżę. 1.5 = Klient może odejść. 2.0+ = Poważne straty wizerunkowe."
)

st.sidebar.header("3. Logistyka i Finanse (Y)")
sztuk_na_palecie = st.sidebar.number_input("Sztuk na palecie", value=100, step=10)
koszt_palety_dzien = st.sidebar.number_input("Koszt palety / dzień (PLN)", value=1.0, step=0.1)
koszt_kapitalu = st.sidebar.number_input("Koszt Kapitału (WACC % rocznie)", value=15.0, step=1.0) / 100
cykl_zapasu = st.sidebar.number_input("Długość cyklu zapasu (dni)", value=30, step=5, help="Średni czas rotacji zapasu bezpieczeństwa")

# --- OBLICZENIA ---

# 1. Koszt Braku (X)
marza_jednostkowa = cena_sprzedazy - cena_zakupu
koszt_braku_X = marza_jednostkowa * mnoznik_braku

# 2. Koszt Magazynowania (Y)
# Koszt miejsca (dzienny na sztukę)
koszt_miejsca_dzien = koszt_palety_dzien / sztuk_na_palecie if sztuk_na_palecie > 0 else 0
# Koszt kapitału (dzienny na sztukę)
koszt_finansowy_dzien = (cena_zakupu * koszt_kapitalu) / 365
# Suma dziennie
koszt_Y_dzienny = koszt_miejsca_dzien + koszt_finansowy_dzien
# Koszt w cyklu (np. 30 dni)
koszt_Y_cykl = koszt_Y_dzienny * cykl_zapasu

# 3. Service Level (SL*)
try:
    service_level = koszt_braku_X / (koszt_braku_X + koszt_Y_cykl)
except ZeroDivisionError:
    service_level = 0

# 4. Z-score (Norm.S.Inv)
if 0 < service_level < 1:
    z_score = norm.ppf(service_level)
else:
    z_score = 0

# --- PREZENTACJA WYNIKÓW ---

col1, col2, col3 = st.columns(3)

with col1:
    st.info("💰 Parametr X (Koszt Braku)")
    st.metric(label="Kara za brak towaru (1 szt.)", value=f"{koszt_braku_X:.2f} PLN")
    st.caption(f"Marża {marza_jednostkowa:.2f} PLN × Mnożnik {mnoznik_braku}")

with col2:
    st.warning("📦 Parametr Y (Koszt Utrzymania)")
    st.metric(label=f"Koszt trzymania (przez {cykl_zapasu} dni)", value=f"{koszt_Y_cykl:.2f} PLN")
    st.caption(f"Magazyn: {koszt_miejsca_dzien*cykl_zapasu:.2f} + Kapitał: {koszt_finansowy_dzien*cykl_zapasu:.2f}")

with col3:
    st.success("🎯 WYNIK: Service Level")
    st.metric(label="Optymalny Poziom", value=f"{service_level:.2%}", delta=f"Z-score: {z_score:.2f}")
    st.caption("Prawdopodobieństwo, że towar będzie dostępny")

st.divider()

# --- WIZUALIZACJA I SCENARIUSZE ---

c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Rozkład Popytu (Krzywa Gaussa)")
    
    # Generowanie wykresu
    x = np.linspace(-4, 4, 1000)
    y = norm.pdf(x, 0, 1)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x, y, label='Rozkład Popytu', color='gray')
    
    # Wypełnienie obszaru Service Level
    x_fill = np.linspace(-4, z_score, 1000)
    y_fill = norm.pdf(x_fill, 0, 1)
    ax.fill_between(x_fill, y_fill, color='#4CAF50', alpha=0.5, label=f'Pokrycie Popytu ({service_level:.1%})')
    
    # Linia odcięcia
    ax.axvline(z_score, color='red', linestyle='--', linewidth=2, label=f'Punkt Odcięcia (Z={z_score:.2f})')
    
    # Formatowanie
    ax.set_title(f"Gdzie stawiamy granicę dla {nazwa_sku}?", fontsize=14)
    ax.set_xlabel("Odchylenia standardowe od średniej")
    ax.set_yticks([])
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    st.pyplot(fig)

with c2:
    st.subheader("💡 Interpretacja")
    
    if service_level > 0.98:
        st.success("**STRATEGIA: AGRESYWNA**\n\nTowar jest tani w utrzymaniu, a brak bardzo kosztowny. \n\n👉 **Zalewamy magazyn.**")
    elif service_level > 0.90:
        st.info("**STRATEGIA: STANDARD**\n\nZbalansowany stosunek kosztów. \n\n👉 **Trzymamy bezpieczny zapas.**")
    else:
        st.error("**STRATEGIA: OSZCZĘDNA**\n\nMagazynowanie jest zbyt drogie w stosunku do marży. \n\n👉 **Akceptujemy braki towaru.**")

    st.markdown("---")
    st.write("**Symulacja Mnożnika (X):**")
    
    # Tabela symulacji
    scenariusze = [1.0, 1.5, 2.0, 3.0]
    wyniki = []
    for m in scenariusze:
        x_sim = marza_jednostkowa * m
        sl_sim = x_sim / (x_sim + koszt_Y_cykl)
        wyniki.append({"Mnożnik": f"{m}x", "Service Level": f"{sl_sim:.2%}"})
    
    df_sim = pd.DataFrame(wyniki)
    st.table(df_sim)