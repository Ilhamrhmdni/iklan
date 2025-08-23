import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="📊 Analisis ROAS Shopee", layout="wide")
st.title("📈 Analisis Data Iklan Shopee - Target ROAS 50.0 + Komisi 5%")

st.markdown("""
**Format Data:** `Nama Studio | Username | Saldo | Penjualan | Biaya Iklan | [Biaya|Order|Efektivitas|Penonton] x96`
""")

# === Input Data ===
mode = st.radio("Pilih Cara Input", ["Upload File", "Paste Manual"])

df = None
lines = []

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

# === Fungsi Bantuan (Helpers) ===
def format_rupiah(x):
    if pd.isna(x): return "-"
    x = float(x)
    if abs(x) >= 1e6:
        return f"Rp {x/1e6:.1f} juta"
    elif abs(x) >= 1e3:
        return f"Rp {x/1e3:.0f}rb"
    else:
        return f"Rp {int(x)}"

def format_order(x):
    return f"{int(x):,}"

def style_summary_table(df_to_style):
    """Fungsi untuk menerapkan styling umum pada tabel ringkasan."""
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
    """Fungsi utama untuk mem-parsing data mentah menjadi DataFrame yang bersih."""
    records = []
    time_slots = [(datetime.strptime("00:00", "%H:%M") + timedelta(minutes=15*i)).strftime("%H:%M") for i in range(96)]

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        # Skip baris yang tidak relevan
        if any(k in line.upper() for k in ["BELUM MENDAFTAR", "BELUM ADA IKLAN", "TOTAL", "PAUSED", "ONGOING"]):
            continue

        parts = line.split("\t")
        # Validasi jumlah kolom
        if len(parts) < 101: # 5 kolom utama + 96 interval
            st.warning(f"Melewatkan baris karena format tidak sesuai (ditemukan {len(parts)} kolom, diharapkan 101): '{line[:70]}...'")
            continue

        studio = parts[0].strip()
        username = parts[1].strip()

        try:
            saldo = float(str(parts[2]).replace(".", "").replace(",", "") or 0)
            total_penjualan = float(str(parts[3]).replace(".", "").replace(",", "") or 0)
            total_biaya_iklan = float(str(parts[4]).replace(".", "").replace(",", "") or 0)
        except (ValueError, IndexError):
            saldo, total_penjualan, total_biaya_iklan = 0, 0, 0

        interval_blocks = parts[5:]
        intervals = []

        for block in interval_blocks:
            subparts = [x.strip() for x in block.replace(" | ", "|").split("|")]
            if len(subparts) >= 4:
                try:
                    biaya = float(subparts[0].replace(".", "").replace(",", ""))
                    order = float(subparts[1].replace(".", "").replace(",", ""))
                    ef_str = subparts[2].replace("%", "").replace(",", ".")
                    efektivitas = float(ef_str) if ef_str else 0
                    penonton = float(subparts[3].replace(".", "").replace(",", ""))
                    intervals.append({"Biaya": biaya, "Order": order, "Efektivitas": efektivitas, "Penonton": penonton})
                except (ValueError, IndexError):
                    intervals.append({"Biaya": 0, "Order": 0, "Efektivitas": 0, "Penonton": 0})
            else:
                intervals.append({"Biaya": 0, "Order": 0, "Efektivitas": 0, "Penonton": 0})

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

    if not records:
        return pd.DataFrame()

    df_parsed = pd.DataFrame(records)

    # Hitung AOV per akun
    aov_map = df_parsed.groupby("Username").apply(
        lambda g: g["Total Penjualan"].iloc[0] / g["Order"].sum() if g["Order"].sum() > 0 else 0
    ).to_dict()

    # Hitung ROAS per 15 menit
    def calc_roas(row):
        aov = aov_map.get(row["Username"], 0)
        revenue = row["Order"] * aov
        return revenue / row["Biaya Iklan"] if row["Biaya Iklan"] > 0 else 0

    df_parsed["ROAS"] = df_parsed.apply(calc_roas, axis=1)
    df_parsed["ROAS"] = df_parsed["ROAS"].replace([np.inf, -np.inf], 0).fillna(0)

    return df_parsed

