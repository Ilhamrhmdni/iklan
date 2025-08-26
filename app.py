import streamlit as st
import pandas as pd
import numpy as np
import logging

# ===== Konfigurasi Logging =====
# Berguna untuk debugging jika dijalankan di lingkungan server
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ===== Konfigurasi Halaman Streamlit =====
st.set_page_config(page_title="Analisis ROI Iklan", layout="wide")
st.title("📊 Analisis Komisi Harian vs Biaya Iklan")

# ==============================================================================
# ---------- BAGIAN FUNGSI HELPER (PEMBANTU) ----------
# ==============================================================================

def num_clean(series):
    """
    Membersihkan sebuah Series pandas yang berisi string angka menjadi tipe data numerik.
    Fungsi ini dirancang untuk menangani format ribuan (titik) dan desimal (koma) secara aman.
    """
    # Jika sudah numerik, tidak perlu diproses lagi
    if pd.api.types.is_numeric_dtype(series):
        return series
    
    # Konversi ke string, hapus semua karakter non-numerik kecuali koma, titik, dan minus
    s = series.astype(str).str.replace(r"[^\d,\.\-]", "", regex=True)
    
    # Hapus titik (pemisah ribuan), lalu ganti koma (pemisah desimal) dengan titik
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    
    # Konversi ke numerik. Data yang gagal (teks, dll) akan menjadi NaN, lalu isi NaN dengan 0.
    # Ini adalah kunci untuk mencegah error 'float' vs 'str'.
    return pd.to_numeric(s, errors="coerce").fillna(0.0)

def detect_date_columns(df):
    """
    Mendeteksi kolom yang namanya adalah tanggal dan mengonversinya ke objek date.
    Secara otomatis mencoba format yyyy-mm-dd dan dd-mm-yyyy.
    """
    col2date = {}
    for col in df.columns:
        token = str(col).strip().split()[0]
        try:
            # Coba format standar (yyyy-mm-dd) terlebih dahulu, lebih umum
            date_val = pd.to_datetime(token, dayfirst=False).date()
            col2date[col] = date_val
        except (ValueError, TypeError):
            try:
                # Jika gagal, coba format dengan hari di depan (dd-mm-yyyy)
                date_val = pd.to_datetime(token, dayfirst=True).date()
                col2date[col] = date_val
            except (ValueError, TypeError):
                # Abaikan jika bukan format tanggal
                continue
    return col2date

def style_roi(val):
    """Memberi warna latar pada sel ROI berdasarkan nilainya untuk visualisasi."""
    if pd.isna(val) or not isinstance(val, (int, float)):
        return ""
    
    if val >= 200:
        # Semakin tinggi ROI di atas 200, semakin pekat hijaunya
        g = max(50, int(255 - (val - 200) * 0.5))
        return f"background-color: rgb(0,{g},0); color: white;"
    else:
        # Di bawah 200%, warna bergradasi dari merah pekat (ROI 0) ke kuning (mendekati ROI 200)
        r_val = 255
        gb_val = max(0, int(255 * (val / 200))) 
        return f"background-color: rgb({r_val},{gb_val},{gb_val}); color: white;"

def standardize_key_columns(df, file_type):
    """
    Menemukan dan mengganti nama kolom kunci ('Studio', 'Username') menjadi nama standar.
    Membuat skrip lebih fleksibel terhadap variasi nama kolom di file sumber.
    """
    df_renamed = df.copy()
    # Buat pemetaan nama kolom versi lowercase tanpa spasi ke nama asli
    col_map = {c.lower().strip().replace(" ", ""): c for c in df_renamed.columns}

    # Cari dan ganti nama kolom untuk 'Studio'
    studio_key = next((k for k in ["studio", "namastudio"] if k in col_map), None)
    if not studio_key:
        raise ValueError(f"Tidak menemukan kolom 'Studio' atau 'Nama Studio' di data {file_type}.")
    df_renamed.rename(columns={col_map[studio_key]: "Studio"}, inplace=True)

    # Cari dan ganti nama kolom untuk 'Username'
    user_key = next((k for k in ["username", "user", "akun"] if k in col_map), None)
    if not user_key:
        raise ValueError(f"Tidak menemukan kolom 'Username'/'User'/'Akun' di data {file_type}.")
    df_renamed.rename(columns={col_map[user_key]: "Username"}, inplace=True)
    
    return df_renamed

# ==============================================================================
# ---------- BAGIAN UTAMA APLIKASI STREAMLIT ----------
# ==============================================================================

# --- UI untuk Upload File ---
st.subheader("📥 Upload Data")
komisi_file = st.file_uploader("1. Upload Data Komisi Harian (CSV/Excel)", type=["csv", "xlsx"])
biaya_file  = st.file_uploader("2. Upload Data Biaya Iklan (CSV/Excel)", type=["csv", "xlsx"])

