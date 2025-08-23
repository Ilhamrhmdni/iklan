import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="📊 Analisis ROAS Shopee", layout="wide")
st.title("📈 Analisis Data Iklan Shopee - Target ROAS 50.0 + Komisi 5%")

st.markdown("""
**Format Data:**  
`Nama Studio | Username | Saldo | Penjualan | Biaya Iklan | [Biaya|Order|Efektivitas|Penonton] x96`
""")

# === Input Data ===
mode = st.radio("Pilih Cara Input", ["Upload File", "Paste Manual"])
df, lines = None, []

# --- MODE 1: Upload File ---
if mode == "Upload File":
    uploaded_file = st.file_uploader("Upload file (.txt, .csv)", type=["txt", "csv"])
    if uploaded_file:
        raw_data = uploaded_file.read().decode("utf-8", errors="ignore")
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

# === Fungsi Bantuan ===
def safe_float(x):
    """Konversi string ke float dengan aman."""
    try:
        return float(str(x).replace(".", "").replace(",", "").replace("%", "").strip())
    except:
        return 0.0

def format_rupiah(x):
    if pd.isna(x): return "-"
    x = float(x)
    if abs(x) >= 1e6:
        return f"Rp {x/1e6:.1f} juta"
    elif abs(x) >= 1e3:
        return f"Rp {x/1e3:.0f} rb"
    return f"Rp {int(x)}"

def format_order(x):
    return f"{int(x):,}"

def style_summary_table(df_to_style):
    """Styling umum tabel ringkasan."""
    return df_to_style.style.format({
        "Penjualan": format_rupiah,
        "Komisi 5%": format_rupiah,
        "Biaya_Iklan": format_rupiah,
        "Profit": format_rupiah,
        "Rata_ROAS": "{:.2f}"
    })

# === Parsing Function ===
@st.cache_data
def parse_shopee_data(raw_lines):
    records = []
    time_slots = [(datetime.strptime("00:00", "%H:%M") + timedelta(minutes=15*i)).strftime("%H:%M") for i in range(96)]

    for line in raw_lines:
        if not line or any(k in line.upper() for k in ["BELUM", "TOTAL", "PAUSED", "ONGOING"]):
            continue

        parts = line.split("\t")
        if len(parts) < 101:  # 5 utama + 96 blok
            continue

        studio, username = parts[0].strip(), parts[1].strip()
        saldo, total_penjualan, total_biaya_iklan = map(safe_float, parts[2:5])

        interval_blocks = parts[5:]
        intervals = []
        for block in interval_blocks:
            subparts = [x.strip() for x in block.replace(" | ", "|").split("|")]
            if len(subparts) >= 4:
                biaya, order, ef, penonton = map(safe_float, subparts[:4])
                intervals.append({"Biaya": biaya, "Order": order, "Efektivitas": ef, "Penonton": penonton})
            else:
                intervals.append({"Biaya": 0, "Order": 0, "Efektivitas": 0, "Penonton": 0})

        for i, iv in enumerate(intervals[:96]):  # pastikan max 96
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

    if not records:
        return pd.DataFrame()

    df_parsed = pd.DataFrame(records)

    # Hitung AOV per akun
    aov_map = df_parsed.groupby("Username").apply(
        lambda g: g["Total Penjualan"].iloc[0] / g["Order"].sum() if g["Order"].sum() > 0 else 0
    ).to_dict()

    # Hitung ROAS per slot
    def calc_roas(row):
        aov = aov_map.get(row["Username"], 0)
        revenue = row["Order"] * aov
        return revenue / row["Biaya Iklan"] if row["Biaya Iklan"] > 0 else 0

    df_parsed["ROAS"] = df_parsed.apply(calc_roas, axis=1)
    df_parsed["ROAS"] = df_parsed["ROAS"].replace([np.inf, -np.inf], 0).fillna(0)

    return df_parsed

# === Proses Data ===
if lines:
    try:
        df = parse_shopee_data(lines)
        if df.empty:
            st.warning("⚠️ Tidak ada data valid. Periksa kembali format data Anda.")
        else:
            st.success(f"✅ Data berhasil diproses! {df['Username'].nunique()} akun ditemukan.")
            # 👉 lanjutkan logika ringkasan, filter, grafik dll...
            st.write(df.head())  # sementara preview 5 baris
    except Exception as e:
        st.error(f"❌ Error parsing data: {str(e)}")
else:
    st.info("📤 Silakan masukkan data untuk mulai analisis.")
