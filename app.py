# app.py
# Dashboard "Monitor Digital" Kinerja Studio — Mode Akumulasi & Per Tanggal
# Sumber: transaksi baris (OWNER, STUDIO, USERNAME, OMSET, EST KOMISI, TANGGAL, NAMA OPERATOR, area)
# Sidebar: panel 📚 Database (RAW) tanpa limit
# By Albert

import io, re, math
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import streamlit as st

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="Dashboard Kinerja Studio", layout="wide", page_icon="📊")

# =========================
# STYLES
# =========================
st.markdown("""
<style>
.block-container {padding-top:0rem; padding-bottom:0rem; max-width:100%;}
header[data-testid="stHeader"] {display:none;}
#MainMenu, footer {visibility:hidden;}
.dashboard-header{width:100%; padding:18px 24px; font-size:40px; font-weight:800;
  background:linear-gradient(90deg,#0f172a,#111827); color:#f8fafc; border-bottom:2px solid #0ea5e9;
  display:flex; align-items:center; justify-content:space-between;}
.badge{font-size:14px; padding:6px 10px; border-radius:999px; margin-left:6px; background:#0ea5e91a;
  color:#7dd3fc; border:1px solid #0ea5e9;}
@keyframes fadeInSoft{from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:translateY(0);}}
.fade-in{animation:fadeInSoft 550ms ease-in-out;}
.styled-table{border-collapse:collapse; width:100%; font-size:16px; color:#0f172a; background:#fff;}
.styled-table thead th, .styled-table td, .styled-table th{color:#0f172a !important; padding:12px 10px; border-bottom:1px solid #e5e7eb; text-align:left;}
.styled-table thead th{background:#f8fafc !important; border-bottom:2px solid #cbd5e1; position:sticky; top:0; z-index:2; font-weight:700;}
.row-green{background:#dcfce7 !important;} .row-red{background:#fee2e2 !important;} .row-yellow{background:#fef9c3 !important;}
.pill{padding:4px 10px; border-radius:999px; font-weight:700; font-size:13px; display:inline-block;}
.pill-green{background:#16a34a !important; color:#fff !important;}
.pill-red{background:#dc2626 !important; color:#fff !important;}
.pill-yellow{background:#ca8a04 !important; color:#fff !important;}
.marquee-wrap{position:fixed; left:0; right:0; bottom:0; background:#0f172a; color:#e2e8f0; border-top:2px solid #0ea5e9;
  padding:10px 0; overflow:hidden; z-index:9999; font-size:18px; font-weight:700;}
.marquee-inner{display:inline-block; white-space:nowrap; will-change:transform; animation:slideLeft 20s linear infinite;}
@keyframes slideLeft{0%{transform:translateX(100%);}100%{transform:translateX(-100%);}}
html, body, [data-testid="stAppViewContainer"] *{
  -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
  font-family:Inter, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial;}
</style>
""", unsafe_allow_html=True)

# =========================
# CONST
# =========================
PAGE_SIZE = 20
AUTO_INTERVAL_MS = 5000  # 5 detik rotate

# =========================
# HELPERS
# =========================
def parse_number(x):
    if pd.isna(x): return 0.0
    s = str(x).strip()
    if s == "": return 0.0
    s = re.sub(r"[^\d,.\-]", "", s)
    if s.count(",") == 1 and (s.rfind(",") > s.rfind(".")):
        s = s.replace(".", "").replace(",", ".")  # ID
    else:
        s = s.replace(",", "")  # EN/plain
    try: return float(s)
    except: return 0.0

def parse_date_any(x):
    if pd.isna(x): return None
    s = str(x).strip()
    for fmt in ("%Y-%m-%d","%d/%m/%Y","%m/%d/%Y","%d-%m-%Y"):
        try: return datetime.strptime(s, fmt).date()
        except: pass
    try: return pd.to_datetime(s, errors="coerce").date()
    except: return None

def rupiah(x):
    try: x = int(round(float(x)))
    except: x = 0
    return f"Rp{x:,}".replace(",", ".")

