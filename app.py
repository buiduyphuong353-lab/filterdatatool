import streamlit as st
import os
import json
import csv
import math
import re
import unicodedata
from datetime import datetime
import bisect
import pandas as pd

st.set_page_config(page_title="Xử lý dữ liệu tưới", layout="wide")
st.title("🚀 Dashboard xử lý & chuẩn hóa dữ liệu AI")

# ==========================================
# 1. HÀM CÔNG CỤ
# ==========================================
def remove_accents(text):
    return "".join([c for c in unicodedata.normalize('NFKD', str(text)) if not unicodedata.combining(c)])

def doc_json_sieu_bu(file):
    raw_text = file.read().decode("utf-8-sig")
    try:
        return json.loads(raw_text)
    except:
        text_clean = re.sub(r',\s*\]', ']', raw_text)
        text_clean = re.sub(r',\s*\}', '}', text_clean)
        try:
            return json.loads(text_clean)
        except:
            return []

def parse_time(t_str):
    if not t_str: return None
    for fmt in ['%Y-%m-%d %H-%M-%S', '%Y-%m-%d %H:%M:%S']:
        try: return datetime.strptime(str(t_str)[:19], fmt)
        except: continue
    return None

def boc_tach_sach(val):
    if val in [None, "", "0"]: return 0.0
    s = str(val)
    if "/" in s:
        nums = [float(c.split("/")[1]) for c in s.split() if "/" in c]
        return sum(nums)/len(nums) if nums else 0.0
    try: return float(s)
    except: return 0.0

# ==========================================
# 2. UPLOAD FILE
# ==========================================
uploaded_files = st.file_uploader("📂 Tải nhiều file JSON", type=["json"], accept_multiple_files=True)

if uploaded_files:

    list_goc = []
    list_vetinh = []

    for file in uploaded_files:
        data = doc_json_sieu_bu(file)
        if any(k in remove_accents(file.name.lower()) for k in ["lich", "goc"]):
            list_goc.extend(data)
        else:
            list_vetinh.extend(data)

    # ==========================================
    # 3. XỬ LÝ
    # ==========================================
    dict_vt = {}
    for vt in list_vetinh:
        stt = str(vt.get('STT', ''))
        t_obj = parse_time(vt.get('Thời gian'))
        if t_obj:
            vt['Time_Obj'] = t_obj
            dict_vt.setdefault(stt, []).append(vt)

    for stt in dict_vt:
        dict_vt[stt].sort(key=lambda x: x['Time_Obj'])

    df_processed = []
    for g in list_goc:
        t_obj = parse_time(g.get('Thời gian'))
        if not t_obj: continue
        g['Time_Obj'] = t_obj
        df_processed.append(g)

    danh_sach_vuon = sorted(list(set(str(r.get('STT', '')) for r in df_processed)))
    chon_stt = st.multiselect("🌱 Chọn vườn", ["Tất cả"] + danh_sach_vuon, default=["Tất cả"])

    check_khat_khe = st.checkbox("🚫 Bỏ dòng thiếu dữ liệu", True)

    # lấy key
    keys = set()
    for r in df_processed:
        keys.update(r.keys())

    tu_khoa_an = [
    '_ID', 'TIME_OBJ', 'DURATION_SEC', 'LỊCH TRÌNH',
    'STT', 'THỜI GIAN', 'BỒN', 'NGƯỠNG',
    'CHÊNH LỆCH', 'NGƯỜI', 'TRẠNG THÁI',
    'LƯU LƯỢNG', 'PHƯƠNG THỨC'
]

cot = [
    k for k in keys
    if not any(tk in k.upper() for tk in tu_khoa_an)
]

    st.subheader("📊 Chọn cột")
    cot_lay = []
    for c in cot:
        if st.checkbox(c, value=("EC" in c or "PH" in c)):
            cot_lay.append(c)

    # ==========================================
    # 4. XỬ LÝ + XUẤT
    # ==========================================
    if st.button("🚀 Xử lý & xuất file"):

        final_data = []

        for g in df_processed:
            stt = str(g.get('STT', ''))
            if 'Tất cả' not in chon_stt and stt not in chon_stt:
                continue

            row = {
                "STT": stt,
                "Thời gian": g.get('Thời gian')
            }

            for c in cot_lay:
                row[c] = boc_tach_sach(g.get(c))

            final_data.append(row)

        if not final_data:
            st.warning("Không có dữ liệu")
        else:
            # chuẩn hóa
            final_norm = []
            for row in final_data:
                new_row = row.copy()
                t_obj = parse_time(row['Thời gian'])

                if t_obj:
                    t = t_obj.hour + t_obj.minute/60
                    new_row['Time_Sin'] = math.sin(2*math.pi*t/24)
                    new_row['Time_Cos'] = math.cos(2*math.pi*t/24)

                final_norm.append(new_row)

            df1 = pd.DataFrame(final_data)
            df2 = pd.DataFrame(final_norm)

            st.success(f"✅ Xong {len(df1)} dòng")

            st.dataframe(df1.head())

            st.download_button("📥 Tải file thường", df1.to_csv(index=False), "data_thuong.csv")
            st.download_button("📥 Tải file AI", df2.to_csv(index=False), "data_ai.csv")
