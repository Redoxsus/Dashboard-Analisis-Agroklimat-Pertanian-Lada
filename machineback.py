import re
import warnings

import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm
from linearmodels.panel import PanelOLS, RandomEffects
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore')

VAR_PERTANIAN = ['Luas Panen (ha)', 'Produksi (ton)', 'Produktivitas (kg/ha)']
VAR_IKLIM = [
    'Suhu Minimum (°C)', 'Suhu Maksimum (°C)', 'Suhu Rata-rata (°C)',
    'Kecepatan Angin Maksimum', 'Kecepatan Angin Rata-rata',
    'Curah Hujan Total (mm)', 'Kelembapan Rata-rata (%)',
    'Evapotranspirasi Total (mm)'
]

BATAS_CAKUPAN_IKLIM = 0.9

def _tahun_dari_kolom(nama_kolom):
    m = re.search(r'((?:19|20)\d{2})\s*$', str(nama_kolom))
    return int(m.group(1)) if m else None


def _alasan(pertanian_ok, iklim_ok):
    if pertanian_ok and iklim_ok:
        return 'Siap dianalisis'
    if not pertanian_ok and not iklim_ok:
        return 'Data pertanian & iklim belum lengkap'
    if not pertanian_ok:
        return 'Data pertanian belum diisi'
    return 'Data iklim belum lengkap'


def _status_panel(df):
    produksi = pd.to_numeric(df['Produksi (ton)'], errors='coerce').fillna(0)
    total_prod = produksi.groupby(df['Tahun']).sum()

    iklim_ada = [c for c in VAR_IKLIM if c in df.columns]
    if iklim_ada:
        lengkap = df[iklim_ada].apply(pd.to_numeric, errors='coerce').notna().all(axis=1)
        cakupan = lengkap.groupby(df['Tahun']).mean().reindex(total_prod.index).fillna(0)
    else:
        cakupan = pd.Series(1.0, index=total_prod.index)

    out = pd.DataFrame({
        'Tahun': total_prod.index.astype(int),
        'Total Produksi (ton)': total_prod.values,
        'Cakupan Iklim (%)': (cakupan.values * 100).round(1),
    })
    out['Pertanian Terisi'] = out['Total Produksi (ton)'] > 0
    out['Iklim Lengkap'] = out['Cakupan Iklim (%)'] >= BATAS_CAKUPAN_IKLIM * 100
    out['Dipakai Analisis'] = out['Pertanian Terisi'] & out['Iklim Lengkap']
    out['Status'] = [_alasan(a, b) for a, b in zip(out['Pertanian Terisi'], out['Iklim Lengkap'])]
    return out.sort_values('Tahun').reset_index(drop=True)


def status_tahun(file_upload):
    df_panel = pd.read_excel(file_upload, sheet_name='Data Panel')
    return _status_panel(df_panel)


def _tahun_dilewati_cluster(df_wide):
    semua_tahun = sorted({t for t in (_tahun_dari_kolom(c) for c in df_wide.columns) if t})
    dilewati = set()
    for th in semua_tahun:
        kolom_th = [c for c in df_wide.columns if _tahun_dari_kolom(c) == th]

        prod_cols = [c for c in kolom_th if 'Produksi (ton)' in str(c)]
        pertanian_ok = True
        if prod_cols:
            nilai = df_wide[prod_cols].apply(pd.to_numeric, errors='coerce').fillna(0).to_numpy()
            pertanian_ok = nilai.sum() > 0

        iklim_cols = [c for c in kolom_th if any(v in str(c) for v in VAR_IKLIM)]
        iklim_ok = True
        if iklim_cols:
            cakupan = df_wide[iklim_cols].apply(pd.to_numeric, errors='coerce').notna().mean()
            iklim_ok = bool((cakupan >= BATAS_CAKUPAN_IKLIM).all())

        if not (pertanian_ok and iklim_ok):
            dilewati.add(th)
    return dilewati