def status_to_class(s):
    s = (s or "").lower()
    if s == "naik": return "row-green"
    if s == "turun": return "row-red"
    return "row-yellow"

def status_to_pill(s):
    s = (s or "").lower()
    if s == "naik": return '<span class="pill pill-green">Naik</span>'
    if s == "turun": return '<span class="pill pill-red">Turun</span>'
    return '<span class="pill pill-yellow">Stabil</span>'

def df_page_to_html(df_page, start_idx, use_total_labels=True):
    heads = ["No","Nama Studio","Total Omset" if use_total_labels else "Omset Hari Ini",
             "Total Komisi" if use_total_labels else "Komisi",
             "Target (%)","Status"]
    html = ['<table class="styled-table">',"<thead><tr>"]
    html += [f"<th>{h}</th>" for h in heads]
    html.append("</tr></thead><tbody>")
    for i,row in enumerate(df_page.itertuples(index=False), start=start_idx+1):
        html.append(f'<tr class="{status_to_class(row.status)}">')
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
# SIDEBAR — petunjuk + MODE
# =========================
with st.sidebar:
    st.markdown("### Sumber Data")
    st.markdown("Paste/Upload **transaksi baris**:")
    st.code("OWNER | STUDIO | USERNAME | OMSET | EST KOMISI | TANGGAL | NAMA OPERATOR | area", language="text")
    st.markdown("---")
    mode = st.radio("Mode Tampilan", ["Akumulasi penuh","Per tanggal"], index=0)

# =========================
# INPUT
# =========================
pasted = st.text_area(
    "Paste data transaksi (termasuk header):",
    height=240,
    placeholder="OWNER\tSTUDIO\tUSERNAME\tOMSET\tEST KOMISI\tTANGGAL\tNAMA OPERATOR\tarea\nCMDTIM\tSTUDIO PUSAT 102\tanekagamis77\t892.009\t73.420\t2025-11-01\tVALEN\tarea 1",
)
uploaded = st.file_uploader("atau Upload CSV/XLSX", type=["csv","xlsx"])

def _detect_sep(text):
    if "\t" in text: return "\t"
    if ";" in text: return ";"
    return ","

raw = None
if pasted.strip():
    raw = pd.read_csv(io.StringIO(pasted), sep=_detect_sep(pasted))
elif uploaded is not None:
    raw = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)

if raw is None or raw.empty:
    st.info("Belum ada data. Silakan paste atau upload.")
    st.stop()

# =========================
# NORMALISASI RAW
# =========================
lu = {c: re.sub(r"\s+"," ",str(c)).strip().lower() for c in raw.columns}
def pick(*keys):
    for c in raw.columns:
        if all(k in lu[c] for k in keys): return c
    return None

c_owner   = pick("owner")
c_studio  = pick("studio")
c_user    = pick("username")
c_omset   = pick("omset")
c_estkom  = pick("est","komisi") or pick("komisi")
c_tanggal = pick("tanggal")
c_op      = pick("nama","operator") or pick("operator")
c_area    = pick("area")

df_tx = pd.DataFrame({
    "OWNER": raw[c_owner] if c_owner else "",
    "STUDIO": raw[c_studio].astype(str),
    "USERNAME": raw[c_user] if c_user else "",
    "OMSET": [parse_number(v) for v in raw[c_omset]] if c_omset else 0,
    "EST KOMISI": [parse_number(v) for v in raw[c_estkom]] if c_estkom else 0,
    "TANGGAL": raw[c_tanggal].apply(parse_date_any) if c_tanggal else None,
    "NAMA OPERATOR": raw[c_op] if c_op else "",
    "area": raw[c_area] if c_area else "",
})

valid_dates = df_tx["TANGGAL"].dropna()
if valid_dates.empty:
    st.error("Kolom TANGGAL tidak terbaca. Pastikan ada kolom 'TANGGAL'.")
    st.stop()
min_d_all, max_d_all = valid_dates.min(), valid_dates.max()

