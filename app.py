import streamlit as st
import pandas as pd
import numpy as np
import re
import logging

# ===== Logging =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

st.set_page_config(page_title="Analisis Komisi vs Biaya Iklan", layout="wide")
st.title("📊 Analisis Komisi Harian vs Biaya Iklan")

# ---------- Helpers ----------

def num_clean(series):
    """Membersihkan series pandas yang berisi string angka menjadi numeric."""
    if pd.api.types.is_numeric_dtype(series):
        return series
    # Ganti semua yang bukan digit, koma, titik, atau minus dengan string kosong
    s = series.astype(str).str.replace(r"[^\d,\.\-]", "", regex=True)
    # Hapus titik ribuan, lalu ganti koma desimal dengan titik (standar float)
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce").fillna(0.0)

def detect_date_columns(df):
    """Mendeteksi kolom tanggal dari NAMA kolom dan mengonversinya ke objek date."""
    col2date = {}
    for col in df.columns:
        # Coba parsing dengan format yyyy-mm-dd (lebih umum) lalu dd-mm-yyyy
        try:
            date_val = pd.to_datetime(str(col).split()[0], dayfirst=False).date()
            col2date[col] = date_val
        except (ValueError, TypeError):
            try:
                date_val = pd.to_datetime(str(col).split()[0], dayfirst=True).date()
                col2date[col] = date_val
            except (ValueError, TypeError):
                continue
    return col2date

def style_roi(val):
    """Memberi warna pada sel ROI berdasarkan nilainya."""
    if pd.isna(val) or not isinstance(val, (int, float)):
        return ""
    if val >= 200:
        # Semakin tinggi, semakin hijau
        g = max(50, int(255 - (val - 200) * 0.5))
        return f"background-color: rgb(0,{g},0); color: white;"
    else:
        # Semakin rendah, semakin merah
        r_val = 255
        gb_val = max(0, int(255 * (val / 200)))
        return f"background-color: rgb({r_val},{gb_val},{gb_val}); color: white;"

def standardize_key_columns(df, file_type):
    """Menemukan dan mengganti nama kolom kunci ('Studio', 'Username') menjadi nama standar."""
    df_renamed = df.copy()
    col_map = {c.lower().strip().replace(" ", ""): c for c in df_renamed.columns}

    # Cari dan ganti nama kolom Studio
    studio_key = next((k for k in ["studio", "namastudio"] if k in col_map), None)
    if not studio_key:
        raise ValueError(f"Tidak menemukan kolom 'Studio' atau 'Nama Studio' di data {file_type}.")
    df_renamed.rename(columns={col_map[studio_key]: "Studio"}, inplace=True)

    # Cari dan ganti nama kolom Username
    user_key = next((k for k in ["username", "user", "akun"] if k in col_map), None)
    if not user_key:
        raise ValueError(f"Tidak menemukan kolom 'Username'/'User'/'Akun' di data {file_type}.")
    df_renamed.rename(columns={col_map[user_key]: "Username"}, inplace=True)
    
    return df_renamed

# ---------- UI Upload ----------
st.subheader("📥 Upload Data")
komisi_file = st.file_uploader("Data Komisi Harian (CSV/Excel)", type=["csv", "xlsx"])
biaya_file  = st.file_uploader("Data Biaya Iklan (CSV/Excel)", type=["csv", "xlsx"])

