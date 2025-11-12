# app.py
# Dashboard "Monitor Digital" Kinerja Studio Harian
# Sumber utama: database transaksi baris (OWNER, STUDIO, USERNAME, OMSET, EST KOMISI, TANGGAL, NAMA OPERATOR, area)
# By Albert

import io
import re
import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st

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

/* Animasi lembut saat ganti halaman */
@keyframes fadeInSoft { from {opacity:0; transform: translateY(6px);} to {opacity:1; transform: translateY(0);} }
.fade-in { animation: fadeInSoft 550ms ease-in-out; }

/* Tabel kontras aman di Dark Mode */
.styled-table { border-collapse: collapse; width: 100%; font-size: 16px; color:#0f172a; background:#ffffff; }
.styled-table thead th, .styled-table td, .styled-table th { color:#0f172a !important; padding:12px 10px; border-bottom:1px solid #e5e7eb; text-align:left; }
.styled-table thead th { background:#f8fafc !important; border-bottom:2px solid #cbd5e1; position: sticky; top: 0; z-index: 2; font-weight: 700; }

/* Warna status */
.row-green  { background:#dcfce7 !important; }  /* Naik */
.row-red    { background:#fee2e2 !important; }  /* Turun */
.row-yellow { background:#fef9c3 !important; }  /* Stabil */

/* Pill */
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
    """Angka format ID/EN/plain -> float."""
    if pd.isna(x): return 0.0
    s = str(x).strip()
    if s == "": return 0.0
    s = re.sub(r"[^\d,.\-]", "", s)
    if s.count(",") == 1 and (s.rfind(",") > s.rfind(".")):
        s = s.replace(".", "").replace(",", ".")  # Indonesia
    else:
        s = s.replace(",", "")  # English/plain
    try:
        return float(s)
    except:
        return 0.0

def parse_date_any(x):
    """Coba parse berbagai format tanggal."""
    if pd.isna(x): return None
    s = str(x).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
    try:
        return pd.to_datetime(s, errors="coerce").date()
    except:
        return None

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
# SIDEBAR (Input)
# =========================
with st.sidebar:
    st.markdown("### Sumber Data")
    st.markdown("Mode ini menerima **transaksi baris**:")
    st.code("OWNER | STUDIO | USERNAME | OMSET | EST KOMISI | TANGGAL | NAMA OPERATOR | area", language="text")

# =========================
# INPUT (Paste/Upload)
# =========================
pasted = st.text_area(
    "Paste data transaksi (termasuk header):",
    height=260,
    placeholder="OWNER\tSTUDIO\tUSERNAME\tOMSET\tEST KOMISI\tTANGGAL\tNAMA OPERATOR\tarea\nCMDTIM\tSTUDIO PUSAT 102\tanekagamis77\t892.009\t73.420\t2025-11-01\tVALEN\tarea 1",
)
uploaded = st.file_uploader("atau Upload CSV/XLSX", type=["csv", "xlsx"])

def _detect_sep(text: str) -> str:
    if "\t" in text: return "\t"
    if ";" in text: return ";"
    return ","

raw = None
if pasted.strip():
    sep = _detect_sep(pasted)
    raw = pd.read_csv(io.StringIO(pasted), sep=sep)
elif uploaded is not None:
    if uploaded.name.lower().endswith(".csv"):
        raw = pd.read_csv(uploaded)
    else:
        raw = pd.read_excel(uploaded)

if raw is None or raw.empty:
    st.info("Belum ada data. Silakan paste atau upload.")
    st.stop()

# =========================
# NORMALISASI & FILTER
# =========================
# Pemetaan kolom longgar (tanpa minta user pilih)
lu = {c: re.sub(r"\s+", " ", str(c)).strip().lower() for c in raw.columns}

def pick(*keys):
    for c in raw.columns:
        if all(k in lu[c] for k in keys):
            return c
    return None

c_owner   = pick("owner")
c_studio  = pick("studio")
c_user    = pick("username")
c_omset   = pick("omset")
c_estkom  = pick("est", "komisi") or pick("komisi")
c_tanggal = pick("tanggal")
c_op      = pick("nama", "operator") or pick("operator")
c_area    = pick("area")

# Build dataframe typed
df_tx = pd.DataFrame({
    "owner": raw[c_owner] if c_owner else "",
    "studio": raw[c_studio].astype(str),
    "username": raw[c_user] if c_user else "",
    "omset": [parse_number(v) for v in raw[c_omset]] if c_omset else 0,
    "komisi": [parse_number(v) for v in raw[c_estkom]] if c_estkom else 0,
    "tanggal": raw[c_tanggal].apply(parse_date_any) if c_tanggal else None,
    "operator": raw[c_op] if c_op else "",
    "area": raw[c_area] if c_area else "",
})

# Tanggal min/max untuk UI
valid_dates = df_tx["tanggal"].dropna()
if valid_dates.empty:
    st.error("Kolom TANGGAL tidak terbaca. Pastikan ada kolom 'TANGGAL' dengan format tanggal.")
    st.stop()

min_d, max_d = valid_dates.min(), valid_dates.max()

with st.sidebar:
    st.markdown("---")
    st.markdown("### Filter Data")
    f_area = st.multiselect("Area", sorted(df_tx["area"].dropna().unique()), help="Kosongkan jika ingin semua.")
    f_owner = st.multiselect("Owner", sorted(df_tx["owner"].dropna().unique()))
    f_op = st.multiselect("Operator", sorted(df_tx["operator"].dropna().unique()))
    pick_date = st.date_input("Pilih tanggal (untuk dashboard hari ini):", value=max_d, min_value=min_d, max_value=max_d)

# Terapkan filter (selain tanggal)
mask = pd.Series(True, index=df_tx.index)
if f_area:  mask &= df_tx["area"].isin(f_area)
if f_owner: mask &= df_tx["owner"].isin(f_owner)
if f_op:    mask &= df_tx["operator"].isin(f_op)
df_tx_f = df_tx[mask].copy()

# =========================
# AGREGASI HARI INI (per STUDIO)
# =========================
today_df = df_tx_f[df_tx_f["tanggal"] == pick_date]
agg_today = today_df.groupby("studio", as_index=False).agg(
    omset_hari_ini=("omset", "sum"),
    komisi=("komisi", "sum"),
)
agg_today.rename(columns={"studio": "nama_studio"}, inplace=True)

# =========================
# TARGET_PERSEN vs rata-rata 7 hari sebelumnya per studio
# =========================
hist_until = df_tx_f[df_tx_f["tanggal"] < pick_date].copy()
ref = (
    hist_until.sort_values("tanggal")
    .groupby("studio")["komisi"]
    .apply(lambda s: s.tail(7).mean() if len(s) else np.nan)
    .reset_index().rename(columns={"studio": "nama_studio", "komisi": "komisi_avg7"})
)
df = agg_today.merge(ref, on="nama_studio", how="left")
df["target_persen"] = np.where(df["komisi_avg7"] > 0, (df["komisi"] / df["komisi_avg7"]) * 100.0, 100.0)
df.drop(columns=["komisi_avg7"], inplace=True)

# =========================
# STATUS & RANK
# =========================
tp = df["target_persen"].fillna(100)
df["status"] = np.where(tp >= 100, "Naik", np.where(tp <= 90, "Turun", "Stabil"))
df["rank_omset"] = df["omset_hari_ini"].rank(ascending=False, method="min").astype(int)
df = df.sort_values("nama_studio").reset_index(drop=True)

# =========================
# AUTO REFRESH / ROTATE
# =========================
try:
    from streamlit import autorefresh as st_autorefresh  # Streamlit 1.25+
except Exception:
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
meta_right = f"{len(df)} studio • {pick_date.strftime('%d %b %Y')} • {now.strftime('%H:%M:%S')}"
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

    # Panel putih untuk kontras
    st.markdown('<div style="background:#ffffff; padding:8px; border-radius:12px;">', unsafe_allow_html=True)
    st.markdown(df_page_to_html(page_df, start_idx=start), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# RUNNING TEXT (Bottom)
# =========================
if not df.empty:
    best_row = df.iloc[df["omset_hari_ini"].astype(float).idxmax()]
    running_text = (
        f"Studio terbaik hari ini: {best_row['nama_studio']} (Omset: {rupiah(best_row['omset_hari_ini'])})   •   "
        f"Update terakhir: {now.strftime('%H:%M:%S, %d %b %Y')}"
    )
else:
    running_text = "Belum ada data untuk tanggal ini • Update terakhir: " + now.strftime('%H:%M:%S, %d %b %Y')

st.markdown(f"""
<div class="marquee-wrap">
  <div class="marquee-inner">{running_text}</div>
</div>
""", unsafe_allow_html=True)
