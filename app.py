import streamlit as st
import pandas as pd
import numpy as np

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="📊 Analisis ROAS Shopee", layout="wide")
st.title("📈 Analisis Data Iklan Shopee (Advanced)")

st.markdown("""
**Aplikasi ini dirancang untuk membaca data ringkasan dari Shopee.**
**Format Data yang Diharapkan:** `Nama Studio | Username | Saldo | Total Penjualan | Total Biaya Iklan`
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

def style_profit_color(val):
    """Memberi warna hijau untuk profit dan merah untuk rugi."""
    color = 'black'
    if isinstance(val, (int, float)):
        if val > 0: color = 'green'
        elif val < 0: color = 'red'
    return f'color: {color}'

def style_summary_table(df_to_style):
    """Fungsi untuk menerapkan styling umum pada tabel ringkasan."""
    formatters = {
        "Penjualan": format_rupiah,
        "Biaya_Iklan": format_rupiah,
        "Komisi": format_rupiah,
        "Profit": format_rupiah,
        "ROAS": "{:.2f}",
        "Skor": "{:.1f}"
    }
    # Hanya format kolom yang ada di dataframe
    valid_formatters = {k: v for k, v in formatters.items() if k in df_to_style.columns}
    styled = df_to_style.style.format(valid_formatters)
    
    if "Profit" in df_to_style.columns:
        styled = styled.applymap(style_profit_color, subset=['Profit'])
    if "Skor" in df_to_style.columns:
        styled = styled.background_gradient(cmap='RdYlGn', subset=['Skor'], vmin=1, vmax=100)
        
    return styled

# --- FITUR BARU: SKOR PERFORMA ---
def manual_min_max_scaler(series):
    """Fungsi untuk menormalkan data ke rentang 0-1."""
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series([0.5] * len(series), index=series.index)
    return (series - min_val) / (max_val - min_val)

def calculate_health_score(df):
    """Menghitung Skor Performa berdasarkan ROAS (60%) dan Profit (40%)."""
    if df.empty or len(df) < 2:
        if not df.empty:
            df['Skor'] = 50.0
        return df

    # Atasi nilai ROAS yang ekstrem untuk penskalaan yang lebih baik
    roas_cap = df['ROAS'].quantile(0.95)
    df['roas_capped'] = df['ROAS'].clip(upper=roas_cap)

    roas_scaled = manual_min_max_scaler(df['roas_capped'])
    profit_scaled = manual_min_max_scaler(df['Profit'])

    # Hitung skor tertimbang
    weighted_score = (roas_scaled * 0.6) + (profit_scaled * 0.4)

    # Skalakan hasil ke 1-100
    df['Skor'] = ((weighted_score * 99) + 1).round(1)
    df.drop(columns=['roas_capped'], inplace=True)
    return df

# === Parsing Function untuk Data Ringkasan ===
@st.cache_data
def parse_summary_data(raw_lines, commission_rate):
    records = []
    for line in raw_lines:
        line = line.strip()
        if not line or any(k in line.upper() for k in ["NAMA STUDIO", "TOTAL", "BELUM MENDAFTAR", "PAUSED"]):
            continue

        parts = line.split("\t")
        if len(parts) < 5:
            st.warning(f"Melewatkan baris karena format tidak sesuai: '{line[:70]}...'")
            continue

        try:
            studio = parts[0].strip()
            username = parts[1].strip()
            penjualan = float(str(parts[3]).replace(".", "").replace(",", "") or 0)
            biaya_iklan_sebelum_ppn = float(str(parts[4]).replace(".", "").replace(",", "") or 0)
            biaya_iklan_dengan_ppn = biaya_iklan_sebelum_ppn * 1.11

            roas = penjualan / biaya_iklan_dengan_ppn if biaya_iklan_dengan_ppn > 0 else 0
            komisi = penjualan * (commission_rate / 100)
            profit = komisi - biaya_iklan_dengan_ppn

            records.append({
                "Nama Studio": studio, "Username": username, "Penjualan": penjualan,
                "Biaya_Iklan": biaya_iklan_dengan_ppn, "ROAS": roas,
                "Komisi": komisi, "Profit": profit
            })
        except (ValueError, IndexError) as e:
            st.warning(f"Gagal memproses baris: '{line[:70]}...'. Error: {e}")

    return pd.DataFrame(records) if records else pd.DataFrame()

# --- Penggunaan Session State ---
if 'df_processed' not in st.session_state:
    st.session_state.df_processed = pd.DataFrame()

# === Sidebar & Input ===
st.sidebar.title("⚙️ Pengaturan & Filter")
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
        "Paste data dari Excel/Notepad (gunakan TAB antar kolom)", height=250,
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
        df = calculate_health_score(df) # Hitung Skor Performa
        st.session_state.df_processed = df
        st.success(f"✅ Data berhasil diparsing! {len(df)} akun ditemukan.")

# === Tampilkan Analisis Jika Data Ada di Session State ===
if not st.session_state.df_processed.empty:
    df_processed = st.session_state.df_processed
    all_studios = df_processed['Nama Studio'].unique()
    selected_studios = st.sidebar.multiselect("Filter Nama Studio", all_studios, default=all_studios)
    
    filtered_df = df_processed[df_processed['Nama Studio'].isin(selected_studios)] if selected_studios else pd.DataFrame()
    
    menu_options = [
        "📊 Ringkasan Performa", "🏢 Ringkasan per Studio", "💰 Analisis Komisi & Profit",
        "🕵️ Akun Anomali", # FITUR BARU
        "✅ AMAN (ROAS ≥ 50)", "🎯 Hampir Aman (ROAS 30–49.9)",
        "🟠 Perlu Optimasi (ROAS 5-29.9)", "❌ Akun Boncos (ROAS < 5)", "📥 Download Data"
    ]
    menu = st.sidebar.radio("Pilih Halaman Analisis", menu_options)

    if menu == "📊 Ringkasan Performa" and not filtered_df.empty:
        st.subheader("📋 Ringkasan Performa Studio")
        total_penjualan = filtered_df["Penjualan"].sum()
        total_biaya = filtered_df["Biaya_Iklan"].sum()
        profit_kotor = filtered_df["Komisi"].sum()
        profit_bersih = filtered_df["Profit"].sum()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Penjualan", format_rupiah(total_penjualan))
        col2.metric("Total Biaya Iklan (+PPN 11%)", format_rupiah(total_biaya))
        col3.metric(f"Profit Kotor (Komisi {commission_input}%)", format_rupiah(profit_kotor))
        col4.metric("Profit Bersih", format_rupiah(profit_bersih), delta_color=("inverse" if profit_bersih < 0 else "normal"))
        
        # --- FITUR BARU: METRIK AKUN ANOMALI ---
        st.markdown("---")
        akun_tanpa_penjualan = filtered_df[(filtered_df['Penjualan'] == 0) & (filtered_df['Biaya_Iklan'] > 0)].shape[0]
        akun_tidak_aktif = filtered_df[(filtered_df['Penjualan'] == 0) & (filtered_df['Biaya_Iklan'] == 0)].shape[0]
        
        col5, col6 = st.columns(2)
        col5.metric("⚠️ Akun Tanpa Penjualan", f"{akun_tanpa_penjualan} Akun", help="Akun yang memiliki biaya iklan namun tidak menghasilkan penjualan.")
        col6.metric("⏸️ Akun Tidak Aktif", f"{akun_tidak_aktif} Akun", help="Akun yang tidak memiliki biaya iklan maupun penjualan.")
        
        st.markdown("---")
        st.subheader("Data Lengkap")
        st.dataframe(style_summary_table(filtered_df), use_container_width=True)

    # --- FITUR BARU: HALAMAN AKUN ANOMALI ---
    elif menu == "🕵️ Akun Anomali":
        st.subheader("🕵️ Analisis Akun Anomali")
        st.info("Halaman ini mengidentifikasi akun-akun yang berpotensi bermasalah atau tidak efisien.")

        st.markdown("---")
        st.subheader("⚠️ Akun Tanpa Penjualan (Biaya Iklan > 0)")
        st.warning("Akun-akun ini menghabiskan biaya iklan tanpa menghasilkan penjualan. Perlu investigasi segera.")
        df_tanpa_penjualan = filtered_df[(filtered_df['Penjualan'] == 0) & (filtered_df['Biaya_Iklan'] > 0)]
        if df_tanpa_penjualan.empty:
            st.success("✅ Tidak ditemukan akun tanpa penjualan.")
        else:
            st.dataframe(style_summary_table(df_tanpa_penjualan[['Nama Studio', 'Username', 'Biaya_Iklan', 'Profit', 'Skor']]), use_container_width=True)

        st.markdown("---")
        st.subheader("⏸️ Akun Tidak Aktif (Biaya Iklan & Penjualan = 0)")
        st.write("Akun-akun ini tidak memiliki aktivitas iklan maupun penjualan.")
        df_tidak_aktif = filtered_df[(filtered_df['Penjualan'] == 0) & (filtered_df['Biaya_Iklan'] == 0)]
        if df_tidak_aktif.empty:
            st.success("✅ Tidak ditemukan akun yang tidak aktif.")
        else:
            st.dataframe(df_tidak_aktif[['Nama Studio', 'Username']], use_container_width=True)
    
    # Halaman-halaman lainnya tetap sama
    elif menu == "🏢 Ringkasan per Studio" and not filtered_df.empty:
        st.subheader("🏢 Ringkasan Performa per Studio")
        studio_summary = filtered_df.groupby("Nama Studio").agg(
            Penjualan=("Penjualan", "sum"), Biaya_Iklan=("Biaya_Iklan", "sum"),
            Profit=("Profit", "sum"), Jumlah_Akun=("Username", "count"), Skor_Rata2=("Skor", "mean")
        ).reset_index()
        studio_summary['ROAS'] = (studio_summary['Penjualan'] / studio_summary['Biaya_Iklan']).fillna(0)
        st.dataframe(style_summary_table(studio_summary), use_container_width=True)

    elif menu == "💰 Analisis Komisi & Profit" and not filtered_df.empty:
        st.subheader(f"💰 Estimasi Komisi ({commission_input}%) & Profit")
        profit_df = filtered_df[["Nama Studio", "Username", "Penjualan", "Komisi", "Biaya_Iklan", "Profit", "Status Profit", "Skor"]].copy()
        profit_df = profit_df.sort_values("Profit", ascending=False)
        st.dataframe(style_summary_table(profit_df), use_container_width=True)
    
    elif menu == "📥 Download Data" and not filtered_df.empty:
        st.subheader("📥 Download Data yang Telah Diproses")
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Download CSV", data=csv_data, file_name="analisis_roas_shopee_lanjutan.csv", mime="text/csv")

    elif menu in ["✅ AMAN (ROAS ≥ 50)", "🎯 Hampir Aman (ROAS 30–49.9)", "🟠 Perlu Optimasi (ROAS 5-29.9)", "❌ Akun Boncos (ROAS < 5)"]:
        page_map = {
            "❌ Akun Boncos (ROAS < 5)": (filtered_df["ROAS"] < 5, "💡 Rekomendasi: Pause iklan dan evaluasi ulang produk & target pasar."),
            "🟠 Perlu Optimasi (ROAS 5-29.9)": ((filtered_df["ROAS"] >= 5) & (filtered_df["ROAS"] < 30), "💡 Tips: Cek materi iklan atau sesuaikan bidding."),
            "🎯 Hampir Aman (ROAS 30–49.9)": ((filtered_df["ROAS"] >= 30) & (filtered_df["ROAS"] < 50), "💡 Tips: Optimasi sedikit lagi untuk tembus target ROAS 50!"),
            "✅ AMAN (ROAS ≥ 50)": (filtered_df["ROAS"] >= 50, "🎉 Hebat! Akun-akun ini sudah mencapai target.")
        }
        st.subheader(menu)
        condition, tip = page_map[menu]
        data_view = filtered_df[condition]
        if data_view.empty:
            st.success(f"✅ Tidak ada akun di rentang ini.")
        else:
            st.info(tip)
            st.dataframe(style_summary_table(data_view), use_container_width=True)
    
    elif filtered_df.empty:
        st.warning("Tidak ada data untuk ditampilkan. Silakan pilih setidaknya satu studio di sidebar.")

else:
    st.info("Silakan masukkan data melalui sidebar untuk memulai analisis.")
