import streamlit as st
import pandas as pd
import numpy as np

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="📊 Analisis ROAS Shopee", layout="wide")
st.title("📈 Analisis Data Iklan Shopee (Ringkasan)")

st.markdown("""
**Aplikasi ini dirancang untuk membaca data ringkasan dari Shopee.**
**Format Data yang Diharapkan:** `Nama Studio | Username | Saldo | Total Penjualan | Total Biaya Iklan`
""")

# === Input Data ===
mode = st.radio("Pilih Cara Input", ["Upload File", "Paste Manual"])

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
        placeholder="Contoh:\nSTUDIO SURABAYA FASHION PRIA\tgrosirpakaiandansby\t16.692\t70.675.342\t1.661.067"
    )
    if raw_data.strip():
        lines = [line.strip() for line in raw_data.split("\n") if line.strip()]

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

def style_summary_table(df_to_style):
    """Fungsi untuk menerapkan styling umum pada tabel ringkasan."""
    return df_to_style.style.format({
        "Penjualan": format_rupiah,
        "Biaya_Iklan": format_rupiah,
        "Komisi 5%": format_rupiah,
        "Profit": format_rupiah,
        "ROAS": "{:.2f}"
    })

# === Parsing Function untuk Data Ringkasan ===
@st.cache_data
def parse_summary_data(raw_lines):
    """Fungsi yang disederhanakan untuk mem-parsing data ringkasan harian."""
    records = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        # Skip baris header atau footer yang tidak relevan
        if any(k in line.upper() for k in ["NAMA STUDIO", "TOTAL", "BELUM MENDAFTAR", "PAUSED"]):
            continue

        parts = line.split("\t")
        
        # Membutuhkan setidaknya 5 kolom utama
        if len(parts) < 5:
            st.warning(f"Melewatkan baris karena format tidak sesuai: '{line[:70]}...'")
            continue

        try:
            studio = parts[0].strip()
            username = parts[1].strip()
            # Membersihkan angka dari titik atau karakter non-numerik lainnya
            penjualan = float(str(parts[3]).replace(".", "").replace(",", "") or 0)
            biaya_iklan = float(str(parts[4]).replace(".", "").replace(",", "") or 0)

            # Kalkulasi langsung di sini
            roas = penjualan / biaya_iklan if biaya_iklan > 0 else 0
            komisi = penjualan * 0.05
            profit = komisi - biaya_iklan

            records.append({
                "Nama Studio": studio,
                "Username": username,
                "Penjualan": penjualan,
                "Biaya_Iklan": biaya_iklan,
                "ROAS": roas,
                "Komisi 5%": komisi,
                "Profit": profit
            })
        except (ValueError, IndexError) as e:
            st.warning(f"Gagal memproses baris: '{line[:70]}...'. Error: {e}")

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)

