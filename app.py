import streamlit as st
import pandas as pd
from parser import process_dataframe

st.set_page_config(page_title="Shopee Komisi Parser", layout="wide")

st.title("📊 Shopee Komisi & Omset Parser")

st.write("Upload file CSV/Excel atau paste manual data mentah Shopee.")

# Upload file
uploaded = st.file_uploader("Upload file", type=["csv", "xlsx"])

# Input manual
manual_input = st.text_area("Atau paste data mentah di sini (format Excel copas)")

df = None

if uploaded:
    if uploaded.name.endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)

elif manual_input.strip():
    rows = [row.split("\t") for row in manual_input.split("\n")]
    df = pd.DataFrame(rows[1:], columns=rows[0])

if df is not None:
    st.subheader("Data Mentah")
    st.dataframe(df)

    try:
        clean_df = process_dataframe(df)
        st.subheader("Hasil Parsing & Perhitungan")
        st.dataframe(clean_df)

        csv = clean_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "hasil.csv")

    except Exception as e:
        st.error(f"Error: {e}")
