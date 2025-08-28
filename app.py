import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="📊 Analisis ROAS Shopee", layout="wide")
st.title("📈 Analisis Data Iklan Shopee v6")
st.markdown("Kini dengan dukungan Analisis Historis per 15 Menit!")

# === Fungsi Bantuan (Helpers) ===
def format_rupiah(x):
    if pd.isna(x) or not isinstance(x, (int, float)): return "-"
    x = float(x)
    if abs(x) >= 1e6: return f"Rp {x/1e6:.1f} juta"
    elif abs(x) >= 1e3: return f"Rp {x/1e3:.0f}rb"
    else: return f"Rp {int(x)}"

def style_profit_color(val):
    color = 'black'
    if isinstance(val, (int, float)):
        if val > 0: color = 'green'
        elif val < 0: color = 'red'
    return f'color: {color}'

def style_summary_table(df_to_style):
    formatters = {
        "Penjualan": format_rupiah, "Biaya_Iklan": format_rupiah,
        "Biaya_Iklan_PPN": format_rupiah, "Komisi": format_rupiah, 
        "Profit": format_rupiah, "ROAS": "{:.2f}", "View": "{:,.0f}"
    }
    valid_formatters = {k: v for k, v in formatters.items() if k in df_to_style.columns}
    styled = df_to_style.style.format(valid_formatters)
    if "Profit" in df_to_style.columns:
        styled = styled.applymap(style_profit_color, subset=['Profit'])
    return styled

# === Fungsi Parsing (Parser) ===

# --- Parser untuk Data Historis (Format Baru) ---
@st.cache_data
def parse_historical_data(raw_data, commission_rate):
    lines = raw_data.strip().split('\n')
    header = lines[0].split('\t')
    
    try:
        time_cols_start_index = 5
        valid_time_headers_with_indices = []
        for i, h in enumerate(header[time_cols_start_index:]):
            if h.strip():
                original_index = time_cols_start_index + i
                valid_time_headers_with_indices.append((original_index, h.strip()))

        timestamp_strings = [h for _, h in valid_time_headers_with_indices]
        if not timestamp_strings:
            st.error("Tidak ada kolom tanggal yang valid ditemukan di header.")
            return pd.DataFrame()
            
        timestamps = pd.to_datetime(timestamp_strings)
    except Exception as e:
        st.error(f"Gagal mem-parsing header tanggal. Pastikan formatnya benar. Error: {e}")
        return pd.DataFrame()

    records = []
    for line in lines[1:]:
        parts = line.split('\t')
        if len(parts) < time_cols_start_index + 1 or "TOTAL" in parts[0].upper():
            continue
            
        nama_studio = parts[0]
        username = parts[1]
        
        for i, ts in enumerate(timestamps):
            original_data_index = valid_time_headers_with_indices[i][0]
            if original_data_index >= len(parts): continue

            data_cell = parts[original_data_index].strip()
            
            try:
                cell_parts = data_cell.split('|')
                if len(cell_parts) < 4: continue

                # Biaya iklan sekarang adalah nilai asli tanpa PPN
                biaya_iklan = float(cell_parts[0].replace(".", "") or 0)
                penjualan = float(cell_parts[1].replace(".", "") or 0)
                view = int(cell_parts[3].replace(".", "") or 0)
                
                komisi = penjualan * (commission_rate / 100)
                # Profit di sini juga dihitung dari biaya asli
                profit = komisi - biaya_iklan
                roas = penjualan / biaya_iklan if biaya_iklan > 0 else 0

                records.append({
                    "Timestamp": ts, "Nama Studio": nama_studio, "Username": username,
                    "Biaya_Iklan": biaya_iklan, "Penjualan": penjualan, "View": view,
                    "Komisi": komisi, "Profit": profit, "ROAS": roas
                })

            except (ValueError, IndexError):
                continue

    return pd.DataFrame(records)

# --- Parser untuk Data Ringkasan (Format Lama) ---
@st.cache_data
def parse_summary_data(raw_data, commission_rate):
    lines = raw_data.strip().split('\n')
    records = []
    for line in lines:
        if not line or any(k in line.upper() for k in ["NAMA STUDIO", "TOTAL"]):
            continue
        parts = line.split("\t")
        if len(parts) < 5: continue
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
        except (ValueError, IndexError):
            continue
    return pd.DataFrame(records)