# --- Proses Utama (berjalan jika kedua file sudah di-upload) ---
if komisi_file and biaya_file:
    try:
        # 1. Baca file dari upload pengguna
        dfk = pd.read_excel(komisi_file) if komisi_file.name.endswith(".xlsx") else pd.read_csv(komisi_file, sep=None, engine="python")
        dfb = pd.read_excel(biaya_file) if biaya_file.name.endswith(".xlsx") else pd.read_csv(biaya_file, sep=None, engine="python")

        # 2. Standarisasi nama kolom kunci ('Studio', 'Username')
        dfk = standardize_key_columns(dfk, "komisi")
        dfb = standardize_key_columns(dfb, "biaya")

        # 3. Exclude baris yang berisi 'TOTAL' di kolom Username (case-insensitive)
        dfk = dfk[~dfk["Username"].astype(str).str.contains("TOTAL", case=False, na=False)]
        dfb = dfb[~dfb["Username"].astype(str).str.contains("TOTAL", case=False, na=False)]

        # 4. Deteksi otomatis semua kolom tanggal di kedua file
        komisi_dates = detect_date_columns(dfk)
        biaya_dates  = detect_date_columns(dfb)

        # 5. Cari tanggal yang sama di kedua dataset sebagai dasar analisis
        common_dates = sorted(list(set(komisi_dates.values()) & set(biaya_dates.values())))

        if not common_dates:
            st.error("❌ Tidak ada tanggal yang cocok antara data komisi & biaya. Pastikan format tanggal di header kolom benar.")
            st.stop()

        # 6. UI untuk memilih rentang tanggal analisis
        st.subheader("📅 Pilih Rentang Tanggal")
        date_labels = [d.isoformat() for d in common_dates]
        start_label = st.selectbox("Tanggal Mulai", options=date_labels, index=0)
        end_label   = st.selectbox("Tanggal Akhir", options=date_labels, index=len(date_labels)-1)

        start_d, end_d = pd.to_datetime(start_label).date(), pd.to_datetime(end_label).date()
        if start_d > end_d:
            st.error("Tanggal Mulai tidak boleh lebih besar dari Tanggal Akhir.")
            st.stop()

        # 7. Filter kolom berdasarkan rentang tanggal yang dipilih pengguna
        k_cols = [col for col, date in komisi_dates.items() if start_d <= date <= end_d]
        b_cols = [col for col, date in biaya_dates.items() if start_d <= date <= end_d]

        # 8. Proses Agregasi Data (Metode Vectorized yang Cepat dan Efisien)
        
        # Hitung Total Estimasi Komisi
        komisi_sum = dfk[["Studio", "Username"]].copy()
        komisi_data = dfk[k_cols].astype(str).apply(lambda x: x.str.extract(r"^(\s*[\d\.]+)", expand=False))
        komisi_sum["Est. Komisi"] = num_clean(komisi_data.stack()).groupby(level=0).sum()
        komisi_agg = komisi_sum.groupby(["Studio", "Username"])["Est. Komisi"].sum().reset_index()

        # Hitung Total Biaya Iklan
        biaya_sum = dfb[["Studio", "Username"]].copy()
        biaya_data = dfb[b_cols].astype(str).apply(lambda x: x.str.split("|").str[0])
        biaya_sum["Biaya Iklan"] = num_clean(biaya_data.stack()).groupby(level=0).sum()
        biaya_agg = biaya_sum.groupby(["Studio", "Username"])["Biaya Iklan"].sum().reset_index()
        
        # 9. Gabungkan Data & Hitung ROI
        # Menggunakan 'outer' merge untuk memastikan tidak ada data pengguna yang hilang
        merged = pd.merge(komisi_agg, biaya_agg, on=["Studio", "Username"], how="outer").fillna(0)
        
        # Kalkulasi ROI yang aman dari error pembagian dengan nol dan tipe data
        merged["ROI (%)"] = np.where(
            merged["Biaya Iklan"] > 0,
            (merged["Est. Komisi"] / merged["Biaya Iklan"]) * 100.0,
            0.0
        )

        # 10. Tampilkan Hasil Akhir
        st.subheader("📈 Hasil Analisis")
        show = merged.sort_values(["Studio", "Username"]).reset_index(drop=True)
        show = show[["Studio", "Username", "Biaya Iklan", "Est. Komisi", "ROI (%)"]]

        styled = show.style.format({
            "Biaya Iklan": "Rp {:,.0f}",
            "Est. Komisi": "Rp {:,.0f}",
            "ROI (%)": "{:.2f}%"
        }).applymap(style_roi, subset=["ROI (%)"])

        st.dataframe(styled, use_container_width=True)

        # 11. Tombol untuk mengunduh hasil analisis
        csv = show.to_csv(index=False).encode("utf-8")
        st.download_button("💾 Download Hasil (CSV)", csv, "hasil_analisis_roi.csv", "text/csv")

    except Exception as e:
        st.error(f"❌ Terjadi error saat memproses data: {e}")
        logging.exception("Gagal memproses file")
