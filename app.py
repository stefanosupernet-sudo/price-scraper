import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from scraper import run_scraper, load_config

st.set_page_config(page_title="Price Scraper – Scrivanie Lusso", page_icon="🪑", layout="wide")

# Custom CSS for a refined look
st.markdown("""
<style>
    .main { background-color: #f8f5f0; }
    .stMetric { background-color: #ffffff; padding: 1rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    h1 { color: #3d2b1f; font-family: 'Georgia', serif; }
    .product-card { background: white; border-radius: 10px; padding: 1rem; margin: 0.5rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }
</style>
""", unsafe_allow_html=True)

st.title("🪑 Price Scraper – Scrivanie di Lusso")
st.caption("Monitoraggio prezzi scrivanie classiche in legno · Mercato italiano")

if st.button("🔄 Aggiorna prezzi", type="primary"):
    with st.spinner("Sto raccogliendo i prezzi..."):
        results = run_scraper()
        st.session_state["results"] = results
        st.session_state["last_update"] = datetime.now()

if "results" not in st.session_state:
    st.info("Clicca su **Aggiorna prezzi** per eseguire lo scraping.")
    st.stop()

results = st.session_state["results"]
df = pd.DataFrame(results)
valid = df[df["price"].notna()].copy()

if valid.empty:
    st.error("Nessun prezzo estratto. Controlla gli URL in config.json")
    st.stop()

# Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Prezzo minimo", f"{valid['price'].min():.2f} €")
col2.metric("Prezzo massimo", f"{valid['price'].max():.2f} €")
col3.metric("Prezzo medio", f"{valid['price'].mean():.2f} €")
col4.metric("Prodotti tracciati", len(valid))

st.markdown("---")

# Chart
fig = px.bar(
    valid.sort_values("price"),
    x="name",
    y="price",
    color="category",
    title="Confronto prezzi",
    labels={"price": "Prezzo (€)", "name": "Prodotto"},
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.update_layout(xaxis_tickangle=-45, height=450, plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, use_container_width=True)

# Table
st.subheader("Dettaglio")
display_df = valid[["name", "price", "url", "category"]].sort_values("price")
display_df["price"] = display_df["price"].map(lambda x: f"{x:.2f} €")
st.dataframe(display_df, use_container_width=True, hide_index=True)

# Errors
errors = df[df["status"] != "ok"]
if not errors.empty:
    with st.expander("⚠️ Errori / Prezzi non trovati"):
        st.dataframe(errors[["name", "url", "status", "error"]], hide_index=True)

if "last_update" in st.session_state:
    st.caption(f"Ultimo aggiornamento: {st.session_state['last_update'].strftime('%Y-%m-%d %H:%M')}")

st.markdown("---")
st.markdown("**Come modificare:** edita `config.json` per aggiungere o rimuovere prodotti, poi rilancia.")
