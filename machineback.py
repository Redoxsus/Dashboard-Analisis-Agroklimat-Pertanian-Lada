import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score
import statsmodels.api as sm
from linearmodels.panel import PanelOLS, RandomEffects
import scipy.stats as stats
import warnings
from sklearn.decomposition import PCA   

warnings.filterwarnings('ignore')

def running(file_upload, selected_cluster_features=None, k_clusters=3):
    # 1. Membaca file Excel dan memisahkan sheet
    xls = pd.ExcelFile(file_upload)
    
    df_panel = pd.read_excel(xls, sheet_name='Data Panel')
    df_cluster_raw = pd.read_excel(xls, sheet_name='Cluster')
    
    # =========================================================
    # BLOK REGRESI DATA PANEL (Sheet: 'data panel')
    # =========================================================
    
    # 1. Menghapus bari data untuk tahun 2025
    df_clean = df_panel[df_panel['Tahun'] < 2025].copy()
    
    var_pertanian = ['Luas Panen (ha)', 'Produksi (ton)', 'Produktivitas (kg/ha)']
    var_pertanian_ada = [col for col in var_pertanian if col in df_clean.columns]
    
    # 2. Ubah nilai 0 menjadi NaN untuk variabel pertanian
    df_clean[var_pertanian_ada] = df_clean[var_pertanian_ada].replace(0, np.nan)
    
    # 3. Mengecek Variabel Produksi yang data terdapat 40% keatas berdasarkan kota / kabupaten
    persentase_valid = df_clean.groupby('Kode')['Produksi (ton)'].transform(lambda x: x.notna().sum() / len(x))
    
    # 4. Buang daerah yang ketersediaan datanya < 40%
    df_clean = df_clean[persentase_valid >= 0.4].copy()
    
    # 5. Untuk wilayah yang dipertahankan (>= 40%), isi nilai NaN menggunakan ffill lalu bfill per daerah
    df_clean[var_pertanian_ada] = df_clean.groupby('Kode')[var_pertanian_ada].transform(lambda x: x.ffill().bfill())
    
    # 6. Pastikan tidak ada sisa NaN dengan mengembalikan nilai NaN ke 0
    df_clean[var_pertanian_ada] = df_clean[var_pertanian_ada].fillna(0)
    
    df_indexed = df_clean.set_index(['Kode', 'Tahun'])

    var_iklim = [
        'Suhu Minimum (°C)', 'Suhu Maksimum (°C)', 'Suhu Rata-rata (°C)',
        'Kecepatan Angin Maksimum', 'Kecepatan Angin Rata-rata',
        'Curah Hujan Total (mm)', 'Kelembapan Rata-rata (%)',
        'Evapotranspirasi Total (mm)'
    ]
    var_iklim_ada = [col for col in var_iklim if col in df_indexed.columns]

    hasil_testing = []

    for x_col in var_iklim_ada:
        for y_col in var_pertanian:
            Y = df_indexed[y_col]
            X = sm.add_constant(df_indexed[[x_col]])

            try:
                # Random Effects (RE)
                re_model = RandomEffects(Y, X).fit()
                re_coef = re_model.params[x_col]
                re_pval = re_model.pvalues[x_col]

                # Fixed Effects (FE)
                fe_model = PanelOLS(Y, X, entity_effects=True).fit()
                fe_coef = fe_model.params[x_col]
                fe_pval = fe_model.pvalues[x_col]

                # Hausman Test
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

                hasil_testing.append({
                    'Independent Var.': x_col,
                    'Dependent Var.': y_col,
                    'RE Coef': round(re_coef, 4),
                    'RE p-Value': round(re_pval, 4),
                    'FE Coef': round(fe_coef, 4),
                    'FE p-Value': round(fe_pval, 4),
                    'Hausman p-Value': f"{hausman_pval:.4e}" if not np.isnan(hausman_pval) else "N/A",
                    'Model Terpilih': model_terpilih
                })
            except Exception as e:
                print(f"Gagal pada {x_col} -> {y_col}: {e}")

    df_hasil = pd.DataFrame(hasil_testing)
    
    # =========================================================
    # BLOK CLUSTERING (Sheet: 'Cluster')
    # =========================================================
    df_wide = df_cluster_raw.copy()

    # Menerapkan persis blok preprocessing clustering Anda
    
    # 1. Menghapus kolom data yang bernilai 2025
    cols_2025 = [c for c in df_wide.columns if '2025' in str(c)]
    df_wide.drop(columns=cols_2025, inplace=True, errors='ignore')

    # 2. Mengelompokkan kolom pertanian
    prod_cols = [c for c in df_wide.columns if 'Produksi (ton)' in c]
    luas_cols = [c for c in df_wide.columns if 'Luas Panen (ha)' in c]
    prodv_cols = [c for c in df_wide.columns if 'Produktivitas (kg/ha)' in c]
    all_pertanian_cols = prod_cols + luas_cols + prodv_cols

    # 3. Replace 0 dengan NaN khusus pada kolom pertanian wide format
    existing_pertanian_cols = [c for c in all_pertanian_cols if c in df_wide.columns]
    if len(existing_pertanian_cols) > 0:
        df_wide[existing_pertanian_cols] = df_wide[existing_pertanian_cols].replace(0, np.nan)
    
    # 3. Mengecek Variabel Produksi yang data terdapat 40% keatas berdasarkan kota / kabupaten
        filled_years = df_wide[[c for c in prod_cols if c in df_wide.columns]].notna().sum(axis=1)
        df_clean_cluster = df_wide[filled_years >= 6].copy()

        existing_prod = [c for c in prod_cols if c in df_clean_cluster.columns]
        existing_luas = [c for c in luas_cols if c in df_clean_cluster.columns]
        existing_prodv = [c for c in prodv_cols if c in df_clean_cluster.columns]

    # 4. Untuk wilayah yang dipertahankan (>= 40%), isi nilai NaN menggunakan ffill lalu bfill per daerah
        if existing_prod:
            df_clean_cluster[existing_prod] = df_clean_cluster[existing_prod].ffill(axis=1).bfill(axis=1)
        if existing_luas:
            df_clean_cluster[existing_luas] = df_clean_cluster[existing_luas].ffill(axis=1).bfill(axis=1)
        if existing_prodv:
            df_clean_cluster[existing_prodv] = df_clean_cluster[existing_prodv].ffill(axis=1).bfill(axis=1)
                
            df_clean_cluster = df_clean_cluster.fillna(0)
        else:
            df_clean_cluster = df_wide.fillna(0)
            
    # 5. Mengembalikan nilai NaN ke 0
        df_clean_cluster = df_clean_cluster.reset_index(drop=True)

        # Tentukan base features untuk clustering
        default_features = ['Luas Panen (ha)', 'Produksi (ton)', 'Suhu Rata-rata (°C)']
        base_features = selected_cluster_features if (selected_cluster_features and len(selected_cluster_features) > 0) else default_features
                
        # Mengambil kolom-kolom time-series di wide format yang sesuai dengan base features pilihan
        features_to_scale = [c for c in df_clean_cluster.columns if any(var in c for var in base_features) and c not in ['Kode', 'Nama Wilayah']]
        
        if len(features_to_scale) == 0:
            base_features = default_features
            features_to_scale = [c for c in df_clean_cluster.columns if any(var in c for var in base_features) and c not in ['Kode', 'Nama Wilayah']]
                
        # Transformasi dan KMeans Clustering
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df_clean_cluster[features_to_scale])

        kmeans = KMeans(n_clusters=k_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(X_scaled)
        
        sil_score = silhouette_score(X_scaled, cluster_labels) if k_clusters > 1 and len(df_clean_cluster) > k_clusters else 0.0
        db_score = davies_bouldin_score(X_scaled, cluster_labels) if k_clusters > 1 and len(df_clean_cluster) > k_clusters else 0.0
        cluster_metrics = {'silhouette': sil_score, 'davies_bouldin': db_score, 'selected_base_features': base_features}
        
        cluster_mapping_names = {i: f'Klaster {i+1}' for i in range(k_clusters)}
        df_clean_cluster['Klaster'] = [cluster_mapping_names[label] for label in cluster_labels]
        
        return df_clean_cluster, cluster_metrics, df_hasil