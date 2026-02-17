import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

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
# 2. RÉCUPÉRATION DES DONNÉES (PRIX UNIQUEMENT)
# ==========================================
@st.cache_data(ttl=3600)
def load_financial_data(ticker_list):
    # On télécharge uniquement les prix de clôture
    df_history = yf.download(ticker_list + ['^FCHI'], period="1y")['Close']
    return df_history

tickers = list(st.session_state.mon_portefeuille.keys())
df_prices = load_financial_data(tickers)
last_prices = df_prices[tickers].iloc[-1]

# ==========================================
# 3. CALCULS FINANCIERS GLOBAUX
# ==========================================
total_achat = sum(v['qte'] * v['pru'] for v in st.session_state.mon_portefeuille.values())
total_actuel = sum(st.session_state.mon_portefeuille[t]['qte'] * last_prices[t] for t in tickers)
total_div_annuel = sum(v['qte'] * v['div'] for v in st.session_state.mon_portefeuille.values())
total_div_5ans = total_div_annuel * 5
diff_globale = total_actuel - total_achat

# ==========================================
# 4. INTERFACE STREAMLIT
# ==========================================
st.title("🚀 Tracker PEA : Objectif 5 ans")

# --- INDICATEURS CLÉS (3 colonnes au lieu de 4) ---
m1, m2, m3 = st.columns(3)
m1.metric("Valeur Portefeuille", f"{total_actuel:.2f} €", f"{diff_globale:.2f} €")
m2.metric("Plus-value Totale", f"{((total_actuel/total_achat)-1)*100:.2f} %")
m3.metric("Dividendes cumulés (5 ans)", f"{total_div_5ans:.2f} €")

# --- GRAPHIQUE PERFORMANCE ---
st.subheader("Comparaison Performance (Base 100)", divider="rainbow")
weights = {t: (st.session_state.mon_portefeuille[t]['qte'] * st.session_state.mon_portefeuille[t]['pru']) / total_achat for t in tickers}
port_idx = (df_prices[tickers].pct_change().dropna() @ pd.Series(weights)).add(1).cumprod() * 100
cac_idx = df_prices['^FCHI'].pct_change().dropna().add(1).cumprod() * 100
st.line_chart(pd.DataFrame({'Mon Portefeuille': port_idx, 'CAC 40': cac_idx}))

# --- ONGLETS D'ANALYSE ---
tab_detail, tab_repart = st.tabs(["📋 Détail & Projection 5 ans", "🍕 Répartition"])

with tab_detail:
    st.info("💡 **PRU Net (5 ans)** : Votre prix de revient après encaissement de 5 ans de dividendes.")
    
    data_rows = []
    for t, v in st.session_state.mon_portefeuille.items():
        cours = last_prices[t]
        pru_initial = v['pru']
        div_annuel = v['div']
        pru_net_5ans = pru_initial - (div_annuel * 5)
        
        data_rows.append({
            "Nom": v['nom'],
            "Cours": cours,
            "PRU Initial": pru_initial,
            "Plus/Moins-Value": (cours - pru_initial) * v['qte'],
            "Div. 5 ans": div_annuel * 5 * v['qte'],
            "PRU Net (5 ans)": pru_net_5ans,
            "Rendement (YOC)": (div_annuel / pru_initial) * 100
        })

    df_positions = pd.DataFrame(data_rows)

    # Styles
    def style_positive(val):
        if isinstance(val, (int, float)):
            return f'color: {"#2ecc71" if val >= 0 else "#e74c3c"}; font-weight: bold'
        return ''

    st.dataframe(
        df_positions.style.applymap(style_positive, subset=['Plus/Moins-Value'])
        .format({
            "Cours": "{:.2f} €", 
            "PRU Initial": "{:.2f} €", 
            "Plus/Moins-Value": "{:+.2f} €",
            "Div. 5 ans": "{:.2f} €", 
            "PRU Net (5 ans)": "{:.2f} €",
            "Rendement (YOC)": "{:.2f} %"
        }),
        use_container_width=True, hide_index=True
    )

with tab_repart:
    col1, col2 = st.columns(2)
    with col1:
        df_act = pd.DataFrame({
            'Action': [v['nom'] for v in st.session_state.mon_portefeuille.values()], 
            'Valeur': [st.session_state.mon_portefeuille[t]['qte'] * last_prices[t] for t in tickers]
        })
        st.plotly_chart(px.pie(df_act, values='Valeur', names='Action', title="Poids des lignes", hole=0.4, template="plotly_dark"), use_container_width=True)
    with col2:
        df_sect = pd.DataFrame({
            'Secteur': [v['secteur'] for v in st.session_state.mon_portefeuille.values()], 
            'Valeur': [st.session_state.mon_portefeuille[t]['qte'] * last_prices[t] for t in tickers]
        }).groupby('Secteur').sum().reset_index()
        st.plotly_chart(px.pie(df_sect, values='Valeur', names='Secteur', title="Répartition Sectorielle", template="plotly_dark"), use_container_width=True)
