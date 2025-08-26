import streamlit as st
import pandas as pd
import numpy as np
import re
import logging

# ===== Logging =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

st.set_page_config(page_title="Analisis Komisi vs Biaya Iklan", layout="wide")
st.title("📊 Analisis Komisi Harian vs Biaya Iklan")

# ---------- Helpers ----------

def num_clean(x):
    """Bersihkan string angka: buang 'Rp', titik ribuan, koma, spasi, huruf; kembalikan float."""
    if pd.isna(x):
        return 0.0
    s = str(x)
    # ambil hanya bagian angka/-, ., ,
    s = re.sub(r"[^\d,\.\-]", "", s)  # hilangkan huruf/pipe/%
    # buang titik ribuan & koma desimal (anggap semua integer rupiah)
    s = s.replace(".", "").replace(",", "")
    if s == "" or s == "-":
        return 0.0
    try:
        return float(s)
    except:
        return 0.0

def parse_komisi_cell(cell):
    """
    Format contoh: '56.207 - 1.368.775 (B)' -> ambil komisi=56.207
    Jika '0 - 0 (D)' atau NaN -> 0
    """
    if pd.isna(cell):
        return 0.0
    s = str(cell).strip()
    if s == "0" or s.startswith("0 - 0"):
        return 0.0
    # Ambil angka pertama (sebelum ' - ')
    m = re.match(r"\s*([\d\.]+)", s)
    if m:
        return num_clean(m.group(1))
    return 0.0

def detect_date_columns(df, dayfirst=False):
    """
    Deteksi kolom yang terlihat seperti tanggal dari NAMA kolom.
    Kembalikan dict {original_col_name: date_obj}
    - Komisi: '25-08-2025' (dayfirst=True)
    - Biaya: '2025-08-25 00:00' -> ambil token pertama sebelum spasi
    """
    col2date = {}
    for c in df.columns:
        token = str(c).strip().split()[0]
        try:
            d = pd.to_datetime(token, dayfirst=dayfirst, errors="raise").date()
            col2date[c] = d
        except Exception:
            continue
    return col2date

def style_roi(val):
    if pd.isna(val):
        return ""
    v = float(val)
    if v >= 200:
        # makin tinggi, makin hijau gelap (turunkan channel G)
        g = max(0, int(255 - min(v, 600 - 1) - 200))  # sederhana, 200..600
        return f"background-color: rgb(0,{g},0); color: white;"
    else:
        # makin rendah, makin merah gelap (turunkan channel G & B)
        r_drop = min(200, int(200 - v))  # v 0 -> drop 200 (merah gelap), v 200 -> drop 0
        g = max(0, 255 - r_drop)
        b = max(0, 255 - r_drop)
        return f"background-color: rgb(255,{g},{b}); color: white;"

def standardize_party_columns(df, file_type):
    """
    Menyesuaikan kolom kunci tanpa mengubah file sumber:
    - Studio bisa muncul sebagai 'Studio' atau 'Nama Studio'
    - Username bisa 'Username' / 'USER' / 'username'
    Return: df dengan kolom 'Studio' & 'Username' tersedia.
    """
    cols = {c.lower().strip(): c for c in df.columns}

    # Studio
    studio_col = None
    for cand in ["studio", "nama studio"]:
        if cand in cols:
            studio_col = cols[cand]
            break
    if studio_col is None:
        raise ValueError(f"Tidak menemukan kolom Studio di data {file_type} (butuh 'Studio' atau 'Nama Studio').")

    # Username
    user_col = None
    for cand in ["username", "user", "akun"]:
        if cand in cols:
            user_col = cols[cand]
            break
    if user_col is None:
        raise ValueError(f"Tidak menemukan kolom Username di data {file_type} (butuh 'Username'/'User'/'Akun').")

    # Pastikan dua kolom standar ada (buat salinan)
    if studio_col != "Studio":
        df["Studio"] = df[studio_col]
    if user_col != "Username":
        df["Username"] = df[user_col]

    return df

# ---------- UI Upload ----------

st.subheader("📥 Upload Data")
komisi_file = st.file_uploader("Data Komisi Harian (CSV/Excel)", type=["csv", "xlsx"])
biaya_file  = st.file_uploader("Data Biaya Iklan (CSV/Excel)", type=["csv", "xlsx"])

