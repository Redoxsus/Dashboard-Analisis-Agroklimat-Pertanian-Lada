import pandas as pd
import numpy as np

# 1. Load File Excel Master dan File Input 2025
file_master = 'data/Data_Gabungan_Lada_Cuaca_Full_Used.xlsx'
file_input = 'data/Input2025.xlsx'

print("🔄 Sedang membaca data...")
df_panel = pd.read_excel(file_master, sheet_name='Data Panel')
df_cluster = pd.read_excel(file_master, sheet_name='Cluster')
df_baru = pd.read_excel(file_input)

# 2. Proses Injeksi Data ke Kedua Sheet
print("⚙️ Sedang menyuntikkan data 2025 ke kedua format sheet...")
for index, row in df_baru.iterrows():
    # PERBAIKAN 1: Ekstrak hanya nama wilayahnya saja (Hilangkan "1101 - ")
    # Jika formatnya "1101 - Kab. Simeulue", ambil teks setelah " - "
    raw_wilayah = str(row['Nama Wilayah']).strip()
    if " - " in raw_wilayah:
        wilayah = raw_wilayah.split(" - ")[1].strip()
    else:
        wilayah = raw_wilayah
        
    # PERBAIKAN 2: Ubah koma menjadi titik untuk desimal, dan atur kolom sesuai excel
    produksi_str = str(row['Produksi']).replace(',', '.')
    luas_str = str(row['Luas Areal']).replace(',', '.')
    produktivitas_str = str(row['Produktivitas']).replace(',', '.')
    
    # Amankan dari error jika string tidak bisa diconvert ke float
    try:
        produksi = float(produksi_str) if pd.notna(row['Produksi']) else 0.0
        luas = float(luas_str) if pd.notna(row['Luas Areal']) else 0.0
        produktivitas = float(produktivitas_str) if pd.notna(row['Produktivitas']) else 0.0
    except ValueError:
        produksi, luas, produktivitas = 0.0, 0.0, 0.0
    
    # --- UPDATE SHEET: DATA PANEL (Format Vertikal) ---
    mask_panel = (df_panel['Nama Wilayah'] == wilayah) & (df_panel['Tahun'] == 2025)
    df_panel.loc[mask_panel, 'Produksi (ton)'] = produksi
    df_panel.loc[mask_panel, 'Luas Panen (ha)'] = luas
    df_panel.loc[mask_panel, 'Produktivitas (kg/ha)'] = produktivitas
    
    # --- UPDATE SHEET: CLUSTER (Format Horizontal) ---
    mask_cluster = (df_cluster['Nama Wilayah'] == wilayah)
    # Memastikan nama kolomnya sesuai dengan di Excel
    df_cluster.loc[mask_cluster, 'Produksi (ton) 2025'] = produksi
    df_cluster.loc[mask_cluster, 'Luas Panen (ha) 2025'] = luas
    df_cluster.loc[mask_cluster, 'Produktivitas (kg/ha) 2025'] = produktivitas

# 3. Simpan Menjadi File Excel Baru (agar file lama tetap aman sebagai backup)
file_output = 'data/Data_Gabungan_Lada_Cuaca_Full_Updated.xlsx'
with pd.ExcelWriter(file_output, engine='openpyxl') as writer:
    df_panel.to_excel(writer, sheet_name='Data Panel', index=False)
    df_cluster.to_excel(writer, sheet_name='Cluster', index=False)

print(f"✅ Selesai! Data 2025 berhasil diperbarui. File baru tersimpan sebagai: {file_output}")