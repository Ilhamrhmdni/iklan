import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO, BytesIO
from datetime import datetime
import logging

# --- Konfigurasi Logging ---
# Setup logging untuk menampilkan info di terminal saat debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(layout="wide", page_title="Advanced ROI Analyzer")

# --- Fungsi-Fungsi Inti ---

def load_data(uploaded_file, pasted_text):
    """Memuat data dari file yang diunggah atau teks yang ditempel."""
    if uploaded_file is not None:
        try:
            # Menggunakan BytesIO untuk membaca file di memori
            file_buffer = BytesIO(uploaded_file.getvalue())
            if uploaded_file.name.endswith('.csv'):
                return pd.read_csv(file_buffer)
            elif uploaded_file.name.endswith(('.xls', '.xlsx')):
                return pd.read_excel(file_buffer, engine='openpyxl')
        except Exception as e:
            st.error(f"Gagal membaca file {uploaded_file.name}: {e}")
            return pd.DataFrame()
    elif pasted_text:
        try:
            return pd.read_csv(StringIO(pasted_text.strip()), sep='\t', lineterminator='\n')
        except Exception as e:
            st.error(f"Gagal memproses data yang ditempel: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def clean_numeric_value(series):
    """Membersihkan seri Pandas untuk mengubahnya menjadi numerik."""
    # Hapus semua karakter non-numerik kecuali tanda minus
    cleaned_series = series.astype(str).str.replace(r'[^\d-]', '', regex=True)
    # Konversi ke numerik, ubah error menjadi NaN, lalu isi NaN dengan 0
    return pd.to_numeric(cleaned_series, errors='coerce').fillna(0)

def normalize_and_process(df, value_name):
    """
    Menormalkan nama kolom, mengubah format dari wide ke long, dan membersihkan data.
    """
    if df.empty:
        return pd.DataFrame()

    logging.info(f"--- Memproses data untuk: {value_name} ---")
    logging.info(f"Kolom asli terbaca: {df.columns.tolist()}")

    # 1. Normalisasi Nama Kolom
    rename_map = {
        col: 'Studio' for col in df.columns if 'studio' in col.lower()
    }
    rename_map.update({
        col: 'Username' for col in df.columns if 'user' in col.lower()
    })
    
    df.rename(columns=rename_map, inplace=True)
    logging.info(f"Mapping nama kolom yang diterapkan: {rename_map}")
    logging.info(f"Kolom setelah normalisasi: {df.columns.tolist()}")

    if 'Studio' not in df.columns or 'Username' not in df.columns:
        st.error(f"Data '{value_name}' harus memiliki kolom 'Studio' dan 'Username'.")
        return pd.DataFrame()

    # 2. Melt Data (Wide to Long)
    id_vars = ['Studio', 'Username']
    date_cols = [col for col in df.columns if col not in id_vars]
    
    df_long = pd.melt(df, id_vars=id_vars, value_vars=date_cols, var_name='Tanggal', value_name=value_name)
    
    # 3. Cleaning
    df_long['Tanggal'] = pd.to_datetime(df_long['Tanggal'], errors='coerce')
    df_long[value_name] = clean_numeric_value(df_long[value_name])
    
    # Hapus baris dengan tanggal yang tidak valid
    df_long.dropna(subset=['Tanggal'], inplace=True)
    
    logging.info(f"Tipe data setelah cleaning untuk '{value_name}':\n{df_long.dtypes}")
    
    return df_long

def style_roi_column(df):
    """Menerapkan background gradient pada kolom ROI."""
    cm_red = st.theme.get_theme().secondary_background_color
    cm_green = 'mediumseagreen' # Warna hijau yang lebih jelas
    
    # Buat style dengan gradient merah-putih-hijau
    return df.style.background_gradient(
        cmap='coolwarm', # Peta warna yang cocok untuk divergensi
        subset=['ROI (%)'],
        vmin=0, # Minimum untuk skala warna
        vmax=400  # Maksimum untuk skala warna (ROI 400% akan menjadi hijau paling pekat)
    ).format({
        'Est. Komisi': 'Rp {:,.0f}',
        'Biaya Iklan': 'Rp {:,.0f}',
        'ROI (%)': '{:,.2f}%'
    })


# --- Tampilan Aplikasi Streamlit ---

st.title("📊 Analisis ROI Iklan Tingkat Lanjut")

# --- Input Data ---
col1, col2 = st.columns(2)

with col1:
    st.header("1. Data Komisi Harian")
    comm_upload_tab, comm_paste_tab = st.tabs(["📁 Upload File", "📋 Paste Data"])
    with comm_upload_tab:
        commission_file = st.file_uploader("Upload file Komisi (CSV/Excel)", type=['csv', 'xlsx', 'xls'], key="comm_file")
    with comm_paste_tab:
        commission_text = st.text_area("Atau tempelkan data komisi di sini (dipisahkan TAB)", height=150, key="comm_paste")

with col2:
    st.header("2. Data Biaya Iklan")
    cost_upload_tab, cost_paste_tab = st.tabs(["📁 Upload File", "📋 Paste Data"])
    with cost_upload_tab:
        cost_file = st.file_uploader("Upload file Biaya Iklan (CSV/Excel)", type=['csv', 'xlsx', 'xls'], key="cost_file")
    with cost_paste_tab:
        cost_text = st.text_area("Atau tempelkan data biaya iklan di sini (dipisahkan TAB)", height=150, key="cost_paste")

# --- Pemilihan Tanggal ---
st.header("3. Pilih Rentang Tanggal")
d_col1, d_col2 = st.columns(2)
start_date = d_col1.date_input("🗓️ Tanggal Mulai", datetime(2025, 8, 1).date())
end_date = d_col2.date_input("🗓️ Tanggal Akhir", datetime(2025, 8, 27).date())

# --- Proses & Output ---
if st.button("🚀 Proses & Hitung ROI", type="primary", use_container_width=True):
    # Load data dari sumber yang dipilih
    df_comm_raw = load_data(commission_file, commission_text)
    df_cost_raw = load_data(cost_file, cost_text)

    if df_comm_raw.empty or df_cost_raw.empty:
        st.warning("Pastikan kedua sumber data (Komisi dan Biaya Iklan) sudah diisi.")
    else:
        with st.spinner("Menormalkan, membersihkan, dan menghitung data..."):
            # Proses kedua dataset
            df_comm_long = normalize_and_process(df_comm_raw, 'Est. Komisi')
            df_cost_long = normalize_and_process(df_cost_raw, 'Biaya Iklan')

            if df_comm_long.empty or df_cost_long.empty:
                st.error("Gagal memproses salah satu dataset. Periksa log di terminal untuk detail.")
            else:
                # Gabungkan kedua dataset
                df_merged = pd.merge(df_comm_long, df_cost_long, on=['Studio', 'Username', 'Tanggal'], how='outer').fillna(0)

                # Filter berdasarkan rentang tanggal
                mask = (df_merged['Tanggal'].dt.date >= start_date) & (df_merged['Tanggal'].dt.date <= end_date)
                df_filtered = df_merged[mask]

                # Group by dan agregasi
                result = df_filtered.groupby(['Studio', 'Username']).agg({
                    'Est. Komisi': 'sum',
                    'Biaya Iklan': 'sum'
                }).reset_index()

                # Hitung ROI
                result['ROI (%)'] = np.where(result['Biaya Iklan'] > 0, (result['Est. Komisi'] / result['Biaya Iklan']) * 100, 0)
                
                logging.info(f"Contoh data final sebelum ditampilkan:\n{result.head().to_string()}")

                st.success("🎉 Analisis Selesai!")
                st.subheader("Tabel Hasil Analisis ROI")
                
                # Tampilkan hasil dengan styling
                st.dataframe(style_roi_column(result), use_container_width=True)

                # Fitur Download
                csv_buffer = StringIO()
                result.to_csv(csv_buffer, index=False, encoding='utf-8')
                st.download_button(
                    label="📥 Download Hasil sebagai CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"hasil_roi_{start_date}_sd_{end_date}.csv",
                    mime="text/csv",
                )

