import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="📊 Analisis ROAS Shopee", layout="wide")
st.title("📈 Analisis Data Iklan Shopee - Per 15 Menit")

st.markdown("""
**Format Data:**  
`Nama Studio | Username | Saldo | Penjualan | Biaya Iklan | [Biaya|Order|Efektivitas|Penonton] x96`
""")

# === Input Data ===
mode = st.radio("Pilih Cara Input", ["Upload File", "Paste Manual"])

df = None

# --- MODE 1: Upload File ---
if mode == "Upload File":
    uploaded_file = st.file_uploader("Upload file (.txt, .csv)", type=["txt", "csv"])
    if uploaded_file:
        raw_data = uploaded_file.read().decode("utf-8")
        lines = [line.strip() for line in raw_data.split("\n") if line.strip()]

# --- MODE 2: Paste Manual ---
elif mode == "Paste Manual":
    raw_data = st.text_area(
        "Paste data dari Excel/Notepad (gunakan TAB)",
        height=300,
        placeholder="Contoh:\nSTUDIO SURABAYA\tgrosir...\t14.589\t2.584.462\t62.311\t0|0|0%|0\t562|0|0%|5\t..."
    )
    if raw_data.strip():
        lines = [line.strip() for line in raw_data.split("\n") if line.strip()]
    else:
        lines = []

# === Parsing Function ===
def parse_shopee_data(raw_lines):
    records = []
    time_slots = [(datetime.strptime("00:00", "%H:%M") + timedelta(minutes=15*i)).strftime("%H:%M") for i in range(96)]

    for line in raw_lines:
        if any(k in line.upper() for k in ["TOTAL", "BELUM", "BOS METRO", "STUDIO"]) == 0:
            continue

        parts = line.split("\t")
        if len(parts) < 5:
            continue

        studio = parts[0].strip()
        username = parts[1].strip()

        try:
            saldo = float(str(parts[2]).replace(".", "").replace(",", "") or 0)
            total_penjualan = float(str(parts[3]).replace(".", "").replace(",", "") or 0)
            total_biaya_iklan = float(str(parts[4]).replace(".", "").replace(",", "") or 0)
        except:
            saldo = 0
            total_penjualan = 0
            total_biaya_iklan = 0

        interval_blocks = parts[5:]
        intervals = []

        for block in interval_blocks:
            block = block.strip()
            separators = [" | ", "|", " "]
            for sep in separators:
                if sep in block and len(block.split(sep)) >= 4:
                    subparts = [x.strip() for x in block.split(sep)]
                    break
            else:
                subparts = block.split()

            if len(subparts) >= 4:
                try:
                    biaya = float(subparts[0].replace(".", "").replace(",", ""))
                    order = float(subparts[1].replace(".", "").replace(",", ""))
                    ef_str = subparts[2].replace("%", "").replace(",", ".")
                    efektivitas = float(ef_str) if ef_str else 0
                    penonton = float(subparts[3].replace(".", "").replace(",", ""))
                    intervals.append({
                        "Biaya": biaya, "Order": order,
                        "Efektivitas": efektivitas, "Penonton": penonton
                    })
                except:
                    intervals.append({
                        "Biaya": 0, "Order": 0, "Efektivitas": 0, "Penonton": 0
                    })
            else:
                intervals.append({
                    "Biaya": 0, "Order": 0, "Efektivitas": 0, "Penonton": 0
                })

        for i, iv in enumerate(intervals):
            if i < len(time_slots):
                records.append({
                    "Nama Studio": studio,
                    "Username": username,
                    "Waktu": time_slots[i],
                    "Penonton": iv["Penonton"],
                    "Order": iv["Order"],
                    "Biaya Iklan": iv["Biaya"],
                    "Efektivitas Iklan (%)": iv["Efektivitas"],
                    "Saldo": saldo,
                    "Total Penjualan": total_penjualan,
                    "Total Biaya Iklan": total_biaya_iklan
                })

    df = pd.DataFrame(records)

    # Hitung AOV per akun
    aov_map = df.groupby("Username").apply(
        lambda g: g["Total Penjualan"].iloc[0] / g["Order"].sum() if g["Order"].sum() > 0 else 0
    ).to_dict()

    # Hitung ROAS per interval
    def calc_roas(row):
        aov = aov_map.get(row["Username"], 0)
        revenue = row["Order"] * aov
        return revenue / row["Biaya Iklan"] if row["Biaya Iklan"] > 0 else 0

    df["ROAS"] = df.apply(calc_roas, axis=1)
    df["ROAS"] = df["ROAS"].replace([np.inf, -np.inf], 0).fillna(0)

    return df

