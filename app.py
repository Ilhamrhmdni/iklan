import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Dashboard Iklan Shopee", layout="wide")

st.title("📊 Dashboard Monitoring Iklan Shopee (Per 15 Menit)")

# === Upload File ===
uploaded_file = st.file_uploader("Upload file laporan (.xlsx atau .csv)", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith("csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

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

    # Ambil hanya kolom jam (format per 15 menit)
    akun_data = df[df["Username"] == akun].drop(
        ["Nama Studio", "Username", "Saldo", "Total Penjualan", "Total Biaya Iklan", "ROAS", "Status"], axis=1
    ).T

    # Pisahkan jadi 4 kategori: Biaya, Omzet, Rate, View
    akun_data = akun_data[0].str.split("|", expand=True).astype(float)
    akun_data.columns = ["Biaya", "Omzet", "Rate", "View"]
    akun_data.index.name = "Waktu"

    # Grafik multi-line
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
