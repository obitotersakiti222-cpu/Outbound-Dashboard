import pandas as pd
import streamlit as st
import numpy as np

def clean_data(df):
    # 1. BERSIHKAN NAMA KOLOM
    df.columns = df.columns.str.replace(r'\s+', ' ', regex=True).str.strip()

    # 2. FORMAT TANGGAL
    date_cols = ['Create Date', 'Tgl_loading', 'Tgl_Packing']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=False, errors='coerce')

    # 3. FORMAT ANGKA (TAMBAHKAN 'DP Qty' DI SINI)
    num_cols = ['Qty_Packing', 'Qty_Loading', 'DP Qty', 'volume', 'Total M3', 'Weight', 'Total Weight']
    
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = df[col].str.lower().str.replace('kg', '').str.replace('m3', '')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Jaga-jaga jika kolom tidak ada di Excel, buat kolom 0
        if col not in df.columns:
            df[col] = 0

    # 4. FORMAT STATUS
    status_cols = ['Status_Packing', 'Status_Loading']
    for col in status_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
            df[col] = df[col].replace({'NAN': None, 'NAT': None, 'NULL': None, '0': None, 'nan': None})

    # 5. LOGIC JOB STATUS
    def determine_status(row):
        pack = str(row.get('Status_Packing', ''))
        load = str(row.get('Status_Loading', ''))
        
        if 'OVERLOAD' in load:
            return 'Overload'
        
        pack_finished = pack in ['COMPLETE', 'PACKING DONE']
        load_finished = load in ['COMPLETE', 'LOADING DONE']
        
        if pack_finished and load_finished:
            return 'Complete'
        else:
            return 'In Progress'

    df['Job_Status'] = df.apply(determine_status, axis=1)

    return df