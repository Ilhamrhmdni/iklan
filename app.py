# app.py
# Dashboard "Monitor Digital" Kinerja Studio Harian
# Versi: pivot-wide aware + auto-detect kolom (sesuai data contoh Ilham)
# By Albert

import io
import re
import math
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Dashboard Kinerja Studio Harian",
    layout="wide",
    page_icon="📊",
)

# =========================
# GLOBAL STYLES (Dark Mode friendly)
# =========================
st.markdown("""
<style>
.block-container {padding-top: 0rem; padding-bottom: 0rem; max-width: 100%;}
header[data-testid="stHeader"] {display: none;}
#MainMenu, footer {visibility: hidden;}

/* Header besar */
.dashboard-header {
  width: 100%;
  padding: 18px 24px;
  font-size: 40px;
  font-weight: 800;
  letter-spacing: .3px;
  background: linear-gradient(90deg, #0f172a, #111827);
  color: #f8fafc;
  border-bottom: 2px solid #0ea5e9;
  display:flex; align-items:center; justify-content:space-between;
}
.badge {
  font-size:14px; padding:6px 10px; border-radius:999px; margin-left:6px;
  background:#0ea5e91a; color:#7dd3fc; border:1px solid #0ea5e9;
}

/* Fade-in lembut saat ganti halaman */
@keyframes fadeInSoft { from {opacity:0; transform: translateY(6px);} to {opacity:1; transform: translateY(0);} }
.fade-in { animation: fadeInSoft 550ms ease-in-out; }

/* --- FIX KONTRAS TEKS TABLE DI DARK MODE --- */
.styled-table {
  border-collapse: collapse;
  width: 100%;
  font-size: 16px;
  color:#0f172a;                  /* teks gelap */
  background:#ffffff;             /* latar putih */
}
.styled-table thead th,
.styled-table td, .styled-table th {
  color:#0f172a !important;
  padding: 12px 10px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
}
.styled-table thead th {
  background:#f8fafc !important;
  border-bottom: 2px solid #cbd5e1;
  position: sticky; top: 0; z-index: 2; font-weight: 700;
}

/* Warna baris status */
.row-green  { background:#dcfce7 !important; }  /* Naik */
.row-red    { background:#fee2e2 !important; }  /* Turun */
.row-yellow { background:#fef9c3 !important; }  /* Stabil */

/* Status pill */
.pill { padding:4px 10px; border-radius:999px; font-weight:700; font-size:13px; display:inline-block; }
.pill-green  { background:#16a34a !important; color:#ffffff !important; }
.pill-red    { background:#dc2626 !important; color:#ffffff !important; }
.pill-yellow { background:#ca8a04 !important; color:#ffffff !important; }

/* Marquee bawah */
.marquee-wrap {
  position: fixed; left:0; right:0; bottom:0;
  background: #0f172a; color:#e2e8f0; border-top: 2px solid #0ea5e9;
  padding: 10px 0; overflow: hidden; z-index: 9999;
  font-size: 18px; font-weight: 700;
}
.marquee-inner {
  display: inline-block; white-space: nowrap; will-change: transform;
  animation: slideLeft 20s linear infinite;
}
@keyframes slideLeft { 0% { transform: translateX(100%);} 100% { transform: translateX(-100%);} }

/* Font rapi */
html, body, [data-testid="stAppViewContainer"] * {
  -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
  font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
}
</style>
""", unsafe_allow_html=True)

# =========================
# CONST
# =========================
PAGE_SIZE = 20
AUTO_INTERVAL_MS = 5000  # 5 detik

# =========================
# HELPERS
# =========================
def parse_number(x):
    """
    Terima angka format ID (1.234.567,89) / EN (1,234,567.89) / plain.
    Kembalikan float (0 jika gagal).
    """
    if pd.isna(x): return 0.0
    s = str(x).strip()
    if s == "": return 0.0
    s = re.sub(r"[^\d,.\-]", "", s)
    # Pola Indonesia: satu koma di kanan titik terakhir
    if s.count(",") == 1 and (s.rfind(",") > s.rfind(".")):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except:
        return 0.0

def rupiah(x):
    try:
        x = int(round(float(x)))
    except:
        x = 0
    return f"Rp{x:,}".replace(",", ".")

def status_to_class(s: str) -> str:
    s = (s or "").lower()
    if s == "naik": return "row-green"
    if s == "turun": return "row-red"
    return "row-yellow"

