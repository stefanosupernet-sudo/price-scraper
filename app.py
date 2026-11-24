import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from scraper import analyze

st.set_page_config(page_title="Price Scraper – Analisi di Mercato", page_icon="🪑", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f8f5f0; }
    .stMetric { background-color: #ffffff; padding: 1rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    h1 { color: #3d2b1f; font-family: 'Georgia', serif; }
</style>
""", unsafe_allow_html=True)

st.title("🪑 Price Scraper – Analisi di Mercato")
st.caption("Inserisci il tuo prodotto e 3 concorrenti. Aggiungiamo automaticamente prodotti simili da Trovaprezzi, Idealo, Google Shopping e Amazon.")

with st.form("input_form"):
    product_url = st.text_input("URL del tuo prodotto *", placeholder="https://www.tuosito.it/prodotto...")
    keywords = st.text_input("Parole chiave prodotto (opzionale, per cercare lookalike)", placeholder="scrivania victorian classica legno")
    col1, col2, col3 = st.columns(3)
    with col1:
        comp1 = st.text_input("URL Concorrente 1", placeholder="https://...")
    with col2:
        comp2 = st.text_input("URL Concorrente 2", placeholder="https://...")
    with col3:
        comp3 = st.text_input("URL Concorrente 3", placeholder="https://...")
    submitted = st.form_submit_button("🔍 Analizza mercato", type="primary")

if submitted:
    if not product_url.strip():
        st.error("Inserisci almeno l'URL del tuo prodotto.")
        st.stop()

    with st.spinner("Sto analizzando i prezzi (diretti + marketplace)..."):
        competitors = [comp1, comp2, comp3]
        results = analyze(product_url.strip(), competitors, keywords.strip() or None)
        st.session_state["results"] = results
        st.session_state["last_update"] = datetime.now()

if "results" not in st.session_state:
    st.info("Compila il form e clicca **Analizza mercato**.")
    st.stop()

results = st.session_state["results"]
df = pd.DataFrame(results)
valid = df[df["price"].notna()].copy()

if valid.empty:
    st.error("Nessun prezzo estratto. Controlla gli URL o prova con parole chiave più precise.")
    st.stop()

# Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Prezzo minimo", f"{valid['price'].min():.2f} €")
col2.metric("Prezzo massimo", f"{valid['price'].max():.2f} €")
col3.metric("Prezzo medio", f"{valid['price'].mean():.2f} €")
col4.metric("Offerte trovate", len(valid))

st.markdown("---")

# Chart
fig = px.bar(
    valid.sort_values("price"),
    x="name",
    y="price",
    color="source",
    title="Confronto prezzi di mercato",
    labels={"price": "Prezzo (€)", "name": "Prodotto"},
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.update_layout(xaxis_tickangle=-45, height=500, plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, use_container_width=True)

# Table
st.subheader("Dettaglio offerte")
display_df = valid[["name", "price", "source", "url"]].sort_values("price")
display_df["price"] = display_df["price"].map(lambda x: f"{x:.2f} €")
st.dataframe(display_df, use_container_width=True, hide_index=True)

# Download
csv = display_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Scarica report CSV",
    data=csv,
    file_name=f"report_prezzi_{datetime.now():%Y%m%d}.csv",
    mime="text/csv",
)

# Errors
errors = df[df["status"] != "ok"]
if not errors.empty:
    with st.expander("⚠️ Errori / Prezzi non trovati"):
        st.dataframe(errors[["name", "url", "status", "error"]], hide_index=True)

if "last_update" in st.session_state:
    st.caption(f"Ultimo aggiornamento: {st.session_state['last_update'].strftime('%Y-%m-%d %H:%M')}")
