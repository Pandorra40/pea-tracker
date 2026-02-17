import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Mon PEA (Via Google Sheets)", layout="wide")

# ---------------------------------------------------------
# ⬇️ COLLEZ VOTRE LIEN GOOGLE SHEET (CSV) ICI ENTRE LES GUILLEMETS ⬇️
# Exemple : "https://docs.google.com/spreadsheets/d/e/2PACX-1vQThkmN-VWRHc-R-DP97YXuTIqshxmPK5twHitZvfeLPcpzk_VJ6Z_KgIlA-Oah71v7iiJ96UPbVoOD/pub?output=csv"
SHEET_URL = "VOTRE_LIEN_GOOGLE_SHEET_ICI" 
# ---------------------------------------------------------

# ==========================================
# 2. CHARGEMENT DES DONNÉES (FIABLE À 100%)
# ==========================================
@st.cache_data(ttl=60) # Actualisation toutes les minutes
def load_data():
    if "VOTRE_LIEN" in SHEET_URL:
        return None
    try:
        # On lit le CSV directement depuis Google
        df = pd.read_csv(SHEET_URL)
        
        # Conversion des nombres (parfois Google envoie des virgules au lieu de points)
        cols_num = ['Qte', 'PRU', 'Div', 'Cours']
        for col in cols_num:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(',', '.').str.replace('€', '').astype(float)
        
        return df
    except Exception as e:
        st.error(f"Erreur de lecture Google Sheet : {e}")
        return None

df = load_data()

# ==========================================
# 3. INTERFACE
# ==========================================
st.title("🚀 Tracker PEA (Google Sheet Edition)")

if df is None:
    st.warning("⚠️ Veuillez coller votre lien Google Sheet (publié en CSV) dans le code à la ligne 12.")
    st.stop()

# --- CALCULS ---
df['Val. Initiale'] = df['Qte'] * df['PRU']
df['Val. Actuelle'] = df['Qte'] * df['Cours']
df['Plus-Value €'] = df['Val. Actuelle'] - df['Val. Initiale']
df['Plus-Value %'] = ((df['Val. Actuelle'] / df['Val. Initiale']) - 1) * 100
df['Div. 5 Ans'] = df['Qte'] * df['Div'] * 5
df['PRU Net'] = df['PRU'] - (df['Div'] * 5)

# Totaux
total_investi = df['Val. Initiale'].sum()
total_actuel = df['Val. Actuelle'].sum()
plus_value_totale = total_actuel - total_investi
perf_globale = (plus_value_totale / total_investi) * 100
div_cumul = df['Div. 5 Ans'].sum()

# --- KPI (INDICATEURS) ---
k1, k2, k3 = st.columns(3)
k1.metric("Valeur Portefeuille", f"{total_actuel:.2f} €", f"{plus_value_totale:+.2f} €")
k2.metric("Performance Globale", f"{perf_globale:+.2f} %")
k3.metric("Dividendes cumulés (5 ans)", f"{div_cumul:.2f} €")

# --- GRAPHIQUES ---
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("🍕 Répartition par Action")
    fig_pie = px.pie(df, values='Val. Actuelle', names='Nom', hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

with col_g2:
    st.subheader("🏭 Répartition Sectorielle")
    df_secteur = df.groupby('Secteur')['Val. Actuelle'].sum().reset_index()
    fig_sect = px.pie(df_secteur, values='Val. Actuelle', names='Secteur')
    st.plotly_chart(fig_sect, use_container_width=True)

# --- TABLEAU DÉTAILLÉ ---
st.subheader("📋 Détail des lignes")

# Mise en forme du tableau
df_display = df[['Nom', 'Cours', 'PRU', 'PRU Net', 'Plus-Value €', 'Plus-Value %', 'Div. 5 Ans']].copy()

# Fonction de style pour les couleurs
def color_sur_pv(val):
    color = '#2ecc71' if val >= 0 else '#e74c3c'
    return f'color: {color}; font-weight: bold'

st.dataframe(
    df_display.style.applymap(color_sur_pv, subset=['Plus-Value €', 'Plus-Value %'])
    .format({
        "Cours": "{:.2f} €",
        "PRU": "{:.2f} €",
        "PRU Net": "{:.2f} €",
        "Plus-Value €": "{:+.2f} €",
        "Plus-Value %": "{:+.2f} %",
        "Div. 5 Ans": "{:.2f} €"
    }),
    use_container_width=True,
    hide_index=True
)

if st.button("🔄 Actualiser"):
    st.cache_data.clear()
    st.rerun()
