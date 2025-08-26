import streamlit as st
import pandas as pd
import re
from io import StringIO

st.set_page_config(page_title="Analisis ROI Shopee", layout="wide")
st.title("📊 Analisis ROI Shopee")

# --- Fungsi parsing komisi-omset ---
def split_data(cell):
    if pd.isna(cell) or str(cell).strip() in ["0", "0 - 0 (D)"]:
        return pd.Series([0, 0, None])
    match = re.match(r"([\d\.]+)\s*-\s*([\d\.]+)\s*\((.*?)\)", str(cell))
    if match:
        komisi = int(match.group(1).replace(".", ""))
        omset = int(match.group(2).replace(".", ""))
        status = match.group(3)
        return pd.Series([komisi, omset, status])
    return pd.Series([None, None, None])

# --- Input data paste ---
st.subheader("📥 Paste Data Komisi Harian (dari Excel)")
komisi_text = st.text_area("Paste data komisi harian di sini (format CSV/Excel)")

st.subheader("📥 Paste Data Biaya Iklan (dari Excel)")
iklan_text = st.text_area("Paste data biaya iklan di sini (format CSV/Excel)")

if komisi_text and iklan_text:
    try:
        # Convert text to DataFrame
        df_komisi = pd.read_csv(StringIO(komisi_text), sep="\t")
        df_iklan = pd.read_csv(StringIO(iklan_text), sep="\t")

        # Ambil kolom tanggal
        tanggal_cols = [col for col in df_komisi.columns if "-" in col]
        tanggal_cols_sorted = sorted(tanggal_cols, key=lambda x: pd.to_datetime(x, dayfirst=True))

        start_date = st.selectbox("📅 Pilih Tanggal Awal", tanggal_cols_sorted)
        end_date = st.selectbox("📅 Pilih Tanggal Akhir", tanggal_cols_sorted, index=len(tanggal_cols_sorted)-1)

        if tanggal_cols_sorted.index(start_date) <= tanggal_cols_sorted.index(end_date):
            selected_cols = tanggal_cols_sorted[
                tanggal_cols_sorted.index(start_date): tanggal_cols_sorted.index(end_date)+1
            ]

            # Proses data komisi
            processed = df_komisi[['Studio', 'Username']].copy()
            for col in selected_cols:
                temp = df_komisi[col].apply(split_data)
                temp.columns = [f"Komisi_{col}", f"Omset_{col}", f"Status_{col}"]
                processed = pd.concat([processed, temp], axis=1)

            # Hitung total komisi
            komisi_cols = [col for col in processed.columns if col.startswith("Komisi_")]
            processed["Est. Komisi"] = processed[komisi_cols].sum(axis=1)

            # Join dengan biaya iklan
            df_final = processed.merge(df_iklan[["Studio","Username","Total Biaya Iklan"]], 
                                       on=["Studio","Username"], how="left")
            df_final.rename(columns={"Total Biaya Iklan":"Biaya Iklan"}, inplace=True)

            # Hitung ROI
            df_final["ROI"] = (df_final["Est. Komisi"] / df_final["Biaya Iklan"]) * 100
            df_final["ROI"] = df_final["ROI"].fillna(0)

            # --- Styling ROI ---
            def color_roi(val):
                if pd.isna(val) or val == 0:
                    return "color: black"
                if val >= 200:
                    # hijau makin pekat kalau makin tinggi
                    g = min(255, int(255 - (min(val, 600) - 200) * 0.6))  # range 200%-600%
                    return f"background-color: rgb(0,{g},0); color:white;"
                else:
                    # merah makin pekat kalau makin rendah
                    r = min(255, int(255 - max(val, 0) * 0.8))  # range 0%-200%
                    return f"background-color: rgb(255,{r},{r}); color:white;"

            styled = df_final[["Studio","Username","Biaya Iklan","Est. Komisi","ROI"]].style.applymap(color_roi, subset=["ROI"])

            st.write("### 📊 Hasil Analisis ROI (dengan Highlight)")
            st.dataframe(styled, use_container_width=True)

            # Tombol download
            csv = df_final.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Hasil CSV", csv, "hasil_roi.csv", "text/csv")

    except Exception as e:
        st.error(f"Terjadi error saat parsing data: {e}")
