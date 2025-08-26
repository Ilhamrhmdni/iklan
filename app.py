import streamlit as st
import pandas as pd
import numpy as np
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

st.set_page_config(page_title="Analisis Komisi & Biaya Iklan", layout="wide")
st.title("📊 Analisis Komisi Harian vs Biaya Iklan")

# Fungsi untuk mapping nama kolom supaya fleksibel
def standardize_columns(df, file_type="komisi"):
    rename_map = {}

    if "Nama Studio" in df.columns:
        rename_map["Nama Studio"] = "Studio"
    elif "STUDIO" in df.columns:
        rename_map["STUDIO"] = "Studio"

    if "username" in df.columns:
        rename_map["username"] = "Username"
    elif "USER" in df.columns:
        rename_map["USER"] = "Username"

    if rename_map:
        df = df.rename(columns=rename_map)
        logging.info(f"{file_type} -> Rename applied: {rename_map}")

    return df

def load_data(file, file_type="komisi"):
    try:
        if file.name.endswith(".xlsx"):
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file, sep="\t")

        df.columns = df.columns.str.strip()
        df = standardize_columns(df, file_type=file_type)

        st.write(f"📂 Kolom terbaca dari {file_type}:", df.columns.tolist())
        return df
    except Exception as e:
        logging.error(f"Error loading {file_type} data: {e}")
        st.error(f"❌ Terjadi error saat parsing data {file_type}: {e}")
        return None

def highlight_roi(val):
    if pd.isna(val):
        return ""
    if val >= 200:
        intensity = min(255, int(255 - (val - 200) * 0.5))
        return f"background-color: rgb({intensity}, 255, {intensity})"
    else:
        intensity = min(255, int(255 - (200 - val) * 0.5))
        return f"background-color: rgb(255, {intensity}, {intensity})"

# Fungsi cleaning angka (buang Rp, %, titik, koma, dsb)
def clean_numeric(series):
    return (
        series.astype(str)
        .str.replace(r"[^0-9\.\-]", "", regex=True)
        .replace("", "0")
        .astype(float)
    )

# Upload file
komisi_file = st.file_uploader("📥 Upload Data Komisi Harian", type=["csv", "xlsx"])
biaya_file = st.file_uploader("📥 Upload Data Biaya Iklan", type=["csv", "xlsx"])

if komisi_file and biaya_file:
    komisi = load_data(komisi_file, "komisi")
    biaya = load_data(biaya_file, "biaya")

    if komisi is not None and biaya is not None:
        try:
            if not {"Studio", "Username"}.issubset(komisi.columns):
                st.error("❌ Data Komisi tidak memiliki kolom 'Studio' dan 'Username'")
                st.stop()
            if not {"Studio", "Username"}.issubset(biaya.columns):
                st.error("❌ Data Biaya tidak memiliki kolom 'Studio' dan 'Username'")
                st.stop()

            # Ambil kolom tanggal
            tanggal_cols = [col for col in komisi.columns if "-" in col]

            st.subheader("📅 Pilih Rentang Tanggal")
            start_date = st.selectbox("Tanggal Mulai", options=tanggal_cols, index=0)
            end_date = st.selectbox("Tanggal Akhir", options=tanggal_cols, index=len(tanggal_cols)-1)

            start_idx = tanggal_cols.index(start_date)
            end_idx = tanggal_cols.index(end_date)
            selected_dates = tanggal_cols[start_idx:end_idx+1]

            # --- Komisi ---
            komisi_long = komisi.melt(
                id_vars=["Studio", "Username"],
                value_vars=selected_dates,
                var_name="Tanggal",
                value_name="Komisi"
            )
            komisi_long["Komisi"] = clean_numeric(komisi_long["Komisi"])
            komisi_sum = komisi_long.groupby(["Studio", "Username"], as_index=False)["Komisi"].sum()
            komisi_sum = komisi_sum.rename(columns={"Komisi": "Est. Komisi"})

            # --- Biaya ---
            biaya_long = biaya.melt(
                id_vars=["Studio", "Username"],
                value_vars=selected_dates,
                var_name="Tanggal",
                value_name="Biaya"
            )
            biaya_long["Biaya"] = biaya_long["Biaya"].astype(str).str.split("|").str[0]
            biaya_long["Biaya"] = clean_numeric(biaya_long["Biaya"])
            biaya_sum = biaya_long.groupby(["Studio", "Username"], as_index=False)["Biaya"].sum()
            biaya_sum = biaya_sum.rename(columns={"Biaya": "Biaya Iklan"})

            # --- Merge ---
            merged = pd.merge(komisi_sum, biaya_sum, on=["Studio", "Username"], how="inner")

            # Paksa numeric lagi
            merged["Est. Komisi"] = clean_numeric(merged["Est. Komisi"])
            merged["Biaya Iklan"] = clean_numeric(merged["Biaya Iklan"])

            # Debug
            logging.info("Sample nilai sebelum ROI:\n%s", merged.head().to_string())
            logging.info("Tipe data kolom:\n%s", merged.dtypes)

            # --- ROI ---
            merged["ROI (%)"] = np.where(
                merged["Biaya Iklan"] > 0,
                (merged["Est. Komisi"] / merged["Biaya Iklan"]) * 100.0,
                0.0
            )

            # --- Output ---
            st.subheader("📊 Hasil Analisis")
            st.dataframe(merged.style.applymap(highlight_roi, subset=["ROI (%)"]))

            csv = merged.to_csv(index=False).encode("utf-8")
            st.download_button("💾 Download CSV", csv, "hasil_analisis.csv", "text/csv")

        except Exception as e:
            logging.error(f"Processing error: {e}")
            st.error(f"❌ Terjadi error saat memproses data: {e}")
