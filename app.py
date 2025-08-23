import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Dashboard Iklan Shopee", layout="wide")
st.title("📊 Dashboard Monitoring Iklan Shopee (Per 15 Menit)")

# Pilih mode input
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
        "Paste data di sini persis dari laporan Shopee (format panjang dengan pemisah tab/spasi)",
        height=300,
        placeholder="Contoh:\nSTUDIO SURABAYA\takun1\t10000\t500000\t20000\t0 | 0 | 0% | 0\t516 | 0 | 0% | 3 ..."
    )

    if raw_data:
        try:
            rows = []
            for line in raw_data.strip().split("\n"):
                parts = line.split("\t")  # pisah tab (copy dari excel biasanya tab)
                if len(parts) < 6:
                    continue

                studio, username = parts[0], parts[1]

                # data per 15 menit mulai dari kolom ke-5
                slot_data = parts[5:]
                waktu = 1
                for slot in slot_data:
                    try:
                        biaya, omset, rate, view = [s.strip().replace("%", "").replace("-", "0") for s in slot.split("|")]
                        rows.append([
                            studio, username, waktu,
                            float(biaya), float(omset), float(rate), float(view)
                        ])
                        waktu += 1
                    except:
                        continue

            df = pd.DataFrame(rows, columns=["Studio", "Username", "Waktu", "Biaya", "Omset", "Rate (%)", "View"])
        except Exception as e:
            st.error(f"Gagal parsing data: {e}")

# === Kalau ada data ===
if df is not None:
    st.success("✅ Data berhasil diproses")
    st.dataframe(df, use_container_width=True)

    # === Ringkasan global ===
    st.subheader("📌 Ringkasan")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Biaya Iklan", f"{df['Biaya'].sum():,.0f}")
    col2.metric("Total Omset", f"{df['Omset'].sum():,.0f}")
    col3.metric("Rata-rata Efektivitas", f"{df['Rate (%)'].mean():.2f}%")
    col4.metric("Total View", f"{df['View'].sum():,.0f}")

    # === Ringkasan per akun ===
    st.subheader("🏢 Ringkasan Per Akun")
    summary = df.groupby("Username").agg({
        "Biaya": "sum",
        "Omset": "sum",
        "Rate (%)": "mean",
        "View": "sum"
    }).reset_index()
    summary["ROAS"] = summary.apply(lambda x: x["Omset"] / x["Biaya"] if x["Biaya"] > 0 else 0, axis=1)

    def status_roas(roas):
        if roas < 30:
            return "❌ Boncos"
        elif roas < 50:
            return "⚠️ Rawan"
        else:
            return "✅ Aman"

    summary["Status"] = summary["ROAS"].apply(status_roas)
    st.dataframe(summary, use_container_width=True)

    # === Grafik per akun ===
    akun = st.selectbox("Pilih akun untuk detail grafik:", df["Username"].unique())
    akun_data = df[df["Username"] == akun]

    st.subheader(f"📈 Grafik Tren - {akun}")
    fig, ax = plt.subplots(figsize=(12, 5))
    akun_data.set_index("Waktu")[["Biaya", "Omset", "View"]].plot(ax=ax, marker="o")
    plt.title(f"Performa Iklan per 15 Menit - {akun}")
    plt.xlabel("Waktu (slot 15 menit)")
    plt.ylabel("Nilai")
    st.pyplot(fig)

    fig2, ax2 = plt.subplots(figsize=(12, 3))
    akun_data.set_index("Waktu")["Rate (%)"].plot(ax=ax2, color="orange", marker="x")
    plt.title(f"Efektivitas Rate % per 15 Menit - {akun}")
    plt.xlabel("Waktu (slot 15 menit)")
    plt.ylabel("Rate %")
    st.pyplot(fig2)
