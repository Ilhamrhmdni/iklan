import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime

# --- Konfigurasi Halaman ---
st.set_page_config(layout="wide", page_title="Analisis ROI Iklan")

# --- Fungsi-Fungsi Pengolahan Data ---

def process_commission_data(raw_text: str) -> pd.DataFrame:
    """Mengolah data mentah komisi harian menjadi DataFrame yang terstruktur."""
    try:
        data_io = StringIO(raw_text.strip())
        df = pd.read_csv(data_io, sep='\t', header=0, lineterminator='\n')

        main_cols = ['Nama Studio', 'Username', 'Saldo', 'Total Penjualan', 'Total Biaya Iklan']
        date_cols = [col for col in df.columns if col not in main_cols]

        df_processed = df[main_cols].copy()

        for col in main_cols[2:]:
             df_processed[col] = pd.to_numeric(df_processed[col].astype(str).str.replace('.', '', regex=False), errors='coerce').fillna(0)

        for col_date in date_cols:
            clean_date = col_date.split(' ')[0]
            split_data = df[col_date].astype(str).str.split(' \| ', expand=True)
            if split_data.shape[1] == 4:
                komisi_col_name = f"Komisi_{clean_date}"
                split_data.columns = [f"Biaya_{clean_date}", f"Penjualan_{clean_date}", f"ROI_{clean_date}", komisi_col_name]
                df_processed[komisi_col_name] = pd.to_numeric(split_data[komisi_col_name].astype(str).str.replace('.', '', regex=False), errors='coerce').fillna(0)
        
        return df_processed
    except Exception as e:
        st.error(f"Error saat memproses data komisi: {e}. Pastikan format data (terutama header) sudah benar dan menggunakan pemisah TAB.")
        return pd.DataFrame()

