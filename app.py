import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Rekap Komisi Shopee", layout="wide")

st.title("Rekap Komisi & Omset Shopee per Akun")

st.write("Paste data mentahan di bawah ini (format Shopee)")

raw_text = st.text_area("Input Data", height=300)

def parse_cell(value):
    """
    Parse format seperti:
    63.406 - 983.145 (B)
    0 - 0
    """
    value = value.strip()

    # Jika kosong atau 0 - 0
    if value == "" or value == "0 - 0":
        return 0, 0
    
    # Ambil komisi & omset
    match = re.match(r"([\d\.]+)\s*-\s*([\d\.]+)", value)
    if not match:
        return 0, 0
    
    komisi = int(match.group(1).replace(".", ""))
    omset = int(match.group(2).replace(".", ""))
    return komisi, omset


def process_table(text):
    rows = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or "TOTAL" in line:
            continue

        parts = line.split("\t")
        if len(parts) < 3:
            continue
        
        studio = parts[0]
        username = parts[1]
        tanggal_values = parts[2:]

        total_komisi = 0
        total_omset = 0

        for cell in tanggal_values:
            k, o = parse_cell(cell)
            total_komisi += k
            total_omset += o

        rows.append([username, total_komisi, total_omset])

    df = pd.DataFrame(rows, columns=["Username", "Komisi", "Omset"])
    return df


if st.button("Proses Data"):
    if raw_text.strip() == "":
        st.error("Isi dulu datanya.")
    else:
        df = process_table(raw_text)
        st.subheader("Hasil Rekap")
        st.dataframe(df, use_container_width=True)

        st.subheader("TOTAL")
        total_row = pd.DataFrame([{
            "Username": "ALL",
            "Komisi": df["Komisi"].sum(),
            "Omset": df["Omset"].sum()
        }])
        st.dataframe(total_row, use_container_width=True)
