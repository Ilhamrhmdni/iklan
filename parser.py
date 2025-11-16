import pandas as pd
import re

def parse_value(text):
    """
    Mengambil komisi, omset dari format:
    '23.918 - 509.972 (D)'
    """
    if pd.isna(text):
        return 0, 0

    text = str(text)

    match = re.match(r"([\d\.]+)\s*-\s*([\d\.]+)", text)
    if not match:
        return 0, 0

    komisi = float(match.group(1).replace(".", ""))
    omset = float(match.group(2).replace(".", ""))

    return komisi, omset


def process_dataframe(df):
    """
    Input DataFrame dengan kolom:
    Username | 11-11-2025
    (isi format komisi - omset)

    Output DataFrame rapi:
    Username | Est. Komisi | Omset
    """
    usernames = df["Username"]
    values = df.iloc[:, 1]  # kolom harian

    komisi_list = []
    omset_list = []

    for val in values:
        k, o = parse_value(val)
        komisi_list.append(k)
        omset_list.append(o)

    output = pd.DataFrame({
        "Username": usernames,
        "Est. Komisi": komisi_list,
        "Omset": omset_list
    })

    total_row = pd.DataFrame({
        "Username": ["TOTAL"],
        "Est. Komisi": [sum(komisi_list)],
        "Omset": [sum(omset_list)]
    })

    output = pd.concat([output, total_row], ignore_index=True)

    return output
