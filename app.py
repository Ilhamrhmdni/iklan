import streamlit as st
import pandas as pd
import plotly.express as px
import time
from datetime import datetime

# Fungsi untuk memuat data dari CSV
@st.cache_data
def load_data():
    df = pd.read_csv('data_studio.csv')
    # Pastikan kolom TANGGAL dalam format datetime
    df['TANGGAL'] = pd.to_datetime(df['TANGGAL'], errors='coerce')
    return df

# Fungsi untuk format angka ribuan
def format_number(num):
    return f"{num:,.0f}"

# Fungsi untuk styling tabel berdasarkan area
def style_table(df):
    def color_area(val):
        if val == 1:
            color = 'background-color: lightblue'
        elif val == 2:
            color = 'background-color: lightgreen'
        elif val == 3:
            color = 'background-color: lightcoral'
        elif val == 4:
            color = 'background-color: lightsalmon'
        else:
            color = ''
        return color
    return df.style.applymap(color_area, subset=['AREA'])

# Load data
df = load_data()

# Judul dashboard
st.title("📊 DASHBOARD OMSET & KOMISI STUDIO SHOPEE LIVE AFFILIATE")

# Hitung total omset dan estimasi komisi
total_omset = df['OMSET'].sum()
total_komisi = df['EST_KOMISI'].sum()

# Tampilkan total di atas
col1, col2 = st.columns(2)
with col1:
    st.metric("Total Omset", format_number(total_omset))
with col2:
    st.metric("Total Estimasi Komisi", format_number(total_komisi))

# Filter
st.sidebar.header("Filter Data")
area_filter = st.sidebar.multiselect("Pilih Area", options=df['AREA'].unique(), default=df['AREA'].unique())
operator_filter = st.sidebar.multiselect("Pilih Operator", options=df['NAMA_OPERATOR'].unique(), default=df['NAMA_OPERATOR'].unique())
studio_filter = st.sidebar.multiselect("Pilih Studio", options=df['STUDIO'].unique(), default=df['STUDIO'].unique())
tanggal_start = st.sidebar.date_input("Tanggal Mulai", value=df['TANGGAL'].min().date())
tanggal_end = st.sidebar.date_input("Tanggal Akhir", value=df['TANGGAL'].max().date())

# Search bar
search_query = st.sidebar.text_input("Cari Username atau Studio", "")

# Terapkan filter
filtered_df = df[
    (df['AREA'].isin(area_filter)) &
    (df['NAMA_OPERATOR'].isin(operator_filter)) &
    (df['STUDIO'].isin(studio_filter)) &
    (df['TANGGAL'].dt.date >= tanggal_start) &
    (df['TANGGAL'].dt.date <= tanggal_end)
]

# Terapkan search
if search_query:
    filtered_df = filtered_df[
        filtered_df['USERNAME'].str.contains(search_query, case=False, na=False) |
        filtered_df['STUDIO'].str.contains(search_query, case=False, na=False)
    ]

# Tampilkan tabel dengan styling dan pagination
st.subheader("Data Studio")
if not filtered_df.empty:
    # Batasi hingga 400 baris untuk performa
    display_df = filtered_df.head(400)
    # Gunakan st.dataframe dengan styling
    st.dataframe(style_table(display_df), use_container_width=True)
else:
    st.write("Tidak ada data yang cocok dengan filter.")

# Grafik total omset & komisi per area
st.subheader("Grafik Total Omset & Komisi per Area")
area_summary = filtered_df.groupby('AREA').agg({'OMSET': 'sum', 'EST_KOMISI': 'sum'}).reset_index()
if not area_summary.empty:
    fig = px.bar(area_summary, x='AREA', y=['OMSET', 'EST_KOMISI'], barmode='group', title="Omset dan Komisi per Area")
    st.plotly_chart(fig)
else:
    st.write("Tidak ada data untuk grafik.")

# Auto-refresh setiap 60 detik
placeholder = st.empty()
while True:
    time.sleep(60)
    st.rerun()
