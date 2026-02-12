import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
import pandas as pd

# Konfiguracja strony
st.set_page_config(page_title="Kalkulator Service Level & Safety Stock", layout="wide")

st.title("📊 Inventory Optimization Dashboard")
st.markdown("Narzędzie wspomagające decyzje o alokacji kapitału w zapasy.")

# ==============================================================================
# SEKCJA 1: EKONOMIA (Service Level)
# ==============================================================================

st.header("1. Ekonomiczny Poziom Dostępności (Service Level)")
st.caption("Decyzja biznesowa: Czy opłaca się mieć towar?")

col1_in, col2_in = st.columns(2)

with col1_in:
    st.subheader("Parametry Finansowe")
    nazwa_sku = st.text_input("Nazwa SKU", value="Przykładowy Produkt")
    cena_zakupu = st.number_input("Cena Zakupu (PLN)", value=10.0, step=1.0)
    cena_sprzedazy = st.number_input("Cena Sprzedaży (PLN)", value=30.0, step=1.0)
    marza_jednostkowa = cena_sprzedazy - cena_zakupu
    
    mnoznik_braku = st.slider(
        "Mnożnik Kosztu Braku (X)", 
        min_value=1.0, max_value=5.0, value=1.5, step=0.1,
        help="Ile razy bardziej boli brak towaru niż utrata samej marży?"
    )

with col2_in:
    st.subheader("Logistyka (Koszty)")
    sztuk_na_palecie = st.number_input("Sztuk na palecie", value=100, step=10)
    koszt_palety_dzien = st.number_input("Koszt palety / dzień (PLN)", value=1.0, step=0.1)
    koszt_kapitalu_proc = st.number_input("Koszt Kapitału (WACC %)", value=15.0, step=1.0) / 100
    cykl_zapasu = st.number_input("Długość cyklu rotacji (dni)", value=30, step=5, help="Ile dni średnio towar leży")

# --- OBLICZENIA FINANSOWE ---
koszt_braku_X = marza_jednostkowa * mnoznik_braku
koszt_miejsca_dzien = koszt_palety_dzien / sztuk_na_palecie if sztuk_na_palecie > 0 else 0
koszt_finansowy_dzien = (cena_zakupu * koszt_kapitalu_proc) / 365
koszt_Y_cykl = (koszt_miejsca_dzien + koszt_finansowy_dzien) * cykl_zapasu

try:
    opt_sl = koszt_braku_X / (koszt_braku_X + koszt_Y_cykl)
except:
    opt_sl = 0

# Wyliczamy Z-score dla sekcji ekonomicznej (do wykresu)
if 0 < opt_sl < 1:
    z_score_eco = norm.ppf(opt_sl)
else:
    z_score_eco = 0

st.metric(label="Rekomendowany Service Level (Ekonomiczny)", value=f"{opt_sl:.2%}", 
          delta=f"Z-score: {z_score_eco:.2f}")

st.caption(f"Koszt braku (X): {koszt_braku_X:.2f} zł vs Koszt trzymania (Y): {koszt_Y_cykl:.2f} zł")

# --- WIZUALIZACJA I SYMULACJA (DODANE) ---
st.markdown("### 🔍 Analiza Wizualna i Scenariusze")

c_chart, c_sim = st.columns([2, 1])

with c_chart:
    st.write("**Rozkład Popytu (Krzywa Gaussa)**")
    
    # Generowanie wykresu
    x = np.linspace(-4, 4, 1000)
    y = norm.pdf(x, 0, 1)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x, y, label='Rozkład Popytu', color='gray')
    
    # Wypełnienie obszaru Service Level
    x_fill = np.linspace(-4, z_score_eco, 1000)
    y_fill = norm.pdf(x_fill, 0, 1)
    ax.fill_between(x_fill, y_fill, color='#4CAF50', alpha=0.5, label=f'Pokrycie Popytu ({opt_sl:.1%})')
    
    # Linia odcięcia
    ax.axvline(z_score_eco, color='red', linestyle='--', linewidth=2, label=f'Punkt Odcięcia (Z={z_score_eco:.2f})')
    
    # Formatowanie
    ax.set_title(f"Gdzie stawiamy granicę dla {nazwa_sku}?", fontsize=12)
    ax.set_xlabel("Odchylenia standardowe od średniej")
    ax.set_yticks([])
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