def process_ad_cost_data(raw_text: str) -> pd.DataFrame:
    """Mengolah data mentah biaya iklan. Meniru logika VLOOKUP."""
    try:
        data_io = StringIO(raw_text.strip())
        # Asumsi data hanya 2 kolom: Username dan Biaya Iklan, tanpa header
        df = pd.read_csv(data_io, sep='\t', header=None, lineterminator='\n')
        df.columns = ['Username', 'Biaya Iklan']
        df['Biaya Iklan'] = pd.to_numeric(df['Biaya Iklan'].astype(str).str.replace('.', '', regex=False), errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error saat memproses data biaya iklan: {e}. Pastikan formatnya adalah 'Username [TAB] Biaya Iklan' per baris.")
        return pd.DataFrame()

# --- Tampilan Aplikasi Streamlit ---

st.title("📈 Aplikasi Analisis ROI Iklan Otomatis")
st.markdown("Aplikasi ini menggabungkan dua sumber data untuk menghitung performa iklan per akun dalam rentang waktu tertentu.")

# --- Langkah 1: Input Data Komisi Harian ---
with st.expander("Langkah 1: Masukkan Data Komisi Harian", expanded=True):
    st.info("Tempelkan data komisi harian dari spreadsheet. Pastikan baris pertama adalah **header** dan pemisah antar kolom adalah **TAB**.", icon="📋")
    SAMPLE_COMMISSION = """Nama Studio	Username	Saldo	Total Penjualan	Total Biaya Iklan	2025-08-25 00:00	2025-08-24 00:00	2025-08-23 00:00
STUDIO PUSAT	khusustecno	0	44.425.886	465.000	0 | 336.930 | 0% | 0	60.000 | 250.000 | 4.17% | 54	71.793 | 3.388.560 | 47.20% | 130
BOS METRO	top_service.workshop	14.224	18.049.447	505.699	40.384 | 1.826.794 | 45.24% | 275	18.891 | 930.070 | 49.23% | 153	4.086 | 84.999 | 20.80% | 70
BOS METRO	prabotan_rumah_tangga60	0	24.133.613	559.511	87.868 | 4.237.693 | 48.23% | 481	36.849 | 1.631.419 | 44.27% | 441	9.794 | 366.488 | 37.42% | 23
"""
    commission_text = st.text_area("Data Komisi Harian:", value=SAMPLE_COMMISSION, height=200, key="commission_input")

# --- Langkah 2: Input Data Biaya Iklan ---
with st.expander("Langkah 2: Masukkan Data Biaya Iklan (Sumber untuk VLOOKUP)", expanded=True):
    st.info("Tempelkan data biaya iklan dengan format: `Username [TAB] Biaya Iklan`. **Tanpa header**.", icon="💰")
    SAMPLE_COST = """khusustecno	465000
top_service.workshop	505699
prabotan_rumah_tangga60	559511
"""
    cost_text = st.text_area("Data Biaya Iklan:", value=SAMPLE_COST, height=150, key="cost_input")

# --- Langkah 3: Pilih Rentang Tanggal ---
st.markdown("---")
st.header("Langkah 3: Pilih Rentang Waktu Analisis")
col1, col2 = st.columns(2)
try:
    start_date = col1.date_input("🗓️ Tanggal Mulai", value=datetime(2025, 8, 23))
    end_date = col2.date_input("🗓️ Tanggal Akhir", value=datetime(2025, 8, 25))
except Exception: # Fallback for potential date issues
    start_date = col1.date_input("🗓️ Tanggal Mulai")
    end_date = col2.date_input("🗓️ Tanggal Akhir")

# --- Tombol Proses dan Output ---
st.markdown("---")
if st.button("🚀 Proses & Hitung ROI", type="primary", use_container_width=True):
    if not commission_text or not cost_text:
        st.warning("Harap pastikan kedua data (Komisi dan Biaya Iklan) sudah dimasukkan.")
    else:
        with st.spinner("Menggabungkan dan menghitung data..."):
            df_commission = process_commission_data(commission_text)
            df_cost = process_ad_cost_data(cost_text)

            if not df_commission.empty and not df_cost.empty:
                # Filter kolom komisi berdasarkan rentang tanggal
                komisi_cols = [col for col in df_commission.columns if col.startswith('Komisi_')]
                selected_komisi_cols = []
                for col in komisi_cols:
                    try:
                        col_date_str = col.replace('Komisi_', '')
                        col_date = datetime.strptime(col_date_str, '%Y-%m-%d').date()
                        if start_date <= col_date <= end_date:
                            selected_komisi_cols.append(col)
                    except ValueError:
                        continue # Abaikan jika nama kolom tidak bisa diubah jadi tanggal
                
                if not selected_komisi_cols:
                    st.error("Tidak ada data komisi yang ditemukan pada rentang tanggal yang dipilih. Periksa kembali tanggal Anda atau data yang dimasukkan.")
                else:
                    # Hitung "Est. Komisi"
                    df_commission['Est. Komisi'] = df_commission[selected_komisi_cols].sum(axis=1)
                    
                    # Gabungkan data (simulasi VLOOKUP)
                    # Kita join berdasarkan 'Username'
                    df_final = pd.merge(
                        df_commission[['Nama Studio', 'Username', 'Est. Komisi']],
                        df_cost,
                        on='Username',
                        how='left' # Left join untuk menjaga semua user dari data komisi
                    ).fillna({'Biaya Iklan': 0})

                    # Hitung ROI
                    # Tambahkan kondisi untuk menghindari pembagian dengan nol
                    df_final['ROI'] = (df_final['Est. Komisi'] / df_final['Biaya Iklan']).where(df_final['Biaya Iklan'] != 0, 0)
                    
                    st.success("🎉 Perhitungan Selesai!")
                    st.subheader("Hasil Analisis ROI")

                    # Tampilkan tabel hasil
                    formatters = {
                        'Est. Komisi': '{:,.0f}',
                        'Biaya Iklan': '{:,.0f}',
                        'ROI': '{:.2%}'
                    }
                    st.dataframe(df_final.style.format(formatters), use_container_width=True)

                    # Siapkan tombol download
                    csv_data = df_final.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Hasil sebagai CSV",
                        data=csv_data,
                        file_name=f"analisis_roi_{start_date}_to_{end_date}.csv",
                        mime="text/csv",
                    )
            else:
                 st.error("Gagal memproses salah satu data. Mohon periksa kembali input Anda.")