def status_to_pill(s: str) -> str:
    s_lower = (s or "").lower()
    if s_lower == "naik":   return '<span class="pill pill-green">Naik</span>'
    if s_lower == "turun":  return '<span class="pill pill-red">Turun</span>'
    return '<span class="pill pill-yellow">Stabil</span>'

def df_page_to_html(df_page: pd.DataFrame, start_idx: int) -> str:
    headers = ["No", "Nama Studio", "Omset Hari Ini", "Komisi", "Target (%)", "Status"]
    html = ['<table class="styled-table">', "<thead><tr>"]
    html += [f"<th>{h}</th>" for h in headers]
    html.append("</tr></thead><tbody>")
    for i, row in enumerate(df_page.itertuples(index=False), start=start_idx+1):
        row_class = status_to_class(row.status)
        html.append(f'<tr class="{row_class}">')
        html.append(f"<td>{i}</td>")
        html.append(f"<td><strong>{row.nama_studio}</strong></td>")
        html.append(f"<td>{rupiah(row.omset_hari_ini)}</td>")
        html.append(f"<td>{rupiah(row.komisi)}</td>")
        html.append(f"<td>{row.target_persen:.2f}%</td>")
        html.append(f"<td>{status_to_pill(row.status)}</td>")
        html.append("</tr>")
    html.append("</tbody></table>")
    return "\n".join(html)

# =========================
# DATA SOURCES (simulasi)
# =========================
def simulate_data(n=400, seed=42):
    rng = np.random.default_rng(seed)
    names = [f"Studio {i:03d}" for i in range(1, n+1)]
    omset = rng.integers(5_000_000, 250_000_000, size=n)
    komisi = (omset * rng.uniform(0.05, 0.15, size=n)).astype(int)
    target = np.round(rng.uniform(80, 125, size=n), 2)
    status_choices = rng.choice(["Naik", "Stabil", "Turun"], size=n, p=[0.45, 0.30, 0.25])
    df = pd.DataFrame({
        "nama_studio": names,
        "omset_hari_ini": omset,
        "komisi": komisi,
        "target_persen": target,
        "status": status_choices
    })
    df["rank_omset"] = df["omset_hari_ini"].rank(ascending=False, method="min").astype(int)
    return df.sort_values("nama_studio").reset_index(drop=True)

# =========================
# SIDEBAR (Sumber Data)
# =========================
with st.sidebar:
    st.markdown("### Sumber Data")
    src = st.radio("Pilih sumber:", ["Paste/Upload", "Google Sheets (CSV)", "Simulasi"], index=0)
    st.markdown("---")
    st.markdown("**Petunjuk Paste:**")
    st.markdown("- Copy dari Excel/Google Sheets **termasuk header**.\n"
                "- App ini otomatis memahami model pivot seperti contohmu.\n"
                "- Minimal kolom: **STUDIO** dan salah satu dari **harian** atau blok tanggal.")
    st.caption("Format angka Indonesia/English otomatis terdeteksi.")

