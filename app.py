import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="AI Data Cleaner", layout="wide", page_icon="🌱")

# --- HÀM TIỀN XỬ LÝ ---
def boc_tach_va_tinh_trung_binh(gia_tri):
    if pd.isna(gia_tri) or gia_tri == "" or gia_tri == 0:
        return 0.0
    gia_tri_str = str(gia_tri).strip()
    if "/" in gia_tri_str:
        cac_cum = gia_tri_str.split()
        danh_sach = []
        for cum in cac_cum:
            if "/" in cum:
                try:
                    danh_sach.append(float(cum.split("/")[1]))
                except: pass
        if danh_sach: return round(sum(danh_sach) / len(danh_sach), 3)
    try: return float(gia_tri_str)
    except: return 0.0

# --- GIAO DIỆN ---
st.title("🚀 Máy Chém Rác Dữ Liệu & Hiệu Chuẩn AI")

col_up1, col_up2 = st.columns(2)
with col_up1:
    file_goc = st.file_uploader("Upload file 'Lich nho giotj.json'", type=['json'])
with col_up2:
    file_champhan = st.file_uploader("Upload file 'châm phân trung gian.json'", type=['json'])

# Chỉ chạy logic phía dưới nếu ĐÃ UPLOAD ĐỦ 2 FILE
if file_goc and file_champhan:
    try:
        df_goc = pd.read_json(file_goc)
        df_champhan = pd.read_json(file_champhan)

        for df in [df_goc, df_champhan]:
            df['Thời gian'] = pd.to_datetime(df['Thời gian'], format='%Y-%m-%d %H-%M-%S', errors='coerce')
            df['STT'] = df['STT'].astype(str)
            df.sort_values('Thời gian', inplace=True)

        df_tong = pd.merge_asof(
            df_goc, df_champhan, on='Thời gian', by='STT', 
            direction='nearest', tolerance=pd.Timedelta(minutes=60), 
            suffixes=('_Goc', '_ChamPhan')
        )

        # Cài đặt bộ lọc
        st.sidebar.header("⚙️ Cài đặt")
        check_loc_5 = st.sidebar.checkbox("Chỉ lấy ngày ≥ 5 lần đọc tốt", value=True)
        check_ai = st.sidebar.checkbox("Hiệu chuẩn AI ([-1,1])", value=True)

        tu_khoa_an = ['NGƯỠNG', 'BỒN', 'LƯU LƯỢNG', 'THỜI GIAN MỞ', 'BƠM', 'VAN', '_ID']
        cot_kha_thi = [c for c in df_tong.columns if not any(tk in c.upper() for tk in tu_khoa_an)]
        
        st.markdown("### 1. Cấu hình thông số")
        selected_stt = st.multiselect("Chọn Vườn:", options=sorted(df_tong['STT'].unique()), default=sorted(df_tong['STT'].unique()))
        selected_cols = st.multiselect("Chọn cột giữ lại:", options=cot_kha_thi, default=['STT', 'Thời gian', 'EC_Goc', 'PH_Goc'])

        if st.button("🔥 BẮT ĐẦU XỬ LÝ"):
            df_final = df_tong[df_tong['STT'].isin(selected_stt)].copy()
            df_final = df_final[selected_cols] 

            for col in selected_cols:
                if col not in ['Thời gian', 'STT']:
                    df_final[col] = df_final[col].apply(boc_tach_va_tinh_trung_binh)
                    df_final[col] = pd.to_numeric(df_final[col], errors='coerce')
                    # Lọc rác
                    if 'PH' in col.upper():
                        df_final = df_final[(df_final[col] > 0) & (df_final[col] <= 14)]
                    elif 'EC' in col.upper():
                        df_final = df_final[(df_final[col] > 0) & (df_final[col] <= 10000)]

            if check_loc_5:
                df_final['Ngay_Tam'] = df_final['Thời gian'].dt.date
                counts = df_final.groupby(['STT', 'Ngay_Tam']).size().reset_index(name='C')
                ok_days = counts[counts['C'] >= 5]
                df_final = df_final.merge(ok_days[['STT', 'Ngay_Tam']], on=['STT', 'Ngay_Tam'], how='inner')
                df_final.drop(columns=['Ngay_Tam'], inplace=True)

            if not df_final.empty:
                st.success(f"✅ Đã xử lý {len(df_final)} dòng.")
                st.dataframe(df_final.head(20), use_container_width=True) # Hiển thị bảng gọn gàng

                # Nút tải file
                csv_goc = df_final.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 Tải File Gốc Sạch", data=csv_goc, file_name="Data_Sach.csv", mime='text/csv')
            else:
                st.error("Dữ liệu sau lọc trống rỗng!")
    except Exception as e:
        st.error(f"Lỗi xử lý: {e}")
else:
    st.warning("👈 Vui lòng upload file để bắt đầu.")
