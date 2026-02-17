import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# ==========================================
# 1. CONFIGURATION ET SESSION STATE
# ==========================================
st.set_page_config(page_title="Mon Tracker PEA Long Terme", layout="wide", initial_sidebar_state="collapsed")

# Initialisation du portefeuille (Données à jour avec Sartorius)
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
# 2. RÉCUPÉRATION DES DONNÉES (CORRIGÉ FINAL)
# ==========================================
@st.cache_data(ttl=3600) # On remet 1h de cache car on charge 1 an de données
def load_financial_data(ticker_list):
    full_tickers = ticker_list + ['^FCHI']
    
    # ON REPASSE À 1 AN (1y) pour avoir un beau graphique
    data = yf.download(full_tickers, period="1y", group_by='ticker', auto_adjust=True)
    
    df_close = pd.DataFrame()
    last_prices_dict = {}
    infos = {}

    # Reconstruction propre
    for t in full_tickers:
        try:
            # Extraction sécurisée de la colonne 'Close'
            if isinstance(data, pd.DataFrame):
                if t in data.columns and isinstance(data[t], pd.DataFrame):
                    series = data[t]['Close']
                elif ('Close', t) in data.columns:
                    series = data[('Close', t)]
                else:
                    # Tentative générique si la structure change
                    series = data.xs(t, axis=1, level=0)['Close']
            
            # NETTOYAGE CRUCIAL : On remplit les trous (jours fériés, bugs API)
            # ffill() propage la dernière valeur connue vers l'avant
            series = series.ffill().bfill()
            
            df_close[t] = series
            
            # PRIX ACTUEL : On prend la toute dernière valeur de la série nettoyée
            last_prices_dict[t] = series.iloc[-1]
            
        except Exception as e:
            # En cas de crash total sur une action
            print(f"Erreur {t}: {e}")
            last_prices_dict[t] = 0.0
            df_close[t] = 0.0

    # Récupération des infos fondamentales
    tickers_only = [t for t in ticker_list]
    for t in tickers_only:
        try:
            tk = yf.Ticker(t)
            inf = tk.info
            infos[t] = {
                'target': inf.get('targetMeanPrice', 0),
                'payout': inf.get('payoutRatio', 0) * 100 if inf.get('payoutRatio') else 0
            }
        except:
            infos[t] = {'target': 0, 'payout': 0}
            
    return df_close, infos, last_prices_dict

tickers = list(st.session_state.mon_portefeuille.keys())
df_prices, fund_data, last_prices = load_financial_data(tickers)

# ==========================================
# 3. CALCULS FINANCIERS GLOBAUX
# ==========================================
total_achat = sum(v['qte'] * v['pru'] for v in st.session_state.mon_portefeuille.values())
total_actuel = sum(st.session_state.mon_portefeuille[t]['qte'] * last_prices[t] for t in tickers)
total_div_annuel = sum(v['qte'] * v['div'] for v in st.session_state.mon_portefeuille.values())
total_div_5ans = total_div_annuel * 5
diff_globale = total_actuel - total_achat

# Calcul de la valuation cible totale (Targets)
total_target_valuation = 0
valeur_actuelle_pour_upside = 0
for t in tickers:
    qty = st.session_state.mon_portefeuille[t]['qte']
    target = fund_data[t]['target']
    if target > 0:
        total_target_valuation += (target * qty)
        valeur_actuelle_pour_upside += (last_prices[t] * qty)

upside_total = ((total_target_valuation / valeur_actuelle_pour_upside) - 1) * 100 if valeur_actuelle_pour_upside > 0 else 0

# ==========================================
# 4. INTERFACE STREAMLIT
# ==========================================
st.title("🚀 Tracker PEA : Objectif 5 ans")

# --- INDICATEURS CLÉS ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Valeur Portefeuille", f"{total_actuel:.2f} €", f"{diff_globale:.2f} €")
m2.metric("Plus-value Totale", f"{((total_actuel/total_achat)-1)*100:.2f} %")
m3.metric("Dividendes cumulés (5 ans)", f"{total_div_5ans:.2f} €")
m4.metric("Marge de hausse (Target)", f"+{upside_total:.1f} %")

# --- GRAPHIQUE PERFORMANCE ---
st.subheader("Comparaison Performance (Base 100)", divider="rainbow")

# On s'assure que les poids sont alignés avec les colonnes disponibles
weights = pd.Series({t: (st.session_state.mon_portefeuille[t]['qte'] * st.session_state.mon_portefeuille[t]['pru']) / total_achat for t in tickers})