# === Proses Data Jika Ada ===
if 'lines' in locals() and len(lines) > 0:
    try:
        df = parse_shopee_data(lines)
        st.success(f"✅ Data berhasil diparsing! {len(df['Username'].unique())} akun, {len(df)} interval 15 menit.")

        # === Ringkasan Harian per Akun ===
        daily = df.groupby(["Nama Studio", "Username"]).agg(
            Penjualan=("Total Penjualan", "mean"),
            Biaya_Iklan=("Total Biaya Iklan", "mean"),
            Total_Order=("Order", "sum"),
            Total_Penonton=("Penonton", "sum"),
            Rata_ROAS=("ROAS", "mean"),
            Max_ROAS=("ROAS", "max")
        ).reset_index()

        # Status
        def status(r):
            if r < 5: return "🔴 Boncos"
            elif r < 30: return "🟠 Perlu Optimasi"
            elif r < 50: return "🟡 Hampir Aman"
            else: return "🟢 Aman"

        daily["Status"] = daily["Rata_ROAS"].apply(status)
        daily["AOV"] = daily["Penjualan"] / daily["Total_Order"].replace(0, 1)

        st.subheader("📋 Ringkasan Harian")
        st.dataframe(daily.style.background_gradient(cmap="RdYlGn_r", subset=["Rata_ROAS"]), use_container_width=True)

        # === Akun Boncos ===
        boncos = daily[daily["Rata_ROAS"] < 5]
        if len(boncos) > 0:
            st.subheader("❌ Akun Boncos (ROAS < 5)")
            st.dataframe(boncos[["Username", "Penjualan", "Biaya_Iklan", "Rata_ROAS"]])
            st.warning("💡 Rekomendasi: Pause iklan & evaluasi ulang konten.")

        # === Pilih Akun untuk Detail ===
        st.subheader("📊 Detail Per 15 Menit")
        selected_user = st.selectbox("Pilih akun:", df["Username"].unique())
        user_data = df[df["Username"] == selected_user].copy()

        # Tambahkan kolom jam
        user_data["Jam"] = pd.to_datetime(user_data["Waktu"], format="%H:%M").dt.hour

        st.dataframe(
            user_data[["Waktu", "Penonton", "Order", "Biaya Iklan", "ROAS"]],
            use_container_width=True
        )

        # === Grafik ===
        fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        ax[0].plot(user_data["Waktu"], user_data["ROAS"], color="orange", marker="o", markersize=3, label="ROAS")
        ax[0].set_ylabel("ROAS")
        ax[0].set_title(f"ROAS per 15 Menit - {selected_user}")
        ax[0].grid(True, alpha=0.3)
        ax[0].legend()

        ax[1].bar(user_data["Waktu"], user_data["Penonton"], alpha=0.7, label="Penonton", color="skyblue")
        ax[1].set_ylabel("Penonton")
        ax[1].set_xlabel("Waktu")
        ax[1].tick_params(axis='x', rotation=45)
        ax[1].legend()

        plt.xticks(ticks=range(0, 96, 8), labels=[f"{h:02d}:00" for h in range(0, 24, 3)])
        plt.tight_layout()
        st.pyplot(fig)

        # === Download CSV ===
        st.subheader("📥 Download Data")
        csv = user_data.to_csv(index=False)
        st.download_button(
            "⬇️ Download Data Per 15 Menit",
            data=csv,
            file_name=f"{selected_user}_per_15menit.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"❌ Terjadi kesalahan saat memproses data: {str(e)}")

else:
    st.info("Silakan masukkan data untuk memulai analisis.")
