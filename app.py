import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime, timedelta

def parse_shopee_data(raw_lines):
    """
    Parse data Shopee dengan format:
    Studio | User | Saldo | Penjualan | Biaya Total | [Biaya | Order | Efektivitas | Penonton] x96
    """
    records = []
    
    # Generate 96 time slots: 00:00, 00:15, ..., 23:45
    time_slots = []
    current = datetime.strptime("00:00", "%H:%M")
    for _ in range(96):
        time_slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=15)

    for line in raw_lines:
        line = line.strip()
        if not line or "TOTAL" in line or "BELUM" in line:
            continue  # skip kosong, total, atau tidak aktif

        parts = line.split("\t")
        if len(parts) < 5:
            continue

        studio = parts[0].strip()
        username = parts[1].strip()
        try:
            saldo = float(str(parts[2]).replace(".", "").replace(",", "") or 0)
            total_penjualan = float(str(parts[3]).replace(".", "").replace(",", "") or 0)
            total_biaya_iklan = float(str(parts[4]).replace(".", "").replace(",", "") or 0)
        except:
            saldo = 0
            total_penjualan = 0
            total_biaya_iklan = 0

        # Ambil data per 15 menit (mulai dari indeks 5)
        interval_blocks = parts[5:]

        intervals = []
        for block in interval_blocks:
            block = block.strip()
            if "|" in block or "|" in block:
                # Ganti | jika digunakan sebagai pemisah
                sep = "|" if "|" in block else "\|"
                subparts = [x.strip() for x in block.split(sep)]
                if len(subparts) >= 4:
                    try:
                        biaya = float(subparts[0].replace(".", ""))
                        order = float(subparts[1].replace(".", ""))
                        efektivitas_str = subparts[2].replace("%", "").replace(",", ".")
                        efektivitas = float(efektivitas_str) if efektivitas_str else 0
                        penonton = float(subparts[3].replace(".", ""))
                        intervals.append({
                            "Biaya Iklan": biaya,
                            "Order": order,
                            "Efektivitas Iklan (%)": efektivitas,
                            "Penonton": penonton
                        })
                    except:
                        intervals.append({
                            "Biaya Iklan": 0,
                            "Order": 0,
                            "Efektivitas Iklan (%)": 0,
                            "Penonton": 0
                        })
                else:
                    intervals.append({
                        "Biaya Iklan": 0, "Order": 0, "Efektivitas Iklan (%)": 0, "Penonton": 0
                    })
            else:
                intervals.append({
                    "Biaya Iklan": 0, "Order": 0, "Efektivitas Iklan (%)": 0, "Penonton": 0
                })

        # Tambahkan ke records dengan waktu
        for i, interval in enumerate(intervals):
            if i < len(time_slots):
                records.append({
                    "Nama Studio": studio,
                    "Username": username,
                    "Waktu": time_slots[i],
                    "Penonton": interval["Penonton"],
                    "Order": interval["Order"],
                    "Biaya Iklan (15 menit)": interval["Biaya Iklan"],
                    "Efektivitas Iklan (%)": interval["Efektivitas Iklan (%)"],
                    "Saldo": saldo,
                    "Total Penjualan": total_penjualan,
                    "Total Biaya Iklan": total_biaya_iklan
                })

    df = pd.DataFrame(records)
    
    # Hitung ROAS per interval (opsional)
    df["ROAS"] = df.apply(
        lambda row: (row["Order"] * (row["Total Penjualan"] / row["Order"].sum() if row["Order"] > 0 else 0)) / row["Biaya Iklan (15 menit)"]
        if row["Biaya Iklan (15 menit)"] > 0 and row["Total Penjualan"] > 0 and row["Order"] > 0
        else 0,
        axis=1
    )
    df["ROAS"] = df["ROAS"].replace([np.inf, -np.inf], 0).fillna(0)

    return df

