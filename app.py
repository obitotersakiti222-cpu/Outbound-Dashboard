import streamlit as st
import plotly.express as px
import pandas as pd
from src.data_loader import load_data
from streamlit_option_menu import option_menu
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & CSS ---
st.set_page_config(
    page_title="Outbound Command Center",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# AUTO REFRESH (4 Menit)
count = st_autorefresh(interval=240 * 1000, key="data_refresh")

# Custom CSS
st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 2rem;}
        div[data-testid="stMetric"] {
            background-color: #262730;
            border: 1px solid #41444d;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        }
        div[data-testid="stMetricValue"] {
            font-size: 26px !important;
            color: #ffffff !important;
        }
        div[data-testid="stMetricLabel"] {
            color: #b0b0b0 !important;
            font-size: 14px !important;
        }
        div.stButton > button {
            width: 100%;
            border-radius: 5px;
            border: 1px solid #444;
        }
    </style>
""", unsafe_allow_html=True)

# Link Google Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTo3xmLlgCtryi4V1Aw9ZwjdWohQSR-x6d4MyGafPD6GJzTiipu1I0MkFQFY5Cvv-rL3eaECAS874vq/pub?gid=0&single=true&output=csv"

# --- 2. LOAD DATA ---
with st.spinner("🔄 Syncing Warehouse Data..."):
    df_raw = load_data(SHEET_URL)

if df_raw.empty:
    st.error("❌ Data Source Error. Check Connection.")
    st.stop()

df = df_raw.copy()

# --- 3. SIDEBAR MENU ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2821/2821854.png", width=50)
    st.markdown("### **Outbound Dashboard**")
    
    selected = option_menu(
        menu_title=None,
        options=["Outbound Overview", "Packing Ops", "Loading Ops"], 
        icons=["speedometer2", "box-seam", "truck"],
        menu_icon="cast", 
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "orange", "font-size": "18px"}, 
            "nav-link": {"font-size": "14px", "text-align": "left", "margin":"0px", "--hover-color": "#333"},
            "nav-link-selected": {"background-color": "#2E86C1"},
        }
    )
    
    st.divider()

    with st.expander("🎛️ Filter Data", expanded=True):
        min_date = df['Create Date'].min()
        max_date = df['Create Date'].max()
        if pd.isna(min_date):
            date_range = (None, None)
        else:
            date_range = st.date_input("📅 Date Range", value=(min_date, max_date))

        cust_list = ["All"] + sorted(df['TP Full Name'].astype(str).unique().tolist())
        sel_cust = st.selectbox("👥 Customer", cust_list)
        
        stat_list = ["All"] + sorted(df['Job_Status'].unique().tolist())
        sel_stat = st.selectbox("📌 Status", stat_list)

    st.divider()
    if st.button("🔄 Refresh Data", type="primary", use_container_width=True):
        st.cache_data.clear() 
        st.rerun() 
    st.caption(f"Last Sync: {pd.Timestamp.now().strftime('%H:%M:%S')} (Auto: 4m)")

# APPLY FILTER
if date_range[0] is not None and len(date_range) == 2:
    df = df[(df['Create Date'].dt.date >= date_range[0]) & (df['Create Date'].dt.date <= date_range[1])]
if sel_cust != "All":
    df = df[df['TP Full Name'] == sel_cust]
if sel_stat != "All":
    df = df[df['Job_Status'] == sel_stat]


# --- 4. MAIN CONTENT ---

# ==========================================
# HALAMAN 1: OUTBOUND OVERVIEW
# ==========================================
if selected == "Outbound Overview":
    col_head1, col_head2 = st.columns([1, 20])
    with col_head1: st.title("🚀")
    with col_head2: st.title("Outbound Overview")

    # --- KPI UTAMA ---
    total_unique_job = df['JOB Num'].nunique()
    total_unique_do = df['Order No'].nunique() 
    
    # KPI RATE (Tetap Strict: Job dianggap selesai jika 100% itemnya complete)
    done_load = ['LOADING DONE', 'COMPLETE']
    jobs_complete_strict = df.groupby('JOB Num')['Status_Loading'].apply(lambda x: x.isin(done_load).all())
    unique_job_done = jobs_complete_strict.sum()
    
    rate = (unique_job_done/total_unique_job*100) if total_unique_job else 0
    total_weight = df['Total Weight'].sum()/1000
    vol_col = 'Total M3' if 'Total M3' in df.columns else 'volume'
    total_vol_all = df[vol_col].sum() if vol_col in df.columns else 0
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Jobs / DO", f"{total_unique_job:,} / {total_unique_do:,}")
    k2.metric("Job Completion Rate", f"{rate:.1f}%")
    k3.metric("Total Tonnage", f"{total_weight:,.1f} Ton")
    k4.metric("Total Volume", f"{total_vol_all:,.1f} m³")

    st.markdown("---")
    
    # --- BREAKDOWN OPERASIONAL (FULL ROW SPLIT) ---
    st.markdown("### 🛠️ Operational Status Breakdown")
    
    if 'view_mode' not in st.session_state:
        st.session_state.view_mode = 'All'

    done_pack = ['PACKING DONE', 'COMPLETE']
    # done_load sudah didefinisikan di atas

    # 1. GREEN (LOADED ITEMS)
    # Semua baris yang statusnya Loading Done masuk ke sini.
    df_green = df[df['Status_Loading'].isin(done_load)]
    
    # 2. PURPLE (OVERLOAD ITEMS)
    # Semua baris yang statusnya Overload masuk ke sini.
    df_purple = df[df['Status_Loading'].str.contains('OVERLOAD', na=False)]
    
    # 3. SISA BARANG (PENDING)
    # Ambil baris yang BUKAN Green dan BUKAN Purple.
    # Ini adalah barang-barang yang masih di lantai gudang.
    processed_indices = df_green.index.union(df_purple.index)
    df_pending_rows = df[~df.index.isin(processed_indices)]
    
    # 4. KATEGORISASI SISA BARANG (Blue / Yellow / Red)
    # Logic: Cek apakah JOB ID barang tersebut sudah ada di daftar Green (Sudah mulai loading)?
    started_jobs = set(df_green['JOB Num'].unique())

    # BLUE (IN PROGRESS - SISA)
    # Barang pending, TAPI Job-nya sudah dimulai (ada item lain yg sudah loaded).
    df_blue = df_pending_rows[df_pending_rows['JOB Num'].isin(started_jobs)]
    
    # NOT STARTED
    # Barang pending, dan Job-nya belum dimulai sama sekali (tidak ada item loaded).
    df_not_started = df_pending_rows[~df_pending_rows['JOB Num'].isin(started_jobs)]
    
    # Split Not Started jadi Yellow (Ready) & Red (Belum Packing)
    df_yellow = df_not_started[df_not_started['Status_Packing'].isin(done_pack)]
    df_red = df_not_started[~df_not_started['Status_Packing'].isin(done_pack)]

    # --- HITUNG STATISTIK ---
    def get_stats(df_subset):
        if df_subset.empty: return 0, 0
        return df_subset['JOB Num'].nunique(), df_subset['Order No'].nunique()

    gj, gd = get_stats(df_green)
    bj, bd = get_stats(df_blue)
    pj, pd_val = get_stats(df_purple)
    yj, yd = get_stats(df_yellow)
    rj, rd = get_stats(df_red)
    
    # LAYOUT KARTU
    c_hero, c_b, c_p, c_y, c_r = st.columns([1.5, 1, 1, 1, 1])
    
    with c_hero:
        # Judul diganti sedikit agar lebih akurat: "ITEMS LOADED" atau tetap "LOADING COMPLETE" tapi bermakna items.
        # Kita pertahankan LOADING COMPLETE sesuai request, tapi user paham ini row-based.
        st.markdown(f"""
        <div style="background-color: #262730; border: 2px solid #27AE60; border-radius: 10px; padding: 15px; text-align: center; box-shadow: 0 0 15px rgba(39, 174, 96, 0.4);">
            <p style="color: #27AE60; font-size: 16px; margin-bottom: 0px; font-weight: bold;">🟢 LOADING COMPLETE</p>
            <p style="color: #ffffff; font-size: 48px; font-weight: bold; margin: 0; line-height: 1.2;">{gj:,} <span style="font-size: 20px; color: #b0b0b0;">Jobs</span></p>
            <p style="color: #b0b0b0; font-size: 16px; margin-top: 5px;">( {gd:,} DO Selesai )</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📂 Data Complete", key="btn_green", use_container_width=True):
            st.session_state.view_mode = 'Green'

    with c_b:
        # Kartu Biru sekarang Murni Sisa Barang Pending dari Job yg sedang jalan
        st.metric("🔵 In Progress", f"{bj:,} Jobs", delta=f"{bd:,} DO", help="Sisa barang yang belum naik truk (Job aktif)")
        if st.button("🏃 Sisa Loading", key="btn_blue", use_container_width=True):
            st.session_state.view_mode = 'Blue'

    with c_p:
        st.metric("🟣 OVERLOAD", f"{pj:,} Jobs", delta=f"{pd_val:,} DO", delta_color="inverse")
        if st.button("⚠️ Cek Overload", key="btn_purple", use_container_width=True):
            st.session_state.view_mode = 'Purple'
            
    with c_y:
        st.metric("🟡 Ready to Load", f"{yj:,} Jobs", delta=f"{yd:,} DO")
        if st.button("🚛 Cek Staging", key="btn_yellow", use_container_width=True):
            st.session_state.view_mode = 'Yellow'

    with c_r:
        st.metric("🔴 Belum Packing", f"{rj:,} Jobs", delta=f"{rd:,} DO")
        if st.button("🔍 Cek Pending", key="btn_red", use_container_width=True):
            st.session_state.view_mode = 'Red'

    st.divider()

    # --- TABEL DETAIL ---
    st.subheader(f"📋 Detail Data: {st.session_state.view_mode} List")
    
    base_cols = ['JOB Num', 'Order No', 'Prod Code', 'TP Full Name']
    
    if st.session_state.view_mode == 'Green':
        df_display = df_green
        specific_cols = ['Status_Loading', 'DP Qty', 'Qty_Loading', 'Total M3', 'Total Weight']
        st.success("Menampilkan ITEM yang SUDAH DIMUAT (Loaded).")
        
    elif st.session_state.view_mode == 'Blue':
        df_display = df_blue
        # Tampilkan Qty Loading (biasanya 0 karena ini sisa pending) dan DP Qty
        specific_cols = ['Status_Loading', 'DP Qty', 'Qty_Loading', 'Total M3']
        st.info("Menampilkan SISA BARANG PENDING (Dari Job yang sedang loading).")

    elif st.session_state.view_mode == 'Purple':
        df_display = df_purple
        specific_cols = ['Status_Loading', 'DP Qty', 'Qty_Loading', 'Total M3']
        st.warning("Menampilkan ITEM OVERLOAD (Tidak Muat).")
        
    elif st.session_state.view_mode == 'Yellow':
        df_display = df_yellow
        specific_cols = ['Status_Packing', 'DP Qty', 'Qty_Packing', 'Total M3']
        st.warning("Menampilkan ITEM READY TO LOAD (Job Belum Mulai).")
        
    elif st.session_state.view_mode == 'Red':
        df_display = df_red
        specific_cols = ['Status_Packing', 'DP Qty', 'Total M3']
        st.error("Menampilkan ITEM BELUM PACKING.")
        
    else:
        df_display = df
        specific_cols = ['Status_Packing', 'Status_Loading', 'DP Qty', 'Qty_Loading', 'Total M3']
        st.caption("Menampilkan semua data.")

    final_cols = base_cols + specific_cols
    existing_cols = [c for c in final_cols if c in df_display.columns]

    st.dataframe(
        df_display[existing_cols],
        use_container_width=True, hide_index=True, height=400
    )

    st.divider()
    
    # CHART BAWAH
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📊 Flow Harian")
        daily_ops = df.groupby(df['Tgl_loading'].dt.date)[['Qty_Packing', 'Qty_Loading']].sum().reset_index()
        daily_melt = daily_ops.melt(id_vars='Tgl_loading', var_name='Activity', value_name='Qty')
        fig_flow = px.bar(daily_melt, x='Tgl_loading', y='Qty', color='Activity', barmode='group', template='plotly_white', height=350)
        fig_flow.update_layout(font=dict(color="white"), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_flow, use_container_width=True)
    with c2:
        st.subheader("🍩 Status")
        fig_pie = px.pie(df, names='Job_Status', color='Job_Status', hole=0.6, height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# HALAMAN 2 & 3
# ==========================================
elif selected == "Packing Ops":
    col_head1, col_head2 = st.columns([1, 20])
    with col_head1: st.title("📦")
    with col_head2: st.title("Packing Operations")
    total_pack_qty = df['Qty_Packing'].sum()
    total_volume = df['volume'].sum() if 'volume' in df.columns else 0
    col_kpi1, col_kpi2 = st.columns(2)
    with col_kpi1: st.metric("Total Qty Packed", f"{total_pack_qty:,.0f} Pcs")
    with col_kpi2: st.metric("Total Volume Processed", f"{total_volume:,.2f} m³")
    st.divider()
    if 'volume' in df.columns:
        st.subheader("Top Products by Volume (m³)")
        top_vol = df.groupby('Prod Desc')['volume'].sum().nlargest(10).reset_index()
        fig_pack = px.bar(top_vol, x='volume', y='Prod Desc', orientation='h', text_auto='.2f', color='volume', template='plotly_dark')
        fig_pack.update_layout(yaxis={'categoryorder':'total ascending'}, height=500, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pack, use_container_width=True)

elif selected == "Loading Ops":
    col_head1, col_head2 = st.columns([1, 20])
    with col_head1: st.title("🚛")
    with col_head2: st.title("Loading Operations")
    total_load_qty = df['Qty_Loading'].sum()
    jobs_loaded = len(df[df['Status_Loading'].isin(['COMPLETE', 'LOADING DONE'])])
    l1, l2 = st.columns(2)
    l1.metric("Total Qty Loaded", f"{total_load_qty:,.0f} Pcs")
    l2.metric("Jobs Loading Complete", f"{jobs_loaded:,} Jobs")
    st.divider()
    df_loaded = df[df['Status_Loading'].isin(['COMPLETE', 'LOADING DONE'])].copy()
    if not df_loaded.empty:
        col_viz, col_data = st.columns(2)
        with col_viz:
            st.subheader("Top Customers (Loaded)")
            top_cust_load = df_loaded['TP Full Name'].value_counts().head(10).reset_index()
            fig_load = px.bar(top_cust_load, x='count', y='TP Full Name', orientation='h', template='plotly_dark')
            fig_load.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_load, use_container_width=True)
        with col_data:
            st.subheader("Loading Manifest")
            st.dataframe(df_loaded[['JOB Num', 'TP Full Name', 'Tgl_loading', 'Qty_Loading']], use_container_width=True, hide_index=True, height=400)