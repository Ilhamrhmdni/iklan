import streamlit as st
import pandas as pd
import re

st.title("Rekap Komisi & Omset Shopee per Akun")

st.write("Paste data mentahan di bawah ini:")

raw_text = st.text_area("Input Data", height=300)

def parse_value(text):
    """
    Menerima format seperti:
    63.406 - 983.145 (B)
    24.619 - 474.566 (D)
    0 - 0
    1.172.799 (S)
    """

    text = text.strip()

    # Jika "0 - 0"
    if text == "0 - 0":
        return 0, 0

    # Pisahkan komisi dan omset
    parts = text.split("-")
    if len(parts) < 2:
        return 0, 0

    komisi_raw = parts[0].strip()
    omset_raw = parts[1].strip()

    # Hapus grade (B), (C), (S), (S+), (D), dll
    omset_raw = re.sub(r"\([^)]*\)", "", omset_raw).strip()

    # Bersihkan titik ribuan
    komisi_raw = komisi_raw.replace(".", "").strip()
    omset_raw = omset_raw.replace(".", "").strip()

    # Convert ke integer aman
    try:
        komisi = int(komisi_raw)
    except:
        komisi = 0

    try:
        omset = int(omset_raw)
    except:
        omset = 0

    return komisi, omset


def process(raw):
    lines = raw.split("\n")
    data = {}

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        # Studio + Username
        studio = parts[0]
        username = parts[1]

        # Gabungkan kembali username jika mengandung spasi (jarang, tapi aman)
        if "_" not in username and "." in parts[2]:  
            username = f"{username} {parts[2]}"
            row_data = parts[3:]
        else:
            row_data = parts[2:]

        # Parsing semua tanggal dalam baris
        komisi_total = 0
        omset_total = 0

        joined = " ".join(row_data)
        entries = re.findall(r"([0-9\.\s]+-\s*[0-9\.\s]+(?:\s*\([^)]*\))?)", joined)

        for e in entries:
            k, o = parse_value(e)
            komisi_total += k
            omset_total += o

        data[username] = {"Komisi": komisi_total, "Omset": omset_total}

    df = pd.DataFrame.from_dict(data, orient="index")
    df.loc["TOTAL"] = df.sum(numeric_only=True)
    return df


if st.button("Proses Data"):
    if raw_text.strip():
        df = process(raw_text)
        st.subheader("Hasil Rekap")
        st.dataframe(df)
    else:
        st.error("Silakan paste data terlebih dahulu.")
