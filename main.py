import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Mon PEA (Via Google Sheets)", layout="wide")

# ---------------------------------------------------------
# ⬇️ COLLEZ VOTRE LIEN GOOGLE SHEET (CSV) ICI ⬇️
# ---------------------------------------------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQThkmN-VWRHc-R-DP97YXuTIqshxmPK5twHitZvfeLPcpzk_VJ6Z_KgIlA-Oah71v7iiJ96UPbVoOD/pub?output=csv" 
# ---------------------------------------------------------

@st.cache_data(ttl=60)
def load_data():
    if "VOTRE_LIEN" in SHEET_URL or not SHEET_URL.startswith("http"):
        return None
    try:
        # Lecture du CSV
        df = pd.read_csv(SHEET_URL)
        
        # Nettoyage automatique des noms de colonnes (enlève espaces et met en minuscule)
        df.columns = df.columns.str.strip()
        
        # Mapping pour tolérer différentes écritures
        mapping = {
            'nom': 'Nom', 'action': 'Nom',
            'secteur': 'Secteur',
            'qte': 'Qte', 'quantité': 'Qte', 'quantite': 'Qte',
            'pru': 'PRU',
            'div': 'Div', 'dividende': 'Div',
            'cours': 'Cours', 'prix': 'Cours'
        }
        df = df.rename(columns={c: mapping[c.lower()] for c in df.columns if c.lower() in mapping})

        # Nettoyage des données numériques
        cols_num = ['Qte', 'PRU', 'Div', 'Cours']
        for col in cols_num:
            if col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].astype(str).str.replace(',', '.').str.replace('€', '').str.strip()
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                st.error(f"La colonne '{col}' est manquante dans votre fichier Google Sheets.")
                return None
        
        return df.dropna(subset=['Nom']) # Supprime les lignes vides
    except Exception as e:
        st.error(f"Détail de l'erreur : {e}")
        return None

df = load_data()

# ==========================================
# 2. INTERFACE ET CALCULS
# ==========================================
st.title("🚀 Tracker PEA (Google Sheet Edition)")

if df is None:
    st.info("💡 **Aide :** Vérifiez que vous avez bien fait 'Fichier' > 'Partager' > 'Publier sur le web' > Format 'CSV' dans Google Sheets.")
    st.stop()

# Calculs
df['Val. Initiale'] = df['Qte'] * df['PRU']
df['Val. Actuelle'] = df['Qte'] * df['Cours']
df['Plus-Value €'] = df['Val. Actuelle'] - df['Val. Initiale']
df['Plus-Value %'] = ((df['Val. Actuelle'] / df['Val. Initiale']) - 1) * 100
df['Div. 5 Ans'] = df['Qte'] * df['Div'] * 5

# KPI
t_inv, t_act = df['Val. Initiale'].sum(), df['Val. Actuelle'].sum()
pv_t = t_act - t_inv
perf = (pv_t / t_inv) * 100 if t_inv != 0 else 0

k1, k2, k3 = st.columns(3)
k1.metric("Valeur Portefeuille", f"{t_act:,.2f} €", f"{pv_t:+.2f} €")
k2.metric("Performance Globale", f"{perf:+.2f} %")
k3.metric("Dividendes prévus (5 ans)", f"{df['Div. 5 Ans'].sum():,.2f} €")

# Graphiques
c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(px.pie(df, values='Val. Actuelle', names='Nom', title="Répartition par Action", hole=0.4), use_container_width=True)
with c2:
    df_s = df.groupby('Secteur')['Val. Actuelle'].sum().reset_index()
    st.plotly_chart(px.pie(df_s, values='Val. Actuelle', names='Secteur', title="Répartition Sectorielle"), use_container_width=True)

# Tableau
st.subheader("📋 Détail des positions")
st.dataframe(df.style.format({
    "Cours": "{:.2f} €", "PRU": "{:.2f} €", "Plus-Value €": "{:+.2f} €", "Plus-Value %": "{:+.2f} %"
}), use_container_width=True, hide_index=True)

