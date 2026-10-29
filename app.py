import streamlit as st
import pandas as pd
import geopandas as gpd
import difflib
import plotly.express as px
from machineback import running
import warnings

st.set_page_config(
    page_title="Dashboard Analisis Agroklimat Lada", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="🌱"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    header[data-testid="stHeader"] {
        display: none !important;
    }

    .block-container { 
        padding-top: 2.5rem !important; 
        padding-bottom: 2.5rem !important; 
    }
    
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    
    .hero-tag {
        display: inline-flex;
        align-items: center;
        background: #F0FDF4;
        color: #166534;
        border: 1px solid #BBF7D0;
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.02em;
        margin-bottom: 6px;
        line-height: 1.3;
        padding-top: 4px;
    }
    .hero-subtitle {
        color: #64748B;
        font-size: 0.95rem;
        font-weight: 500;
        margin-bottom: 1.5rem;
    }

    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px -1px rgba(0, 0, 0, 0.01);
        transition: all 0.25s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        border-color: #CBD5E1;
    }
    .metric-accent {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }
    .accent-blue { background: #3B82F6; }
    .accent-green { background: #10B981; }
    .accent-purple { background: #8B5CF6; }
    .accent-amber { background: #F59E0B; }

    .metric-title { 
        color: #64748B; 
        font-size: 0.72rem; 
        font-weight: 700; 
        text-transform: uppercase; 
        letter-spacing: 0.06em; 
    }
    .metric-value { 
        color: #0F172A; 
        font-size: 1.85rem; 
        font-weight: 800; 
        margin-top: 6px; 
        line-height: 1;
    }

    .stTabs [data-baseweb="tab-list"] { 
        gap: 12px; 
        border-bottom: 1px solid #E2E8F0; 
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 46px;
        background-color: #F8FAFC;
        padding: 8px 20px;
        color: #64748B;
        font-weight: 600;
        font-size: 0.95rem;
        border-radius: 8px 8px 0 0;
        border: 1px solid #E2E8F0;
        border-bottom: none;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        color: #1E40AF !important;
        font-weight: 700 !important;
        background-color: #FFFFFF !important;
        border-top: 3px solid #2563EB !important;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.02);
    }

    .active-badge {
        display: inline-block;
        background-color: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 6px;
        margin-top: 4px;
    }

    .cluster-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 10px;
        transition: all 0.2s ease;
    }
    .cluster-card:hover {
        border-color: #CBD5E1;
        background-color: #F8FAFC;
    }
    
    .section-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.01em;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_data
def prepare_map_data(df):
    SHAPEFILE_PATH = "data/gadm41_IDN_2.shp"
    try:
        gdf = gpd.read_file(SHAPEFILE_PATH)
    except Exception:
        return None 
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        gdf['lat'] = gdf.geometry.centroid.y
        gdf['lon'] = gdf.geometry.centroid.x

    df_map = df.copy()
    df_map['Nama_Clean'] = df_map['Nama Wilayah'].astype(str)
    df_map['Nama_Clean'] = df_map['Nama_Clean'].str.replace('Kab. ', '', regex=False)\
                                               .str.replace('Kabupaten ', '', regex=False)\
                                               .str.replace('Kota ', '', regex=False)\
                                               .str.strip()
    
    gadm_names = gdf['NAME_2'].unique().tolist()
    kamus_manual = {
        "Aceh Pidie": "Pidie", "Mahakam Hulu": "Kutai Barat", "Malaka": "Belu",
        "Mamuju Utara/Pasangkayu": "Mamuju Utara", "Mempawah": "Pontianak",
        "Pangandaran": "Ciamis", "Penukal Abab Lematang Ilir": "Muara Enim",
        "Pulau Taliabu": "Kepulauan Sula", "Medan": "Kota Medan"
    }
    
    def auto_match_nama(nama_excel):
        if nama_excel in kamus_manual: return kamus_manual[nama_excel]
        if nama_excel in gadm_names: return nama_excel
        kemiripan = difflib.get_close_matches(nama_excel, gadm_names, n=1, cutoff=0.7)
        return kemiripan[0] if kemiripan else nama_excel
        
    df_map['Nama_Matched'] = df_map['Nama_Clean'].apply(auto_match_nama)
    gdf_merged = gdf.merge(df_map, left_on='NAME_2', right_on='Nama_Matched', how='left')
    gdf_merged['Klaster'] = gdf_merged['Klaster'].fillna('Tidak Ada Data')
    
    gdf_merged['geometry'] = gdf_merged['geometry'].simplify(tolerance=0.01, preserve_topology=True)
    gdf_merged = gdf_merged.set_index('NAME_2')
    gdf_merged.index.name = 'Nama Wilayah'
    return gdf_merged

@st.cache_data
def load_panel_data(path):
    try:
        return pd.read_excel(path, sheet_name='Data Panel')
    except Exception:
        return pd.DataFrame()

FILE_DATASET = "data/Data_Gabungan_Lada_Cuaca_Full_Used.xlsx"
color_map = {
    'Klaster 1': '#E5734A', 
    'Klaster 2': '#5D9CE2', 
    'Klaster 3': '#47B376', 
    'Klaster 4': '#9B51E0', 
    'Klaster 5': '#F2994A', 
    'Tidak Ada Data': '#E2E8F0'
}

available_options = [
    'Suhu Rata-rata (°C)', 'Curah Hujan Total (mm)', 'Kelembapan Rata-rata (%)', 
    'Kecepatan Angin Rata-rata', 'Suhu Minimum (°C)', 'Suhu Maksimum (°C)', 
    'Evapotranspirasi Total (mm)', 'Kecepatan Angin Maksimum', 'Luas Panen (ha)', 
    'Produksi (ton)', 'Produktivitas (kg/ha)'
]

df, cluster_metrics, reg_data, gdf_merged = None, None, None, None

st.markdown("""
    <div style="margin-bottom: 1.2rem;">
        <div class="hero-title">Dashboard Analisis Agroklimat Pertanian Lada</div>
        <div class="hero-subtitle">Pemetaan Klaster Wilayah & Evaluasi Model Regresi Data Panel Komoditas Lada Indonesia</div>
    </div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📍 Clustering Analysis", "📈 Panel Regression", "ℹ️ About Dataset"])

# ========================================================
# TAB 1: CLUSTERING
# ========================================================
with tab1:
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    
    if 'selected_vars' not in st.session_state:
        st.session_state.selected_vars = ['Suhu Rata-rata (°C)', 'Produksi (ton)', 'Luas Panen (ha)']
    if 'k_num' not in st.session_state:
        st.session_state.k_num = 3

    curr_vars = st.session_state.selected_vars
    curr_k = st.session_state.k_num

    try:
        with st.spinner('Memuat Data & Memproses Model Clustering...'):
            df, cluster_metrics, reg_data = running(FILE_DATASET, selected_cluster_features=curr_vars, k_clusters=curr_k)
            
            map_display_vars = [
                'Luas Panen (ha)', 'Produksi (ton)', 'Produktivitas (kg/ha)', 
                'Suhu Rata-rata (°C)', 'Kelembapan Rata-rata (%)', 'Curah Hujan Total (mm)'
            ]
            for var in map_display_vars:
                matched_cols = [c for c in df.columns if var in c]
                if matched_cols:
                    df[f'Rata-rata {var}'] = df[matched_cols].mean(axis=1)
                else:
                    df[f'Rata-rata {var}'] = 0.0 
                    
            gdf_merged = prepare_map_data(df)
            
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-accent accent-blue"></div>
                <div class="metric-title">TOTAL WILAYAH</div>
                <div class="metric-value">{len(df):,}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-accent accent-green"></div>
                <div class="metric-title">JUMLAH CLUSTER</div>
                <div class="metric-value">{curr_k}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-accent accent-purple"></div>
                <div class="metric-title">SILHOUETTE SCORE</div>
                <div class="metric-value">{cluster_metrics['silhouette']:.3f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-accent accent-amber"></div>
                <div class="metric-title">DAVIES-BOULDIN SCORE</div>
                <div class="metric-value">{cluster_metrics['davies_bouldin']:.3f}</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        col_map, col_stats = st.columns([2.6, 1.1])

        with col_map:
            st.markdown("<div class='section-title'>VISUALISASI PETA KLASTER WILAYAH</div>", unsafe_allow_html=True)
            st.caption(f"Pemetaan K-Means berdasarkan {len(curr_vars)} indikator agroklimat & produksi terpilih.")
            
            if gdf_merged is not None:
                fig_map = px.choropleth(
                    gdf_merged,
                    geojson=gdf_merged.geometry,
                    locations=gdf_merged.index,
                    color='Klaster',
                    color_discrete_map=color_map,
                    category_orders={"Klaster": ["Klaster 1", "Klaster 2", "Klaster 3", "Klaster 4", "Klaster 5"]},
                    hover_name=gdf_merged.index,
                    hover_data={
                        'Nama Wilayah': False, 
                        'Klaster': False, 
                        'lat': ':.4f',
                        'lon': ':.4f',
                        'Rata-rata Luas Panen (ha)': ':.2f',
                        'Rata-rata Produksi (ton)': ':.2f', 
                        'Rata-rata Produktivitas (kg/ha)': ':.2f',
                        'Rata-rata Suhu Rata-rata (°C)': ':.2f', 
                        'Rata-rata Kelembapan Rata-rata (%)': ':.2f', 
                        'Rata-rata Curah Hujan Total (mm)': ':.2f'
                    },
                    labels={
                        'lat': 'Latitude (°)', 
                        'lon': 'Longitude (°)'
                    }
                )
                
                fig_map.update_geos(
                    fitbounds="locations",
                    visible=False,
                    bgcolor='rgba(0,0,0,0)'
                )

                fig_map.add_annotation(
                    text="<b>▲<br>U</b>",
                    xref="paper", yref="paper",
                    x=0.02, y=0.96,
                    showarrow=False,
                    font=dict(size=13, color="#0F172A"),
                    align="center",
                    bgcolor="rgba(255, 255, 255, 0.9)",
                    bordercolor="#CBD5E1",
                    borderwidth=1,
                    borderpad=5
                )

                fig_map.update_layout(
                    height=520,
                    plot_bgcolor='rgba(0,0,0,0)', 
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=0, r=0, t=10, b=0),
                    legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )

                for trace in fig_map.data:
                    if trace.hovertemplate: 
                        trace.hovertemplate = trace.hovertemplate.replace('index=%{location}<br>', '')
                    if trace.name == 'Tidak Ada Data':
                        trace.showlegend = False

                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.error("⚠️ File shapefile `gadm41_IDN_2.shp` tidak ditemukan di folder `data/`.")

        with col_stats:
            st.markdown("<div class='section-title'>DISTRIBUSI DATA CLUSTER</div>", unsafe_allow_html=True)
            st.caption("Proporsi anggota wilayah per klaster.")
            
            cluster_list = [f"Klaster {i+1}" for i in range(curr_k)]
            cluster_colors = ['#E5734A', '#5D9CE2', '#47B376', '#9B51E0', '#F2994A']
            
            for idx, klaster in enumerate(cluster_list):
                hex_color = cluster_colors[idx % len(cluster_colors)]
                subset = df[df['Klaster'] == klaster]
                count = len(subset)
                pct = (count / len(df)) * 100 if len(df) > 0 else 0
                
                st.markdown(f"""
                <div class="cluster-card">
                    <div style="color: {hex_color}; font-weight: 700; font-size: 0.95rem; margin-bottom: 6px;">
                        ■ {klaster}
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem;">
                        <span style="color: #64748B;">Jumlah Wilayah</span>
                        <span style="color: #0F172A; font-weight: 700;">{count} <span style="color: #94A3B8; font-weight: 500;">({pct:.1f}%)</span></span>
                    </div>
                    <div style="background-color: #F1F5F9; border-radius: 4px; height: 6px; width: 100%; margin-top: 8px; overflow: hidden;">
                        <div style="background-color: {hex_color}; height: 100%; width: {pct}%;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<hr style='margin-top: 15px; margin-bottom: 25px; border-color: #E2E8F0;'>", unsafe_allow_html=True)

        with st.form(key="clustering_form", border=True):
            st.markdown("<div style='font-weight: 700; font-size: 1.05rem; color: #0F172A;'>🎛️ Clustering Filter Control</div>", unsafe_allow_html=True)
            st.caption("Ubah indikator di bawah ini lalu klik 'Terapkan Filter' untuk mengkalibrasi ulang algoritma K-Means.")
            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
            
            col_vars, col_k = st.columns([3.5, 1])

            with col_vars:
                input_vars = st.pills(
                    "Pilih Variabel Indikator Clustering:",
                    options=available_options,
                    default=st.session_state.selected_vars,
                    selection_mode="multi"
                )

            with col_k:
                input_k = st.segmented_control(
                    "Jumlah Cluster (k):",
                    options=[2, 3, 4, 5],
                    default=st.session_state.k_num
                )

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            
            col_btn, col_badge = st.columns([1.2, 3])
            
            with col_btn:
                submit_filter = st.form_submit_button("Terapkan Filter 🚀", type="primary", use_container_width=True)
            
            with col_badge:
                if curr_vars:
                    st.markdown("**Variabel Aktif:** " + " ".join([f"<span class='active-badge'>✓ {v}</span>" for v in curr_vars]), unsafe_allow_html=True)
            
            if submit_filter:
                if len(input_vars) == 0:
                    st.session_state.selected_vars = ['Curah Hujan Total (mm)']
                else:
                    st.session_state.selected_vars = input_vars
                
                st.session_state.k_num = input_k
                st.rerun()

        # =====================================================================
        #  CLUSTER PROFILING 
        # =====================================================================
        st.markdown("<hr style='margin-top: 30px; margin-bottom: 25px; border-color: #E2E8F0;'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title' style='font-size: 1.15rem;'>📊 Cluster Profiling (Analisis Tren Variabel 2010–2024)</div>", unsafe_allow_html=True)
        st.caption("Visualisasi perbandingan tren historis rata-rata seluruh indikator penelitian antar klaster (2010–2024).")

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("##### 🌾 Komponen Pertanian")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.image("CLUSTER PROFILING/Produksi.png", caption="Tren Produksi (Ton)", use_container_width=True)
        with c2:
            st.image("CLUSTER PROFILING/Luas Panen.png", caption="Tren Luas Panen (Ha)", use_container_width=True)
        with c3:
            st.image("CLUSTER PROFILING/Produktivitas.png", caption="Tren Produktivitas (Kg/Ha)", use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("##### 🌡️ Indikator Suhu Udara")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.image("CLUSTER PROFILING/Suhu Maksimum.png", caption="Tren Suhu Maksimum (°C)", use_container_width=True)
        with c2:
            st.image("CLUSTER PROFILING/Suhu Minimum.png", caption="Tren Suhu Minimum (°C)", use_container_width=True)
        with c3:
            st.image("CLUSTER PROFILING/Suhu Rata - rata.png", caption="Tren Suhu Rata-rata (°C)", use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("##### 💧 Presipitasi & Kelembapan")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.image("CLUSTER PROFILING/Curah Hujan Total.png", caption="Tren Curah Hujan Total (mm)", use_container_width=True)
        with c2:
            st.image("CLUSTER PROFILING/Kelembapan Rata - rata.png", caption="Tren Kelembapan Rata-rata (%)", use_container_width=True)
        with c3:
            st.image("CLUSTER PROFILING/Evapotranspirasi Total.png", caption="Tren Evapotranspirasi Total (mm)", use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("##### 🌪️ Indikator Kecepatan Angin")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.image("CLUSTER PROFILING/Kecepatan Angin Rata - rata.png", caption="Tren Kecepatan Angin Rata-rata (m/s)", use_container_width=True)
        with c2:
            st.image("CLUSTER PROFILING/Kecepatan Angin Maksimum.png", caption="Tren Kecepatan Angin Maksimum (m/s)", use_container_width=True)

    except FileNotFoundError:
        st.error(f"⚠️ File dataset `{FILE_DATASET}` tidak ditemukan. Pastikan lokasi file di folder `data/` sudah benar.")

# ========================================================
# TAB 2: PANEL REGRESSION 
# ========================================================
with tab2:
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title' style='font-size: 1.2rem;'>📈 Hasil Uji Regresi Data Panel</div>", unsafe_allow_html=True)
    st.caption("Evaluasi pengaruh indikator agroklimatologi terhadap komponen pertanian (FEM vs REM via Uji Hausman).")
    st.markdown("<br>", unsafe_allow_html=True)

    if reg_data is not None and not reg_data.empty:
        
        df_display = reg_data.copy()
        
        def tarik_kesimpulan(row):
            if row['Model Terpilih'] == 'FE':
                coef = row['FE Coef']
                pval = row['FE p-Value']
            else:
                coef = row['RE Coef']
                pval = row['RE p-Value']
            
            if pval < 0.05:
                if coef > 0:
                    return "📈 Signifikan Meningkatkan"
                else:
                    return "📉 Signifikan Menurunkan"
            else:
                return "➖ Tidak Signifikan"
                
        df_display['Faktor Mempengaruhi'] = df_display.apply(tarik_kesimpulan, axis=1)
        
        cols = [
            'Independent Var.', 'Dependent Var.', 'Faktor Mempengaruhi', 
            'Model Terpilih', 'Hausman p-Value', 'RE Coef', 'RE p-Value', 'FE Coef', 'FE p-Value'
        ]
        df_display = df_display[cols]
        
        # 1. BAGIAN FILTER INTERAKTIF
        with st.container(border=True):
            st.markdown("**🎛️ Pilih Kombinasi Variabel untuk Dianalisis:**")
            col_dep, col_ind = st.columns(2)
            with col_dep:
                dep_var = st.selectbox(
                    "🎯 Variabel Pertanian (Dependen/Y):",
                    options=['Produksi (ton)', 'Luas Panen (ha)', 'Produktivitas (kg/ha)']
                )
            with col_ind:
                ind_var = st.selectbox(
                    "☁️ Variabel Iklim (Independen/X):",
                    options=[
                        'Curah Hujan Total (mm)', 'Suhu Minimum (°C)', 'Suhu Maksimum (°C)',
                        'Suhu Rata-rata (°C)', 'Kelembapan Rata-rata (%)', 
                        'Kecepatan Angin Rata-rata', 'Kecepatan Angin Maksimum', 'Evapotranspirasi Total (mm)'
                    ]
                )

        selected_result = df_display[(df_display['Dependent Var.'] == dep_var) & (df_display['Independent Var.'] == ind_var)]
        
        if not selected_result.empty:
            res = selected_result.iloc[0]
            kesimpulan = res['Faktor Mempengaruhi']
            model_terpilih = res['Model Terpilih']
            
            def safe_format(val):
                try:
                    return f"{float(val):.4f}"
                except (ValueError, TypeError):
                    return str(val)
            
            if model_terpilih == 'FE':
                coef_val = safe_format(res['FE Coef'])
                pval_val = safe_format(res['FE p-Value'])
                model_name = "Fixed Effects Model (FEM)"
                model_color = "#EFF6FF"
                model_text = "#1D4ED8"
            else:
                coef_val = safe_format(res['RE Coef'])
                pval_val = safe_format(res['RE p-Value'])
                model_name = "Random Effects Model (REM)"
                model_color = "#FEF3C7"
                model_text = "#D97706"

            hausman_p = safe_format(res['Hausman p-Value'])

            if 'Meningkatkan' in kesimpulan:
                bg_color = "#ECFDF5"
                border_color = "#10B981"
            elif 'Menurunkan' in kesimpulan:
                bg_color = "#FEF2F2"
                border_color = "#EF4444"
            else:
                bg_color = "#F8FAFC"
                border_color = "#CBD5E1"

            st.markdown(f"""
            <div style="background-color: {bg_color}; border-left: 5px solid {border_color}; padding: 20px; border-radius: 8px; margin-top: 15px; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                <div style="font-size: 0.9rem; color: #64748B; font-weight: 600; text-transform: uppercase;">Kesimpulan Analisis Data Panel</div>
                <div style="font-size: 1.25rem; color: #0F172A; font-weight: 700; margin-top: 5px; margin-bottom: 10px;">
                    {ind_var} <span style="color: {border_color};">{kesimpulan.split(' ', 1)[1] if 'Signifikan' in kesimpulan else 'Tidak Berpengaruh Signifikan Terhadap'}</span> {dep_var}
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 15px; font-size: 0.85rem; color: #475569;">
                    <div><b>Model Terbaik:</b> <span style="background-color: {model_color}; color: {model_text}; padding: 2px 8px; border-radius: 12px; font-weight: bold;">{model_name}</span></div>
                    <div><b>Koefisien:</b> {coef_val}</div>
                    <div><b>p-Value Model:</b> {pval_val}</div>
                    <div><b>Uji Hausman (p-Val):</b> {hausman_p}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        df_panel = load_panel_data(FILE_DATASET)
        if not df_panel.empty and ind_var in df_panel.columns and dep_var in df_panel.columns:
            st.markdown(f"**Visualisasi Korelasi: {ind_var} vs {dep_var}**")
            
            df_plot = df_panel[(df_panel[ind_var] > 0) & (df_panel[dep_var] > 0)].copy()
            df_plot['Var_Bin'] = pd.cut(df_plot[ind_var], bins=12)
            df_binned = df_plot.groupby('Var_Bin', observed=False).agg({
                ind_var: 'mean', dep_var: 'mean'
            }).dropna().reset_index()

            fig_scatter = px.scatter(
                df_binned, x=ind_var, y=dep_var, 
                trendline="ols", template='plotly_white'
            )
            
            fig_scatter.update_traces(
                marker=dict(size=10, color='#3B82F6', line=dict(width=1, color='#1E40AF')),
                line=dict(color='#1E293B', width=2.5)
            )
            
            suffix = " mm" if "mm" in ind_var else " °C" if "°C" in ind_var else " %" if "%" in ind_var else ""

            fig_scatter.update_layout(
                plot_bgcolor='#FFFFFF', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(showgrid=True, gridcolor='#F1F5F9', title=ind_var, ticksuffix=suffix),
                yaxis=dict(showgrid=True, gridcolor='#F1F5F9', title=f"Rata-rata {dep_var}")
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.warning("⚠️ Kombinasi variabel tidak ditemukan pada sheet data panel atau data tidak cukup.")

        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        with st.expander("📊 Lihat Tabel Lengkap Seluruh Kombinasi Uji Regresi"):
            def style_table(row):
                style = [''] * len(row)
                idx_model = df_display.columns.get_loc('Model Terpilih')
                if row['Model Terpilih'] == 'FE':
                    style[idx_model] = 'color: #1D4ED8; font-weight: bold; background-color: #EFF6FF;'
                elif row['Model Terpilih'] == 'RE':
                    style[idx_model] = 'color: #D97706; font-weight: bold; background-color: #FEF3C7;'
                    
                idx_kesimpulan = df_display.columns.get_loc('Faktor Mempengaruhi')
                if 'Meningkatkan' in row['Faktor Mempengaruhi']:
                    style[idx_kesimpulan] = 'color: #059669; font-weight: bold;' 
                elif 'Menurunkan' in row['Faktor Mempengaruhi']:
                    style[idx_kesimpulan] = 'color: #DC2626; font-weight: bold;' 
                else:
                    style[idx_kesimpulan] = 'color: #9CA3AF;' 
                return style

            st.dataframe(
                df_display.style.apply(style_table, axis=1),
                use_container_width=True,
                hide_index=True,
                height=350
            )
            
    else:
        st.info("⚠️ Data belum dimuat. Silakan periksa dataset Anda di Tab Clustering.")


# ========================================================
# TAB 3: ABOUT
# ========================================================
with tab3:
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title' style='font-size: 1.2rem;'>ℹ️ Metadata & Metodologi Penelitian</div>", unsafe_allow_html=True)
    st.markdown("""
    Sistem ini memfasilitasi analisis spasial data panel serta klasterisasi wilayah berdasarkan parameter agroklimatologi dan hasil produksi komoditas lada di Indonesia.
    """)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_ds1, col_ds2 = st.columns(2)
    with col_ds1:
        with st.container(border=True):
            st.markdown("**📌 Struktur & Periode Data**")
            st.markdown("- **Rentang Waktu:** 2010–2024 (15 Tahun)")
            st.markdown("- **Tingkat Wilayah:** Kabupaten/Kota di Indonesia")
            st.markdown("- **Sumber Data:** BDSP & Open-Meteo API")
    with col_ds2:
        with st.container(border=True):
            st.markdown("**⚙️ Metode Ekonometrika & Machine Learning**")
            st.markdown("- **Model Regresi:** Fixed Effects Model (FEM) / Random Effects Model (REM)")
            st.markdown("- **Uji Spesifikasi:** Uji Hausman")
            st.markdown("- **Algoritma Clustering:** K-Means dengan Standard Scaling")

    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown("**📋 Variabel Penelitian**")
        st.markdown("""
        * **Produksi (Ton):** Akumulasi hasil panen lada per kabupaten/kota per tahun.
        * **Luas Panen (Ha):** Total luas area tanaman lada produktif.
        * **Produktivitas (Kg/Ha):** Hasil rata-rata produksi per hektar.
        * **Suhu Minimum & Maksimum (°C):** Temperatur udara ekstrem tahunan.
        * **Kelembapan Rata-rata (%):** Tingkat kelembapan relatif tahunan.
        * **Curah Hujan Total (mm):** Akumulasi presipitasi tahunan.
        * **Evapotranspirasi Total (mm):** Total laju penguapan air tahunan.
        * **Kecepatan Angin Maksimum & Rata-rata:** Vektor kecepatan angin rata-rata.
        """)
    
    st.markdown("<hr style='margin-top: 20px; margin-bottom: 20px; border-color: #E2E8F0;'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Pratinjau Dataset Mentah</div>", unsafe_allow_html=True)
    
    subtab_panel, subtab_cluster = st.tabs(["📊 Sheet: Panel Regression", "🗺️ Sheet: Clustering "])
    
    with subtab_panel:
        df_raw_panel = pd.read_excel(FILE_DATASET, sheet_name='Data Panel')
        if not df_raw_panel.empty:
            st.dataframe(df_raw_panel, use_container_width=True)
            st.caption(f"Menampilkan {len(df_raw_panel)} baris data untuk Panel Regression.")
        else:
            st.warning(f"Sheet 'data panel' tidak ditemukan di `{FILE_DATASET}`.")

    with subtab_cluster:
        df_raw_cluster = pd.read_excel(FILE_DATASET, sheet_name='Cluster')
        if not df_raw_cluster.empty:
            st.dataframe(df_raw_cluster, use_container_width=True)
            st.caption(f"Menampilkan {len(df_raw_cluster)} baris data untuk Clustering.")
        else:
            st.warning(f"Sheet 'Cluster' tidak ditemukan di `{FILE_DATASET}`.")