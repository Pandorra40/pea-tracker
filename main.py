import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Mon PEA", layout="wide")

# Remplacez bien VOTRE_LIEN_ICI par votre lien se terminant par output=csv
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQThkmN-VWRHc-R-DP97YXuTIqshxmPK5twHitZvfeLPcpzk_VJ6Z_KgIlA-Oah71v7iiJ96UPbVoOD/pub?output=csv" 

@st.cache_data(ttl=60)
def load_data():
    if "VOTRE_LIEN" in SHEET_URL:
        return None
    try:
        df = pd.read_csv(SHEET_URL)
        
        # Nettoyage des noms de colonnes pour correspondre à votre fichier
        df.columns = df.columns.str.strip()
        
        # Mapping spécifique à votre fichier (Gestion de l'accent sur Qté)
        mapping = {
            'Qté': 'Qte',
            'Nom': 'Nom',
            'Secteur': 'Secteur',
            'PRU': 'PRU',
            'Div': 'Div',
            'Cours': 'Cours'
        }
        df = df.rename(columns=mapping)
        
        # On ne garde que les colonnes utiles pour recalculer proprement
        cols_needed = ['Nom', 'Qte', 'PRU', 'Secteur', 'Div', 'Cours']
        df = df[cols_needed]

        # Conversion numérique (nettoyage des virgules et symboles)
        for col in ['Qte', 'PRU', 'Div', 'Cours']:
            df[col] = df[col].astype(str).str.replace(',', '.').str.replace('€', '').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df.dropna(subset=['Nom'])
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        return None

df = load_data()

# ==========================================
# 2. CALCULS PROPRES (Ignore les #VALUE! de Sheets)
# ==========================================
if df is not None:
    df['Val. Initiale'] = df['Qte'] * df['PRU']
    df['Val. Actuelle'] = df['Qte'] * df['Cours']
    df['Plus-Value €'] = df['Val. Actuelle'] - df['Val. Initiale']
    df['Plus-Value %'] = (df['Plus-Value €'] / df['Val. Initiale']) * 100
    df['Div. Totaux'] = df['Qte'] * df['Div']

    # --- INTERFACE ---
    st.title("🚀 Mon Portefeuille PEA")

    # KPI
    t_inv = df['Val. Initiale'].sum()
    t_act = df['Val. Actuelle'].sum()
    pv_totale = t_act - t_inv
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Investi", f"{t_inv:,.2f} €")
    c2.metric("Valeur Actuelle", f"{t_act:,.2f} €", f"{pv_totale:+.2f} €")
    c3.metric("Performance", f"{(pv_totale/t_inv*100):+.2f} %")

    # Graphiques
    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(px.pie(df, values='Val. Actuelle', names='Nom', title="Poids des lignes", hole=0.4), use_container_width=True)
    with g2:
        st.plotly_chart(px.bar(df, x='Nom', y='Plus-Value %', color='Plus-Value %', title="Performance par Action (in %)"), use_container_width=True)

    # Tableau détaillé
    st.subheader("📋 Analyse détaillée")
    st.dataframe(df.style.format({
        "Cours": "{:.2f} €", "PRU": "{:.2f} €", "Val. Actuelle": "{:.2f} €", 
        "Plus-Value €": "{:+.2f} €", "Plus-Value %": "{:+.2f} %"
    }), use_container_width=True, hide_index=True)
else:
    st.warning("En attente du lien Google Sheets valide...")
