import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, time

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="📊 Analisis ROAS Shopee", layout="wide")
st.title("📈 Analisis Data Iklan Shopee")

st.markdown("""
**Format Data:** `Paste Data Dari Menu Histori`
""")

# === Input Data ===
mode = st.radio("Pilih Cara Input", ["Upload File", "Paste Manual"])

# --- PERUBAHAN: Opsi untuk input fleksibel ---
st.sidebar.title("⚙️ Pengaturan Input Data")
report_type = st.sidebar.radio(
    "Pilih Jenis Laporan",
    ["Laporan Harian Penuh (24 Jam)", "Laporan Parsial (Sebagian)"]
)

start_time = time(0, 0)
if report_type == "Laporan Parsial (Sebagian)":
    start_time = st.sidebar.time_input("Waktu Mulai Data", value=time(9, 0))
    st.sidebar.info("Tentukan jam mulai untuk data parsial yang Anda masukkan.")


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
    return f"{int(x):,}" if pd.notna(x) else "-"

def format_percent(x):
    return f"{x:.2f}%" if pd.notna(x) else "-"

def style_summary_table(df_to_style):
    """Fungsi untuk menerapkan styling umum pada tabel ringkasan."""
    return df_to_style.style.format({
        "Penjualan": format_rupiah,
        "Komisi 5%": format_rupiah,
        "Biaya_Iklan": format_rupiah,
        "Profit": format_rupiah,
        "Rata_ROAS": "{:.2f}",
        "CPA": format_rupiah,
        "CPC": format_rupiah,
        "CR": format_percent,
        "Biaya_Ideal_ROAS_50": format_rupiah,
        "Selisih_Biaya": format_rupiah,
    })

