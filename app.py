import streamlit as st
import pandas as pd

st.set_page_config(page_title="Analisis ROAS Shopee", layout="wide")
st.title("📊 Analisis ROAS Shopee (Boncos / Aman)")

# === Input data ===
mode = st.radio("Pilih cara input data:", ["Upload File", "Paste Manual"])

df = None

# MODE 1: Upload File
if mode == "Upload File":
    uploaded_file = st.file_uploader("Upload file (.xlsx atau .csv)", type=["xlsx", "csv"])
    if uploaded_file:
        if uploaded_file.name.endswith("csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

# MODE 2: Paste Manual
elif mode == "Paste Manual":
    raw_data = st.text_area(
        "Paste data tabel Shopee (pisahkan kolom dengan TAB / copy langsung dari Excel)",
        height=300,
        placeholder="Contoh:\nSTUDIO SURABAYA\tgrosirpakaianadalamsby\t15775\t2584462\t61581"
    )
    if raw_data:
        try:
            rows = []
            for line in raw_data.strip().split("\n"):
                parts = line.split("\t")
                if len(parts) < 5: 
                    continue
                studio, username, saldo, penjualan, biaya = parts[:5]
                rows.append([
                    studio,
                    username,
                    float(str(saldo).replace(".", "").replace(",", "")) if saldo else 0,
                    float(str(penjualan).replace(".", "").replace(",", "")) if penjualan else 0,
                    float(str(biaya).replace(".", "").replace(",", "")) if biaya else 0
                ])
            df = pd.DataFrame(rows, columns=["Nama Studio", "Username", "Saldo", "Total Penjualan", "Total Biaya Iklan"])
        except Exception as e:
            st.error(f"Gagal parsing data: {e}")

# === Analisis Data ===
if df is not None:
    # Hitung ROAS
    df["ROAS"] = df.apply(
        lambda x: (x["Total Penjualan"] / x["Total Biaya Iklan"]) if x["Total Biaya Iklan"] > 0 else 0, axis=1
    )

    # Status
    def status_roas(roas):
        if roas < 30 and roas > 0:
            return "❌ Boncos"
        elif roas < 50:
            return "⚠️ Rawan"
        elif roas >= 50:
            return "✅ Aman"
        else:
            return "-"
    df["Status"] = df["ROAS"].apply(status_roas)

    # Tampilkan tabel utama
    st.subheader("📋 Hasil Analisis")
    st.dataframe(df, use_container_width=True)

    # Daftar akun boncos
    st.subheader("❌ Daftar Akun Boncos (ROAS < 30)")
    boncos_df = df[df["Status"] == "❌ Boncos"]
    if not boncos_df.empty:
        st.dataframe(boncos_df, use_container_width=True)
    else:
        st.success("Tidak ada akun yang boncos ✅")

    # Ringkasan angka besar
    st.subheader("📌 Ringkasan Keseluruhan")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Penjualan", f"{df['Total Penjualan'].sum():,.0f}")
    col2.metric("Total Biaya Iklan", f"{df['Total Biaya Iklan'].sum():,.0f}")
    col3.metric("ROAS Rata-rata", f"{df['ROAS'].mean():.2f}")
