import streamlit as st
import pandas as pd
import geopandas as gpd
import difflib
import plotly.express as px
from machineback import running, status_tahun 
import warnings
import time
import datetime
import shutil


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
        gdf['shp_lat'] = gdf.geometry.centroid.y
        gdf['shp_lon'] = gdf.geometry.centroid.x

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
        return kemiripan[0] if kemiripan else None
        
    df_map['Nama_Matched'] = df_map['Nama_Clean'].apply(auto_match_nama)

    gdf_merged = gdf.merge(df_map, left_on='NAME_2', right_on='Nama_Matched', how='left')
    gdf_merged['Klaster'] = gdf_merged['Klaster'].fillna('Tidak Ada Data')
    
    gdf_merged = gdf_merged.drop_duplicates(subset=['NAME_2'])
    
    lat_col = 'Latitude' if 'Latitude' in gdf_merged.columns else ('Lat' if 'Lat' in gdf_merged.columns else 'shp_lat')
    lon_col = 'Longitude' if 'Longitude' in gdf_merged.columns else ('Lon' if 'Lon' in gdf_merged.columns else 'shp_lon')
    
    gdf_merged['lat'] = gdf_merged[lat_col]
    gdf_merged['lon'] = gdf_merged[lon_col]
    
    gdf_merged['geometry'] = gdf_merged['geometry'].simplify(tolerance=0.01, preserve_topology=True)
    gdf_merged = gdf_merged.set_index('NAME_2')
    gdf_merged.index.name = 'Nama Wilayah'
    return gdf_merged


def generate_dynamic_profiling(df_data, selected_vars, k_num):
    if df_data is None or df_data.empty or not selected_vars:
        return {}
        
    rata_cols = []
    for var in selected_vars:
        rata_col = f'Rata-rata {var}'
        if rata_col not in df_data.columns:
            matched_cols = [c for c in df_data.columns if var in c and c != rata_col and c not in ['Kode', 'Nama Wilayah', 'Klaster']]
            if matched_cols:
                df_data[rata_col] = df_data[matched_cols].mean(axis=1)
            else:
                df_data[rata_col] = 0.0
        rata_cols.append(rata_col)

    try:
        profile_df = df_data.groupby('Klaster', observed=False)[rata_cols].mean()
    except Exception:
        return {}

    agri_keywords = ['Produksi', 'Luas Panen', 'Produktivitas']
    narratives = {}
    
    for klaster in profile_df.index:
        agri_status = []
        iklim_tertinggi = []
        iklim_terendah = []
        iklim_menengah = []
        
        is_lahan_rendah = False
        is_cuaca_mendukung = False
        
        for var, rata_col in zip(selected_vars, rata_cols):
            val = profile_df.loc[klaster, rata_col]
            all_vals = profile_df[rata_col]
            
            is_agri = any(k in var for k in agri_keywords)
            clean_var = var.split(' (')[0].strip()
            
            if k_num > 1:
                max_val = all_vals.max()
                min_val = all_vals.min()
                
                if val == max_val:
                    if is_agri: 
                        agri_status.append(1)
                    else: 
                        iklim_tertinggi.append(clean_var)
                        if 'Hujan' in clean_var or 'Kelembapan' in clean_var:
                            is_cuaca_mendukung = True
                elif val == min_val:
                    if is_agri: 
                        agri_status.append(-1)
                        if 'Luas Panen' in clean_var:
                            is_lahan_rendah = True
                    else: 
                        iklim_terendah.append(clean_var)
                else:
                    if is_agri: 
                        agri_status.append(0)
                    else:
                        iklim_menengah.append(clean_var)
                    
        agri_text = ""
        if len(agri_status) > 0:
            avg_agri = sum(agri_status) / len(agri_status)
            if avg_agri > 0.3:
                agri_text = "<b>Wilayah Sentra Produksi Utama</b>"
            elif avg_agri < -0.3:
                agri_text = "<b>Wilayah Potensi Pertanian Rendah</b>"
            else:
                agri_text = "<b>Wilayah Kapasitas Produksi Menengah</b>"
                
        iklim_text_parts = []
        if iklim_tertinggi:
            iklim_text_parts.append(f"{', '.join(iklim_tertinggi)} <span style='color:#DC2626; font-weight:600;'>Tertinggi</span>")
        if iklim_terendah:
            iklim_text_parts.append(f"{', '.join(iklim_terendah)} <span style='color:#059669; font-weight:600;'>Terendah</span>")
        if iklim_menengah and not iklim_tertinggi and not iklim_terendah:
             iklim_text_parts.append(f"kondisi iklim yang <span style='color:#D97706; font-weight:600;'>relatif stabil/menengah</span>")
             
        iklim_text = ""
        if iklim_text_parts:
            if "kondisi iklim" in iklim_text_parts[0]:
                iklim_text = iklim_text_parts[0]
            else:
                iklim_text = "memiliki tingkat " + " dan ".join(iklim_text_parts)
            
        insight_text = ""
        if is_lahan_rendah and is_cuaca_mendukung:
            insight_text = " 💡 <i>Meskipun didukung agroklimat yang ideal, produksi belum optimal diduga akibat keterbatasan luas lahan panen.</i>"
            
        if agri_text and iklim_text:
            final_text = f"{agri_text} yang {iklim_text}.{insight_text}"
        elif agri_text:
            final_text = f"Merupakan {agri_text} dibandingkan klaster lainnya.{insight_text}"
        elif iklim_text:
            final_text = f"Wilayah yang {iklim_text} (untuk indikator yang dipilih)."
        else:
            final_text = "Karakteristik wilayah berada pada tingkat <b>Menengah</b> secara keseluruhan."
            
        narratives[klaster] = final_text
        
    return narratives


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

