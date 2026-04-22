import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ Thống Xử Lý Data AI", layout="wide")

# --- HÀM TIỀN XỬ LÝ (Giữ nguyên logic của bạn) ---
def boc_tach_va_tinh_trung_binh(gia_tri):
    if pd.isna(gia_tri) or gia_tri == "" or gia_tri == "0":
        return 0.0
    gia_tri_str = str(gia_tri).strip()
    if "/" in gia_tri_str:
        cac_cum_thong_so = gia_tri_str.split()
        danh_sach_so = []
        for cum in cac_cum_thong_so:
            if "/" in cum:
                try:
                    so = float(cum.split("/")[1])
                    danh_sach_so.append(so)
                except: pass
        if len(danh_sach_so) > 0:
            return round(sum(danh_sach_so) / len(danh_sach_so), 3)
    try: return float(gia_tri_str)
    except: return gia_tri_str

# --- GIAO DIỆN CHÍNH ---
st.title("🚀 Máy Chém Rác Dữ Liệu & Hiệu Chuẩn AI")
st.markdown("---")

# 1. Upload File
col1, col2 = st.columns(2)
with col1:
    file_goc = st.file_uploader("Upload file 'Lich nho giotj.json'", type=['json'])
with col2:
    file_champhan = st.file_uploader("Upload file 'châm phân trung gian.json'", type=['json'])

if file_goc and file_champhan:
    # Load dữ liệu
    df_goc = pd.read_json(file_goc)
    df_champhan = pd.read_json(file_champhan)

    # Tiền xử lý nhanh
    for df in [df_goc, df_champhan]:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'], format='%Y-%m-%d %H-%M-%S', errors='coerce')
        df['STT'] = df['STT'].astype(str)

    # Ghép nối
    df_tong = pd.merge_asof(
        df_goc.sort_values('Thời gian'), 
        df_champhan.sort_values('Thời gian'), 
        on='Thời gian', by='STT', 
        direction='nearest', tolerance=pd.Timedelta(minutes=60), 
        suffixes=('_Goc', '_ChamPhan')
    )

    # 2. Cài đặt lọc (Sidebar)
    st.sidebar.header("⚙️ Cài đặt bộ lọc")
    tu_khoa_an = ['NGƯỠNG', 'BỒN', 'LƯU LƯỢNG', 'THỜI GIAN MỞ', 'BƠM', 'VAN', 'NGƯỜI ĐIỀU KHIỂN', 'TRẠNG THÁI', 'PHƯƠNG THỨC', 'LỊCH TRÌNH', '_ID', 'SỐ LẦN', 'TÊN']
    cot_kha_thi = [c for c in df_tong.columns if not any(tk in c.upper() for tk in tu_khoa_an)]
    
    selected_stt = st.sidebar.multiselect("Chọn Vườn (STT):", options=sorted(df_tong['STT'].unique()), default=sorted(df_tong['STT'].unique()))
    check_loc_5_lan = st.sidebar.checkbox("Chỉ lấy ngày ≥ 5 lần đọc tốt", value=True)
    check_ai = st.sidebar.checkbox("Hiệu chuẩn AI (Sin/Cos & [-1,1])", value=True)
    
    selected_cols = st.multiselect("Chọn thông số muốn giữ lại:", options=cot_kha_thi, default=['STT', 'Thời gian', 'EC_Goc', 'PH_Goc'])

    # 3. Xử lý Logic
    if st.button("🔥 BẮT ĐẦU XỬ LÝ DỮ LIỆU"):
        df_final = df_tong[df_tong['STT'].isin(selected_stt)].copy()
        
        # Áp dụng hàm tách số cho các cột đã chọn
        for col in selected_cols:
            if col not in ['Thời gian', 'STT']:
                df_final[col] = df_final[col].apply(boc_tach_va_tinh_trung_binh)

        # Lọc rác cảm biến
        for col in selected_cols:
            if 'PH' in col.upper() and 'NHIỆT ĐỘ' not in col.upper():
                df_final = df_final[(pd.to_numeric(df_final[col], errors='coerce') > 0) & (pd.to_numeric(df_final[col], errors='coerce') <= 14)]
            elif 'EC' in col.upper() and 'NHIỆT ĐỘ' not in col.upper():
                df_final = df_final[(pd.to_numeric(df_final[col], errors='coerce') > 0) & (pd.to_numeric(df_final[col], errors='coerce') <= 10000)]

        # Lọc 5 lần/ngày
        if check_loc_5_lan:
            df_final['Ngay_Tam'] = df_final['Thời gian'].dt.date
            counts = df_final.groupby(['STT', 'Ngay_Tam']).size().reset_index(name='Count')
            ok_days = counts[counts['Count'] >= 5]
            df_final = df_final.merge(ok_days[['STT', 'Ngay_Tam']], on=['STT', 'Ngay_Tam'], how='inner')
            df_final.drop(columns=['Ngay_Tam'], inplace=True)

        st.success(f"✅ Đã xử lý xong {len(df_final)} dòng đạt chuẩn!")
        st.dataframe(df_final.head(50))

        # 4. Xuất file (Download Button)
        col_dl1, col_dl2 = st.columns(2)
        
        # File Gốc
        csv_goc = df_final.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        col_dl1.download_button("📥 Tải File Gốc (.csv)", data=csv_goc, file_name="Data_Goc_Sạch.csv", mime='text/csv')

        # File AI
        if check_ai:
            df_ai = df_final.copy()
            if 'Thời gian' in df_ai.columns:
                sec = df_ai['Thời gian'].dt.hour * 3600 + df_ai['Thời gian'].dt.minute * 60 + df_ai['Thời gian'].dt.second
                df_ai['Time_Sin'] = np.sin(2 * np.pi * sec / 86400)
                df_ai['Time_Cos'] = np.cos(2 * np.pi * sec / 86400)
            
            cot_so = df_ai.select_dtypes(include=[np.number]).columns.tolist()
            cot_so = [c for c in cot_so if c not in ['Time_Sin', 'Time_Cos', 'STT']]
            for col in cot_so:
                c_min, c_max = df_ai[col].min(), df_ai[col].max()
                df_ai[col] = 2 * ((df_ai[col] - c_min) / (c_max - c_min)) - 1 if c_max != c_min else 0.0
            
            csv_ai = df_ai.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            col_dl2.download_button("📥 Tải File Hiệu Chuẩn AI (.csv)", data=csv_ai, file_name="Data_AI_Chuan_Hoa.csv", mime='text/csv')