if komisi_file and biaya_file:
    try:
        # Baca file
        dfk = pd.read_excel(komisi_file) if komisi_file.name.endswith(".xlsx") else pd.read_csv(komisi_file, sep=None, engine="python")
        dfb = pd.read_excel(biaya_file) if biaya_file.name.endswith(".xlsx") else pd.read_csv(biaya_file, sep=None, engine="python")

        # Standarisasi kolom kunci
        dfk = standardize_key_columns(dfk, "komisi")
        dfb = standardize_key_columns(dfb, "biaya")

        # Exclude baris TOTAL (lebih robust dengan .str.contains)
        dfk = dfk[~dfk["Username"].astype(str).str.contains("TOTAL", case=False, na=False)]
        dfb = dfb[~dfb["Username"].astype(str).str.contains("TOTAL", case=False, na=False)]

        # Deteksi kolom tanggal
        komisi_dates = detect_date_columns(dfk)
        biaya_dates  = detect_date_columns(dfb)

        # Cari tanggal yang sama
        common_dates = sorted(list(set(komisi_dates.values()) & set(biaya_dates.values())))

        if not common_dates:
            st.error("❌ Tidak ada tanggal yang cocok antara data komisi & biaya.")
            st.stop()

        # UI Pilihan rentang tanggal
        st.subheader("📅 Pilih Rentang Tanggal")
        date_labels = [d.isoformat() for d in common_dates]
        start_label = st.selectbox("Tanggal Mulai", options=date_labels, index=0)
        end_label   = st.selectbox("Tanggal Akhir", options=date_labels, index=len(date_labels)-1)

        start_d, end_d = pd.to_datetime(start_label).date(), pd.to_datetime(end_label).date()
        if start_d > end_d:
            st.error("Tanggal Mulai tidak boleh lebih besar dari Tanggal Akhir.")
            st.stop()

        # Filter kolom berdasarkan rentang tanggal
        k_cols = [col for col, date in komisi_dates.items() if start_d <= date <= end_d]
        b_cols = [col for col, date in biaya_dates.items() if start_d <= date <= end_d]

        # ---------- Proses Data (Lebih Efisien dengan Vectorization) ----------
        
        # 1. Hitung Est. Komisi
        komisi_sum = dfk[["Studio", "Username"]].copy()
        # Ekstrak angka pertama sebelum ' - ' menggunakan regex, lalu bersihkan
        komisi_data = dfk[k_cols].astype(str).apply(lambda x: x.str.extract(r"^(\s*[\d\.]+)", expand=False))
        komisi_sum["Est. Komisi"] = num_clean(komisi_data.stack()).groupby(level=0).sum()
        komisi_agg = komisi_sum.groupby(["Studio", "Username"])["Est. Komisi"].sum().reset_index()

        # 2. Hitung Biaya Iklan
        biaya_sum = dfb[["Studio", "Username"]].copy()
        # Ambil bagian pertama sebelum '|', lalu bersihkan
        biaya_data = dfb[b_cols].astype(str).apply(lambda x: x.str.split("|").str[0])
        biaya_sum["Biaya Iklan"] = num_clean(biaya_data.stack()).groupby(level=0).sum()
        biaya_agg = biaya_sum.groupby(["Studio", "Username"])["Biaya Iklan"].sum().reset_index()
        
        # ---------- Merge & ROI (Gunakan 'outer' agar tidak ada data hilang) ----------
        merged = pd.merge(komisi_agg, biaya_agg, on=["Studio", "Username"], how="outer").fillna(0)
        
        merged["ROI (%)"] = np.where(
            merged["Biaya Iklan"] > 0,
            (merged["Est. Komisi"] / merged["Biaya Iklan"]) * 100.0,
            0.0
        )

        # ---------- Tampilkan Hasil ----------
        st.subheader("📊 Hasil Analisis")
        show = merged.sort_values(["Studio", "Username"]).reset_index(drop=True)
        show = show[["Studio", "Username", "Biaya Iklan", "Est. Komisi", "ROI (%)"]]

        styled = show.style.format({
            "Biaya Iklan": "Rp {:,.0f}",
            "Est. Komisi": "Rp {:,.0f}",
            "ROI (%)": "{:.2f}%"
        }).applymap(style_roi, subset=["ROI (%)"])

        st.dataframe(styled, use_container_width=True)

        # Download
        csv = show.to_csv(index=False).encode("utf-8")
        st.download_button("💾 Download CSV", csv, "hasil_analisis.csv", "text/csv")

    except Exception as e:
        st.error(f"❌ Terjadi error: {e}")
        logging.exception("Gagal memproses file")