# =========================
# CORE: builder yang paham pivot lebar
# =========================
def build_from_df(raw: pd.DataFrame) -> pd.DataFrame:
    # Normalisasi nama kolom (untuk pencarian longgar)
    orig_cols = list(raw.columns)
    norm = {c: re.sub(r"\s+", " ", str(c)).strip().lower() for c in orig_cols}

    def find_col(*keywords, contains=True):
        """Cari kolom berdasar kata kunci (semua harus match). Return kolom asli atau None."""
        keys = [k.lower() for k in keywords]
        for c in orig_cols:
            lc = norm[c]
            ok = all(((k in lc) if contains else (k == lc)) for k in keys)
            if ok:
                return c
        return None

    # 1) Deteksi otomatis kolom ringkas
    col_studio = find_col("studio") or find_col("nama", "studio")
    col_harian = find_col("harian")
    col_komisi_ringkas = find_col("komisi - iklan") or find_col("komisi", "iklan")
    col_target = find_col("target komisi harian") or find_col("target", "harian")
    col_status = find_col("status")

    # 2) Jika 'harian' tidak ada, ambil blok TANGGAL TERAKHIR: cari kolom tanggal "dd/mm/yyyy"
    date_cols = [c for c in orig_cols if re.search(r"\b\d{2}/\d{2}/\d{4}\b", str(c))]
    last_date = None
    if not col_harian and date_cols:
        # ambil tanggal paling kanan (urut sesuai posisi muncul)
        last_date = max(date_cols, key=lambda c: orig_cols.index(c))
        idx = orig_cols.index(last_date)
        # cari subkolom setelah tanggal tsb (SUM of OMSET, SUM of EST KOMISI)
        subcols = orig_cols[idx: idx+8]  # ambil beberapa kolom kanan
        col_omset_last = None
        col_komisi_last = None
        for sc in subcols:
            if sc == last_date:
                continue
            lsc = norm[sc]
            if ("sum of omset" in lsc or "omset" in lsc) and col_omset_last is None:
                col_omset_last = sc
            if ("sum of est komisi" in lsc or "komisi - iklan" in lsc or "komisi" in lsc) and col_komisi_last is None:
                col_komisi_last = sc
        if col_omset_last:
            col_harian = col_omset_last
        if not col_komisi_ringkas and col_komisi_last:
            col_komisi_ringkas = col_komisi_last

    # 3) Jika masih ada yang belum ketemu, sediakan mapping manual (fallback)
    cols = list(raw.columns)
    need_manual = (col_studio is None) or (col_harian is None)
    if need_manual:
        st.warning("Tidak semua kolom terdeteksi otomatis. Pilih mapping manual di bawah.")
        c1, c2 = st.columns(2)
        with c1:
            col_studio = st.selectbox("↗️ Kolom Nama Studio", cols, index=0 if col_studio is None else cols.index(col_studio))
            col_harian = st.selectbox(
                "↗️ Kolom Omset Hari Ini (contoh: 'harian' atau 'SUM of OMSET' untuk tanggal terbaru)",
                cols, index=min(1, len(cols)-1) if col_harian is None else cols.index(col_harian)
            )
        with c2:
            col_komisi_ringkas = st.selectbox("↗️ Kolom Komisi (opsional)",
                                              ["(Tidak ada)"]+cols,
                                              index=0 if col_komisi_ringkas is None else 1+cols.index(col_komisi_ringkas))
            col_target = st.selectbox("↗️ Kolom Target % (opsional)",
                                      ["(Tidak ada)"]+cols,
                                      index=0 if col_target is None else 1+cols.index(col_target))
            col_status = st.selectbox("↗️ Kolom Status (opsional)",
                                      ["(Tidak ada)"]+cols,
                                      index=0 if col_status is None else 1+cols.index(col_status))
    else:
        st.info(
            f"Deteksi otomatis:\n"
            f"- Studio → **{col_studio}**\n"
            f"- Omset harian → **{col_harian}**" +
            (f"\n- Komisi → **{col_komisi_ringkas}**" if col_komisi_ringkas else "") +
            (f"\n- Target % → **{col_target}**" if col_target else "") +
            (f"\n- Status → **{col_status}**" if col_status else "") +
            (f"\n- Tanggal dipakai: **{last_date}**" if last_date else "")
        )

    # 4) Bangun DataFrame sesuai skema app
    df = pd.DataFrame({
        "nama_studio": raw[col_studio].astype(str),
        "omset_hari_ini": [parse_number(v) for v in raw[col_harian]],
        "komisi": [parse_number(v) for v in (raw[col_komisi_ringkas] if (col_komisi_ringkas and col_komisi_ringkas != "(Tidak ada)") else 0)],
        "target_persen": [parse_number(v) for v in (raw[col_target] if (col_target and col_target != "(Tidak ada)") else np.nan)],
        "status": (raw[col_status] if (col_status and col_status != "(Tidak ada)") else np.nan)
    })

    # 5) Status otomatis bila kosong
    if df["status"].isna().any():
        tp = df["target_persen"].fillna(100)
        auto = np.where(tp >= 100, "Naik", np.where(tp <= 90, "Turun", "Stabil"))
        df["status"] = df["status"].fillna(pd.Series(auto))

    # 6) Tipe data akhir + ranking
    df["omset_hari_ini"] = df["omset_hari_ini"].fillna(0).astype(float)
    df["komisi"] = df["komisi"].fillna(0).astype(float)
    df["target_persen"] = df["target_persen"].astype(float)
    df["rank_omset"] = df["omset_hari_ini"].rank(ascending=False, method="min").astype(int)

    st.success(f"Data terbaca: {len(df)} baris.")
    with st.expander("Preview 10 baris pertama"):
        st.dataframe(df.head(10), use_container_width=True)
    return df

