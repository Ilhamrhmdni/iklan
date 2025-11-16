import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Rekap Komisi & Omset Studio", layout="wide")

st.title("Rekap Komisi & Omset Harian (Auto SUM)")

st.write("""
Paste data mentah di bawah ini (format seperti dari Shopee):
""")

raw_text = st.text_area("Input Data", height=400, placeholder="Paste data di sini...")

def parse_number(value):
    # Hilangkan grade (contoh: (B), (C), (S), (D))
    value = re.sub(r"\([A-Z]\)", "", value).strip()
    
    # Pisahkan komisi - omset
    if "-" not in value:
        return 0, 0
    
    komisi_raw, omset_raw = value.split("-")
    
    # Hilangkan titik ribuan
    komisi = int(komisi_raw.replace(".", "").strip())
    omset = int(omset_raw.replace(".", "").strip())
    
    return komisi, omset

def process_data(raw):
    rows = []
    lines = raw.split("\n")

    for line in lines:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        
        studio = parts[0]
        username = parts[1]

        # Data tanggal mulai kolom ke-3
        tanggal_data = parts[2:]

        total_komisi = 0
        total_omset = 0

        for item in tanggal_data:
            if item.strip() == "" or item == "0 - 0":
                continue
            
            komisi, omset = parse_number(item)
            total_komisi += komisi
            total_omset += omset

        rows.append([username, total_komisi, total_omset])

    df = pd.DataFrame(rows, columns=["Username", "Est. Komisi", "Omset"])
    
    # Tambahkan total keseluruhan
    total_row = pd.DataFrame([[
        "TOTAL",
        df["Est. Komisi"].sum(),
        df["Omset"].sum()
    ]], columns=df.columns)

    df = pd.concat([df, total_row], ignore_index=True)
    return df

if raw_text.strip():
    df = process_data(raw_text)
    
    st.subheader("Hasil Rekap")
    st.dataframe(df, use_container_width=True)

    st.subheader("Download CSV")
    st.download_button(
        label="Download Rekap CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="rekap_komisi_omset.csv",
        mime="text/csv"
    )
else:
    st.info("Silakan paste data mentah pada kolom input di atas.")