# Calcul de la performance
# On utilise df_prices[tickers] pour s'assurer de l'ordre
# .fillna(0) évite que le graphique plante s'il manque une donnée au début
port_perf = df_prices[tickers].pct_change().fillna(0)
port_idx = (port_perf @ weights).add(1).cumprod() * 100

cac_perf = df_prices['^FCHI'].pct_change().fillna(0)
cac_idx = cac_perf.add(1).cumprod() * 100

st.line_chart(pd.DataFrame({'Mon Portefeuille': port_idx, 'CAC 40': cac_idx}))

# --- ONGLETS D'ANALYSE ---
tab_detail, tab_repart = st.tabs(["📋 Détail & Projection 5 ans", "🍕 Répartition"])

with tab_detail:
    st.info("💡 **Objectif (Target)** : Prix visé par les analystes. **PRU Net (5 ans)** : Votre prix de revient après encaissement de 5 ans de dividendes.")
    
    # Construction du tableau détaillé
    data_rows = []
    for t, v in st.session_state.mon_portefeuille.items():
        cours = last_prices[t]
        pru_initial = v['pru']
        div_annuel = v['div']
        div_5ans_cumul = div_annuel * 5
        pru_net_5ans = pru_initial - div_5ans_cumul
        target = fund_data[t]['target']
        upside = ((target / cours) - 1) * 100 if target > 0 else 0
        
        data_rows.append({
            "Nom": v['nom'],
            "Cours": cours,
            "PRU Initial": pru_initial,
            "Plus/Moins-Value": (cours - pru_initial) * v['qte'],
            "Objectif (Target)": target if target > 0 else 0,
            "Potentiel (%)": upside,
            "Div. 5 ans": div_5ans_cumul * v['qte'],
            "PRU Net (5 ans)": pru_net_5ans,
            "Rendement (YOC)": (div_annuel / pru_initial) * 100
        })

    df_positions = pd.DataFrame(data_rows)

    # Ligne de TOTAL
    df_total = pd.DataFrame([{
        "Nom": "💰 TOTAL",
        "Cours": None,
        "PRU Initial": total_achat,
        "Plus/Moins-Value": diff_globale,
        "Objectif (Target)": total_target_valuation,
        "Potentiel (%)": upside_total,
        "Div. 5 ans": total_div_5ans,
        "PRU Net (5 ans)": total_achat - total_div_5ans,
        "Rendement (YOC)": (total_div_annuel / total_achat) * 100
    }])

    df_final = pd.concat([df_positions, df_total], ignore_index=True)

    # Styles de couleurs
    def style_positive(val):
        if isinstance(val, (int, float)):
            return f'color: {"#2ecc71" if val >= 0 else "#e74c3c"}; font-weight: bold'
        return ''

    def style_pru_net(val):
        return 'color: #3498db; font-weight: bold' if isinstance(val, (int, float)) else ''

    st.dataframe(
        df_final.style.applymap(style_positive, subset=['Plus/Moins-Value', 'Potentiel (%)'])
        .applymap(style_pru_net, subset=['PRU Net (5 ans)'])
        .format({
            "Cours": "{:.2f} €", 
            "PRU Initial": "{:.2f} €", 
            "Plus/Moins-Value": "{:.2f} €",
            "Objectif (Target)": lambda x: f"{x:.2f} €" if (x and x > 0) else "N/A",
            "Potentiel (%)": "+{:.1f} %",
            "Div. 5 ans": "{:.2f} €", 
            "PRU Net (5 ans)": "{:.2f} €",
            "Rendement (YOC)": "{:.2f} %"
        }, na_rep="-"),
        use_container_width=True, hide_index=True
    )

with tab_repart:
    col1, col2 = st.columns(2)
    with col1:
        df_act = pd.DataFrame({'Action': [v['nom'] for v in st.session_state.mon_portefeuille.values()], 
                               'Valeur': [st.session_state.mon_portefeuille[t]['qte'] * last_prices[t] for t in tickers]})
        st.plotly_chart(px.pie(df_act, values='Valeur', names='Action', title="Poids des lignes", hole=0.4, template="plotly_dark"), use_container_width=True)
    with col2:
        df_sect = pd.DataFrame({'Secteur': [v['secteur'] for v in st.session_state.mon_portefeuille.values()], 
                                'Valeur': [st.session_state.mon_portefeuille[t]['qte'] * last_prices[t] for t in tickers]}).groupby('Secteur').sum().reset_index()
        st.plotly_chart(px.pie(df_sect, values='Valeur', names='Secteur', title="Répartition Sectorielle", template="plotly_dark"), use_container_width=True)

# Barre latérale
with st.sidebar:
    st.subheader("🔄 Actions")
    if st.button("Actualiser les données"):
        st.cache_data.clear()

        st.rerun()