if komisi_file and biaya_file:
    try:
        # Baca dua file (deteksi csv/excel)
        if komisi_file.name.lower().endswith(".xlsx"):
            dfk = pd.read_excel(komisi_file)
        else:
            dfk = pd.read_csv(komisi_file, sep=None, engine="python")
        if biaya_file.name.lower().endswith(".xlsx"):
            dfb = pd.read_excel(biaya_file)
        else:
            dfb = pd.read_csv(biaya_file, sep=None, engine="python")

        # Standarisasi kolom kunci tanpa mengubah aslinya
        dfk = standardize_party_columns(dfk, "komisi")
        dfb = standardize_party_columns(dfb, "biaya")

        # (Opsional) Exclude baris TOTAL
        if "Username" in dfk.columns:
            dfk = dfk[dfk["Username"].astype(str).str.upper() != "TOTAL"]
        if "Username" in dfb.columns:
            dfb = dfb[dfb["Username"].astype(str).str.upper() != "TOTAL"]

        # Deteksi & mapping kolom tanggal
        komisi_dates = detect_date_columns(dfk, dayfirst=True)     # dd-mm-yyyy
        biaya_dates  = detect_date_columns(dfb, dayfirst=False)    # yyyy-mm-dd [00:00]

        # Tanggal yang tersedia di KEDUA dataset
        dates_k = set(komisi_dates.values())
        dates_b = set(biaya_dates.values())
        common_dates = sorted(list(dates_k & dates_b))

        if not common_dates:
            st.error("❌ Tidak ada tanggal yang cocok antara data komisi & biaya. "
                     "Pastikan format tanggal di header kolom benar.")
            st.stop()

        # Pilihan rentang tanggal (YYYY-MM-DD)
        date_labels = [pd.to_datetime(d).date().isoformat() for d in common_dates]
        st.subheader("📅 Pilih Rentang Tanggal")
        start_label = st.selectbox("Tanggal Mulai", options=date_labels, index=0)
        end_label   = st.selectbox("Tanggal Akhir", options=date_labels, index=len(date_labels)-1)

        start_d = pd.to_datetime(start_label).date()
        end_d   = pd.to_datetime(end_label).date()
        if start_d > end_d:
            st.error("Tanggal Mulai tidak boleh lebih besar dari Tanggal Akhir.")
            st.stop()

        # Ambil daftar tanggal terpilih
        selected_dates = [d for d in common_dates if start_d <= d <= end_d]

        # Peta: date -> kolom_asli (ambil kolom pertama yang match tanggal tsb)
        date_to_kcol = {}
        for c, d in komisi_dates.items():
            if d in selected_dates and d not in date_to_kcol:
                date_to_kcol[d] = c
        date_to_bcol = {}
        for c, d in biaya_dates.items():
            if d in selected_dates and d not in date_to_bcol:
                date_to_bcol[d] = c

        # ---------- Hitung Est. Komisi ----------
        kcols = [date_to_kcol[d] for d in selected_dates if d in date_to_kcol]
        proc_k = dfk[["Studio", "Username"]].copy()
        for c in kcols:
            proc_k[c] = dfk[c].apply(parse_komisi_cell)
        proc_k["Est. Komisi"] = proc_k[kcols].sum(axis=1) if kcols else 0.0

        komisi_sum = proc_k.groupby(["Studio", "Username"], as_index=False)["Est. Komisi"].sum()
        komisi_sum["Est. Komisi"] = komisi_sum["Est. Komisi"].apply(num_clean)

        # ---------- Hitung Biaya Iklan ----------
        bcols = [date_to_bcol[d] for d in selected_dates if d in date_to_bcol]
        proc_b = dfb[["Studio", "Username"]].copy()
        for c in bcols:
            # sel berformat "angka | angka | % | angka" -> ambil bagian pertama (biaya)
            val = dfb[c].astype(str).str.split("|").str[0]
            proc_b[c] = val.apply(num_clean)
        proc_b["Biaya Iklan"] = proc_b[bcols].sum(axis=1) if bcols else 0.0

        biaya_sum = proc_b.groupby(["Studio", "Username"], as_index=False)["Biaya Iklan"].sum()
        biaya_sum["Biaya Iklan"] = biaya_sum["Biaya Iklan"].apply(num_clean)

        # ---------- Merge & ROI ----------
        merged = pd.merge(komisi_sum, biaya_sum, on=["Studio", "Username"], how="inner")

        # Pastikan numeric (menghindari 'float' vs 'str')
        merged["Est. Komisi"] = pd.to_numeric(merged["Est. Komisi"], errors="coerce").fillna(0.0)
        merged["Biaya Iklan"] = pd.to_numeric(merged["Biaya Iklan"], errors="coerce").fillna(0.0)

        merged["ROI (%)"] = np.where(
            merged["Biaya Iklan"] > 0,
            (merged["Est. Komisi"] / merged["Biaya Iklan"]) * 100.0,
            0.0
        )

        # ---------- Tampilkan ----------
        st.subheader("📊 Hasil Analisis")
        show = merged.copy()
        show = show[["Studio", "Username", "Biaya Iklan", "Est. Komisi", "ROI (%)"]]
        show = show.sort_values(["Studio", "Username"]).reset_index(drop=True)

        styled = show.style.format({
            "Biaya Iklan": "Rp {:,.0f}",
            "Est. Komisi": "Rp {:,.0f}",
            "ROI (%)": "{:.2f}%"
        }).applymap(style_roi, subset=["ROI (%)"])

        st.dataframe(styled, use_container_width=True)

        # Download
        csv = show.to_csv(index=False).encode("utf-8")
        st.download_button("💾 Download CSV", csv, "hasil_analisis.csv", "text/csv")

        # ---------- Logging info ----------
        logging.info("=== DTypes After Clean ===\n%s", show.dtypes)
        logging.info("Sample rows:\n%s", show.head(3).to_string(index=False))

    except Exception as e:
        st.error(f"❌ Terjadi error saat parsing data: {e}")
        logging.exception("Gagal memproses")
