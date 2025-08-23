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
        "Paste data dari Excel/Notepad (gunakan TAB antar kolom)",
        height=300,
        placeholder="Contoh:\nSTUDIO SURABAYA\tgrosir...\t14.589\t2.584.462\t62.311\t0|0|0%|0\t562|0|0%|5\t..."
    )
    if raw_data.strip():
        lines = [line.strip() for line in raw_data.split("\n") if line.strip()]
    else:
        lines = []

# === Parsing Function ===
@st.cache_data
def parse_shopee_data(raw_lines):
    records = []
    time_slots = [(datetime.strptime("00:00", "%H:%M") + timedelta(minutes=15*i)).strftime("%H:%M") for i in range(96)]

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        if any(k in line.upper() for k in ["BELUM MENDAFTAR", "BELUM ADA IKLAN", "TOTAL", "PAUSED", "ONGOING"]):
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
            if " | " in block:
                subparts = [x.strip() for x in block.split(" | ")]
            elif "|" in block:
                subparts = [x.strip() for x in block.split("|")]
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

    # Hitung ROAS
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
        st.success(f"✅ Data berhasil diparsing! {len(df['Username'].unique())} akun ditemukan.")

        # Hitung daily summary
        daily = df.groupby(["Nama Studio", "Username"]).agg(
            Penjualan=("Total Penjualan", "mean"),
            Biaya_Iklan=("Total Biaya Iklan", "mean"),
            Total_Order=("Order", "sum"),
            Total_Penonton=("Penonton", "sum"),
            Rata_ROAS=("ROAS", "mean"),
            Max_ROAS=("ROAS", "max")
        ).reset_index()

        # Status ROAS
        def status(r):
            if r == 0: return "⏸️ Tidak Aktif"
            elif r < 5: return "🔴 Boncos"
            elif r < 30: return "🟠 Perlu Optimasi"
            elif r < 50: return "🟡 Hampir Aman"
            else: return "🟢 Aman"

        daily["Status"] = daily["Rata_ROAS"].apply(status)
        daily["AOV"] = (daily["Penjualan"] / daily["Total_Order"].replace(0, 1)).round(0)

        # Format angka
        def format_rupiah(x):
            if pd.isna(x): return "-"
            x = float(x)
            if x >= 1e6:
                return f"Rp {x/1e6:.1f} juta"
            elif x >= 1e3:
                return f"Rp {x/1e3:.0f}rb"
            else:
                return f"Rp {int(x)}"

        def format_order(x):
            return f"{int(x):,}"

        # --- Sidebar Menu ---
        st.sidebar.title("🧭 Navigasi")
        menu = st.sidebar.radio("Pilih Halaman", [
            "📊 Ringkasan Harian",
            "❌ Akun Boncos",
            "🔍 Detail Per 15 Menit",
            "📈 Grafik & Download"
        ])

        # --- 1. Ringkasan Harian ---
        if menu == "📊 Ringkasan Harian":
            st.subheader("📋 Ringkasan Harian per Akun")

            styled_df = daily.style.format({
                "Penjualan": format_rupiah,
                "Biaya_Iklan": format_rupiah,
                "Total_Order": format_order,
                "Total_Penonton": format_order,
                "Rata_ROAS": "{:.2f}",
                "Max_ROAS": "{:.2f}",
                "AOV": format_rupiah
            }).background_gradient(cmap="RdYlGn_r", subset=["Rata_ROAS"])

            st.dataframe(styled_df, use_container_width=True)

        # --- 2. Akun Boncos ---
        elif menu == "❌ Akun Boncos":
            st.subheader("❌ Akun Boncos (ROAS < 5)")
            boncos = daily[daily["Rata_ROAS"] < 5]
            if len(boncos) > 0:
                st.dataframe(
                    boncos[["Nama Studio", "Username", "Penjualan", "Biaya_Iklan", "Rata_ROAS", "Status"]].style.format({
                        "Penjualan": format_rupiah,
                        "Biaya_Iklan": format_rupiah,
                        "Rata_ROAS": "{:.2f}"
                    }),
                    use_container_width=True
                )
                st.warning("💡 Rekomendasi: Pause iklan & evaluasi ulang konten, harga, atau target.")
            else:
                st.success("✅ Tidak ada akun boncos (ROAS ≥ 5 semua).")

        # --- 3. Detail Per 15 Menit ---
        elif menu == "🔍 Detail Per 15 Menit":
            st.subheader("🔍 Detail Per 15 Menit")
            selected_user = st.selectbox("Pilih akun:", df["Username"].unique())
            user_data = df[df["Username"] == selected_user].copy()

            st.dataframe(
                user_data[["Waktu", "Penonton", "Order", "Biaya Iklan", "ROAS"]].style.format({
                    "Penonton": "{:,}",
                    "Order": "{:,}",
                    "Biaya Iklan": "{:,.0f}",
                    "ROAS": "{:.2f}"
                }),
                use_container_width=True
            )

        # --- 4. Grafik & Download ---
        elif menu == "📈 Grafik & Download":
            st.subheader("📈 Grafik Performa")
            selected_user = st.selectbox("Pilih akun untuk grafik:", df["Username"].unique())
            user_data = df[df["Username"] == selected_user].copy().reset_index(drop=True)

            fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
            x_range = range(len(user_data))

            # ROAS
            ax[0].plot(x_range, user_data["ROAS"], color="orange", marker="o", markersize=3, label="ROAS")
            ax[0].set_ylabel("ROAS")
            ax[0].set_title(f"ROAS per 15 Menit - {selected_user}")
            ax[0].grid(True, alpha=0.3)
            ax[0].legend()

            # Penonton
            ax[1].bar(x_range, user_data["Penonton"], alpha=0.7, color="skyblue", label="Penonton")
            ax[1].set_ylabel("Penonton")
            ax[1].set_xlabel("Waktu")
            ax[1].legend()

            # Set ticks setiap 3 jam
            tick_positions = [i for i in range(0, 96, 12)]
            tick_labels = [f"{h:02d}:00" for h in range(0, 24, 3)]
            ax[1].set_xticks(tick_positions)
            ax[1].set_xticklabels(tick_labels, rotation=45)

            plt.tight_layout()
            st.pyplot(fig)

            # Download
            st.subheader("📥 Download Data")
            csv = user_data.to_csv(index=False)
            st.download_button(
                "⬇️ Download CSV (Detail Per 15 Menit)",
                data=csv,
                file_name=f"{selected_user}_detail_15menit.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"❌ Terjadi kesalahan saat memproses data: {str(e)}")

else:
    st.info("Silakan masukkan data untuk memulai analisis.")