# =========================
# SIDEBAR — Database (RAW) tanpa limit + Filter
# =========================
with st.sidebar:
    st.markdown("### 📚 Database (RAW)")
    db_view = st.radio("Tampilan", ["Full (tanpa filter)","Sesuai filter"], index=0)
    st.markdown("### Filter")
    f_area  = st.multiselect("Area", sorted(df_tx["area"].dropna().unique()))
    f_owner = st.multiselect("Owner", sorted(df_tx["OWNER"].dropna().unique()))
    f_op    = st.multiselect("Operator", sorted(df_tx["NAMA OPERATOR"].dropna().unique()))
    # untuk mode "Per tanggal" tampilkan date picker
    if mode == "Per tanggal":
        pick_date = st.date_input("Tanggal (Per tanggal):", value=max_d_all, min_value=min_d_all, max_value=max_d_all)

# Terapkan filter (untuk dashboard & opsi Database)
mask = pd.Series(True, index=df_tx.index)
if f_area:  mask &= df_tx["area"].isin(f_area)
if f_owner: mask &= df_tx["OWNER"].isin(f_owner)
if f_op:    mask &= df_tx["NAMA OPERATOR"].isin(f_op)
df_tx_filtered = df_tx[mask].copy()

# Panel Database (RAW) — no limit
with st.sidebar:
    show_df = df_tx if db_view == "Full (tanpa filter)" else df_tx_filtered
    st.dataframe(show_df, use_container_width=True, height=900)
    st.download_button("⬇️ Download CSV (Database RAW)", data=show_df.to_csv(index=False).encode("utf-8"),
                       file_name="database_raw.csv", mime="text/csv")

# =========================
# HITUNGAN UTAMA (sesuai MODE)
# =========================
if mode == "Akumulasi penuh":
    # Range otomotis min..max (setelah filter)
    min_d, max_d = df_tx_filtered["TANGGAL"].min(), df_tx_filtered["TANGGAL"].max()
    day_count = (max_d - min_d).days + 1

    range_df = df_tx_filtered[(df_tx_filtered["TANGGAL"] >= min_d) & (df_tx_filtered["TANGGAL"] <= max_d)]
    agg_total = range_df.groupby("STUDIO", as_index=False).agg(
        omset_hari_ini=("OMSET","sum"),
        komisi=("EST KOMISI","sum"),
    ).rename(columns={"STUDIO":"nama_studio"})

    # target% = (avg komisi per hari di range) / (avg 7 hari terakhir sebelum max_d)
    hist_before_end = df_tx_filtered[df_tx_filtered["TANGGAL"] <= max_d].copy()
    ref = (
        hist_before_end.sort_values("TANGGAL")
        .groupby("STUDIO")["EST KOMISI"]
        .apply(lambda s: s.tail(7).mean() if len(s) else np.nan)
        .reset_index().rename(columns={"STUDIO":"nama_studio","EST KOMISI":"komisi_avg7"})
    )
    df = agg_total.merge(ref, on="nama_studio", how="left")
    df["avg_per_day"] = np.where(day_count > 0, df["komisi"] / day_count, np.nan)
    df["target_persen"] = np.where(df["komisi_avg7"] > 0, (df["avg_per_day"] / df["komisi_avg7"]) * 100.0, 100.0)
    tp = df["target_persen"].fillna(100)
    df["status"] = np.where(tp >= 100, "Naik", np.where(tp <= 90, "Turun", "Stabil"))
    df["rank_omset"] = df["omset_hari_ini"].rank(ascending=False, method="min").astype(int)
    df = df.drop(columns=["komisi_avg7","avg_per_day"]).sort_values("nama_studio").reset_index(drop=True)

    header_title = "📊 DASHBOARD KINERJA STUDIO (AKUMULASI)"
    header_meta = f"{len(df)} studio • {min_d.strftime('%d %b %Y')} — {max_d.strftime('%d %b %Y')} • {datetime.now().strftime('%H:%M:%S')}"
    use_total_labels = True
    running_text = (
        f"Mode Akumulasi • Range: {min_d.strftime('%d %b')}–{max_d.strftime('%d %b %Y')}"
    )