df, cluster_metrics, reg_data, fem_effects, gdf_merged = None, None, None, None, None

st.markdown("""
    <div style="margin-bottom: 1.2rem;">
        <div class="hero-title">Dashboard Analisis Agroklimat Pertanian Lada</div>
        <div class="hero-subtitle">Pemetaan Klaster Wilayah & Evaluasi Model Regresi Data Panel Komoditas Lada Indonesia</div>
    </div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📍 Clustering Analysis", "📈 Panel Regression", "ℹ️ About Dataset", "⚙️ Data Management"])

# TAB 1: CLUSTERING

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
            df, cluster_metrics, reg_data, fem_effects = running(
                FILE_DATASET, 
                selected_cluster_features=curr_vars, 
                k_clusters=curr_k
            )
            
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

        if cluster_metrics and 'periode' in cluster_metrics:
            p_data = cluster_metrics['periode']
            tahun_invalid = p_data.get('tahun_dilewati', [])
            if tahun_invalid:
                invalid_str = ", ".join([str(t[0]) for t in tahun_invalid])

        col_map, col_stats = st.columns([2.6, 1.1])

        with col_map:
            st.markdown("<div class='section-title'>VISUALISASI PETA KLASTER (AREA)</div>", unsafe_allow_html=True)
            st.caption(f"Peta Choropleth K-Means berdasarkan indikator agroklimat & produksi terpilih.")
            
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
                
                lat_col_name = 'Latitude' if 'Latitude' in df.columns else ('Lat' if 'Lat' in df.columns else None)
                lon_col_name = 'Longitude' if 'Longitude' in df.columns else ('Lon' if 'Lon' in df.columns else None)
                
                if lat_col_name and lon_col_name:
                    st.markdown("<hr style='border-color: #E2E8F0; margin: 15px 0;'>", unsafe_allow_html=True)
                    st.markdown("<div class='section-title'>VISUALISASI SEBARAN TITIK (BUBBLE MAP)</div>", unsafe_allow_html=True)
                    
                    bubble_size_var = None
                    if 'Produksi (ton)' in curr_vars: bubble_size_var = 'Rata-rata Produksi (ton)'
                    elif 'Luas Panen (ha)' in curr_vars: bubble_size_var = 'Rata-rata Luas Panen (ha)'
                    elif 'Produktivitas (kg/ha)' in curr_vars: bubble_size_var = 'Rata-rata Produktivitas (kg/ha)'
                    
                    if bubble_size_var and (df[bubble_size_var].max() > 0):
                        st.caption(f"Besaran titik merepresentasikan volume aktual dari **{bubble_size_var.replace('Rata-rata ', '')}**.")
                        size_param = bubble_size_var
                    else:
                        st.caption("Peta titik kordinat riil dari file Excel (ukuran gelembung disamaratakan).")
                        size_param = None
                        
                    fig_bubble = px.scatter_mapbox(
                        df, 
                        lat=lat_col_name, 
                        lon=lon_col_name, 
                        color="Klaster",
                        size=size_param,
                        size_max=35,
                        color_discrete_map=color_map,
                        hover_name="Nama Wilayah",
                        zoom=3.8, 
                        center={"lat": -2.0, "lon": 118.0},
                        mapbox_style="carto-positron"
                    )
                    
                    fig_bubble.update_layout(
                        margin={"r":0,"t":10,"l":0,"b":0},
                        height=480,
                        legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_bubble, use_container_width=True)
                
            else:
                st.error("⚠️ File shapefile `gadm41_IDN_2.shp` tidak ditemukan di folder `data/`.")

        with col_stats:
            st.markdown("<div class='section-title'>DISTRIBUSI & PROFIL KLASTER</div>", unsafe_allow_html=True)
            st.caption("Karakteristik dinamis berdasarkan indikator yang dipilih.")
            
            cluster_list = [f"Klaster {i+1}" for i in range(curr_k)]
            cluster_colors = ['#E5734A', '#5D9CE2', '#47B376', '#9B51E0', '#F2994A']
            
            dynamic_profiles = generate_dynamic_profiling(df, curr_vars, curr_k)
            
            for idx, klaster in enumerate(cluster_list):
                hex_color = cluster_colors[idx % len(cluster_colors)]
                subset = df[df['Klaster'] == klaster]
                count = len(subset)
                pct = (count / len(df)) * 100 if len(df) > 0 else 0
                
                narasi = dynamic_profiles.get(klaster, "Data profil tidak tersedia.")
                
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
                    <div style="margin-top: 10px; font-size: 0.82rem; color: #334155; line-height: 1.5; padding-top: 8px; border-top: 1px dashed #E2E8F0;">
                        {narasi}
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

        # CLUSTER PROFILING
        st.markdown("<hr style='margin-top: 30px; margin-bottom: 25px; border-color: #E2E8F0;'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title' style='font-size: 1.15rem;'>📊 Cluster Profiling (Analisis Tren Variabel)</div>", unsafe_allow_html=True)
        st.caption("Visualisasi perbandingan tren historis rata-rata seluruh indikator penelitian antar klaster secara interaktif.")
        st.markdown("<br>", unsafe_allow_html=True)

        def plot_dynamic_trend(df_data, variable_name, title, yaxis_label, satuan_x):
            cols = [c for c in df_data.columns if variable_name in c]
            if not cols:
                return None
            
            df_grouped = df_data.groupby('Klaster', observed=False)[cols].mean().reset_index()
            df_melted = df_grouped.melt(id_vars=['Klaster'], var_name='Tahun_Raw', value_name='Nilai')
            df_melted['Tahun'] = df_melted['Tahun_Raw'].str.extract(r'(\d{4})')
            df_melted = df_melted.dropna(subset=['Tahun'])
            df_melted['Tahun'] = df_melted['Tahun'].astype(int)
            df_melted = df_melted.sort_values('Tahun')
            
            fig = px.line(
                df_melted, x='Tahun', y='Nilai', color='Klaster', markers=True,
                color_discrete_map=color_map, title=title
            )
            fig.update_layout(
                xaxis_title=f"Tahun<br><sup>({satuan_x})</sup>", 
                yaxis_title=yaxis_label,
                plot_bgcolor='#FFFFFF', 
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=40, b=20),
                xaxis=dict(showgrid=True, gridcolor='#F1F5F9', dtick=1),
                yaxis=dict(showgrid=True, gridcolor='#F1F5F9'),
                legend_title_text=''
            )
            return fig

        st.markdown("##### 🌾 Komponen Pertanian")
        c1, c2, c3 = st.columns(3)
        with c1:
            fig_prod = plot_dynamic_trend(df, "Produksi (ton)", "Tren Produksi", "Produksi (ton)", "ton")
            if fig_prod: st.plotly_chart(fig_prod, use_container_width=True)
        with c2:
            fig_luas = plot_dynamic_trend(df, "Luas Panen (ha)", "Tren Luas Panen", "Luas Panen (ha)", "ha")
            if fig_luas: st.plotly_chart(fig_luas, use_container_width=True)
        with c3:
            fig_prodv = plot_dynamic_trend(df, "Produktivitas (kg/ha)", "Tren Produktivitas", "Produktivitas (kg/ha)", "kg/ha")
            if fig_prodv: st.plotly_chart(fig_prodv, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("##### 🌡️ Indikator Suhu Udara")
        c1, c2, c3 = st.columns(3)
        with c1:
            fig_tmax = plot_dynamic_trend(df, "Suhu Maksimum", "Tren Suhu Maksimum", "Suhu Maksimum (°C)", "°C")
            if fig_tmax: st.plotly_chart(fig_tmax, use_container_width=True)
        with c2:
            fig_tmin = plot_dynamic_trend(df, "Suhu Minimum", "Tren Suhu Minimum", "Suhu Minimum (°C)", "°C")
            if fig_tmin: st.plotly_chart(fig_tmin, use_container_width=True)
        with c3:
            fig_tavg = plot_dynamic_trend(df, "Suhu Rata-rata", "Tren Suhu Rata-rata", "Suhu Rata-rata (°C)", "°C")
            if fig_tavg: st.plotly_chart(fig_tavg, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("##### 💧 Presipitasi & Kelembapan")
        c1, c2, c3 = st.columns(3)
        with c1:
            fig_rain = plot_dynamic_trend(df, "Curah Hujan Total", "Tren Curah Hujan", "Curah Hujan Total (mm)", "mm")
            if fig_rain: st.plotly_chart(fig_rain, use_container_width=True)
        with c2:
            fig_rh = plot_dynamic_trend(df, "Kelembapan", "Tren Kelembapan", "Kelembapan Rata-rata (%)", "%")
            if fig_rh: st.plotly_chart(fig_rh, use_container_width=True)
        with c3:
            fig_et = plot_dynamic_trend(df, "Evapotranspirasi", "Tren Evapotranspirasi", "Evapotranspirasi Total (mm)", "mm")
            if fig_et: st.plotly_chart(fig_et, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("##### 🌪️ Indikator Kecepatan Angin")
        c1, c2, _ = st.columns([1, 1, 1])
        with c1:
            fig_ws = plot_dynamic_trend(df, "Kecepatan Angin Rata-rata", "Tren Angin Rata-rata", "Kecepatan Angin Rata-rata (m/s)", "m/s")
            if fig_ws: st.plotly_chart(fig_ws, use_container_width=True)
        with c2:
            fig_ws_max = plot_dynamic_trend(df, "Kecepatan Angin Maksimum", "Tren Angin Maksimum", "Kecepatan Angin Maksimum (m/s)", "m/s")
            if fig_ws_max: st.plotly_chart(fig_ws_max, use_container_width=True)

    except FileNotFoundError:
        st.error(f"⚠️ File dataset `{FILE_DATASET}` tidak ditemukan. Pastikan lokasi file di folder `data/` sudah benar.")


SATUAN_DEP = {
    'Produksi (ton)': 'ton',
    'Luas Panen (ha)': 'hektare',
    'Produktivitas (kg/ha)': 'kg/ha',
}
SATUAN_IND = {
    'Curah Hujan Total (mm)': 'mm',
    'Suhu Minimum (°C)': '°C',
    'Suhu Maksimum (°C)': '°C',
    'Suhu Rata-rata (°C)': '°C',
    'Kelembapan Rata-rata (%)': '%',
    'Kecepatan Angin Rata-rata': 'satuan',
    'Kecepatan Angin Maksimum': 'satuan',
    'Evapotranspirasi Total (mm)': 'mm',
}

def _fmt_angka(x):
    x = abs(float(x))
    if x != 0 and x < 0.0001:
        return f"{x:.2e}"
    return f"{x:,.4f}"

def _nama_bersih(label):
    return label.split(' (')[0].strip()

def buat_narasi_koefisien(ind_var, dep_var, coef, pval):
    try:
        coef = float(coef)
        pval = float(pval)
    except (ValueError, TypeError):
        return None

    nama_ind = _nama_bersih(ind_var)
    nama_dep = _nama_bersih(dep_var)
    sat_ind = SATUAN_IND.get(ind_var, 'satuan')
    sat_dep = SATUAN_DEP.get(dep_var, 'satuan')

    if pval >= 0.05:
        return (
            f"Pengaruh {nama_ind} terhadap {nama_dep} tidak signifikan secara statistik, "
            f"sehingga koefisien tidak dapat diinterpretasikan sebagai pengaruh nyata."
        )

    arah_kata = "meningkat" if coef > 0 else "menurun"
    return (
        f"Setiap kenaikan 1 {sat_ind} pada **{nama_ind}**, "
        f"**{nama_dep}** rata-rata **{arah_kata} sekitar {_fmt_angka(coef)} {sat_dep}**."
    )

# TAB 2: PANEL REGRESSION 

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

            if model_terpilih == 'FE':
                coef_raw, pval_raw = res['FE Coef'], res['FE p-Value']
            else:
                coef_raw, pval_raw = res['RE Coef'], res['RE p-Value']

            narasi = buat_narasi_koefisien(ind_var, dep_var, coef_raw, pval_raw)
            if narasi:
                st.markdown(f"**🧮 Interpretasi Koefisien:** {narasi}")

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        if model_terpilih == 'FE':
            key_efek = f"{ind_var}_vs_{dep_var}"
            if fem_effects and key_efek in fem_effects:
                st.markdown(f"""
                **📍 Wilayah Spesifik yang Paling Terdampak / Memiliki Karakteristik Unik**<br>
                <span style="font-size: 0.9rem; color: #475569;">
                Karena model terpilih adalah <b>Fixed Effects Model (FEM)</b>, pengaruh variabel ini tidak merata dan sangat dipengaruhi oleh keunikan karakteristik tiap daerah. 
                Berikut adalah daftar Kabupaten/Kota di Indonesia yang paling signifikan terpengaruh dan menjadi prioritas utama untuk penanganan kebijakan:
                </span>
                """, unsafe_allow_html=True)
                
                wilayah_list = fem_effects[key_efek]
                df_wilayah_terpengaruh = pd.DataFrame({
                    "No.": range(1, len(wilayah_list) + 1),
                    "Kabupaten / Kota Prioritas": wilayah_list
                })

                st.dataframe(
                    df_wilayah_terpengaruh,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("ℹ️ Detail wilayah spesifik tidak tersedia untuk kombinasi variabel ini.")
        else:
            st.markdown(f"""
            **🌍 Karakteristik Model Global (Random Effects)**<br>
            <span style="font-size: 0.9rem; color: #475569;">
            Karena model terpilih adalah <b>Random Effects Model (REM)</b>, variasi antar wilayah bersifat acak dan seragam secara nasional. 
            Oleh karena itu, kebijakan mitigasi dapat diterapkan secara menyeluruh/agregat tanpa perlu mengkhususkan wilayah tertentu.
            </span>
            """, unsafe_allow_html=True)

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
        * **Kecepatan Angin Maksimum & Rata-rata (m/s):** Vektor kecepatan angin rata-rata.
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


# TAB 4: DATA MANAGEMENT 
with tab4:
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title' style='font-size: 1.2rem;'>⚙️ Data Management & Entry</div>", unsafe_allow_html=True)
    st.caption("Input data pertanian baru. Sistem otomatis mengurutkan data berdasarkan wilayah dan memperbarui sheet Cluster.")
    st.markdown("<br>", unsafe_allow_html=True)

    try:
        df_panel = pd.read_excel(FILE_DATASET, sheet_name='Data Panel')
        df_cluster = pd.read_excel(FILE_DATASET, sheet_name='Cluster')
        df_info = pd.read_excel(FILE_DATASET, sheet_name='Info Wilayah')
        
        daftar_wilayah = sorted(df_info['Nama Wilayah'].dropna().unique().tolist())
    except Exception as e:
        st.error(f"Gagal membaca dataset: {e}. Pastikan sheet 'Data Panel', 'Cluster', dan 'Info Wilayah' tersedia.")
        daftar_wilayah = []
        df_panel, df_cluster, df_info = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    with st.form("form_input_data", border=True):
        st.markdown("#### 📝 Form Input / Update Data")
        
        pilih_wilayah = st.selectbox("📍 Pilih Wilayah (Kabupaten/Kota)", options=daftar_wilayah)
        
        tahun_default = int(df_panel['Tahun'].max() + 1) if ('Tahun' in df_panel.columns and not df_panel.empty) else 2025
        pilih_tahun = st.number_input("📅 Tahun Data", min_value=2010, max_value=2030, value=tahun_default, step=1)
        
        st.markdown("---")
        st.markdown("**🌱 Komponen Pertanian**")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            input_luas = st.number_input("Luas Panen (ha)", min_value=0.0, value=0.0, step=10.0)
        with col_b:
            input_produksi = st.number_input("Produksi (ton)", min_value=0.0, value=0.0, step=10.0)
        with col_c:
            input_produktivitas = st.number_input("Produktivitas (kg/ha)", min_value=0.0, value=0.0, step=10.0)
        
        st.markdown("---")
        st.markdown("**☁️ Komponen Iklim**")
        tarik_iklim = st.checkbox(
            "Tarik & Timpa Data Iklim dari Open-Meteo", 
            value=False,
            help="Centang ini untuk menarik data suhu/hujan otomatis. Biarkan kosong jika hanya update data pertanian."
        )
        
        submit_data = st.form_submit_button("💾 Simpan Data ke Dataset", type="primary", use_container_width=True)

        if submit_data:
            info_row = df_info[df_info['Nama Wilayah'] == pilih_wilayah]
            
            if info_row.empty:
                st.error(f"Nama wilayah '{pilih_wilayah}' tidak ditemukan di sheet 'Info Wilayah'.")
            else:
                kode_wilayah = info_row['Kode'].values[0] if 'Kode' in info_row.columns else None
                lat = info_row['Lat'].values[0] if 'Lat' in info_row.columns else None
                lon = info_row['Lon'].values[0] if 'Lon' in info_row.columns else None
                
                if pd.isna(lat) or pd.isna(lon):
                    st.error(f"Koordinat (Lat/Lon) untuk {pilih_wilayah} kosong di sheet 'Info Wilayah'.")
                else:
                    try:
                        data_update_panel = {
                            'Kode': kode_wilayah,
                            'Nama Wilayah': pilih_wilayah,
                            'Tahun': pilih_tahun,
                            'Luas Panen (ha)': input_luas,
                            'Produksi (ton)': input_produksi,
                            'Produktivitas (kg/ha)': input_produktivitas,
                            'Latitude': lat,
                            'Longitude': lon
                        }
                        
                        if tarik_iklim:
                            with st.spinner(f"Menarik data iklim {pilih_wilayah} tahun {pilih_tahun} dari Open-Meteo..."):
                                import datetime, requests
                                today = datetime.date.today()
                                end_date_str = f"{pilih_tahun}-12-31"
                                if pilih_tahun >= today.year:
                                    last_available_date = today - datetime.timedelta(days=5)
                                    end_date_str = last_available_date.strftime("%Y-%m-%d")
                                    
                                start_date_str = f"{pilih_tahun}-01-01"

                                url = (
                                    f"https://archive-api.open-meteo.com/v1/archive?"
                                    f"latitude={lat}&longitude={lon}&start_date={start_date_str}&end_date={end_date_str}"
                                    f"&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
                                    f"precipitation_sum,rain_sum,et0_fao_evapotranspiration,wind_speed_10m_max,"
                                    f"wind_speed_10m_mean&timezone=Asia%2FJakarta"
                                )
                                
                                response = requests.get(url)
                                data_cuaca = response.json()
                                
                                if "error" in data_cuaca:
                                    st.error(f"Gagal menarik data API: {data_cuaca.get('reason')}")
                                else:
                                    daily = data_cuaca['daily']
                                    
                                    suhu_max = max((x for x in daily['temperature_2m_max'] if x is not None), default=0)
                                    suhu_min = min((x for x in daily['temperature_2m_min'] if x is not None), default=0)
                                    suhu_avg = sum(filter(None, daily['temperature_2m_mean'])) / len([x for x in daily['temperature_2m_mean'] if x is not None])
                                    curah_hujan = sum(filter(None, daily['precipitation_sum']))
                                    evapotranspirasi = sum(filter(None, daily['et0_fao_evapotranspiration']))
                                    angin_max = max((x for x in daily['wind_speed_10m_max'] if x is not None), default=0)
                                    angin_avg = sum(filter(None, daily['wind_speed_10m_mean'])) / len([x for x in daily['wind_speed_10m_mean'] if x is not None])
                                    
                                    data_update_panel.update({
                                        'Suhu Maksimum (°C)': round(suhu_max, 2),
                                        'Suhu Minimum (°C)': round(suhu_min, 2),
                                        'Suhu Rata-rata (°C)': round(suhu_avg, 2),
                                        'Curah Hujan Total (mm)': round(curah_hujan, 2),
                                        'Evapotranspirasi Total (mm)': round(evapotranspirasi, 2),
                                        'Kecepatan Angin Maksimum': round(angin_max, 2),
                                        'Kecepatan Angin Rata-rata': round(angin_avg, 2),
                                        'Kelembapan Rata-rata (%)': 80.0
                                    })
                        
                        backup_path = FILE_DATASET.replace(".xlsx", "_backup.xlsx")
                        shutil.copy2(FILE_DATASET, backup_path)

                        if 'Nama Wilayah' in df_panel.columns and 'Tahun' in df_panel.columns:
                            mask_panel = (df_panel['Nama Wilayah'] == pilih_wilayah) & (df_panel['Tahun'] == pilih_tahun)
                        else:
                            mask_panel = pd.Series([False] * len(df_panel))

                        if mask_panel.any():
                            idx = df_panel[mask_panel].index[0]
                            for col, val in data_update_panel.items():
                                df_panel.at[idx, col] = val
                        else:
                            df_panel = pd.concat([df_panel, pd.DataFrame([data_update_panel])], ignore_index=True)
                        
                        if 'Nama Wilayah' in df_cluster.columns and 'Tahun' in df_cluster.columns:
                            mask_cluster = (df_cluster['Nama Wilayah'] == pilih_wilayah) & (df_cluster['Tahun'] == pilih_tahun)
                        else:
                            mask_cluster = pd.Series([False] * len(df_cluster))
                            
                        if not mask_cluster.any():
                            data_update_cluster = {
                                'Kode': kode_wilayah,
                                'Nama Wilayah': pilih_wilayah,
                                'Tahun': pilih_tahun
                            }
                            df_cluster = pd.concat([df_cluster, pd.DataFrame([data_update_cluster])], ignore_index=True)

                        sort_cols_panel = [col for col in ['Kode', 'Tahun'] if col in df_panel.columns]
                        if sort_cols_panel:
                            df_panel = df_panel.sort_values(by=sort_cols_panel).reset_index(drop=True)
                            
                        sort_cols_cluster = [col for col in ['Kode', 'Tahun'] if col in df_cluster.columns]
                        if sort_cols_cluster:
                            df_cluster = df_cluster.sort_values(by=sort_cols_cluster).reset_index(drop=True)
                        
                        with pd.ExcelWriter(FILE_DATASET, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                            df_panel.to_excel(writer, sheet_name='Data Panel', index=False)
                            df_cluster.to_excel(writer, sheet_name='Cluster', index=False)
                        
                        st.success(f"✅ Data {pilih_wilayah} tahun {pilih_tahun} berurut rapi dan berhasil disimpan!")
                        
                        import time
                        st.cache_data.clear()
                        time.sleep(1.5)
                        st.rerun()

                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat memproses/menyimpan data: {str(e)}")