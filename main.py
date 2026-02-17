import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Mon Tracker PEA Long Terme", layout="wide", initial_sidebar_state="collapsed")

# ⬇️ COLLEZ VOTRE LIEN GOOGLE SHEET (CSV) ICI ⬇️
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQThkmN-VWRHc-R-DP97YXuTIqshxmPK5twHitZvfeLPcpzk_VJ6Z_KgIlA-Oah71v7iiJ96UPbVoOD/pub?output=csv"

# ==========================================
# 2. CHARGEMENT ET SYNC DES DONNÉES
# ==========================================
@st.cache_data(ttl=60)
def load_sheet_data():
    try:
        df_gs = pd.read_csv(SHEET_URL)
        # Nettoyage pour correspondre aux noms attendus
        df_gs.columns = df_gs.columns.str.strip()
        mapping = {'Qté': 'qte', 'Nom': 'nom', 'Secteur': 'secteur', 'PRU': 'pru', 'Div': 'div', 'Ticker': 'ticker'}
        df_gs = df_gs.rename(columns=mapping)
        
        # On transforme le DataFrame en dictionnaire compatible avec ton code d'origine
        portfolio = {}
        for _, row in df_gs.iterrows():
            portfolio[row['ticker']] = {
                'nom': row['nom'],
                'qte': float(str(row['qte']).replace(',', '.')),
                'pru': float(str(row['pru']).replace(',', '.')),
                'div': float(str(row['div']).replace(',', '.')),
                'secteur': row['secteur']
            }
        return portfolio
    except Exception as e:
        st.error(f"Erreur de lecture Google Sheet : {e}")
        return None

# Chargement du dictionnaire de portefeuille
portfolio_data = load_sheet_data()

if portfolio_data is None:
    st.warning("⚠️ En attente du lien Google Sheet valide (Ligne 12).")
    st.stop()

# On remplace ton ancien st.session_state par les données du Sheet
tickers = list(portfolio_data.keys())

@st.cache_data(ttl=3600)
def load_financial_data(ticker_list):
    df_history = yf.download(ticker_list + ['^FCHI'], period="1y")['Close']
    infos = {}
    for t in ticker_list:
        try:
            tk = yf.Ticker(t)
            inf = tk.info
            infos[t] = {
                'target': inf.get('targetMeanPrice', 0),
                'payout': inf.get('payoutRatio', 0) * 100
            }
        except:
            infos[t] = {'target': 0, 'payout': 0}
    return df_history, infos

df_prices, fund_data = load_financial_data(tickers)
last_prices = df_prices[tickers].iloc[-1]

# ==========================================
# 3. CALCULS FINANCIERS GLOBAUX
# ==========================================
total_achat = sum(v['qte'] * v['pru'] for v in portfolio_data.values())
total_actuel = sum(portfolio_data[t]['qte'] * last_prices[t] for t in tickers)
total_div_annuel = sum(v['qte'] * v['div'] for v in portfolio_data.values())
total_div_5ans = total_div_annuel * 5
diff_globale = total_actuel - total_achat

# Calcul Target / Upside
total_target_valuation = 0
valeur_actuelle_pour_upside = 0
for t in tickers:
    qty = portfolio_data[t]['qte']
    target = fund_data[t]['target']
    if target > 0:
        total_target_valuation += (target * qty)
        valeur_actuelle_pour_upside += (last_prices[t] * qty)

upside_total = ((total_target_valuation / valeur_actuelle_pour_upside) - 1) * 100 if valeur_actuelle_pour_upside > 0 else 0

# ==========================================
# 4. INTERFACE STREAMLIT (TON DESIGN)
# ==========================================
st.title("🚀 Tracker PEA : Objectif 5 ans")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Valeur Portefeuille", f"{total_actuel:.2f} €", f"{diff_globale:.2f} €")
m2.metric("Plus-value Totale", f"{((total_actuel/total_achat)-1)*100:.2f} %")
m3.metric("Dividendes cumulés (5 ans)", f"{total_div_5ans:.2f} €")
m4.metric("Marge de hausse (Target)", f"+{upside_total:.1f} %")

st.subheader("Comparaison Performance (Base 100)", divider="rainbow")
weights = {t: (portfolio_data[t]['qte'] * portfolio_data[t]['pru']) / total_achat for t in tickers}
port_idx = (df_prices[tickers].pct_change().dropna() @ pd.Series(weights)).add(1).cumprod() * 100
cac_idx = df_prices['^FCHI'].pct_change().dropna().add(1).cumprod() * 100
st.line_chart(pd.DataFrame({'Mon Portefeuille': port_idx, 'CAC 40': cac_idx}))

tab_detail, tab_repart = st.tabs(["📋 Détail & Projection 5 ans", "🍕 Répartition"])

with tab_detail:
    data_rows = []
    for t, v in portfolio_data.items():
        cours = last_prices[t]
        pru_i = v['pru']
        div_a = v['div']
        pru_n = pru_i - (div_a * 5)
        target = fund_data[t]['target']
        upside = ((target / cours) - 1) * 100 if target > 0 else 0
        
        data_rows.append({
            "Nom": v['nom'], "Cours": cours, "PRU Initial": pru_i,
            "Plus/Moins-Value": (cours - pru_i) * v['qte'],
            "Objectif (Target)": target, "Potentiel (%)": upside,
            "Div. 5 ans": div_a * 5 * v['qte'], "PRU Net (5 ans)": pru_n,
            "Rendement (YOC)": (div_a / pru_i) * 100
        })

    df_positions = pd.DataFrame(data_rows)
    # Styles et affichage (identique à ton code)
    st.dataframe(df_positions.style.format({
        "Cours": "{:.2f} €", "PRU Initial": "{:.2f} €", "Plus/Moins-Value": "{:.2f} €",
        "Objectif (Target)": "{:.2f} €", "Potentiel (%)": "+{:.1f} %", "Div. 5 ans": "{:.2f} €",
        "PRU Net (5 ans)": "{:.2f} €", "Rendement (YOC)": "{:.2f} %"
    }), use_container_width=True, hide_index=True)

with tab_repart:
    col1, col2 = st.columns(2)
    with col1:
        df_act = pd.DataFrame({'Action': [v['nom'] for v in portfolio_data.values()], 'Valeur': [portfolio_data[t]['qte'] * last_prices[t] for t in tickers]})
        st.plotly_chart(px.pie(df_act, values='Valeur', names='Action', title="Poids des lignes", hole=0.4, template="plotly_dark"), use_container_width=True)