else:  # Per tanggal
    # gunakan pick_date dari sidebar (sudah dibatasi min/max)
    min_d, max_d = None, None  # tidak dipakai di header
    day_label = pick_date.strftime('%d %b %Y')

    today_df = df_tx_filtered[df_tx_filtered["TANGGAL"] == pick_date]
    agg_today = today_df.groupby("STUDIO", as_index=False).agg(
        omset_hari_ini=("OMSET", "sum"),
        komisi=("EST KOMISI", "sum"),
    ).rename(columns={"STUDIO":"nama_studio"})

    # target% = komisi hari itu / rata2 komisi 7 hari sebelum hari itu
    hist_until = df_tx_filtered[df_tx_filtered["TANGGAL"] < pick_date].copy()
    ref = (
        hist_until.sort_values("TANGGAL")
        .groupby("STUDIO")["EST KOMISI"]
        .apply(lambda s: s.tail(7).mean() if len(s) else np.nan)
        .reset_index().rename(columns={"STUDIO":"nama_studio","EST KOMISI":"komisi_avg7"})
    )
    df = agg_today.merge(ref, on="nama_studio", how="left")
    df["target_persen"] = np.where(df["komisi_avg7"] > 0, (df["komisi"] / df["komisi_avg7"]) * 100.0, 100.0)
    tp = df["target_persen"].fillna(100)
    df["status"] = np.where(tp >= 100, "Naik", np.where(tp <= 90, "Turun", "Stabil"))
    df["rank_omset"] = df["omset_hari_ini"].rank(ascending=False, method="min").astype(int)
    df = df.sort_values("nama_studio").reset_index(drop=True)

    header_title = "📊 DASHBOARD KINERJA STUDIO (PER TANGGAL)"
    header_meta = f"{len(df)} studio • {day_label} • {datetime.now().strftime('%H:%M:%S')}"
    use_total_labels = False
    running_text = f"Mode Per Tanggal • {day_label}"

# =========================
# AUTO REFRESH / ROTATE
# =========================
try:
    from streamlit import autorefresh as st_autorefresh
except Exception:
    from streamlit_autorefresh import st_autorefresh
refresh_counter = st_autorefresh(interval=AUTO_INTERVAL_MS, limit=None, key="auto_refresh_counter")
num_pages = max(1, math.ceil(len(df) / PAGE_SIZE))
page_idx = 0 if refresh_counter is None else (refresh_counter % num_pages)
start, end = page_idx * PAGE_SIZE, page_idx * PAGE_SIZE + PAGE_SIZE
page_df = df.iloc[start:end].copy()

# =========================
# HEADER
# =========================
st.markdown(f"""
<div class="dashboard-header">
  <div>{header_title}
    <span class="badge">Halaman {page_idx+1}/{num_pages}</span>
  </div>
  <div><span class="badge">{header_meta}</span></div>
</div>
""", unsafe_allow_html=True)

# =========================
# MAIN CONTENT
# =========================
content_holder = st.empty()
with content_holder.container():
    st.markdown('<div class="fade-in">', unsafe_allow_html=True)

    k1,k2,k3,k4 = st.columns(4)
    with k1: st.metric("Total Studio", f"{len(df)}")
    with k2: st.metric("Total Omset", rupiah(df["omset_hari_ini"].sum()))
    with k3: st.metric("Total Komisi", rupiah(df["komisi"].sum()))
    with k4:
        naik_pct = (df["status"].str.lower()=="naik").mean()*100
        st.metric("Persentase Naik", f"{naik_pct:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div style="background:#fff; padding:8px; border-radius:12px;">', unsafe_allow_html=True)
    st.markdown(df_page_to_html(page_df, start_idx=start, use_total_labels=use_total_labels), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# RUNNING TEXT
# =========================
if not df.empty:
    best_row = df.iloc[df["omset_hari_ini"].astype(float).idxmax()]
    running = f"{running_text} • Studio terbaik: {best_row['nama_studio']} (Omset: {rupiah(best_row['omset_hari_ini'])}) • Update: {datetime.now().strftime('%H:%M:%S')}"
else:
    running = f"{running_text} • Tidak ada data"
st.markdown(f'<div class="marquee-wrap"><div class="marquee-inner">{running}</div></div>', unsafe_allow_html=True)