# === Parsing Function ===
# --- PERUBAHAN: Menambahkan parameter `start_time_obj` untuk menangani waktu mulai yang dinamis ---
@st.cache_data
def parse_shopee_data(raw_lines, start_time_obj):
    """Fungsi utama untuk mem-parsing data mentah menjadi DataFrame yang bersih."""
    records = []
    base_datetime = datetime.combine(datetime.today(), start_time_obj)

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        if any(k in line.upper() for k in ["BELUM MENDAFTAR", "BELUM ADA IKLAN", "TOTAL", "PAUSED", "ONGOING"]):
            continue

        parts = line.split("\t")
        
        # --- PERUBAHAN: Logika fleksibel untuk jumlah kolom interval ---
        if len(parts) < 6: # Harus ada minimal 5 kolom header + 1 kolom interval
            st.warning(f"Melewatkan baris karena tidak memiliki cukup kolom: '{line[:70]}...'")
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

        # --- PERUBAHAN: Membuat slot waktu dinamis berdasarkan jumlah data yang ada ---
        num_intervals = len(interval_blocks)
        time_slots = [(base_datetime + timedelta(minutes=15*i)).strftime("%H:%M") for i in range(num_intervals)]


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
                    "Nama Studio": studio, "Username": username, "Waktu": time_slots[i],
                    "Penonton": iv["Penonton"], "Order": iv["Order"], "Biaya Iklan": iv["Biaya"],
                    "Efektivitas Iklan (%)": iv["Efektivitas"], "Saldo": saldo,
                    "Total Penjualan": total_penjualan, "Total Biaya Iklan": total_biaya_iklan
                })

    if not records:
        return pd.DataFrame()

    df_parsed = pd.DataFrame(records)

    aov_map = df_parsed.groupby("Username").apply(
        lambda g: g["Total Penjualan"].iloc[0] / g["Order"].sum() if g["Order"].sum() > 0 else 0
    ).to_dict()

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
        # --- PERUBAHAN: Mengirimkan `start_time` ke fungsi parsing ---
        df = parse_shopee_data(lines, start_time)
        if df.empty:
            st.warning("Tidak ada data valid yang dapat diproses. Periksa kembali format data Anda.")
        else:
            st.success(f"✅ Data berhasil diparsing! {len(df['Username'].unique())} akun ditemukan.")

            st.sidebar.markdown("---")
            st.sidebar.title("🧭 Navigasi Halaman")
            all_studios = df['Nama Studio'].unique()
            selected_studios = st.sidebar.multiselect("Filter Nama Studio", all_studios, default=all_studios)
            
            if not selected_studios:
                st.sidebar.warning("Pilih minimal satu studio.")
                filtered_df = pd.DataFrame() 
            else:
                filtered_df = df[df['Nama Studio'].isin(selected_studios)]
            
            menu = st.sidebar.radio("Pilih Halaman Analisis", [
                "📊 Ringkasan Harian",
                "💰 Analisis Komisi & Profit",
                "💡 Simulasi Biaya Ideal (Target ROAS 50)",
                "🔥 Analisis Jam Efektif",
                "✅ AMAN (ROAS ≥ 50)",
                "🎯 Hampir Aman (ROAS 30–49.9)",
                "🟠 Perlu Optimasi (ROAS 5-29.9)",
                "❌ Akun Boncos (ROAS < 5)",
                "🔍 Detail Per Interval",
                "📈 Grafik & Download"
            ])

            # (Sisa kode tidak perlu diubah, karena sudah bekerja berdasarkan DataFrame yang dihasilkan)
            # ... (kode dari `daily = filtered_df.groupby...` hingga akhir skrip) ...
            
            # Hitung ringkasan harian dari data yang sudah difilter
            daily = filtered_df.groupby(["Nama Studio", "Username"]).agg(
                Penjualan=("Total Penjualan", "first"), # Gunakan first karena nilainya sama untuk satu akun
                Biaya_Iklan=("Total Biaya Iklan", "first"), # Gunakan first
                Total_Order=("Order", "sum"),
                Total_Penonton=("Penonton", "sum"),
                Rata_ROAS=("ROAS", "mean"),
                Max_ROAS=("ROAS", "max")
            ).reset_index()

            # Hitung KPI Tambahan
            daily["Komisi 5%"] = daily["Penjualan"] * 0.05
            daily["Profit"] = daily["Komisi 5%"] - daily["Biaya_Iklan"]
            daily["AOV"] = (daily["Penjualan"] / daily["Total_Order"].replace(0, 1)).round(0)
            daily['CPA'] = daily['Biaya_Iklan'] / daily['Total_Order'].replace(0, np.nan)
            daily['CPC'] = daily['Biaya_Iklan'] / daily['Total_Penonton'].replace(0, np.nan)
            daily['CR'] = (daily['Total_Order'] / daily['Total_Penonton'].replace(0, np.nan)) * 100
            daily["Biaya_Ideal_ROAS_50"] = daily["Penjualan"] / 50
            daily["Selisih_Biaya"] = daily["Biaya_Iklan"] - daily["Biaya_Ideal_ROAS_50"]

            # Status Profit & ROAS
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
                st.subheader("📋 Ringkasan Performa Akun")
                if not daily.empty:
                    # Metrik Agregat Termasuk Median
                    total_penjualan = daily["Penjualan"].sum()
                    total_biaya = daily["Biaya_Iklan"].sum()
                    total_profit = daily["Profit"].sum()
                    median_roas = daily[daily["Biaya_Iklan"] > 0]["Rata_ROAS"].median()
                    median_profit = daily["Profit"].median()
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("Total Penjualan", format_rupiah(total_penjualan))
                    col2.metric("Total Biaya Iklan", format_rupiah(total_biaya))
                    col3.metric("Estimasi Total Profit", format_rupiah(total_profit), delta_color=("inverse" if total_profit < 0 else "normal"))
                    col4.metric("Median ROAS Akun", f"{median_roas:.2f}" if pd.notna(median_roas) else "N/A")
                    col5.metric("Median Profit Akun", format_rupiah(median_profit) if pd.notna(median_profit) else "N/A")
                    st.markdown("---")

                    cols_display = ["Nama Studio", "Username", "Penjualan", "Biaya_Iklan", "Profit", "Rata_ROAS", "CR", "CPC", "CPA", "Status Profit"]
                    styled_df = daily[cols_display].style.format({
                        "Penjualan": format_rupiah, "Biaya_Iklan": format_rupiah, "Profit": format_rupiah,
                        "Rata_ROAS": "{:.2f}", "CR": format_percent, "CPC": format_rupiah, "CPA": format_rupiah
                    }).background_gradient(cmap="RdYlGn", subset=["Rata_ROAS"], vmin=0, vmax=60)
                    st.dataframe(styled_df, use_container_width=True)

            elif menu == "💰 Analisis Komisi & Profit":
                st.subheader("💰 Estimasi Komisi 5% & Profit")
                profit_df = daily[["Nama Studio", "Username", "Penjualan", "Komisi 5%", "Biaya_Iklan", "Profit", "Status Profit"]].copy()
                profit_df = profit_df.sort_values("Profit", ascending=False)
                
                st.dataframe(
                    profit_df.style.format({
                        "Penjualan": format_rupiah, "Komisi 5%": format_rupiah,
                        "Biaya_Iklan": format_rupiah, "Profit": format_rupiah
                    }).apply(
                        lambda x: ['background-color: #d4edda' if v == "✅ Profit" else 
                                   'background-color: #f8d7da' if v == "❌ Rugi" else 
                                   'background-color: #fff3cd' for v in x], 
                        subset=["Status Profit"]
                    ),
                    use_container_width=True
                )
            
            elif menu == "💡 Simulasi Biaya Ideal (Target ROAS 50)":
                st.subheader("💡 Simulasi Biaya Ideal untuk Mencapai ROAS 50")
                st.info("Biaya ideal adalah biaya maksimum yang seharusnya dikeluarkan untuk mencapai target ROAS 50 dengan tingkat penjualan saat ini. Selisih negatif (hijau) berarti Anda beriklan secara efisien.")
                
                sim_df = daily[["Nama Studio", "Username", "Penjualan", "Biaya_Iklan", "Biaya_Ideal_ROAS_50", "Selisih_Biaya"]].copy()
                sim_df = sim_df.sort_values("Selisih_Biaya", ascending=True)

                st.dataframe(
                    sim_df.style.format({
                        "Penjualan": format_rupiah, "Biaya_Iklan": format_rupiah,
                        "Biaya_Ideal_ROAS_50": format_rupiah, "Selisih_Biaya": format_rupiah
                    }).bar(subset=["Selisih_Biaya"], align='zero', color=['#d65f5f', '#5fba7d']),
                    use_container_width=True
                )
            
            elif menu == "🔥 Analisis Jam Efektif":
                st.subheader("🔥 Analisis Jam Efektif (Agregat dari Akun Terfilter)")
                st.info("Gunakan grafik ini untuk melihat jam-jam di mana ROAS paling tinggi dan jumlah order terbanyak, untuk membantu optimasi jadwal iklan.")
                if filtered_df.empty:
                    st.warning("Pilih studio untuk menampilkan analisis.")
                else:
                    # Urutkan berdasarkan Waktu untuk memastikan plot benar
                    hourly_perf = filtered_df.groupby("Waktu").agg(
                        Total_Order=("Order", "sum"),
                        Mean_ROAS=("ROAS", "mean")
                    ).reset_index()

                    fig, ax1 = plt.subplots(figsize=(14, 6))
                    
                    color = 'tab:blue'
                    ax1.set_xlabel('Waktu')
                    ax1.set_ylabel('Total Order', color=color)
                    ax1.bar(hourly_perf['Waktu'], hourly_perf['Total_Order'], color=color, alpha=0.6, label='Total Order')
                    ax1.tick_params(axis='y', labelcolor=color)

                    ax2 = ax1.twinx() 
                    color = 'tab:red'
                    ax2.set_ylabel('Rata-rata ROAS', color=color)
                    ax2.plot(hourly_perf['Waktu'], hourly_perf['Mean_ROAS'], color=color, marker='o', markersize=4, label='Rata-rata ROAS')
                    ax2.tick_params(axis='y', labelcolor=color)
                    
                    # Logika tick yang lebih dinamis
                    num_ticks = min(len(hourly_perf['Waktu']), 24) # Tampilkan hingga 24 tick
                    tick_positions = np.linspace(0, len(hourly_perf['Waktu']) - 1, num_ticks, dtype=int)
                    ax1.set_xticks(tick_positions)
                    ax1.set_xticklabels(hourly_perf['Waktu'].iloc[tick_positions], rotation=45, ha="right")
                    
                    fig.tight_layout()
                    plt.title('Performa Order dan ROAS per Interval')
                    st.pyplot(fig)

            else:
                columns_to_show = ["Nama Studio", "Username", "Penjualan", "Biaya_Iklan", "Profit", "Rata_ROAS", "Status ROAS", "Status Profit"]
                data_view = pd.DataFrame()
                
                page_map = {
                    "❌ Akun Boncos (ROAS < 5)": (daily["Rata_ROAS"] < 5, "💡 Rekomendasi: Pause iklan dan evaluasi ulang produk & target pasar."),
                    "🟠 Perlu Optimasi (ROAS 5-29.9)": ((daily["Rata_ROAS"] >= 5) & (daily["Rata_ROAS"] < 30), "💡 Tips: Cek jam efektif, ganti materi iklan, atau sesuaikan bidding."),
                    "🎯 Hampir Aman (ROAS 30–49.9)": ((daily["Rata_ROAS"] >= 30) & (daily["Rata_ROAS"] < 50), "💡 Tips: Optimasi sedikit lagi untuk tembus target ROAS 50!"),
                    "✅ AMAN (ROAS ≥ 50)": (daily["Rata_ROAS"] >= 50, "🎉 Hebat! Akun-akun ini sudah mencapai target.")
                }

                if menu in page_map:
                    st.subheader(menu)
                    condition, tip = page_map[menu]
                    data_view = daily[condition]
                    if data_view.empty:
                        st.success(f"✅ Tidak ada akun di rentang ini.")
                    else:
                        st.info(tip)
                        st.dataframe(style_summary_table(data_view[columns_to_show]), use_container_width=True)

            if menu == "🔍 Detail Per Interval":
                st.subheader("🔍 Detail Per Interval Waktu")
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
                    ax[0].set_ylabel("ROAS"); ax[0].set_title(f"ROAS per Interval - {selected_user_graph}")
                    ax[0].grid(True, alpha=0.3); ax[0].legend()

                    ax[1].bar(x_range, user_data_graph["Penonton"], alpha=0.7, color="skyblue", label="Penonton")
                    ax[1].set_ylabel("Penonton"); ax[1].set_xlabel("Waktu"); ax[1].legend()

                    num_ticks = min(len(user_data_graph), 24)
                    tick_positions = np.linspace(0, len(user_data_graph) - 1, num_ticks, dtype=int)
                    ax[1].set_xticks(tick_positions); 
                    ax[1].set_xticklabels(user_data_graph['Waktu'].iloc[tick_positions], rotation=45, ha="right")


                    plt.tight_layout()
                    st.pyplot(fig)

                    st.subheader("📥 Download Data")
                    csv_daily = daily.to_csv(index=False).encode('utf-8')
                    st.download_button("⬇️ Download CSV (Ringkasan Performa)", data=csv_daily, file_name=f"ringkasan_performa_roas.csv", mime="text/csv")
                    
                    csv_detail = user_data_graph.to_csv(index=False).encode('utf-8')
                    st.download_button("⬇️ Download CSV (Detail Interval Akun Terpilih)", data=csv_detail, file_name=f"{selected_user_graph}_detail_interval.csv", mime="text/csv")

    except Exception as e:
        st.error(f"❌ Terjadi kesalahan saat memproses data: {str(e)}")
        st.exception(e)

else:
    st.info("Silakan atur 'Pengaturan Input Data' di sidebar dan masukkan data untuk memulai analisis.")
