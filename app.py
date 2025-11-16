import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Rekap Komisi & Omset", layout="wide")

st.title("Rekap Komisi & Omset Per Hari")

st.write("Paste data mentah di bawah ini (bukan upload file). Format harus sama persis seperti dari Shopee:")

raw_input = st.text_area("Paste data di sini", height=300)

def parse_value(text):
    """
    Mengubah '63.406 - 983.145 (B)' menjadi:
    komisi=63406, omset=983145, grade=B
    """
    pattern = r"([\d\.]+)\s*-\s*([\d\.]+)(?:\s*\((\w)\))?"
    match = re.search(pattern, text)
    if match:
        komisi = int(match.group(1).replace('.', ''))
        omset = int(match.group(2).replace('.', ''))
        grade = match.group(3) if match.group(3) else ""
        return komisi, omset, grade
    return 0, 0, ""

if raw_input:
    rows = []
    lines = raw_input.strip().split("\n")

    # ambil tanggal dari header
    header_cols = lines[0].split("\t")
    dates = header_cols[2:]  # mulai dari kolom tanggal

    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) < 3:
            continue

        studio = parts[0]
        username = parts[1]

        for i, date_value in enumerate(parts[2:]):
            komisi, omset, grade = parse_value(date_value)
            rows.append({
                "Studio": studio,
                "Username": username,
                "Tanggal": dates[i],
                "Est. Komisi": komisi,
                "Omset": omset,
                "Grade": grade
            })

    df = pd.DataFrame(rows)
    
    st.subheader("Hasil Parsing")
    st.dataframe(df, use_container_width=True)

    # Rekap per tanggal (tabel model contoh kamu)
    st.subheader("Rekap Per Tanggal")
    pivot = df.pivot_table(
        index="Username",
        columns="Tanggal",
        values=["Est. Komisi", "Omset"],
        aggfunc="sum"
    )

    st.dataframe(pivot, use_container_width=True)