# === Inisialisasi Session State ===
if 'df_processed' not in st.session_state:
    st.session_state.df_processed = pd.DataFrame()
if 'analysis_mode' not in st.session_state:
    st.session_state.analysis_mode = None

# === Sidebar & Input ===
st.sidebar.title("⚙️ Pengaturan & Filter")
analysis_mode = st.sidebar.selectbox(
    "Pilih Mode Analisis",
    ["Pilih Mode...", "Analisis Ringkasan (Total)", "Analisis Historis (Per Waktu)"]
)

if analysis_mode != "Pilih Mode...":
    commission_input = st.sidebar.number_input(
        "Persentase Komisi (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.1
    )
    st.sidebar.markdown("---")
    
    uploaded_file = st.sidebar.file_uploader("Upload file (.txt, .csv)", type=["txt", "csv"])
    
    if uploaded_file:
        raw_data = uploaded_file.read().decode("utf-8")
        
        if analysis_mode == "Analisis Historis (Per Waktu)":
            df = parse_historical_data(raw_data, commission_input)
            st.session_state.analysis_mode = "Historis"
        else: # Analisis Ringkasan
            df = parse_summary_data(raw_data, commission_input)
            st.session_state.analysis_mode = "Ringkasan"
        
        if not df.empty:
            st.session_state.df_processed = df
            st.sidebar.success(f"✅ Data berhasil diparsing! {len(df) if st.session_state.analysis_mode == 'Historis' else df['Username'].nunique()} item data ditemukan.")
        else:
            st.sidebar.error("Gagal memproses data. Periksa format file.")

