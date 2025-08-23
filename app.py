import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO

st.set_page_config(page_title="Dashboard Iklan Shopee", layout="wide")
st.title("📊 Dashboard Monitoring Iklan Shopee (Per 15 Menit)")

# Pilih sumber data
mode = st.radio("Pilih cara input data:", ["Upload File", "Paste Manual"])

df = None

# === MODE 1: Upload File ===
if mode == "Upload File":
    uploaded_file = st.file_uploader("Upload file laporan (.xlsx atau .csv)", type=["xlsx", "csv"])
    if uploaded_file:
        if uploaded_file.name.endswith("csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

# === MODE 2: Paste Manual ===
elif mode == "Paste Manual":
    raw_data = st.text_area(
        "Paste data di sini (gunakan pemisah | , dan baris baru untuk data baru)",
        height=300,
        placeholder="Contoh:\n14068|611228|2.30|283\n7408|414928|1.80|334"
    )
    if raw_data:
        try:
            df = pd.read_csv(StringIO(raw_data), sep="|", header=None)
            df.columns = ["Biaya Iklan", "Omset", "Efektivitas (%)", "View (15 menit)"]
        except Exception as e:
            st.error(f"Gagal parsing data: {e}")

# === Kalau ada data ===
if df is not None:
    # Kalau file upload: hitung ROAS + status
    if mode == "Upload File":
        # Hitung ROAS
        df["ROAS"] = df.apply(lambda x: x["Total Penjualan"] / x["Total Biaya Iklan"] if x["Total Biaya Iklan"] > 0 else 0, axis=1)

        # Status ROAS
        def status_roas(roas):
            if roas < 30:
                return "❌ Boncos"
            elif roas < 50:
                return "⚠️ Rawan"
            else:
                return "✅ Aman"
        df["Status"] = df["ROAS"].apply(status_roas)

        # === Tabel Utama ===
        st.subheader("📋 Data Akun")
        st.dataframe(df, use_container_width=True)

        # === Ringkasan Per Studio ===
        st.subheader("🏢 Ringkasan Per Studio")
        summary = df.groupby("Nama Studio").agg({
            "Total Penjualan": "sum",
            "Total Biaya Iklan": "sum"
        })
        summary["ROAS Studio"] = summary["Total Penjualan"] / summary["Total Biaya Iklan"]
        st.dataframe(summary, use_container_width=True)

        # === Grafik Performa ===
        st.subheader("⏱️ Performa Per 15 Menit")
        akun = st.selectbox("Pilih akun:", df["Username"].unique())

        akun_data = df[df["Username"] == akun].drop(
            ["Nama Studio", "Username", "Saldo", "Total Penjualan", "Total Biaya Iklan", "ROAS", "Status"], axis=1
        ).T

        akun_data = akun_data[0].str.split("|", expand=True).astype(float)
        akun_data.columns = ["Biaya", "Omzet", "Rate", "View"]
        akun_data.index.name = "Waktu"

        fig, ax = plt.subplots(figsize=(12, 5))
        akun_data[["Biaya", "Omzet", "View"]].plot(ax=ax, marker="o")
        plt.title(f"Performa Iklan per 15 Menit - {akun}")
        plt.xlabel("Waktu")
        plt.ylabel("Nilai")
        st.pyplot(fig)

        # Grafik Rate %
        st.subheader("📈 Rate %")
        fig2, ax2 = plt.subplots(figsize=(12, 3))
        akun_data["Rate"].plot(ax=ax2, color="orange", marker="x")
        plt.title(f"Rate % per 15 Menit - {akun}")
        plt.xlabel("Waktu")
        plt.ylabel("Rate %")
        st.pyplot(fig2)

    # Kalau paste manual: tampilkan ringkasan + grafik
    elif mode == "Paste Manual":
        st.success("✅ Data berhasil diproses")
        st.dataframe(df, use_container_width=True)

        # Ringkasan
        st.subheader("📌 Ringkasan")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Biaya Iklan", f"{df['Biaya Iklan'].sum():,.0f}")
        col2.metric("Total Omset", f"{df['Omset'].sum():,.0f}")
        col3.metric("Rata-rata Efektivitas", f"{df['Efektivitas (%)'].mean():.2f}%")
        col4.metric("Total View", f"{df['View (15 menit)'].sum():,.0f}")

        # Grafik
        st.subheader("📈 Grafik Tren")
        fig, ax = plt.subplots(figsize=(12, 5))
        df[["Biaya Iklan", "Omset", "View (15 menit)"]].plot(ax=ax, marker="o")
        plt.title("Performa Iklan (Paste Manual)")
        plt.xlabel("Index")
        plt.ylabel("Nilai")
        st.pyplot(fig)

        fig2, ax2 = plt.subplots(figsize=(12, 3))
        df["Efektivitas (%)"].plot(ax=ax2, color="orange", marker="x")
        plt.title("Efektivitas Rate % (Paste Manual)")
        plt.xlabel("Index")
        plt.ylabel("Rate %")
        st.pyplot(fig2)
