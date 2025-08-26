import streamlit as st
import pandas as pd
import re
from io import StringIO
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

st.set_page_config(page_title="Analisis ROI Shopee", layout="wide")
st.title("📊 Analisis ROI Shopee")

# Fungsi parsing data komisi
def split_data(cell):
    if pd.isna(cell) or str(cell).strip() in ["0", "0 - 0 (D)"]:
        return pd.Series([0, 0, None])
    match = re.match(r"([\d\.]+)\s*-\s*([\d\.]+)\s*\((.*?)\)", str(cell))
    if match:
        return pd.Series([
            int(match.group(1).replace(".", "")), 
            int(match.group(2).replace(".", "")), 
            match.group(3)
        ])
    return pd.Series([0, 0, None])

# Styling ROI
def color_roi(val):
    if pd.isna(val) or val == 0:
        return "color: black"
    if val >= 200:
        g = min(255, int(255 - (min(val, 600) - 200) * 0.6))
        return f"background-color: rgb(0,{g},0); color:white;"
    else:
        r = min(255, int(255 - max(val, 0) * 0.8))
        return f"background-color: rgb(255,{r},{r}); color:white;"

# Input data
st.subheader("📥 Paste Data Komisi Harian (copy dari Excel)")
komisi_text = st.text_area("Paste data komisi harian di sini")

st.subheader("📥 Paste Data Biaya Iklan (copy dari Excel)")
iklan_text = st.text_area("Paste data biaya iklan di sini")

if komisi_text and iklan_text:
    try:
        df_komisi = pd.read_csv(StringIO(komisi_text), sep="\t")
        df_iklan = pd.read_csv(StringIO(iklan_text), sep="\t")

        # Normalisasi nama kolom → lowercase semua
        df_komisi.columns = df_komisi.columns.str.strip().str.lower()
        df_iklan.columns = df_iklan.columns.str.strip().str.lower()

        # Mapping agar seragam
        rename_map = {
            "studio": "studio",
            "nama studio": "studio",
            "username": "username",
            "total biaya iklan": "biaya iklan",
            "biaya iklan": "biaya iklan"
        }
        df_komisi.rename(columns=rename_map, inplace=True)
        df_iklan.rename(columns=rename_map, inplace=True)

        # Debug tampilkan kolom
        st.write("### 🔍 Kolom Komisi:", df_komisi.columns.tolist())
        st.write("### 🔍 Kolom Iklan:", df_iklan.columns.tolist())

        # Cari kolom tanggal
        tanggal_cols = [col for col in df_komisi.columns if "-" in col]
        tanggal_cols_sorted = sorted(tanggal_cols, key=lambda x: pd.to_datetime(x, dayfirst=True, errors="coerce"))

        if not tanggal_cols_sorted:
            st.error("❌ Tidak ada kolom tanggal ditemukan di data komisi")
        else:
            start_date = st.selectbox("📅 Pilih Tanggal Awal", tanggal_cols_sorted)
            end_date = st.selectbox("📅 Pilih Tanggal Akhir", tanggal_cols_sorted, index=len(tanggal_cols_sorted)-1)

            if tanggal_cols_sorted.index(start_date) <= tanggal_cols_sorted.index(end_date):
                selected_cols = tanggal_cols_sorted[
                    tanggal_cols_sorted.index(start_date): tanggal_cols_sorted.index(end_date)+1
                ]

                # Proses data komisi
                processed = df_komisi[["studio", "username"]].copy()
                for col in selected_cols:
                    temp = df_komisi[col].apply(split_data)
                    temp.columns = [f"Komisi_{col}", f"Omset_{col}", f"Status_{col}"]
                    processed = pd.concat([processed, temp], axis=1)

                # Total komisi
                komisi_cols = [col for col in processed.columns if col.startswith("Komisi_")]
                processed["Est. Komisi"] = processed[komisi_cols].sum(axis=1)

                # Join dengan biaya iklan
                df_final = processed.merge(
                    df_iklan[["studio","username","biaya iklan"]],
                    on=["studio","username"], how="left"
                )

                # Hitung ROI
                df_final["ROI"] = (df_final["Est. Komisi"] / df_final["biaya iklan"]) * 100
                df_final["ROI"] = df_final["ROI"].fillna(0)

                # Styling tabel
                styled = df_final[["studio","username","biaya iklan","Est. Komisi","ROI"]] \
                            .style.applymap(color_roi, subset=["ROI"]) \
                            .format({
                                "biaya iklan": "Rp {:,.0f}",
                                "Est. Komisi": "Rp {:,.0f}",
                                "ROI": "{:.2f}%"
                            })

                st.write("### 📊 Hasil Analisis ROI")
                st.dataframe(styled, use_container_width=True)

                # Download tombol
                csv = df_final.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Download CSV", csv, "hasil_roi.csv", "text/csv")

    except Exception as e:
        st.error(f"❌ Error saat parsing data: {e}")
        logging.exception("🚨 Error detail")