# === Contoh Input Data ===
raw_data = """
STUDIO SURABAYA FASHION PRIA	grosirpakaiandalamsby	14.589	2.584.462	62.311	0|0|0%|0	562|0|0%|5	684|0|0%|4	743|0|0%|6	617|104.740|169.86%|5	908|0|0%|12	682|49.680|72.84%|17	601|0|0%|15	560|0|0%|18	577|0|0%|3	462|106.020|229.60%|15	580|81.740|140.97%|9	694|45.000|64.82%|6	628|0|0%|7	874|0|0%|14	894|17.393|19.46%|4	1.120|0|0%|10	707|38.999|55.19%|17	682|57.677|84.58%|14	889|0|0%|18	852|0|0%|8	745|75.576|101.49%|8	1.049|133.476|127.28%|18	900|47.500|52.77%|25	700|0|0%|13	756|46.800|61.91%|10	599|0|0%|17	494|0|0%|10	756|15.400|20.36%|22	752|0|0%|12	1.065|28.000|26.28%|12	1.101|0|0%|14	952|0|0%|14	787|0|0%|7	727|0|0%|18	951|0|0%|8	1.673|0|0%|7	1.325|32.999|24.90%|11	1.826|0|0%|15	1.964|0|0%|3	1.515|0|0%|2	0|0|0%|1	0|0|0%|0	0|0|0%|0	1.497|134.149|89.63%|7	1.880|196.899|104.71%|7	3.147|102.000|32.41%|11	1.040|339.206|326.28%|23	1.546|0|0%|18	1.276|243.749|191.05%|10	477|99.599|208.76%|10	446|102.220|229.02%|9	594|0|0%|5	668|0|0%|7	573|0|0%|4	814|0|0%|7	639|142.500|222.87%|14	1.044|0|0%|7	0|0|0%|0	0|0|0%|0	0|0|0%|0	116|0|0%|1	728|0|0%|20	785|39.000|49.66%|11	756|0|0%|4	476|0|0%|7	604|0|0%|9	2.202|0|0%|15	3.696|0|0%|7	472|222.400|471.07%|8	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%|0	0|0|0%......
"""

# === Parsing Data ===
lines = [line.strip() for line in raw_data.strip().split("\n") if line.strip()]
df = parse_shopee_data(lines)

if len(df) > 0:
    print("✅ Data berhasil diparsing!")
    print(f"📊 Total baris (interval 15 menit): {len(df)}")
    print(f"👥 Jumlah akun unik: {df['Username'].nunique()}")

    # === Ringkasan Harian per Akun ===
    daily = df.groupby(["Nama Studio", "Username"]).agg(
        Total_Penjualan=("Total Penjualan", "mean"),
        Total_Biaya_Iklan=("Total Biaya Iklan", "mean"),
        Total_Order=("Order", "sum"),
        Total_Penonton=("Penonton", "sum"),
        Rata_rata_Efektivitas=("Efektivitas Iklan (%)", "mean"),
        Rata_rata_ROAS=("ROAS", "mean")
    ).reset_index()

    # Status ROAS
    def status_roas(roas):
        if roas == 0:
            return "⏸️ Tidak Aktif"
        elif roas < 5:
            return "🔴 Boncos"
        elif roas < 30:
            return "🟠 Perlu Optimasi"
        elif roas < 50:
            return "🟡 Hampir Aman"
        else:
            return "🟢 Aman"

    daily["Status ROAS"] = daily["Rata_rata_ROAS"].apply(status_roas)

    print("\n📋 Ringkasan Harian per Akun:")
    print(daily[["Username", "Total_Penjualan", "Total_Biaya_Iklan", "Rata_rata_ROAS", "Status ROAS"]])

    # === Grafik ROAS per 15 Menit (untuk satu akun) ===
    username_plot = df["Username"].iloc[0]  # ganti jika perlu
    user_data = df[df["Username"] == username_plot].copy()
    user_data["Waktu"] = pd.to_datetime(user_data["Waktu"], format="%H:%M").dt.time

    plt.figure(figsize=(14, 5))
    plt.plot(range(len(user_data)), user_data["ROAS"], marker="o", label="ROAS", color="orange")
    plt.title(f"ROAS per 15 Menit - {username_plot}")
    plt.xlabel("Waktu (15 menit)")
    plt.ylabel("ROAS")
    plt.xticks(ticks=range(0, 96, 8), labels=[f"{h:02d}:00" for h in range(0, 24, 3)], rotation=45)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()

else:
    print("❌ Gagal parsing data. Periksa format input.")