# =========================
# INPUT READERS
# =========================
def read_from_paste() -> pd.DataFrame | None:
    pasted = st.text_area(
        "Paste data di sini (boleh dari Excel/Sheets, termasuk header):",
        height=240,
        placeholder="area\tNAMA OPERATOR\tSTUDIO\t...\narea 1\tBUYUNG\tSTUDIO GRESIK 1\t..."
    )
    up = st.file_uploader("atau Upload CSV/XLSX", type=["csv", "xlsx"])
    raw = None
    if pasted.strip():
        # Deteksi delimiter: tab > ; > ,
        sep = "\t" if "\t" in pasted else (";" if ";" in pasted else ",")
        raw = pd.read_csv(io.StringIO(pasted), sep=sep)
    elif up is not None:
        if up.name.lower().endswith(".csv"):
            raw = pd.read_csv(up)
        else:
            raw = pd.read_excel(up)
    return raw

def read_from_gsheet_csv() -> pd.DataFrame | None:
    url = st.text_input("URL CSV (Publish to web)", st.secrets.get("GSHEET_CSV_URL", ""))
    if url:
        try:
            return pd.read_csv(url)
        except Exception as e:
            st.error(f"Gagal baca CSV: {e}")
    return None

# =========================
# LOAD DATA sesuai pilihan
# =========================
if src == "Paste/Upload":
    raw = read_from_paste()
    if raw is not None and not raw.empty:
        raw.columns = [str(c).strip() for c in raw.columns]
        df = build_from_df(raw)
    else:
        df = simulate_data(400)
elif src == "Google Sheets (CSV)":
    raw = read_from_gsheet_csv()
    if raw is not None and not raw.empty:
        raw.columns = [str(c).strip() for c in raw.columns]
        df = build_from_df(raw)
    else:
        st.info("Masukkan URL CSV dari **File → Publish to the web → CSV**.")
        df = simulate_data(400)
else:
    df = simulate_data(400)

# =========================
# AUTO REFRESH / ROTATE
# =========================
try:
    from streamlit import autorefresh as st_autorefresh  # Streamlit 1.25+
except Exception:
    from streamlit_autorefresh import st_autorefresh       # fallback eksternal

refresh_counter = st_autorefresh(interval=AUTO_INTERVAL_MS, limit=None, key="auto_refresh_counter")
num_pages = max(1, math.ceil(len(df) / PAGE_SIZE))
page_idx = 0 if refresh_counter is None else (refresh_counter % num_pages)
start = page_idx * PAGE_SIZE
end = start + PAGE_SIZE
page_df = df.iloc[start:end].copy()

# =========================
# HEADER
# =========================
now = datetime.now()
meta_left = f"Halaman {page_idx+1}/{num_pages}"
meta_right = f"{len(df)} studio • {now.strftime('%H:%M:%S, %d %b %Y')}"
st.markdown(f"""
<div class="dashboard-header">
  <div>📊 DASHBOARD KINERJA STUDIO HARIAN
    <span class="badge">{meta_left}</span>
  </div>
  <div><span class="badge">{meta_right}</span></div>
</div>
""", unsafe_allow_html=True)

# =========================
# MAIN CONTENT
# =========================
content_holder = st.empty()
with content_holder.container():
    st.markdown('<div class="fade-in">', unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Total Studio", f"{len(df)}")
    with k2: st.metric("Total Omset", rupiah(df["omset_hari_ini"].sum()))
    with k3: st.metric("Rata-rata Omset", rupiah(df["omset_hari_ini"].mean()))
    with k4:
        naik_pct = (df["status"].str.lower() == "naik").mean()*100
        st.metric("Persentase Naik", f"{naik_pct:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # Panel putih agar kontras maksimal di Dark Mode
    st.markdown('<div style="background:#ffffff; padding:8px; border-radius:12px;">', unsafe_allow_html=True)
    st.markdown(df_page_to_html(page_df, start_idx=start), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# RUNNING TEXT (Bottom)
# =========================
best_row = df.iloc[df["omset_hari_ini"].astype(float).idxmax()]
running_text = (
    f"Studio terbaik hari ini: {best_row['nama_studio']} (Omset: {rupiah(best_row['omset_hari_ini'])})   •   "
    f"Update terakhir: {now.strftime('%H:%M:%S, %d %b %Y')}"
)
st.markdown(f"""
<div class="marquee-wrap">
  <div class="marquee-inner">{running_text}</div>
</div>
""", unsafe_allow_html=True)