# =========================================================
# FUNGSI UTAMA
# =========================================================
def running(file_upload, selected_cluster_features=None, k_clusters=3):
    xls = pd.ExcelFile(file_upload)

    df_panel = pd.read_excel(xls, sheet_name='Data Panel')
    df_cluster_raw = pd.read_excel(xls, sheet_name='Cluster')

    # =========================================================
    # BLOK REGRESI DATA PANEL (Sheet: 'Data Panel')
    # =========================================================
    periode = {'tahun_dipakai': [], 'tahun_dilewati': [], 'n_tahun': 0}

    if 'Tahun' in df_panel.columns:
        df_status = _status_panel(df_panel)
        tahun_valid = df_status.loc[df_status['Dipakai Analisis'], 'Tahun'].tolist()
        periode['tahun_dipakai'] = tahun_valid
        periode['tahun_dilewati'] = [
            (int(r['Tahun']), r['Status'])
            for _, r in df_status[~df_status['Dipakai Analisis']].iterrows()
        ]
        periode['n_tahun'] = len(tahun_valid)
        df_clean = df_panel[df_panel['Tahun'].isin(tahun_valid)].copy()
    else:
        df_clean = df_panel.copy()

    var_pertanian = VAR_PERTANIAN
    var_pertanian_ada = [col for col in var_pertanian if col in df_clean.columns]

    df_clean[var_pertanian_ada] = df_clean[var_pertanian_ada].replace(0, np.nan)
    persentase_valid = df_clean.groupby('Kode')['Produksi (ton)'].transform(lambda x: x.notna().sum() / len(x))
    df_clean = df_clean[persentase_valid >= 0.4].copy()

    df_clean[var_pertanian_ada] = df_clean.groupby('Kode')[var_pertanian_ada].transform(lambda x: x.ffill().bfill())
    df_clean[var_pertanian_ada] = df_clean[var_pertanian_ada].fillna(0)

    kode_ke_nama = df_clean[['Kode', 'Nama Wilayah']].drop_duplicates().set_index('Kode')['Nama Wilayah'].to_dict()

    df_indexed = df_clean.set_index(['Kode', 'Tahun'])

    var_iklim_ada = [col for col in VAR_IKLIM if col in df_indexed.columns]

    hasil_testing = []
    fem_effects_dict = {}

    for x_col in var_iklim_ada:
        for y_col in var_pertanian:
            Y = df_indexed[y_col]
            X = sm.add_constant(df_indexed[[x_col]])

            try:
                re_model = RandomEffects(Y, X).fit()
                fe_model = PanelOLS(Y, X, entity_effects=True).fit()

                b = fe_model.params
                B = re_model.params
                v_b = fe_model.cov
                v_B = re_model.cov
                common = [c for c in b.index if c in B.index and c != 'const']

                if len(common) > 0:
                    b_diff = b[common] - B[common]
                    v_diff = v_b.loc[common, common] - v_B.loc[common, common]
                    chi2 = float(np.dot(np.dot(b_diff.T, np.linalg.inv(v_diff)), b_diff))
                    hausman_pval = stats.chi2.sf(chi2, len(common))
                else:
                    hausman_pval = np.nan

                model_terpilih = "FE" if (not np.isnan(hausman_pval) and hausman_pval < 0.05) else "RE"

                if model_terpilih == "FE":
                    efek = fe_model.estimated_effects
                    efek = efek.reset_index()
                    efek_unik = efek.groupby('Kode')['estimated_effects'].mean().reset_index()
                    efek_unik['Nama Wilayah'] = efek_unik['Kode'].map(kode_ke_nama)

                    efek_unik['Absolute Effect'] = efek_unik['estimated_effects'].abs()
                    efek_unik = efek_unik.sort_values(by='Absolute Effect', ascending=False)

                    key = f"{x_col}_vs_{y_col}"
                    fem_effects_dict[key] = efek_unik['Nama Wilayah'].head(15).tolist()

                hasil_testing.append({
                    'Independent Var.': x_col, 'Dependent Var.': y_col,
                    'RE Coef': round(re_model.params[x_col], 4), 'RE p-Value': round(re_model.pvalues[x_col], 4),
                    'FE Coef': round(fe_model.params[x_col], 4), 'FE p-Value': round(fe_model.pvalues[x_col], 4),
                    'Hausman p-Value': f"{hausman_pval:.4f}" if not np.isnan(hausman_pval) else "N/A",
                    'Model Terpilih': model_terpilih
                })
            except Exception:
                pass

    df_hasil = pd.DataFrame(hasil_testing)

    # =========================================================
    # BLOK CLUSTERING (Sheet: 'Cluster')
    # =========================================================
    df_wide = df_cluster_raw.copy()

    # 1. Menghapus Kolom Tahun yang tidak ada data
    tahun_dilewati_cl = _tahun_dilewati_cluster(df_wide)
    cols_dilewati = [c for c in df_wide.columns if _tahun_dari_kolom(c) in tahun_dilewati_cl]
    df_wide.drop(columns=cols_dilewati, inplace=True, errors='ignore')

    # 2. Mengelompokkan kolom pertanian
    prod_cols = [c for c in df_wide.columns if 'Produksi (ton)' in c]
    luas_cols = [c for c in df_wide.columns if 'Luas Panen (ha)' in c]
    prodv_cols = [c for c in df_wide.columns if 'Produktivitas (kg/ha)' in c]
    all_pertanian_cols = prod_cols + luas_cols + prodv_cols

    # 3. Merubah nilai 0 menjadi NaN
    existing_pertanian_cols = [c for c in all_pertanian_cols if c in df_wide.columns]
    if len(existing_pertanian_cols) > 0:
        df_wide[existing_pertanian_cols] = df_wide[existing_pertanian_cols].replace(0, np.nan)

    # 4. Memeriksa wilayah dengan variabel produksi yang terisi lebih dari 40%
    filled_years = df_wide[[c for c in prod_cols if c in df_wide.columns]].notna().sum(axis=1)
    df_clean_cluster = df_wide[filled_years >= 6].copy()

    existing_prod = [c for c in prod_cols if c in df_clean_cluster.columns]
    existing_luas = [c for c in luas_cols if c in df_clean_cluster.columns]
    existing_prodv = [c for c in prodv_cols if c in df_clean_cluster.columns]

    # 5. Wilayah dengan produksi dibawah 40% diisi menggunakan ffil dan bffil
    if existing_prod:
        df_clean_cluster[existing_prod] = df_clean_cluster[existing_prod].ffill(axis=1).bfill(axis=1)
    if existing_luas:
        df_clean_cluster[existing_luas] = df_clean_cluster[existing_luas].ffill(axis=1).bfill(axis=1)
    if existing_prodv:
        df_clean_cluster[existing_prodv] = df_clean_cluster[existing_prodv].ffill(axis=1).bfill(axis=1)

        df_clean_cluster = df_clean_cluster.fillna(0)
    else:
        df_clean_cluster = df_wide.fillna(0)

    # 6. Mengembalikkan NaN ke 0
    df_clean_cluster = df_clean_cluster.reset_index(drop=True)

    default_features = ['Luas Panen (ha)', 'Produksi (ton)', 'Suhu Rata-rata (°C)']
    base_features = selected_cluster_features if (selected_cluster_features and len(selected_cluster_features) > 0) else default_features

    features_to_scale = [c for c in df_clean_cluster.columns if any(var in c for var in base_features) and c not in ['Kode', 'Nama Wilayah']]

    if len(features_to_scale) == 0:
        base_features = default_features
        features_to_scale = [c for c in df_clean_cluster.columns if any(var in c for var in base_features) and c not in ['Kode', 'Nama Wilayah']]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_clean_cluster[features_to_scale])

    kmeans = KMeans(n_clusters=k_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X_scaled)

    sil_score = silhouette_score(X_scaled, cluster_labels) if k_clusters > 1 and len(df_clean_cluster) > k_clusters else 0.0
    db_score = davies_bouldin_score(X_scaled, cluster_labels) if k_clusters > 1 and len(df_clean_cluster) > k_clusters else 0.0
    cluster_metrics = {
        'silhouette': sil_score,
        'davies_bouldin': db_score,
        'selected_base_features': base_features,
        'periode': periode, 
    }

    cluster_mapping_names = {i: f'Klaster {i+1}' for i in range(k_clusters)}
    df_clean_cluster['Klaster'] = [cluster_mapping_names[label] for label in cluster_labels]

    return df_clean_cluster, cluster_metrics, df_hasil, fem_effects_dict