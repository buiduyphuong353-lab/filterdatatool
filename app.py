import streamlit as st
import json, math, re, unicodedata, bisect
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Xử lý dữ liệu tưới", layout="wide")
st.title("🚀 Dashboard xử lý & chuẩn hóa dữ liệu AI")

# ==========================================
# HÀM TIỆN ÍCH
# ==========================================
def remove_accents(text):
    return "".join([c for c in unicodedata.normalize('NFKD', str(text)) if not unicodedata.combining(c)])

def normalize_text(s):
    return remove_accents(s).upper()

def doc_json_sieu_bu(file):
    raw = file.read().decode("utf-8-sig")
    try:
        return json.loads(raw)
    except:
        raw = re.sub(r',\s*\]', ']', raw)
        raw = re.sub(r',\s*\}', '}', raw)
        try:
            return json.loads(raw)
        except:
            return []

def parse_time(t):
    if not t: return None
    for fmt in ['%Y-%m-%d %H-%M-%S','%Y-%m-%d %H:%M:%S']:
        try: return datetime.strptime(str(t)[:19], fmt)
        except: pass
    return None

def boc_tach_sach(val):
    if val in [None,"","0"]: return 0.0
    s = str(val)
    if "/" in s:
        nums = [float(x.split("/")[1]) for x in s.split() if "/" in x]
        return sum(nums)/len(nums) if nums else 0.0
    try: return float(s)
    except: return 0.0

# ==========================================
# UPLOAD FILE
# ==========================================
files = st.file_uploader("📂 Upload JSON", type="json", accept_multiple_files=True)

if files:

    list_goc, list_vt = [], []

    for f in files:
        data = doc_json_sieu_bu(f)
        if any(k in normalize_text(f.name) for k in ["LICH","GOC"]):
            list_goc.extend(data)
        else:
            list_vt.extend(data)

    # ==========================================
    # XỬ LÝ VỆ TINH
    # ==========================================
    dict_vt = {}
    keys_vt = set()

    for vt in list_vt:
        stt = str(vt.get("STT",""))
        t = parse_time(vt.get("Thời gian"))
        if t:
            vt["Time_Obj"] = t
            dict_vt.setdefault(stt, []).append(vt)
            keys_vt.update(vt.keys())

    for stt in dict_vt:
        dict_vt[stt].sort(key=lambda x: x["Time_Obj"])

    # ==========================================
    # XỬ LÝ GỐC
    # ==========================================
    df_processed = []
    thong_ke_ngay = {}
    keys_goc = set()

    for g in list_goc:
        t = parse_time(g.get("Thời gian"))
        if not t: continue

        g["Time_Obj"] = t
        g["Duration_Sec"] = 60  # giả định

        df_processed.append(g)
        keys_goc.update(g.keys())

        if g["Duration_Sec"] >= 40:
            key = (str(g.get("STT","")), t.strftime("%Y-%m-%d"))
            thong_ke_ngay[key] = thong_ke_ngay.get(key,0)+1

    # ==========================================
    # LỌC CỘT
    # ==========================================
    tu_khoa_an = [
        '_ID','TIME_OBJ','DURATION_SEC','LỊCH TRÌNH','STT','THỜI GIAN',
        'BỒN','NGƯỠNG','CHÊNH LỆCH','NGƯỜI','TRẠNG THÁI',
        'LƯU LƯỢNG','PHƯƠNG THỨC'
    ]

    cot_goc = [k for k in keys_goc if not any(normalize_text(tk) in normalize_text(k) for tk in tu_khoa_an)]
    cot_vt  = [k for k in keys_vt if not any(normalize_text(tk) in normalize_text(k) for tk in tu_khoa_an)]

    cot_all = sorted(set(cot_goc + cot_vt))

    # ==========================================
    # UI
    # ==========================================
    ds_vuon = sorted(set(str(r.get("STT","")) for r in df_processed))
    chon_stt = st.multiselect("🌱 Chọn vườn", ["Tất cả"] + ds_vuon, ["Tất cả"])

    check_day = st.checkbox("⚠️ Ngày ≥ 5 cử", True)
    check_strict = st.checkbox("🚫 Bỏ dòng thiếu data", True)

    st.subheader("📊 Chọn cột")
    cot_lay = []
    for c in cot_all:
        if st.checkbox(c, value=("EC" in c or "PH" in c)):
            cot_lay.append(c)

    # ==========================================
    # XỬ LÝ
    # ==========================================
    if st.button("🚀 Xử lý"):

        final = []

        for g in df_processed:
            stt = str(g.get("STT",""))
            if "Tất cả" not in chon_stt and stt not in chon_stt:
                continue

            if check_day:
                key = (stt, g["Time_Obj"].strftime("%Y-%m-%d"))
                if key not in thong_ke_ngay or thong_ke_ngay[key] < 5:
                    continue

            row = {"STT": stt, "Thời gian": g["Thời gian"]}

            # GỐC
            ok_goc = False
            for c in cot_lay:
                val = boc_tach_sach(g.get(c))
                if val != 0: ok_goc = True
                row[c+"_Goc"] = val

            if check_strict and not ok_goc:
                continue

            # VỆ TINH (match gần nhất)
            vt_list = dict_vt.get(stt, [])
            best = None

            if vt_list:
                times = [x["Time_Obj"] for x in vt_list]
                idx = bisect.bisect_left(times, g["Time_Obj"])

                cand = []
                if idx < len(times): cand.append(vt_list[idx])
                if idx > 0: cand.append(vt_list[idx-1])

                best = min(cand, key=lambda x: abs((x["Time_Obj"]-g["Time_Obj"]).total_seconds()))

            ok_vt = False
            for c in cot_lay:
                val = boc_tach_sach(best.get(c)) if best else 0
                if val != 0: ok_vt = True
                row[c+"_VT"] = val

            if check_strict and not ok_vt:
                continue

            final.append(row)

        if not final:
            st.warning("❌ Không có dữ liệu")
        else:
            df = pd.DataFrame(final)

            # ==========================================
            # CHUẨN HÓA AI
            # ==========================================
            df_norm = df.copy()

            for col in df.columns:
                if col in ["STT","Thời gian"]: continue
                vals = df[col]
                mn, mx = vals.min(), vals.max()
                if mx == mn: mx = mn + 1
                df_norm[col] = 2*((vals-mn)/(mx-mn))-1

            # sin cos time
            sin_list, cos_list = [], []
            for t in df["Thời gian"]:
                dt = parse_time(t)
                if dt:
                    h = dt.hour + dt.minute/60
                    sin_list.append(math.sin(2*math.pi*h/24))
                    cos_list.append(math.cos(2*math.pi*h/24))
                else:
                    sin_list.append(0)
                    cos_list.append(0)

            df_norm["Time_Sin"] = sin_list
            df_norm["Time_Cos"] = cos_list

            st.success(f"✅ {len(df)} dòng")

            st.dataframe(df.head())

            st.download_button("📥 CSV thường", df.to_csv(index=False), "data.csv")
            st.download_button("📥 CSV AI", df_norm.to_csv(index=False), "data_ai.csv")