# === Proses Data Jika Ada ===
if lines:
    try:
        df_processed = parse_summary_data(lines)
        
        if df_processed.empty:
            st.warning("Tidak ada data valid yang dapat diproses. Periksa kembali format data Anda.")
        else:
            st.success(f"✅ Data berhasil diparsing! {len(df_processed)} akun ditemukan.")

            # --- Tambahkan Kolom Status ---
            df_processed["Status Profit"] = df_processed["Profit"].apply(lambda p: "✅ Profit" if p > 0 else ("❌ Rugi" if p < 0 else "➖ Break Even"))
            
            def status_roas(r):
                if r == 0: return "⏸️ Tidak Aktif"
                if r < 5: return "🔴 Boncos"
                if r < 30: return "🟠 Perlu Optimasi"
                if r < 50: return "🟡 Hampir Aman"
                return "🟢 AMAN (ROAS ≥ 50)"
            df_processed["Status ROAS"] = df_processed["ROAS"].apply(status_roas)

            # --- Sidebar & Filter ---
            st.sidebar.title("🧭 Navigasi & Filter")
            all_studios = df_processed['Nama Studio'].unique()
            selected_studios = st.sidebar.multiselect("Filter Nama Studio", all_studios, default=all_studios)
            
            if not selected_studios:
                st.sidebar.warning("Pilih minimal satu studio.")
                filtered_df = pd.DataFrame()
            else:
                filtered_df = df_processed[df_processed['Nama Studio'].isin(selected_studios)]
            
            menu = st.sidebar.radio("Pilih Halaman Analisis", [
                "📊 Ringkasan Performa",
                "💰 Analisis Komisi & Profit",
                "✅ AMAN (ROAS ≥ 50)",
                "🎯 Hampir Aman (ROAS 30–49.9)",
                "🟠 Perlu Optimasi (ROAS 5-29.9)",
                "❌ Akun Boncos (ROAS < 5)",
                "📥 Download Data"
            ])

            # --- Tampilan Halaman ---
            if menu == "📊 Ringkasan Performa":
                st.subheader("📋 Ringkasan Performa Studio")
                if not filtered_df.empty:
                    # Kalkulasi Metrik
                    total_penjualan = filtered_df["Penjualan"].sum()
                    total_biaya = filtered_df["Biaya_Iklan"].sum()
                    profit_kotor = filtered_df["Komisi 5%"].sum()
                    profit_bersih = filtered_df["Profit"].sum()
                    total_rugi = filtered_df.loc[filtered_df["Profit"] < 0, "Profit"].sum()
                    jumlah_profit = (filtered_df["Profit"] > 0).sum()
                    jumlah_rugi = (filtered_df["Profit"] < 0).sum()
                    
                    # --- PERUBAHAN PERHITUNGAN ROAS ---
                    # Menghitung ROAS Studio berdasarkan (Profit Kotor / Biaya Iklan)
                    if total_biaya > 0:
                        roas_studio = (profit_kotor / total_biaya) * 100
                    else:
                        roas_studio = 0
                    # --- AKHIR PERUBAHAN ---

                    # Tampilan Metrik Baris 1
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Penjualan", format_rupiah(total_penjualan))
                    col2.metric("Total Biaya Iklan", format_rupiah(total_biaya))
                    col3.metric("Profit Kotor (Komisi 5%)", format_rupiah(profit_kotor))
                    
                    st.markdown("---")

                    # Tampilan Metrik Baris 2
                    col4, col5 = st.columns(2)
                    col4.metric("Profit Bersih (Setelah Biaya Iklan)", format_rupiah(profit_bersih), 
                                delta_color=("inverse" if profit_bersih < 0 else "normal"))
                    col5.metric("Total Kerugian (dari Akun Rugi)", format_rupiah(total_rugi), delta_color="inverse")
                    
                    st.markdown("---")
                    
                    # Tampilan Metrik Baris 3
                    col6, col7, col8 = st.columns(3)
                    col6.metric("Jumlah Akun Profit", f"{jumlah_profit} Akun")
                    col7.metric("Jumlah Akun Rugi", f"{jumlah_rugi} Akun")
                    # --- PERUBAHAN TAMPILAN METRIK ROAS ---
                    col8.metric("ROAS Studio (%)", f"{roas_studio:.2f}%")

                    st.markdown("---")

                    # Tampilkan tabel dengan styling
                    st.dataframe(
                        style_summary_table(filtered_df).background_gradient(cmap="RdYlGn", subset=["ROAS"], vmin=0, vmax=60),
                        use_container_width=True
                    )

            elif menu == "💰 Analisis Komisi & Profit":
                st.subheader("💰 Estimasi Komisi 5% & Profit")
                profit_df = filtered_df[["Nama Studio", "Username", "Penjualan", "Komisi 5%", "Biaya_Iklan", "Profit", "Status Profit"]].copy()
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
                    file_name="analisis_roas_shopee.csv",
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

    except Exception as e:
        st.error(f"❌ Terjadi kesalahan saat memproses data: {str(e)}")
        st.exception(e)

else:
    st.info("Silakan masukkan data untuk memulai analisis.")