# === Proses Data Jika Ada ===
if lines:
    try:
        df = parse_shopee_data(lines)
        if df.empty:
            st.warning("Tidak ada data valid yang dapat diproses. Periksa kembali format data Anda.")
        else:
            st.success(f"✅ Data berhasil diparsing! {len(df['Username'].unique())} akun ditemukan.")

            # --- Sidebar & Filter ---
            st.sidebar.title("🧭 Navigasi & Filter")
            
            all_studios = df['Nama Studio'].unique()
            selected_studios = st.sidebar.multiselect("Filter Nama Studio", all_studios, default=all_studios)
            
            if not selected_studios:
                st.sidebar.warning("Pilih minimal satu studio.")
                filtered_df = pd.DataFrame()
            else:
                filtered_df = df[df['Nama Studio'].isin(selected_studios)]
            
            menu = st.sidebar.radio("Pilih Halaman", [
                "📊 Ringkasan Harian",
                "💰 Analisis Komisi & Profit",
                "✅ AMAN (ROAS ≥ 50)",
                "🎯 Hampir Aman (ROAS 30–49.9)",
                "🟠 Perlu Optimasi (ROAS 5-29.9)",
                "❌ Akun Boncos (ROAS < 5)",
                "🔍 Detail Per 15 Menit",
                "📈 Grafik & Download",
                "🔥 Analisis Jam Efektif",
                "💡 Simulasi Biaya Ideal"
            ])

            # Hitung ringkasan harian
            daily = filtered_df.groupby(["Nama Studio", "Username"]).agg(
                Penjualan=("Total Penjualan", "mean"),
                Biaya_Iklan=("Total Biaya Iklan", "mean"),
                Total_Order=("Order", "sum"),
                Total_Penonton=("Penonton", "sum"),
                Rata_ROAS=("ROAS", "mean"),
                Median_ROAS=("ROAS", "median"),
                Max_ROAS=("ROAS", "max")
            ).reset_index()

            daily["Komisi 5%"] = daily["Penjualan"] * 0.05
            daily["Profit"] = daily["Komisi 5%"] - daily["Biaya_Iklan"]
            daily["AOV"] = (daily["Penjualan"] / daily["Total_Order"].replace(0, 1)).round(0)

            daily["Status Profit"] = daily["Profit"].apply(lambda p: "✅ Profit" if p > 0 else ("❌ Rugi" if p < 0 else "➖ Break Even"))
            
            def status_roas(r):
                if r == 0: return "⏸️ Tidak Aktif"
                if r < 5: return "🔴 Boncos"
                if r < 30: return "🟠 Perlu Optimasi"
                if r < 50: return "🟡 Hampir Aman"
                return "🟢 AMAN (ROAS ≥ 50)"
            daily["Status ROAS"] = daily["Rata_ROAS"].apply(status_roas)

            # --- Tampilan Halaman ---
            if menu == "📊 Ringkasan Harian":
                st.subheader("📋 Ringkasan Harian per Akun")

                if not daily.empty:
                    total_penjualan = daily["Penjualan"].sum()
                    total_biaya = daily["Biaya_Iklan"].sum()
                    total_profit = daily["Profit"].sum()
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Penjualan", format_rupiah(total_penjualan))
                    col2.metric("Total Biaya Iklan", format_rupiah(total_biaya))
                    col3.metric("Estimasi Total Profit", format_rupiah(total_profit), delta_color=("inverse" if total_profit < 0 else "normal"))
                    st.markdown("---")

                styled_df = daily.style.format({
                    "Penjualan": format_rupiah, "Biaya_Iklan": format_rupiah, "Komisi 5%": format_rupiah,
                    "Profit": format_rupiah, "Total_Order": format_order, "Total_Penonton": format_order,
                    "Rata_ROAS": "{:.2f}", "Median_ROAS": "{:.2f}", "Max_ROAS": "{:.2f}", "AOV": format_rupiah
                }).background_gradient(cmap="RdYlGn", subset=["Rata_ROAS"], vmin=0, vmax=60)
                st.dataframe(styled_df, use_container_width=True)

            elif menu == "💰 Analisis Komisi & Profit":
                st.subheader("💰 Estimasi Komisi 5% & Profit")
                profit_df = daily[["Nama Studio", "Username", "Penjualan", "Komisi 5%", "Biaya_Iklan", "Profit", "Status Profit"]].copy()
                profit_df = profit_df.sort_values("Profit", ascending=False)
                
                st.dataframe(
                    style_summary_table(profit_df).apply(
                        lambda x: ['background-color: #d4edda' if v == "✅ Profit" else 
                                   'background-color: #f8d7da' if v == "❌ Rugi" else 
                                   'background-color: #fff3cd' for v in x], 
                        subset=["Status Profit"]
                    ),
                    use_container_width=True
                )
            
            elif menu in ["❌ Akun Boncos (ROAS < 5)", "🟠 Perlu Optimasi (ROAS 5-29.9)", "🎯 Hampir Aman (ROAS 30–49.9)", "✅ AMAN (ROAS ≥ 50)"]:
                columns_to_show = ["Nama Studio", "Username", "Penjualan", "Komisi 5%", "Biaya_Iklan", "Profit", "Rata_ROAS", "Median_ROAS", "Status ROAS", "Status Profit"]
                
                if menu == "❌ Akun Boncos (ROAS < 5)":
                    st.subheader("❌ Akun Boncos (ROAS < 5)")
                    data_view = daily[daily["Rata_ROAS"] < 5]
                    if data_view.empty: st.success("✅ Tidak ada akun dengan ROAS < 5.")
                    else: st.info("💡 Rekomendasi: Pause iklan dan evaluasi ulang produk & target pasar.")
                
                elif menu == "🟠 Perlu Optimasi (ROAS 5-29.9)":
                    st.subheader("🟠 Akun Perlu Optimasi (ROAS 5 - 29.9)")
                    data_view = daily[(daily["Rata_ROAS"] >= 5) & (daily["Rata_ROAS"] < 30)]
                    if data_view.empty: st.success("✅ Tidak ada akun di rentang ROAS ini.")
                    else: st.info("💡 Tips: Cek jam efektif, ganti materi iklan, atau sesuaikan bidding.")

                elif menu == "🎯 Hampir Aman (ROAS 30–49.9)":
                    st.subheader("🎯 Hampir Aman (ROAS 30 – 49.9)")
                    data_view = daily[(daily["Rata_ROAS"] >= 30) & (daily["Rata_ROAS"] < 50)]
                    if data_view.empty: st.success("✅ Tidak ada akun di rentang ROAS ini.")
                    else: st.info("💡 Tips: Optimasi sedikit lagi untuk tembus target ROAS 50!")

                elif menu == "✅ AMAN (ROAS ≥ 50)":
                    st.subheader("✅ Akun AMAN (ROAS ≥ 50.0)")
                    data_view = daily[daily["Rata_ROAS"] >= 50]
                    if data_view.empty: st.warning("Belum ada akun yang mencapai target ROAS ≥ 50.")
                    else: st.success("🎉 Hebat! Akun-akun ini sudah mencapai target.")
                
                if 'data_view' in locals() and not data_view.empty:
                    st.dataframe(style_summary_table(data_view[columns_to_show]), use_container_width=True)

            elif menu == "🔍 Detail Per 15 Menit":
                st.subheader("🔍 Detail Per 15 Menit")
                if filtered_df.empty:
                    st.warning("Tidak ada data untuk ditampilkan. Pilih studio terlebih dahulu.")
                else:
                    selected_user = st.selectbox("Pilih akun:", filtered_df["Username"].unique())
                    user_data = filtered_df[filtered_df["Username"] == selected_user].copy()
                    st.dataframe(
                        user_data[["Waktu", "Penonton", "Order", "Biaya Iklan", "ROAS"]].style.format({
                            "Penonton": "{:,}", "Order": "{:,}", "Biaya Iklan": "{:,.0f}", "ROAS": "{:.2f}"
                        }),
                        use_container_width=True
                    )

            elif menu == "📈 Grafik & Download":
                st.subheader("📈 Grafik Performa (ROAS & Penonton)")
                if filtered_df.empty:
                    st.warning("Tidak ada data untuk ditampilkan. Pilih studio terlebih dahulu.")
                else:
                    selected_user_graph = st.selectbox("Pilih akun untuk grafik:", filtered_df["Username"].unique())
                    user_data_graph = filtered_df[filtered_df["Username"] == selected_user_graph].copy().reset_index(drop=True)

                    fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
                    x_range = range(len(user_data_graph))

                    ax[0].plot(x_range, user_data_graph["ROAS"], color="orange", marker="o", markersize=3, label="ROAS")
                    ax[0].axhline(y=50, color="green", linestyle="--", label="Target ROAS 50")
                    ax[0].set_ylabel("ROAS"); ax[0].set_title(f"ROAS per 15 Menit - {selected_user_graph}")
                    ax[0].grid(True, alpha=0.3); ax[0].legend()

                    ax[1].bar(x_range, user_data_graph["Penonton"], alpha=0.7, color="skyblue", label="Penonton")
                    ax[1].set_ylabel("Penonton"); ax[1].set_xlabel("Waktu"); ax[1].legend()

                    tick_positions = [i for i in range(0, 96, 12)]
                    tick_labels = [user_data_graph["Waktu"][i] for i in tick_positions]
                    ax[1].set_xticks(tick_positions); ax[1].set_xticklabels(tick_labels, rotation=45)

                    plt.tight_layout()
                    st.pyplot(fig)

                    st.subheader("📥 Download Data")
                    csv_daily = daily.to_csv(index=False).encode('utf-8')
                    st.download_button("⬇️ Download CSV (Ringkasan Harian)", data=csv_daily, file_name=f"ringkasan_harian_roas.csv", mime="text/csv")
                    
                    csv_detail = user_data_graph.to_csv(index=False).encode('utf-8')
                    st.download_button("⬇️ Download CSV (Detail 15 Menit Akun Terpilih)", data=csv_detail, file_name=f"{selected_user_graph}_detail_15menit.csv", mime="text/csv")

            elif menu == "🔥 Analisis Jam Efektif":
                st.subheader("🔥 Heatmap Jam Efektif (ROAS & Order)")

                if filtered_df.empty:
                    st.warning("Tidak ada data untuk ditampilkan. Pilih studio terlebih dahulu.")
                else:
                    import seaborn as sns
                    filtered_df["Jam"] = pd.to_datetime(filtered_df["Waktu"], format="%H:%M").dt.hour

                    pivot_roas = filtered_df.pivot_table(index="Jam",
