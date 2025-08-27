import streamlit as st
import pandas as pd
import numpy as np

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Analisis ROAS Shopee Live", layout="wide")
st.title("Analisis Data Iklan Shopee (Advanced)")

st.markdown("""
**Aplikasi ini dirancang untuk membaca data ringkasan dari Shopee.**
**Paste Data Laporan Histori Iklan`
""")

# === Fungsi Bantuan (Helpers) ===
def format_rupiah(x):
    if pd.isna(x) or not isinstance(x, (int, float)): return "-"
    x = float(x)
    if abs(x) >= 1e6:
        return f"Rp {x/1e6:.1f} juta"
    elif abs(x) >= 1e3:
        return f"Rp {x/1e3:.0f}rb"
    else:
        return f"Rp {int(x)}"

# --- LEVEL 1: Fungsi untuk mewarnai profit/rugi ---
def style_profit_color(val):
    """Memberi warna hijau untuk profit dan merah untuk rugi."""
    if val > 0:
        color = 'green'
    elif val < 0:
        color = 'red'
    else:
        color = 'black'
    return f'color: {color}'

def style_summary_table(df_to_style):
    """Fungsi untuk menerapkan styling umum pada tabel ringkasan."""
    styled = df_to_style.style.format({
        "Penjualan": format_rupiah,
        "Biaya_Iklan": format_rupiah,
        "Komisi": format_rupiah,
        "Profit": format_rupiah,
        "ROAS": "{:.2f}"
    })
    # Terapkan pewarnaan pada kolom Profit jika ada
    if "Profit" in df_to_style.columns:
        styled = styled.applymap(style_profit_color, subset=['Profit'])
    return styled

# === Parsing Function untuk Data Ringkasan ===
@st.cache_data
def parse_summary_data(raw_lines, commission_rate):
    """Fungsi yang disederhanakan untuk mem-parsing data ringkasan harian."""
    records = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        if any(k in line.upper() for k in ["NAMA STUDIO", "TOTAL", "BELUM MENDAFTAR", "PAUSED"]):
            continue

        parts = line.split("\t")
        if len(parts) < 5:
            st.warning(f"Melewatkan baris karena format tidak sesuai: '{line[:70]}...'")
            continue

        try:
            studio = parts[0].strip()
            username = parts[1].strip()
            penjualan = float(str(parts[3]).replace(".", "").replace(",", "") or 0)
            biaya_iklan = float(str(parts[4]).replace(".", "").replace(",", "") or 0)

            roas = penjualan / biaya_iklan if biaya_iklan > 0 else 0
            komisi = penjualan * (commission_rate / 100)
            profit = komisi - biaya_iklan

            records.append({
                "Nama Studio": studio,
                "Username": username,
                "Penjualan": penjualan,
                "Biaya_Iklan": biaya_iklan,
                "ROAS": roas,
                "Komisi": komisi,
                "Profit": profit
            })
        except (ValueError, IndexError) as e:
            st.warning(f"Gagal memproses baris: '{line[:70]}...'. Error: {e}")

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)

# --- LEVEL 3: Penggunaan Session State ---
if 'df_processed' not in st.session_state:
    st.session_state.df_processed = pd.DataFrame()

# === Sidebar & Input ===
st.sidebar.title("⚙️ Pengaturan & Filter")
# --- LEVEL 1: Input Komisi Dinamis ---
commission_input = st.sidebar.number_input(
    "Persentase Komisi (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.1
)

st.sidebar.markdown("---")
mode = st.sidebar.radio("Pilih Cara Input", ["Upload File", "Paste Manual"])
lines = []

if mode == "Upload File":
    uploaded_file = st.sidebar.file_uploader("Upload file (.txt, .csv)", type=["txt", "csv"])
    if uploaded_file:
        raw_data = uploaded_file.read().decode("utf-8")
        lines = [line.strip() for line in raw_data.split("\n") if line.strip()]