with c_sim:
    st.write("**💡 Interpretacja**")
    if opt_sl > 0.98:
        st.success("STRATEGIA: **AGRESYWNA**\n\nZalewamy magazyn. Koszt braku jest zbyt duży.")
    elif opt_sl > 0.90:
        st.info("STRATEGIA: **STANDARD**\n\nBalansujemy koszty. Trzymamy bezpieczny zapas.")
    else:
        st.error("STRATEGIA: **OSZCZĘDNA**\n\nMagazynowanie jest za drogie. Akceptujemy braki.")

    st.write("---")
    st.write("**Symulacja Mnożnika (X):**")
    
    # Tabela symulacji
    scenariusze = [1.0, 1.5, 2.0, 3.0]
    wyniki = []
    for m in scenariusze:
        x_sim = marza_jednostkowa * m
        # Zabezpieczenie przed dzieleniem przez zero
        denom = (x_sim + koszt_Y_cykl)
        sl_sim = x_sim / denom if denom != 0 else 0
        wyniki.append({"Mnożnik": f"{m}x", "Service Level": f"{sl_sim:.2%}"})
    
    df_sim = pd.DataFrame(wyniki)
    st.table(df_sim)

# ==============================================================================
# SEPARATOR
# ==============================================================================
st.markdown("---")
# ==============================================================================
# SEKCJA 2: LOGISTYKA (Safety Stock)
# ==============================================================================

st.header("2. Kalkulator Zapasu Bezpieczeństwa (Safety Stock)")
st.caption("Decyzja operacyjna: Ile sztuk musimy kupić, żeby dowieźć powyższy wynik?")

# Layout kolumnowy dla inputów
c1, c2, c3, c4 = st.columns(4)

with c1:
    # Pobieramy domyślnie wartość z sekcji 1, ale pozwalamy zmienić
    default_sl = float(round(opt_sl*100, 2))
    if default_sl > 99.9: default_sl = 99.9
    if default_sl < 50.0: default_sl = 50.0
    
    target_sl_input = st.number_input("Cel Service Level (%)", 
                                      value=default_sl, 
                                      min_value=50.0, max_value=99.9, step=0.1) / 100

with c2:
    lead_time = st.number_input("Lead Time (L) - Dni", value=45, step=1, help="Czas od zamówienia do dostawy")
    review_period = st.number_input("Cykl Przeglądu (T) - Dni", value=7, step=1, help="Co ile dni składasz zamówienie?")

with c3:
    avg_daily_sales = st.number_input("Średnia Sprzedaż Dzienna", value=10.0, step=1.0)
    
with c4:
    wmape_input = st.number_input("Błąd Prognozy (WMAPE %)", value=40.0, step=5.0) / 100

# --- OBLICZENIA SS ---

# 1. Z-score dla celu operacyjnego
if 0 < target_sl_input < 1:
    Z_ops = norm.ppf(target_sl_input)
else:
    Z_ops = 0

# 2. Sigma Popytu (Dzienna)
sigma_D_daily = 1.25 * wmape_input * avg_daily_sales

# 3. Okres Ryzyka
risk_period_days = lead_time + review_period

# 4. Safety Stock
ss_units = Z_ops * sigma_D_daily * np.sqrt(risk_period_days)

# 5. Cycle Stock
cycle_stock = avg_daily_sales * risk_period_days

# --- WYNIKI SS ---

col_res1, col_res2, col_res3 = st.columns([1, 1, 2])

with col_res1:
    st.info("📊 Wyniki Obliczeń")
    st.metric("Zapas Bezpieczeństwa (SS)", f"{int(np.ceil(ss_units))} szt.", help=f"Dokładnie: {ss_units:.2f}")
    st.metric("Współczynnik Z", f"{Z_ops:.2f}")
    
with col_res2:
    st.warning("📉 Parametry Zmienności")
    st.metric("Sigma Dzienna", f"{sigma_D_daily:.1f} szt.")
    st.metric("Okres Ryzyka (L+T)", f"{risk_period_days} dni")

with col_res3:
    st.write("### Struktura Zapasu")
    # Wizualizacja Cycle Stock vs Safety Stock
    fig, ax = plt.subplots(figsize=(6, 2))
    
    categories = ['Popyt Oczekiwany', 'Zapas Bezpieczeństwa']
    values = [cycle_stock, ss_units]
    colors = ['#e0e0e0', '#ff4b4b']
    
    ax.barh(categories, values, color=colors)
    
    for i, v in enumerate(values):
        ax.text(v, i, f' {int(v)} szt.', va='center', fontweight='bold')
        
    ax.set_xlim(0, sum(values)*1.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.get_xaxis().set_visible(False)
    
    st.pyplot(fig)
    st.caption(f"Całkowity punkt ponownego zamawiania (ROP) = {int(cycle_stock + ss_units)} szt.")