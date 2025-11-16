import streamlit as st
import pandas as pd
import re

st.title("Rekap Komisi & Omset Shopee per Akun")

st.write("Paste data mentah di bawah ini:")

raw_text = st.text_area("Input Data", height=300)

def parse_number(num_str):
    """Convert angka '1.234.567' menjadi integer 1234567."""
    if num_str.strip() == "-" or num_str.strip() == "0":
        return 0
    return int(num_str.replace(".", "").strip())

def parse_item(item):
    """
    Format item contoh:
    63.406 - 983.145 (B)
    0 - 0
    """
    # Hilangkan grade (C), (B), (D), (S), dst
    clean = re.sub(r"\([A-Za-z0-9\+\-]+\)", "", item).strip()

    try:
        komisi, omset = clean.split("-")
        komisi = parse_number(komisi)
        omset = parse_number(omset)
        return komisi, omset
    except:
        return 0, 0

def process_data(text):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        studio = parts[0]
        username = parts[1]

        items = " ".join(parts[2:])
        cols = items.split("\t") if "\t" in items else items.split("  ")

        komisi_total = 0
        omset_total = 0

        # Loop tiap kolom tanggal (komisi - omset)
        for col in cols:
            col = col.strip()
            if col == "":
                continue
            k, o = parse_item(col)
            komisi_total += k
            omset_total += o

        rows.append([username, komisi_total, omset_total])

    df = pd.DataFrame(rows, columns=["Username", "Komisi", "Omset"])
    return df

if st.button("Proses Data"):
    try:
        df = process_data(raw_text)

        total_komisi = df["Komisi"].sum()
        total_omset = df["Omset"].sum()

        st.subheader("Hasil Rekap")

        st.dataframe(df)

        st.subheader("TOTAL")
        total_df = pd.DataFrame({
            "Username": ["ALL"],
            "Komisi": [total_komisi],
            "Omset": [total_omset]
        })
        st.dataframe(total_df)

    except Exception as e:
        st.error(f"ERROR: {e}")
