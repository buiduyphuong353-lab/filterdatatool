import streamlit as st
import json
import csv
import math
import io
from datetime import datetime

# --- 1. CÁC HÀM LOGIC (GIỮ NGUYÊN TỪ BẢN NO-PANDAS) ---
def boc_tach_va_tinh_trung_binh(gia_tri):
    if gia_tri is None or gia_tri == "" or gia_tri == "0":
        return 0.0
    gia_tri_str = str(gia_tri).strip()
    if "/" in gia_tri_str:
        cac_cum = gia_tri_str.split()
        danh_sach_so = []
        for cum in cac_cum:
            if "/" in cum:
                try: danh_sach_so.append(float(cum.split("/")[1]))
                except: pass
        if danh_sach_so: return round(sum(danh_sach_so) / len(danh_sach_so), 3)
    try: return float(gia_tri_str)
    except: return gia_tri_str

def parse_time(t_str):
    if not t_str: return None
    for fmt in ['%Y-%m-%d %H-%M-%S', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S']:
        try: return datetime.strptime(str(t_str).strip(), fmt)
        except: continue
    return None

# --- 2. GIAO DIỆN STREAMLIT ---
st.set_page_config(page_title="Hệ thống Xử lý Dữ liệu AH4", layout="wide")
st.title("🚀 Hệ thống Xử lý Dữ liệu ")

# Sidebar
with st.sidebar:
    st.header("📂 Nạp Dữ Liệu")
    uploaded_goc = st.file_uploader("Lịch sử nhỏ giọt (JSON)", type="json")
    uploaded_cp = st.file_uploader("Châm phân trung gian (JSON)", type="json")
    
    st.header("⚙️ Cài đặt bộ lọc")
    loc_thieu = st.checkbox("Bỏ qua dòng không có châm phân", value=True)
    du_5_lan = st.checkbox("Chỉ lấy ngày ≥ 5 lần đọc tốt", value=True)
    chuan_hoa_ai = st.checkbox("Hiệu chuẩn AI ([-1, 1])", value=True)

# KIỂM TRA: Chỉ chạy khi ĐÃ TẢI ĐỦ 2 FILE
if uploaded_goc is not None and uploaded_cp is not None:
    # Đọc dữ liệu
    list_goc = json.load(uploaded_goc)
    list_cp = json.load(uploaded_cp)
    
    # Tiền xử lý (Logic No-Pandas)
    tu_khoa_chia_100 = ['TB', 'YÊU CẦU', 'CHÊNH LỆCH', 'NGƯỠNG']
    
    # Xử lý nhanh cho cả 2 list
    processed_goc = []
    for item in list_goc:
        t_obj = parse_time(item.get('Thời gian'))
        if t_obj:
            item['Time_Obj'] = t_obj
            item['STT'] = str(item.get('STT', 'Unknown')).strip()
            processed_goc.append(item)
            
    processed_cp = []
    for item in list_cp:
        t_obj = parse_time(item.get('Thời gian'))
        if t_obj:
            item['Time_Obj'] = t_obj
            item['STT'] = str(item.get('STT', 'Unknown')).strip()
            processed_cp.append(item)

    # Ghép bảng (Merge nearest 60p)
    df_tong = []
    # Gom CP theo STT để tìm cho nhanh
    dict_cp = {}
    for cp in processed_cp:
        stt = cp['STT']
        if stt not in dict_cp: dict_cp[stt] = []
        dict_cp[stt].append(cp)

    for g in processed_goc:
        row = {'STT': g['STT'], 'Thời gian': g['Time_Obj'].strftime('%Y-%m-%d %H:%M:%S'), 'Time_Obj': g['Time_Obj']}
        for k, v in g.items():
            if k not in ['Thời gian', 'STT', 'Time_Obj']: 
                val = boc_tach_va_tinh_trung_binh(v)
                if any(tk in k.upper() for tk in tu_khoa_chia_100):
                    try: val = float(val) / 100.0
                    except: pass
                row[f"{k}_Goc"] = val
        
        # Tìm châm phân
        best_cp = None
        min_diff = 3600
        if g['STT'] in dict_cp:
            for cp in dict_cp[g['STT']]:
                diff = abs((g['Time_Obj'] - cp['Time_Obj']).total_seconds())
                if diff <= min_diff:
                    min_diff = diff
                    best_cp = cp
        
        if best_cp:
            for k, v in best_cp.items():
                if k not in ['Thời gian', 'STT', 'Time_Obj']:
                    val = boc_tach_va_tinh_trung_binh(v)
                    if any(tk in k.upper() for tk in tu_khoa_chia_100):
                        try: val = float(val) / 100.0
                        except: pass
                    row[f"{k}_ChamPhan"] = val
        df_tong.append(row)

    # --- HIỂN THỊ TÙY CHỌN (CHỈ KHI CÓ df_tong) ---
    st.subheader("📊 Tùy chỉnh xuất dữ liệu")
    
    col1, col2 = st.columns(2)
    with col1:
        all_stt = sorted(list(set(d['STT'] for d in df_tong)))
        chon_stt = st.multiselect("Chọn Vườn:", options=["Tất cả"] + all_stt, default=["Tất cả"])
    
    with col2:
        # Lấy tất cả tên cột trừ biến phụ
        temp_cols = set()
        for r in df_tong: temp_cols.update(r.keys())
        all_cols = sorted([c for c in temp_cols if c != 'Time_Obj'])
        # Mặc định chọn vài cột quan trọng
        defaults = [c for c in ['STT', 'Thời gian', 'EC_Goc', 'PH_Goc', 'EC_ChamPhan', 'PH_ChamPhan'] if c in all_cols]
        cot_chon = st.multiselect("Chọn thông số muốn xuất:", options=all_cols, default=defaults)

    if st.button("🚀 LỌC & XUẤT FILE"):
        # Logic lọc
        final_list = []
        for r in df_tong:
            if "Tất cả" not in chon_stt and r['STT'] not in chon_stt: continue
            if loc_thieu and not any("_ChamPhan" in k for k in r.keys()): continue
            
            # Lọc rác vật lý
            new_r = {c: r.get(c, "") for c in cot_chon}
            new_r['Time_Obj'] = r['Time_Obj'] # Giữ lại để lọc 5 lần/ngày
            
            hop_le = True
            for c, v in new_r.items():
                if 'PH' in str(c).upper() and 'NHIỆT' not in str(c).upper():
                    try:
                        fv = float(v)
                        if fv <= 0 or fv > 14: hop_le = False
                    except: pass
                if 'EC' in str(c).upper() and 'NHIỆT' not in str(c).upper():
                    try:
                        fv = float(v)
                        if fv <= 0 or fv > 10000: hop_le = False
                    except: pass
            if hop_le: final_list.append(new_r)

        if du_5_lan:
            dem = {}
            for r in final_list:
                k = f"{r['STT']}_{r['Time_Obj'].date()}"
                dem[k] = dem.get(k, 0) + 1
            final_list = [r for r in final_list if dem[f"{r['STT']}_{r['Time_Obj'].date()}"] >= 5]

        if not final_list:
            st.error("Không có dữ liệu thỏa mãn điều kiện lọc!")
        else:
            st.success(f"Đã xử lý xong {len(final_list)} dòng!")
            # Hiển thị demo
            demo_list = [ {k:v for k,v in r.items() if k != 'Time_Obj'} for r in final_list[:10] ]
            st.table(demo_list)

            # Tạo file CSV để tải (Dùng io.StringIO cho Python thuần)
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=cot_chon)
            writer.writeheader()
            for r in final_list:
                writer.writerow({c: r.get(c, "") for c in cot_chon})
            
            st.download_button(
                label="📥 Tải xuống File Gốc (.csv)",
                data=output.getvalue().encode('utf-8-sig'),
                file_name="Data_AH4_Clean.csv",
                mime="text/csv"
            )

else:
    st.warning("⚠️ Vui lòng tải lên cả 2 file JSON ở cột bên trái để bắt đầu!")
