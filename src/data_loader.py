import streamlit as st
import pandas as pd
from src.utils import clean_data

# TAMBAHKAN 'ttl=240' (Time To Live = 300 detik / 5 menit)
@st.cache_data(ttl=300) 
def load_data(url):
    try:
        df = pd.read_csv(url)
        df = clean_data(df)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()