# === Tampilan Utama ===
if not st.session_state.df_processed.empty:
    df_processed = st.session_state.df_processed
    
    all_studios = df_processed['Nama Studio'].unique()
    selected_studios = st.sidebar.multiselect("Filter Nama Studio", all_studios, default=all_studios)
    
    filtered_df = df_processed[df_processed['Nama Studio'].isin(selected_studios)] if selected_studios else pd.DataFrame()

    # ===================================================================
    # --- TAMPILAN UNTUK MODE ANALISIS HISTORIS ---
    # ===================================================================
    if st.session_state.analysis_mode == "Historis" and not filtered_df.empty:
        st.sidebar.markdown("---")
        menu = st.sidebar.radio("Pilih Halaman", ["📈 Analisis Tren Waktu", "📄 Tabel Data per 15 Menit", "📊 Ringkasan Performa"])

        min_date = filtered_df['Timestamp'].min().date()
        max_date = filtered_df['Timestamp'].max().date()
        
        date_range = st.sidebar.date_input(
            "Pilih Rentang Tanggal",
            value=(min_date, max_date),
            min_value=min_date, max_value=max_date
        )
        
        time_filtered_df = pd.DataFrame()
        if len(date_range) == 2:
            start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            time_filtered_df = filtered_df[(filtered_df['Timestamp'] >= start_date) & (filtered_df['Timestamp'] <= end_date + pd.Timedelta(days=1))]

        if menu == "📈 Analisis Tren Waktu":
            st.subheader("📈 Analisis Tren Performa Berdasarkan Waktu")
            if not time_filtered_df.empty:
                agg_option = st.sidebar.selectbox("Agregasi Waktu", ["15 Menit", "Per Jam", "Per Hari"])
                agg_map = {"15 Menit": "15T", "Per Jam": "H", "Per Hari": "D"}
                
                df_agg = time_filtered_df.set_index('Timestamp')[['Penjualan', 'Biaya_Iklan', 'Profit']].resample(agg_map[agg_option]).sum().reset_index()

                st.subheader(f"Tren Agregasi {agg_option}")
                st.line_chart(df_agg.set_index('Timestamp'))

                st.markdown("---")
                st.subheader("🏆 Analisis Jam Emas (Golden Hours)")
                hourly_summary = time_filtered_df.copy()
                hourly_summary['Jam'] = hourly_summary['Timestamp'].dt.hour
                golden_hours_df = hourly_summary.groupby('Jam')[['Penjualan', 'Profit']].sum()
                st.bar_chart(golden_hours_df)
            else:
                st.warning("Tidak ada data pada rentang tanggal yang dipilih.")
        
        elif menu == "📄 Tabel Data per 15 Menit":
            st.subheader("📄 Tabel Rincian per 15 Menit")
            st.info("Tabel ini menampilkan biaya iklan asli (tanpa PPN).")
            if not time_filtered_df.empty:
                active_data = time_filtered_df[(time_filtered_df['Penjualan'] > 0) | (time_filtered_df['Biaya_Iklan'] > 0)]
                st.dataframe(style_summary_table(active_data[['Timestamp', 'Username', 'Biaya_Iklan', 'Penjualan', 'Profit', 'View']]), use_container_width=True)
            else:
                st.warning("Tidak ada data pada rentang tanggal yang dipilih.")

        elif menu == "📊 Ringkasan Performa":
            st.subheader("📊 Ringkasan Performa Total")
            st.info("Pada ringkasan ini, PPN 11% ditambahkan ke Total Biaya Iklan untuk menghitung Profit Bersih.")
            if not time_filtered_df.empty:
                total_penjualan = time_filtered_df['Penjualan'].sum()
                total_biaya_asli = time_filtered_df['Biaya_Iklan'].sum()
                total_biaya_ppn = total_biaya_asli * 1.11
                total_komisi = time_filtered_df['Komisi'].sum()
                total_profit_bersih = total_komisi - total_biaya_ppn
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Penjualan", format_rupiah(total_penjualan))
                col2.metric("Total Biaya Iklan (+PPN 11%)", format_rupiah(total_biaya_ppn))
                col3.metric(f"Total Komisi ({commission_input}%)", format_rupiah(total_komisi))
                col4.metric("Profit Bersih (Setelah PPN)", format_rupiah(total_profit_bersih), delta_color=("inverse" if total_profit_bersih < 0 else "normal"))

                st.markdown("---")
                summary = time_filtered_df.groupby(['Nama Studio', 'Username']).agg(
                    Penjualan=("Penjualan", "sum"),
                    Biaya_Iklan=("Biaya_Iklan", "sum"),
                    Komisi=("Komisi", "sum"),
                    View=("View", "sum")
                ).reset_index()
                
                summary['Biaya_Iklan_PPN'] = summary['Biaya_Iklan'] * 1.11
                summary['Profit'] = summary['Komisi'] - summary['Biaya_Iklan_PPN']
                summary['ROAS'] = (summary['Penjualan'] / summary['Biaya_Iklan_PPN']).fillna(0)
                
                st.dataframe(style_summary_table(summary[['Nama Studio', 'Username', 'Penjualan', 'Biaya_Iklan_PPN', 'Profit', 'ROAS', 'View']].rename(columns={"Biaya_Iklan_PPN": "Biaya_Iklan"})), use_container_width=True)
            else:
                st.warning("Tidak ada data pada rentang tanggal yang dipilih.")

    # ===================================================================
    # --- TAMPILAN UNTUK MODE ANALISIS RINGKASAN ---
    # ===================================================================
    elif st.session_state.analysis_mode == "Ringkasan" and not filtered_df.empty:
        menu_options = ["📊 Ringkasan Performa", "🏢 Ringkasan per Studio", "📥 Download Data"]
        menu = st.sidebar.radio("Pilih Halaman", menu_options)

        if menu == "📊 Ringkasan Performa":
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
            
            st.markdown("---")
            st.subheader("Data Lengkap")
            st.dataframe(style_summary_table(filtered_df), use_container_width=True)

        elif menu == "🏢 Ringkasan per Studio":
            st.subheader("🏢 Ringkasan Performa per Studio")
            studio_summary = filtered_df.groupby("Nama Studio").agg(
                Penjualan=("Penjualan", "sum"), Biaya_Iklan=("Biaya_Iklan", "sum"),
                Profit=("Profit", "sum"), Jumlah_Akun=("Username", "count")
            ).reset_index()
            studio_summary['ROAS'] = (studio_summary['Penjualan'] / studio_summary['Biaya_Iklan']).fillna(0)
            st.dataframe(style_summary_table(studio_summary), use_container_width=True)

        elif menu == "📥 Download Data":
            st.subheader("📥 Download Data yang Telah Diproses")
            csv_data = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download CSV", data=csv_data, file_name="analisis_roas_ringkasan.csv", mime="text/csv")

    elif filtered_df.empty:
        st.warning("Tidak ada data untuk ditampilkan. Silakan pilih setidaknya satu studio di sidebar.")

else:
    st.info("Selamat datang! Silakan pilih mode analisis dan upload file data Anda melalui sidebar untuk memulai.")

