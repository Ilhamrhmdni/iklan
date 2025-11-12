# app.py
# Dashboard "Monitor Digital" Kinerja Studio Harian
# Versi: mendukung data transaksi (narrow), pivot 2-header, Google Sheet CSV, simulasi
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

/* Fade-in lembut saat ganti halaman */
@keyframes fadeInSoft { from {opacity:0; transform: translateY(6px);} to {opacity:1; transform: translateY(0);} }
.fade-in { animation: fadeInSoft 550ms ease-in-out; }

/* Tabel kontras aman di Dark Mode */
.styled-table {
  border-collapse: collapse; width: 100%; font-size: 16px;
  color:#0f172a; background:#ffffff;
}
.styled-table thead th, .styled-table td, .styled-table th {
  color:#0f172a !important; padding:12px 10px; border-bottom:1px solid #e5e7eb; text-align:left;
}
.styled-table thead th {
  background:#f8fafc !important; border-bottom:2px solid #cbd5e1;
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
    """Angka format ID/EN/plain -> float."""
    if pd.isna(x): return 0.0
    s = str(x).strip()
    if s == "": return 0.0
    s = re.sub(r"[^\d,.\-]", "", s)
    if s.count(",") == 1 and (s.rfind(",") > s.rfind(".")):
        s = s.replace(".", "").replace(",", ".")  # ID
    else:
        s = s.replace(",", "")  # EN/plain
    try:
        return float(s)
    except:
        return 0.0

def parse_date_any(x):
    """Coba parse tanggal (YYYY-MM-DD, DD/MM/YYYY, dll)."""
    if pd.isna(x): return None
    s = str(x).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
    # Terakhir: biarkan pandas coba
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
# DATA GENERATOR (simulasi)
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
    st.markdown("**Catatan:**")
    st.markdown("- Bisa paste **transaksi baris** *(OWNER, STUDIO, USERNAME, OMSET, EST KOMISI, TANGGAL, NAMA OPERATOR, area)*.")
    st.markdown("- Bisa juga paste **pivot 2 header** (tanggal di baris 1).")
    st.caption("Format angka ID/EN otomatis terdeteksi.")

# =========================
# INPUT READERS
# =========================
def read_from_paste() -> pd.DataFrame | None:
    st.markdown("**Mode paste** — pilih sesuai bentuk data kamu.")
    mode = st.radio("Bentuk data:", ["Transaksi (baris)", "Pivot (2 baris header)"], index=0, horizontal=True)

    pasted = st.text_area(
        "Paste data di sini (termasuk header):",
        height=260,
        placeholder="OWNER\tSTUDIO\tUSERNAME\tOMSET\tEST KOMISI\tTANGGAL\tNAMA OPERATOR\tarea\nCMDTIM\tSTUDIO PUSAT 102\tanekagamis77\t892.009\t73.420\t2025-11-01\tVALEN\tarea 1"
                 if mode == "Transaksi (baris)" else
                 "area\tNAMA OPERATOR\tSTUDIO\t2025-11-08\t\t\t2025-11-09\t...\n \t \t \tCOUNTA ...\tSUM of OMSET\tSUM of EST KOMISI\tCOUNTA ...\tSUM of OMSET\tSUM of EST KOMISI\t..."
    )
    up = st.file_uploader("atau Upload CSV/XLSX", type=["csv", "xlsx"])

    def _detect_sep(text: str) -> str:
        if "\t" in text: return "\t"
        if ";" in text: return ";"
        return ","

    def _combine_two_header_rows(df_: pd.DataFrame) -> pd.DataFrame:
        if df_.shape[0] < 2:
            return df_
        top = [str(x).strip() for x in df_.iloc[0].tolist()]
        sub = [str(x).strip() for x in df_.iloc[1].tolist()]
        new = []
        for t, s in zip(top, sub):
            t_clean = t
            m = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", t)
            if m:
                d, mth, y = m.groups()
                t_clean = f"{y}-{mth}-{d}"
            label = s if t_clean == "" else f"{t_clean} | {s}" if s else t_clean
            new.append(label.strip())
        df_.columns = new
        df_ = df_.iloc[2:].reset_index(drop=True)
        return df_

    raw = None
    if pasted.strip():
        sep = _detect_sep(pasted)
        tmp = pd.read_csv(io.StringIO(pasted), sep=sep, header=None if mode == "Pivot (2 baris header)" else "infer")
        raw = _combine_two_header_rows(tmp) if mode == "Pivot (2 baris header)" else tmp
    elif up is not None:
        if up.name.lower().endswith(".csv"):
            tmp = pd.read_csv(up, header=None if mode == "Pivot (2 baris header)" else "infer")
        else:
            tmp = pd.read_excel(up, header=None if mode == "Pivot (2 baris header)" else 0)
        raw = _combine_two_header_rows(tmp) if mode == "Pivot (2 baris header)" else tmp

    if raw is not None:
        raw.columns = [str(c).strip() for c in raw.columns]
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
# BUILDERS
# =========================
def build_from_transactions(raw: pd.DataFrame) -> pd.DataFrame:
    """Bangun DF dashboard dari data transaksi baris."""
    cols_up = {c: c for c in raw.columns}
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
    c_estkom  = pick("est komisi") or pick("komisi")
    c_tanggal = pick("tanggal")
    c_op      = pick("nama operator") or pick("operator")
    c_area    = pick("area")

    # UI filter (area/owner/operator & tanggal)
    # ambil tanggal min/max
    dates = raw[c_tanggal].apply(parse_date_any)
    min_d = min([d for d in dates if d is not None], default=datetime.today().date())
    max_d = max([d for d in dates if d is not None], default=datetime.today().date())
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Filter Data (Transaksi)")
        f_area = st.multiselect("Area", sorted(raw[c_area].dropna().unique()) if c_area else [], default=None)
        f_owner = st.multiselect("Owner", sorted(raw[c_owner].dropna().unique()) if c_owner else [], default=None)
        f_op = st.multiselect("Operator", sorted(raw[c_op].dropna().unique()) if c_op else [], default=None)
        d1, d2 = st.date_input("Rentang Tanggal", (max_d - timedelta(days=0), max_d))

    df = pd.DataFrame({
        "owner": raw[c_owner] if c_owner else "",
        "nama_studio": raw[c_studio].astype(str),
        "username": raw[c_user] if c_user else "",
        "omset": [parse_number(v) for v in raw[c_omset]] if c_omset else 0,
        "komisi": [parse_number(v) for v in raw[c_estkom]] if c_estkom else 0,
        "tanggal": dates,
        "operator": raw[c_op] if c_op else "",
        "area": raw[c_area] if c_area else "",
    })

    # Apply filters
    m = pd.Series(True, index=df.index)
    if f_area:  m &= df["area"].isin(f_area)
    if f_owner: m &= df["owner"].isin(f_owner)
    if f_op:    m &= df["operator"].isin(f_op)
    if isinstance(d1, tuple) or isinstance(d1, list):
        d_start, d_end = d1[0], d1[1]
    else:
        d_start, d_end = d1, d2
    m &= df["tanggal"].between(d_start, d_end)
    df = df[m]

    # Aggregate per STUDIO untuk rentang tanggal terpilih
    agg = df.groupby("nama_studio", as_index=False).agg(
        omset_hari_ini=("omset", "sum"),
        komisi=("komisi", "sum"),
    )

    # Target % (opsional): jika tidak ada kolom target, hitung vs rata2 7 hari terakhir (di data asli)
    # Ambil rata2 7 hari terakhir per studio dari full data (tanpa filter tanggal) untuk komisi sebagai acuan.
    if len(set(["nama_studio", "komisi", "tanggal"]).difference(df.columns)) == 0:
        base = pd.DataFrame({
            "nama_studio": raw[c_studio].astype(str),
            "komisi": [parse_number(v) for v in raw[c_estkom]] if c_estkom else 0,
            "tanggal": dates
        })
        # rolling mean 7 hari (pakai groupby studio)
        m7 = base.dropna().copy()
        # gunakan mean 7 hari historis sebelum tanggal akhir filter
        ref_end = d_end
        m7 = m7[m7["tanggal"] <= ref_end]
        ref = m7.groupby("nama_studio")["komisi"].apply(lambda s: s.tail(7).mean() if len(s) else np.nan).reset_index(name="komisi_avg7")
        agg = agg.merge(ref, on="nama_studio", how="left")
        agg["target_persen"] = np.where(agg["komisi_avg7"] > 0, (agg["komisi"] / agg["komisi_avg7"]) * 100.0, np.nan)
        agg.drop(columns=["komisi_avg7"], inplace=True)
    else:
        agg["target_persen"] = np.nan

    # Status otomatis
    tp = agg["target_persen"].fillna(100)
    agg["status"] = np.where(tp >= 100, "Naik", np.where(tp <= 90, "Turun", "Stabil"))

    # Rank
    agg["rank_omset"] = agg["omset_hari_ini"].rank(ascending=False, method="min").astype(int)
    return agg.sort_values("nama_studio").reset_index(drop=True)

def build_from_pivot(raw: pd.DataFrame) -> pd.DataFrame:
    """Bangun DF dashboard dari pivot 2 header / lebar."""
    orig_cols = list(raw.columns)
    norm = {c: re.sub(r"\s+", " ", str(c)).strip().lower() for c in orig_cols}

    def find_col(*keywords):
        for c in orig_cols:
            lc = norm[c]
            if all(k in lc for k in keywords):
                return c
        return None

    col_studio = find_col("studio") or find_col("nama", "studio")
    col_harian = find_col("harian")
    col_komisi = find_col("komisi - iklan") or find_col("sum of est komisi") or find_col("komisi")
    col_target = find_col("target komisi harian") or find_col("target", "harian")
    col_status = find_col("status")

    # Tanggal paling kanan (format "YYYY-MM-DD | ...")
    date_cols = [c for c in orig_cols if re.search(r"\b\d{4}-\d{2}-\d{2}\b", str(c))]
    last_date = None
    if not col_harian and date_cols:
        last_date = max(date_cols, key=lambda c: orig_cols.index(c))
        omset_cands  = [c for c in orig_cols if c.startswith(last_date) and ("sum of omset" in norm[c] or "omset" in norm[c])]
        komisi_cands = [c for c in orig_cols if c.startswith(last_date) and ("sum of est komisi" in norm[c] or "komisi - iklan" in norm[c] or "komisi" in norm[c])]
        if omset_cands:
            col_harian = omset_cands[0]
        if (not col_komisi) and komisi_cands:
            col_komisi = komisi_cands[0]

    # Mapping manual jika belum ketemu
    cols = list(raw.columns)
    if (col_studio is None) or (col_harian is None):
        st.warning("Tidak semua kolom terdeteksi (pivot). Pilih mapping manual:")
        c1, c2 = st.columns(2)
        with c1:
            col_studio = st.selectbox("↗️ Kolom Nama Studio", cols, index=0 if col_studio is None else cols.index(col_studio))
            col_harian = st.selectbox("↗️ Kolom Omset Hari Ini", cols, index=min(1, len(cols)-1) if col_harian is None else cols.index(col_harian))
        with c2:
            col_komisi = st.selectbox("↗️ Kolom Komisi (opsional)", ["(Tidak ada)"]+cols, index=0 if col_komisi is None else 1+cols.index(col_komisi))
            col_target = st.selectbox("↗️ Kolom Target % (opsional)", ["(Tidak ada)"]+cols, index=0 if col_target is None else 1+cols.index(col_target))
            col_status = st.selectbox("↗️ Kolom Status (opsional)", ["(Tidak ada)"]+cols, index=0 if col_status is None else 1+cols.index(col_status))
    else:
        st.info(
            f"Deteksi otomatis (pivot):\n"
            f"- Studio → **{col_studio}**\n"
            f"- Omset → **{col_harian}**" +
            (f"\n- Komisi → **{col_komisi}**" if col_komisi else "") +
            (f"\n- Target % → **{col_target}**" if col_target else "") +
            (f"\n- Status → **{col_status}**" if col_status else "") +
            (f"\n- Tanggal dipakai: **{last_date}**" if last_date else "")
        )

    df = pd.DataFrame({
        "nama_studio": raw[col_studio].astype(str),
        "omset_hari_ini": [parse_number(v) for v in raw[col_harian]],
        "komisi": [parse_number(v) for v in (raw[col_komisi] if (col_komisi and col_komisi != "(Tidak ada)") else 0)],
        "target_persen": [parse_number(v) for v in (raw[col_target] if (col_target and col_target != "(Tidak ada)") else np.nan)],
        "status": (raw[col_status] if (col_status and col_status != "(Tidak ada)") else np.nan)
    })

    # Bersihkan baris total/kosong
    df = df[df["nama_studio"].str.strip().str.len() > 0]
    df = df[~df["nama_studio"].str.contains(r"\btotal\b", case=False, na=False)]

    # Status otomatis bila kosong
    tp = df["target_persen"].fillna(100)
    df["status"] = np.where(df["status"].isna(), np.where(tp >= 100, "Naik", np.where(tp <= 90, "Turun", "Stabil")), df["status"])

    df["rank_omset"] = df["omset_hari_ini"].rank(ascending=False, method="min").astype(int)
    return df.sort_values("nama_studio").reset_index(drop=True)

# =========================
# LOAD DATA sesuai pilihan
# =========================
if src == "Paste/Upload":
    raw = read_from_paste()
    if raw is not None and not raw.empty:
        # deteksi otomatis: apakah data transaksi baris?
        cols_low = [c.lower().strip() for c in raw.columns]
        is_transactions = any("username" in c for c in cols_low) and any("tanggal" in c for c in cols_low)
        if is_transactions:
            st.caption("Terdeteksi data **transaksi baris**.")
            df = build_from_transactions(raw)
        else:
            st.caption("Terdeteksi data **pivot/lebar**.")
            df = build_from_pivot(raw)
    else:
        df = simulate_data(400)
elif src == "Google Sheets (CSV)":
    raw = read_from_gsheet_csv()
    if raw is not None and not raw.empty:
        cols_low = [c.lower().strip() for c in raw.columns]
        is_transactions = any("username" in c for c in cols_low) and any("tanggal" in c for c in cols_low)
        if is_transactions:
            st.caption("Terdeteksi data **transaksi baris** dari CSV.")
            df = build_from_transactions(raw)
        else:
            st.caption("Terdeteksi data **pivot/lebar** dari CSV.")
            df = build_from_pivot(raw)
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