elif mode == "Paste Manual":
    raw_data = st.text_area(
        "Paste data dari Excel/Notepad (gunakan TAB antar kolom)",
        height=250,
        placeholder="Contoh:\nSTUDIO SURABAYA FASHION PRIA\tgrosirpakaiandansby\t16.692\t70.675.342\t1.661.067"
    )
    if raw_data.strip():
        lines = [line.strip() for line in raw_data.split("\n") if line.strip()]

# === Proses Data Jika Ada Input Baru ===
if lines:
    df = parse_summary_data(lines, commission_input)
    if not df.empty:
        df["Status Profit"] = df["Profit"].apply(lambda p: "✅ Profit" if p > 0 else ("❌ Rugi" if p < 0 else "➖ Break Even"))
        def status_roas(r):
            if r == 0: return "⏸️ Tidak Aktif"
            if r < 5: return "🔴 Boncos"
            if r < 30: return "🟠 Perlu Optimasi"
            if r < 50: return "🟡 Hampir Aman"
            return "🟢 AMAN (ROAS ≥ 50)"
        df["Status ROAS"] = df["ROAS"].apply(status_roas)
        st.session_state.df_processed = df
        st.success(f"✅ Data berhasil diparsing! {len(df)} akun ditemukan.")

# === Tampilkan Analisis Jika Data Ada di Session State ===
if not st.session_state.df_processed.empty:
    df_processed = st.session_state.df_processed

    # --- Filter Lanjutan di Sidebar ---
    all_studios = df_processed['Nama Studio'].unique()
    selected_studios = st.sidebar.multiselect("Filter Nama Studio", all_studios, default=all_studios)
    
    if not selected_studios:
        st.sidebar.warning("Pilih minimal satu studio.")
        filtered_df = pd.DataFrame()
    else:
        filtered_df = df_processed[df_processed['Nama Studio'].isin(selected_studios)]
    
    # --- Menu Navigasi ---
    menu_options = [
        "📊 Ringkasan Performa",
        "🏢 Ringkasan per Studio", # LEVEL 2
        "💰 Analisis Komisi & Profit",
        "✅ AMAN (ROAS ≥ 50)",
        "🎯 Hampir Aman (ROAS 30–49.9)",
        "🟠 Perlu Optimasi (ROAS 5-29.9)",
        "❌ Akun Boncos (ROAS < 5)",
        "📥 Download Data"
    ]
    menu = st.sidebar.radio("Pilih Halaman Analisis", menu_options)

    # --- Tampilan Halaman ---
    if menu == "📊 Ringkasan Performa":
        st.subheader("📋 Ringkasan Performa Studio")
        if not filtered_df.empty:
            total_penjualan = filtered_df["Penjualan"].sum()
            total_biaya = filtered_df["Biaya_Iklan"].sum()
            profit_kotor = filtered_df["Komisi"].sum()
            profit_bersih = filtered_df["Profit"].sum()
            
            if total_biaya > 0:
                roas_studio = (total_penjualan / total_biaya) * 100
            else:
                roas_studio = 0

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Penjualan", format_rupiah(total_penjualan))
            col2.metric("Total Biaya Iklan", format_rupiah(total_biaya))
            col3.metric(f"Profit Kotor (Komisi {commission_input}%)", format_rupiah(profit_kotor))
            col4.metric("Profit Bersih", format_rupiah(profit_bersih), delta_color=("inverse" if profit_bersih < 0 else "normal"))

            st.markdown("---")
            
            # --- PERUBAHAN VISUALISASI DARI GRAFIK KE TABEL ---
            st.subheader("Akun Performa Terbaik & Terendah")
            col_table1, col_table2 = st.columns(2)

            top_5_profit = filtered_df.nlargest(5, 'Profit')
            top_5_loss = filtered_df.nsmallest(5, 'Profit')
            
            columns_to_show = ['Username', 'Profit', 'Penjualan', 'Biaya_Iklan']

            with col_table1:
                st.write("Top 5 Akun Profit Tertinggi")
                st.dataframe(
                    style_summary_table(top_5_profit[columns_to_show]), 
                    use_container_width=True
                )

            with col_table2:
                st.write("Top 5 Akun Rugi Terbesar")
                st.dataframe(
                    style_summary_table(top_5_loss[columns_to_show]), 
                    use_container_width=True
                )
            # --- AKHIR PERUBAHAN ---
            
            st.markdown("---")
            st.subheader("Data Lengkap")
            st.dataframe(style_summary_table(filtered_df).background_gradient(cmap="RdYlGn", subset=["ROAS"], vmin=0, vmax=60), use_container_width=True)

    # --- LEVEL 2: Halaman Ringkasan per Studio ---
    elif menu == "🏢 Ringkasan per Studio":
        st.subheader("🏢 Ringkasan Performa per Studio")
        if not filtered_df.empty:
            studio_summary = filtered_df.groupby("Nama Studio").agg(
                Penjualan=("Penjualan", "sum"),
                Biaya_Iklan=("Biaya_Iklan", "sum"),
                Profit=("Profit", "sum"),
                Jumlah_Akun=("Username", "count")
            ).reset_index()
            
            studio_summary['ROAS'] = (studio_summary['Penjualan'] / studio_summary['Biaya_Iklan']).fillna(0)
            
            st.dataframe(
                studio_summary.style.format({
                    "Penjualan": format_rupiah,
                    "Biaya_Iklan": format_rupiah,
                    "Profit": format_rupiah,
                    "ROAS": "{:.2f}x"
                }).applymap(style_profit_color, subset=['Profit'])
                .bar(subset=["Profit"], align="zero", color=['#ff9999', '#90ee90']),
                use_container_width=True
            )

    elif menu == "💰 Analisis Komisi & Profit":
        st.subheader(f"💰 Estimasi Komisi ({commission_input}%) & Profit")
        profit_df = filtered_df[["Nama Studio", "Username", "Penjualan", "Komisi", "Biaya_Iklan", "Profit", "Status Profit"]].copy()
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
    
    elif menu == "📥 Download Data":
        st.subheader("📥 Download Data yang Telah Diproses")
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "⬇️ Download CSV (Data Terfilter)",
            data=csv_data,
            file_name="analisis_roas_shopee_lanjutan.csv",
            mime="text/csv"
        )

    else: # Halaman Kategori ROAS
        columns_to_show = ["Nama Studio", "Username", "Penjualan", "Biaya_Iklan", "Profit", "ROAS", "Status ROAS", "Status Profit"]
        data_view = pd.DataFrame()
        
        page_map = {
            "❌ Akun Boncos (ROAS < 5)": (filtered_df["ROAS"] < 5, "💡 Rekomendasi: Pause iklan dan evaluasi ulang produk & target pasar."),
            "🟠 Perlu Optimasi (ROAS 5-29.9)": ((filtered_df["ROAS"] >= 5) & (filtered_df["ROAS"] < 30), "💡 Tips: Cek materi iklan atau sesuaikan bidding."),
            "🎯 Hampir Aman (ROAS 30–49.9)": ((filtered_df["ROAS"] >= 30) & (filtered_df["ROAS"] < 50), "💡 Tips: Optimasi sedikit lagi untuk tembus target ROAS 50!"),
            "✅ AMAN (ROAS ≥ 50)": (filtered_df["ROAS"] >= 50, "🎉 Hebat! Akun-akun ini sudah mencapai target.")
        }

        if menu in page_map:
            st.subheader(menu)
            condition, tip = page_map[menu]
            data_view = filtered_df[condition]
            if data_view.empty:
                st.success(f"✅ Tidak ada akun di rentang ini.")
            else:
                st.info(tip)
                st.dataframe(style_summary_table(data_view[columns_to_show]), use_container_width=True)

else:
    st.info("Silakan masukkan data melalui sidebar untuk memulai analisis.")
