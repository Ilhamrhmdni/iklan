# app.py
# Dashboard "Monitor Digital" Kinerja Studio Harian
# Fitur: Input Manual (paste/upload), Google Sheets CSV, Simulasi
# Auto-rotate 20/baris per 5 detik, warna status, fade-in, running text
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
/* Kontainer penuh & sembunyikan header Streamlit default */
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

/* Animasi lembut saat ganti halaman */
@keyframes fadeInSoft { from {opacity:0; transform: translateY(6px);} to {opacity:1; transform: translateY(0);} }
.fade-in { animation: fadeInSoft 550ms ease-in-out; }

/* --- FIX KONTRAS TEKS TABLE DI DARK MODE --- */
.styled-table {
  border-collapse: collapse;
  width: 100%;
  font-size: 16px;
  color:#0f172a;                  /* teks gelap */
  background:#ffffff;             /* latar tabel putih */
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

/* Marquee bawah (running text) */
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
    Baca angka format Indonesia (1.234.567,89) / English (1,234,567.89) / plain.
    Return float (0 jika gagal).
    """
    if pd.isna(x): return 0.0
    s = str(x).strip()
    if s == "": return 0.0
    s = re.sub(r"[^\d,.\-]", "", s)  # buang simbol non angka
    # Jika ada koma tunggal dan posisinya di kanan titik terakhir -> anggap ID
    if s.count(",") == 1 and (s.rfind(",") > s.rfind(".")):
        s = s.replace(".", "").replace(",", ".")  # titik ribuan -> buang, koma -> desimal
    else:
        s = s.replace(",", "")  # anggap EN, buang koma ribuan
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
# DATA SOURCES
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
                "- Kolom wajib: `nama_studio`, `omset_hari_ini`.\n"
                "- Opsional: `komisi`, `target_persen`, `status`.")
    st.caption("Format angka Indonesia/English otomatis terdeteksi.")

def build_from_df(raw: pd.DataFrame) -> pd.DataFrame:
    # Mapping kolom fleksibel
    cols = list(raw.columns)
    c1, c2 = st.columns(2)
    with c1:
        k_nama  = st.selectbox("↗️ Kolom Nama Studio", cols, index=0)
        k_omset = st.selectbox("↗️ Kolom Omset Hari Ini", cols, index=min(1, len(cols)-1))
        k_komisi = st.selectbox("↗️ Kolom Komisi (opsional)", ["(Tidak ada)"]+cols, index=0)
    with c2:
        k_target = st.selectbox("↗️ Kolom Target % (opsional)", ["(Tidak ada)"]+cols, index=0)
        k_status = st.selectbox("↗️ Kolom Status (opsional: Naik/Turun/Stabil)", ["(Tidak ada)"]+cols, index=0)

    df = pd.DataFrame({
        "nama_studio": raw[k_nama].astype(str),
        "omset_hari_ini": [parse_number(v) for v in raw[k_omset]],
        "komisi": [parse_number(v) for v in (raw[k_komisi] if k_komisi != "(Tidak ada)" else 0)],
        "target_persen": [parse_number(v) for v in (raw[k_target] if k_target != "(Tidak ada)" else np.nan)],
        "status": (raw[k_status] if k_status != "(Tidak ada)" else np.nan)
    })

    # Status otomatis jika kosong
    if df["status"].isna().any():
        tp = df["target_persen"].fillna(100)
        auto = np.where(tp >= 100, "Naik", np.where(tp <= 90, "Turun", "Stabil"))
        df["status"] = df["status"].fillna(pd.Series(auto))

    # Tipe data
    df["omset_hari_ini"] = df["omset_hari_ini"].fillna(0).astype(float)
    df["komisi"] = df["komisi"].fillna(0).astype(float)
    df["target_persen"] = df["target_persen"].astype(float)
    df["rank_omset"] = df["omset_hari_ini"].rank(ascending=False, method="min").astype(int)

    st.success(f"Data terbaca: {len(df)} baris.")
    with st.expander("Preview 10 baris pertama"):
        st.dataframe(df.head(10), use_container_width=True)
    return df

def read_from_paste() -> pd.DataFrame | None:
    pasted = st.text_area(
        "Paste data di sini (boleh dari Excel/Sheets):",
        height=200,
        placeholder="nama_studio\tomset_hari_ini\tkomisi\ttarget_persen\tstatus\nStudio A\t12.345.678\t1.234.567\t101\tNaik"
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
        df = simulate_data(400)  # tampil simulasi dulu biar layar tidak kosong
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
    # Streamlit 1.25+ menyediakan autorefresh bawaan
    from streamlit import autorefresh as st_autorefresh
except Exception:
    # fallback package eksternal (kalau kamu tambahkan di requirements)
    from streamlit_autorefresh import st_autorefresh

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

    # Bungkus tabel dengan panel putih agar kontras maksimal di Dark Mode
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

# =========================
# END
# =========================
