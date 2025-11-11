# app.py
# Streamlit Dashboard "Monitor Digital" Kinerja 400 Studio
# By Albert

import os
import time
import math
import random
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime

# ---------------------------
# PAGE CONFIG & STYLES
# ---------------------------
st.set_page_config(page_title="Dashboard Kinerja Studio Harian",
                   layout="wide",
                   page_icon="📊")

# ---- CSS: full screen feel, header, table, marquee, fade-in
st.markdown("""
<style>
/* Global reset-ish */
.block-container {padding-top: 0rem; padding-bottom: 0rem; max-width: 100%;}
header[data-testid="stHeader"] {display: none;}

/* Big header */
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

/* Subheader meta badges */
.badge {
  font-size:14px; padding:6px 10px; border-radius:999px; margin-left:6px;
  background:#0ea5e91a; color:#7dd3fc; border:1px solid #0ea5e9;
}

/* Fade-in animation on page switch */
@keyframes fadeInSoft {
  from {opacity: 0; transform: translateY(6px);}
  to {opacity: 1; transform: translateY(0);}
}
.fade-in {
  animation: fadeInSoft 550ms ease-in-out;
}

/* Table polish */
.styled-table {
  border-collapse: collapse;
  width: 100%;
  font-size: 16px;
}
.styled-table th, .styled-table td {
  padding: 12px 10px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
}
.styled-table thead th {
  position: sticky; top: 0;
  background: #f8fafc;
  border-bottom: 2px solid #cbd5e1;
  z-index: 2;
  font-weight: 700;
}
.row-green { background-color: #dcfce7; }   /* Naik */
.row-red   { background-color: #fee2e2; }   /* Turun */
.row-yellow{ background-color: #fef9c3; }   /* Stabil */

/* Status pill */
.pill {
  padding: 4px 10px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 13px;
  display: inline-block;
}
.pill-green  { background:#16a34a; color:white; }
.pill-red    { background:#dc2626; color:white; }
.pill-yellow { background:#ca8a04; color:white; }

/* Bottom marquee (running text) */
.marquee-wrap {
  position: fixed; left: 0; right: 0; bottom: 0;
  background: #0f172a; color:#e2e8f0; border-top: 2px solid #0ea5e9;
  padding: 10px 0; overflow: hidden; z-index: 9999;
  font-size: 18px; font-weight: 700;
}
.marquee-inner {
  display: inline-block; white-space: nowrap;
  will-change: transform;
  animation: slideLeft 20s linear infinite;
}
@keyframes slideLeft {
  0% { transform: translateX(100%); }
  100% { transform: translateX(-100%); }
}

/* Hide Streamlit footer/menu for signage feel */
#MainMenu, footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# CONFIGS
# ---------------------------
PAGE_SIZE = 20
AUTO_INTERVAL_MS = 5000  # 5s rotate
RANDOM_SEED_BASE = 42    # for reproducible-ish simulation

# ---------------------------
# DATA FETCH LAYER
# ---------------------------
def simulate_data(n=400, seed=None) -> pd.DataFrame:
    """Simulate 400 studios with today's metrics."""
    if seed is None:
        seed = RANDOM_SEED_BASE + int(datetime.now().strftime("%H%M"))  # change per minute for slight movement
    rng = np.random.default_rng(seed)
    names = [f"Studio {i:03d}" for i in range(1, n+1)]

    omset = rng.integers(5_000_000, 250_000_000, size=n)  # 5 jt - 250 jt
    komisi_pct = rng.uniform(0.05, 0.15, size=n)          # 5% - 15%
    komisi = (omset * komisi_pct).astype(int)

    target = rng.uniform(80, 125, size=n)                 # 80% - 125%
    # Weighted status: Naik(45%), Stabil(30%), Turun(25%)
    status_choices = rng.choice(["Naik", "Stabil", "Turun"], size=n, p=[0.45, 0.30, 0.25])

    df = pd.DataFrame({
        "nama_studio": names,
        "omset_hari_ini": omset,
        "komisi": komisi,
        "target_persen": np.round(target, 2),
        "status": status_choices
    })
    # Rank by omset for "best"
    df["rank_omset"] = df["omset_hari_ini"].rank(ascending=False, method="min").astype(int)
    return df.sort_values("nama_studio").reset_index(drop=True)

def fetch_data_from_supabase() -> pd.DataFrame:
    """
    Placeholder: Change to real Supabase query later.
    Example with supabase-py:
    -------------------------
    from supabase import create_client, Client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    res = supabase.table("studios").select("*").execute()
    df = pd.DataFrame(res.data)
    return df
    """
    # For now, simulate:
    return simulate_data()

# ---------------------------
# SESSION & AUTO ROTATE
# ---------------------------
# st_autorefresh returns an incrementing counter; use it to jump pages
count = st.experimental_rerun  # legacy guard, do nothing (placeholder to avoid linter)
autoref_count = st.experimental_data_editor if False else None  # keep linter calm

# New API for auto refresh (stable):
autoref_count = st.experimental_get_query_params()  # dummy line for older versions
try:
    from streamlit_autorefresh import st_autorefresh  # If you have this ext
except Exception:
    # Use built-in st_autorefresh since Streamlit 1.25+
    from streamlit import autorefresh as st_autorefresh

# Use built-in:
refresh_counter = st_autorefresh(interval=AUTO_INTERVAL_MS, limit=None, key="auto_refresh_counter")

# Track current page via counter to ensure loop
if "num_pages" not in st.session_state:
    st.session_state.num_pages = 1  # will be set after data load
if "page_idx" not in st.session_state:
    st.session_state.page_idx = 0

# ---------------------------
# LOAD DATA
# ---------------------------
df = fetch_data_from_supabase()
total_rows = len(df)
num_pages = math.ceil(total_rows / PAGE_SIZE)
st.session_state.num_pages = num_pages

# Compute the active page based on refresh counter (will loop automatically)
page_idx = 0 if refresh_counter is None else (refresh_counter % num_pages)
st.session_state.page_idx = page_idx

# Slice current page
start = page_idx * PAGE_SIZE
end = start + PAGE_SIZE
page_df = df.iloc[start:end].copy()

# Best studio (by omset)
best_row = df.loc[df["omset_hari_ini"].idxmax()]
best_name = str(best_row["nama_studio"])
best_omset = int(best_row["omset_hari_ini"])

# ---------------------------
# UTILS
# ---------------------------
def rupiah(x: int) -> str:
    return f"Rp{int(x):,}".replace(",", ".")

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

def df_page_to_html(df_page: pd.DataFrame) -> str:
    # Build HTML table manually for full control + row colors
    headers = ["No", "Nama Studio", "Omset Hari Ini", "Komisi", "Target (%)", "Status"]
    html = ['<table class="styled-table">']
    # thead
    html.append("<thead><tr>")
    for h in headers:
        html.append(f"<th>{h}</th>")
    html.append("</tr></thead>")
    # tbody
    html.append("<tbody>")
    for i, row in enumerate(df_page.itertuples(index=False), start=start+1):
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

# ---------------------------
# HEADER
# ---------------------------
now = datetime.now()
meta_left = f"Halaman {page_idx+1}/{num_pages}"
meta_right = f"{total_rows} studio • {now.strftime('%H:%M:%S, %d %b %Y')}"

st.markdown(f"""
<div class="dashboard-header">
  <div>📊 DASHBOARD KINERJA STUDIO HARIAN
    <span class="badge">{meta_left}</span>
  </div>
  <div>
    <span class="badge">{meta_right}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------
# MAIN CONTENT (fade-in + st.empty())
# ---------------------------
content_holder = st.empty()
with content_holder.container():
    st.markdown(f'<div class="fade-in">', unsafe_allow_html=True)

    # Top KPI row
    kpi1, kpi2, kpi3, kpi4 = st.columns([1,1,1,1])
    with kpi1:
        st.metric("Total Studio", f"{total_rows}")
    with kpi2:
        st.metric("Total Omset (simulasi)", rupiah(int(df["omset_hari_ini"].sum())))
    with kpi3:
        st.metric("Rata-rata Omset", rupiah(int(df["omset_hari_ini"].mean())))
    with kpi4:
        naik_pct = (df["status"].str.lower() == "naik").mean()*100
        st.metric("Persentase Naik", f"{naik_pct:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # Data table (custom HTML for row colors + pills)
    st.markdown(df_page_to_html(page_df), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# BOTTOM RUNNING TEXT (marquee)
# ---------------------------
running_text = (
    f"Studio terbaik hari ini: {best_name} (Omset: {rupiah(best_omset)})   •   "
    f"Update terakhir: {now.strftime('%H:%M:%S, %d %b %Y')}"
)
st.markdown(f"""
<div class="marquee-wrap">
  <div class="marquee-inner">{running_text}</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------
# NOTES:
# - Auto-rotate handled by st_autorefresh every 5s (A->B->...->A loop).
# - Content uses st.empty() + CSS fade-in each rerun.
# - To connect Supabase, replace fetch_data_from_supabase() with real client.
# ---------------------------
