# Price Scraper – Scrivanie di Lusso Stile Classico

Dashboard grafica + scraper modificabile per monitorare i prezzi di scrivanie classiche in legno (mercato italiano).

## Avvio rapido

```bash
pip install -r requirements.txt
streamlit run app.py
```

Poi apri il browser su http://localhost:8501 e clicca **Aggiorna prezzi**.

## Come modificare

Edita `config.json` e aggiungi gli URL dei prodotti che vuoi tracciare (tuo sito + concorrenti + lookalike).

Esempio:
```json
{
  "categories": {
    "Scrivania stile classico": [
      {"name": "Nome prodotto", "url": "https://..."}
    ]
  }
}
```

## Report automatico

Per un report giornaliero puoi schedulare:
```bash
python -c "from scraper import run_scraper; print(run_scraper())"
```

## Note

- Lo scraper usa JSON-LD, meta tag e regex per estrarre i prezzi.
- Rispetta i siti (non abusare di richieste).
- Alcuni e-commerce possono bloccare lo scraping o cambiare struttura HTML.
