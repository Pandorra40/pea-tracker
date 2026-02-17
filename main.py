import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests

# ==========================================
# 1. CONFIGURATION ET SESSION STATE
# ==========================================
st.set_page_config(page_title="Mon Tracker PEA Long Terme", layout="wide", initial_sidebar_state="collapsed")

if 'mon_portefeuille' not in st.session_state:
    st.session_state.mon_portefeuille = {
        'AI.PA':  {'nom': 'Air Liquide', 'qte': 2, 'pru': 161.64, 'div': 3.20, 'secteur': 'Industrie'},
        'GTT.PA': {'nom': 'GTT', 'qte': 2, 'pru': 175.50, 'div': 7.30, 'secteur': 'Énergie'},
        'PUB.PA': {'nom': 'Publicis', 'qte': 4, 'pru': 86.60, 'div': 3.40, 'secteur': 'Communication'},
        'SU.PA':  {'nom': 'Schneider', 'qte': 1, 'pru': 234.28, 'div': 3.80, 'secteur': 'Industrie'},
        'SOP.PA': {'nom': 'Sopra Steria', 'qte': 2, 'pru': 155.12, 'div': 4.65, 'secteur': 'Tech'},
        'DIM.PA': {'nom': 'Sartorius Stedim', 'qte': 1, 'pru': 175.00, 'div': 0.69, 'secteur': 'Santé'}
    }

# ==========================================
# 2. RÉCUPÉRATION DES DONNÉES (CORRECTION TARGET)
# ==========================================
@st.cache_data(ttl=3600)
def load_financial_data(ticker_list):
    # Création d'une session avec un User-Agent pour éviter le blocage Yahoo
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    
    # Download des prix historiques
    df_history = yf.download(ticker_list + ['^FCHI'], period="1y", session=session)['Close']
    
    infos = {}
    for t in ticker_list:
        try:
            tk = yf.Ticker(t, session=session)
            # Tentative de récupération de la Target via l'attribut spécifique
            target = tk.analyst_price_target.get('mean', 0)
            # Si vide, repli sur le dictionnaire info
            if target == 0:
                target = tk.info.get('targetMeanPrice', 0)
            infos[t] = {'target': target}
        except:
            infos[t] = {'target': 0}
    return df_history, infos

tickers = list(st.session_state.mon_portefeuille.keys())
df_prices, fund_data = load_financial_data(tickers)
last_prices = df_prices[tickers].iloc[-1]

# ==========================================
# 3. CALCULS FINANCIERS GLOBAUX
# ==========================================
total_achat = sum(v['qte'] * v['pru'] for v in st.session_state.mon_portefeuille.values())
total_actuel = sum(st.session_state.mon_portefeuille[t]['qte'] * last_prices[t] for t in tickers)
total_div_annuel = sum(v['qte'] * v['div'] for v in st.session_state.mon_portefeuille.values())
total_div_5ans = total_div_annuel * 5
diff_globale = total_actuel - total_achat

# Calcul de l'Upside Global
total_target_valuation = 0
valeur_actuelle_pour_upside = 0
for t in tickers:
    qty = st.session_state.mon_portefeuille[t]['qte']
    target = fund_data[t]['target']
    if target > 0:
        total_target_valuation += (target * qty
