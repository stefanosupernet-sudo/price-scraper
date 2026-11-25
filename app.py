from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from scraper import analyze

st.set_page_config(page_title="Price Scraper", page_icon="🪑", layout="wide")

# Language selector
lang = st.sidebar.selectbox("Lingua / Język", ["Italiano", "Polski"], index=0)
is_pl = lang == "Polski"

# Translations
T = {
    "title": "🪑 Price Scraper – Analisi di Mercato" if not is_pl else "🪑 Price Scraper – Analiza rynku",
    "caption": "Inserisci il tuo prodotto e 3 concorrenti. Aggiungiamo automaticamente prodotti simili da Trovaprezzi, Idealo, Google Shopping e Amazon." if not is_pl else "Wprowadź swój produkt i 3 konkurentów. Automatycznie dodajemy podobne produkty z Allegro, Ceneo, Google Shopping i Amazon.",
    "product_url": "URL del tuo prodotto *" if not is_pl else "URL Twojego produktu *",
    "product_ph": "https://www.tuosito.it/prodotto..." if not is_pl else "https://twojastrona.pl/produkt...",
    "keywords": "Parole chiave prodotto (opzionale)" if not is_pl else "Słowa kluczowe produktu (opcjonalnie)",
    "keywords_ph": "scrivania victorian classica legno" if not is_pl else "biurko klasyczne drewniane",
    "comp1": "URL Concorrente 1" if not is_pl else "URL Konkurent 1",
    "comp2": "URL Concorrente 2" if not is_pl else "URL Konkurent 2",
    "comp3": "URL Concorrente 3" if not is_pl else "URL Konkurent 3",
    "analyze": "🔍 Analizza mercato" if not is_pl else "🔍 Analizuj rynek",
    "error_url": "Inserisci almeno l'URL del tuo prodotto." if not is_pl else "Wprowadź przynajmniej URL swojego produktu.",
    "spinner": "Sto analizzando i prezzi..." if not is_pl else "Analizuję ceny...",
    "info": "Compila il form e clicca **Analizza mercato**." if not is_pl else "Wypełnij formularz i kliknij **Analizuj rynek**.",
    "no_price": "Nessun prezzo estratto. Controlla gli URL o prova con parole chiave più precise." if not is_pl else "Nie znaleziono cen. Sprawdź adresy URL lub spróbuj bardziej precyzyjnych słów kluczowych.",
    "min": "Prezzo minimo" if not is_pl else "Cena minimalna",
    "max": "Prezzo massimo" if not is_pl else "Cena maksymalna",
    "avg": "Prezzo medio" if not is_pl else "Cena średnia",
    "count": "Offerte trovate" if not is_pl else "Znalezione oferty",
    "chart_title": "Confronto prezzi di mercato" if not is_pl else "Porównanie cen rynkowych",
    "detail": "Dettaglio offerte" if not is_pl else "Szczegóły ofert",
    "download": "📥 Scarica report CSV" if not is_pl else "📥 Pobierz raport CSV",
    "errors": "⚠️ Errori / Prezzi non trovati" if not is_pl else "⚠️ Błędy / Nie znaleziono cen",
    "last": "Ultimo aggiornamento" if not is_pl else "Ostatnia aktualizacja",
}

st.markdown("""
<style>
    .main { background-color: #f8f5f0; }
    .stMetric { background-color: #ffffff; padding: 1rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    h1 { color: #3d2b1f; font-family: 'Georgia', serif; }
</style>
""", unsafe_allow_html=True)

st.title(T["title"])
st.caption(T["caption"])

with st.form("input_form"):
    product_url = st.text_input(T["product_url"], placeholder=T["product_ph"])
    keywords = st.text_input(T["keywords"], placeholder=T["keywords_ph"])
    col1, col2, col3 = st.columns(3)
    with col1:
        comp1 = st.text_input(T["comp1"], placeholder="https://...")
    with col2:
        comp2 = st.text_input(T["comp2"], placeholder="https://...")
    with col3:
        comp3 = st.text_input(T["comp3"], placeholder="https://...")
    submitted = st.form_submit_button(T["analyze"], type="primary")

if submitted:
    if not product_url.strip():
        st.error(T["error_url"])
        st.stop()

    with st.spinner(T["spinner"]):
        competitors = [comp1, comp2, comp3]
        results = analyze(product_url.strip(), competitors, keywords.strip() or None, lang="pl" if is_pl else "it")
        st.session_state["results"] = results
        st.session_state["last_update"] = datetime.now()

if "results" not in st.session_state:
    st.info(T["info"])
    st.stop()

results = st.session_state["results"]
df = pd.DataFrame(results)
valid = df[df["price"].notna()].copy()

if valid.empty:
    st.error(T["no_price"])
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric(T["min"], f"{valid['price'].min():.2f} €")
col2.metric(T["max"], f"{valid['price'].max():.2f} €")
col3.metric(T["avg"], f"{valid['price'].mean():.2f} €")
col4.metric(T["count"], len(valid))

st.markdown("---")

fig = px.bar(
    valid.sort_values("price"),
    x="name",
    y="price",
    color="source",
    title=T["chart_title"],
    labels={"price": "Prezzo (€)" if not is_pl else "Cena (€)", "name": "Prodotto" if not is_pl else "Produkt"},
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.update_layout(xaxis_tickangle=-45, height=500, plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, use_container_width=True)

st.subheader(T["detail"])
display_df = valid[["name", "price", "source", "url"]].sort_values("price")
display_df["price"] = display_df["price"].map(lambda x: f"{x:.2f} €")
st.dataframe(display_df, use_container_width=True, hide_index=True)

csv = display_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label=T["download"],
    data=csv,
    file_name=f"report_prezzi_{datetime.now():%Y%m%d}.csv",
    mime="text/csv",
)

errors = df[df["status"] != "ok"]
if not errors.empty:
    with st.expander(T["errors"]):
        st.dataframe(errors[["name", "url", "status", "error"]], hide_index=True)

if "last_update" in st.session_state:
    st.caption(f"{T['last']}: {st.session_state['last_update'].strftime('%Y-%m-%d %H:%M')}")
