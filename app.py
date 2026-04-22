import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(page_title="AI Data Cleaner", layout="wide", page_icon="🌱")

# --- 1. HÀM XỬ LÝ CHUỖI CẢM BIẾN (CHỐNG LỖI 6-0) ---
def boc_tach_va_tinh_trung_binh(gia_tri):
    if pd.isna(gia_tri) or gia_tri == "" or gia_tri == "0" or gia_tri == 0:
        return 0.0
    gia_tri_str = str(gia_tri).strip()
    if "/" in gia_tri_str:
        cac_cum_thong_so = gia_tri_str.split()
        danh_sach_so = []
        for cum in cac_cum_thong_so:
            if "/" in cum:
                try:
                    # Lấy giá trị sau dấu gạch chéo
                    so = float(cum.split("/")[1])
                    danh_sach_so.append(so)
                except: pass
        if len(danh_sach_so) > 0:
            return round(sum(danh_sach_so) / len(danh_sach_so), 3)
    try:
        return float(gia_tri_str)
    except:
        return 0.0

# --- 2. GIAO DIỆN SIDEBAR (CÀI ĐẶT) ---
st.sidebar.header("⚙️ Cài đặt bộ lọc")
check_loc_5_lan = st.sidebar.checkbox("⚠️ Chỉ lấy ngày ≥ 5 lần đọc tốt", value=True)
check_ai = st.sidebar.checkbox("🤖 Hiệu chuẩn AI (Sin/Cos & [-1,1])", value=True)

# --- 3. GIAO DIỆN CHÍNH ---
st.title("🚀 Máy Chém Rác Dữ Liệu & Hiệu Chuẩn AI")
st.info("Hướng dẫn: Upload 2 file JSON -> Chọn cột muốn lấy -> Nhấn Bắt đầu xử lý.")

# Upload File
col_up1, col_up2 = st.columns(2)
with col_up1:
    file_goc = st.file_uploader("Upload file 'Lich nho giotj.json'", type=['json'])
with col_up2:
    file_champhan = st.file_uploader("Upload file 'châm phân trung gian.json'", type=['json'])

if file_goc and file_champhan:
    # Đọc dữ liệu
    df_goc = pd.read_json(file_goc)
    df_champhan = pd.read_json(file_champhan)

    # Tiền xử lý thời gian và STT để ghép nối
    for df in [df_goc, df_champhan]:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'], format='%Y-%m-%d %H-%M-%S', errors='coerce')
        df['STT'] = df['STT'].astype(str)
        df.sort_values('Thời gian', inplace=True)

    # Ghép nối dữ liệu (Merge)
    df_tong = pd.merge_asof(
        df_goc, df_champhan, on='Thời gian', by='STT', 
        direction='nearest', tolerance=pd.Timedelta(minutes=60), 
        suffixes=('_Goc', '_ChamPhan')
    )

    # Chọn cột hiển thị (Lọc bỏ bớt các cột ID và rác hệ thống để người dùng dễ chọn)
    tu_khoa_an = ['NGƯỠNG', 'BỒN', 'LƯU LƯỢNG', 'THỜI GIAN MỞ', 'BƠM', 'VAN', '_ID', 'LỊCH TRÌNH']
    cot_kha_thi = [c for c in df_tong.columns if not any(tk in c.upper() for tk in tu_khoa_an)]
    
    st.markdown("### 1. Cấu hình thông số")
    selected_stt = st.multiselect("Chọn Vườn (STT):", options=sorted(df_tong['STT'].unique()), default=sorted(df_tong['STT'].unique()))
    selected_cols = st.multiselect("Chọn các cột muốn giữ lại:", options=cot_kha_thi, default=['STT', 'Thời gian', 'EC_Goc', 'PH_Goc', 'EC_ChamPhan', 'PH_ChamPhan'])

    # --- 4. XỬ LÝ LOGIC KHI BẤM NÚT ---
    if st.button("🔥 BẮT ĐẦU XỬ LÝ DỮ LIỆU"):
        # Bước 1: Lọc theo STT và Cắt gọt cột ngay lập tức
        df_final = df_tong[df_tong['STT'].isin(selected_stt)].copy()
        df_final = df_final[selected_cols] 

        # Bước 2: Làm sạch dữ liệu số (Tách chuỗi & Lọc rác vật lý)
        for col in selected_cols:
            if col not in ['Thời gian', 'STT']:
                # Tách số từ chuỗi 6-0/6.5...
                df_final[col] = df_final[col].apply(boc_tach_va_tinh_trung_binh)
                
                # Ép kiểu về số để lọc
                df_final[col] = pd.to_numeric(df_final[col], errors='coerce')
                
                # Lọc giá trị thực tế (Bỏ số 0 và giá trị ảo)
                if 'PH' in col.upper() and 'NHIỆT ĐỘ' not in col.upper():
                    df_final = df_final[(df_final[col] > 0) & (df_final[col] <= 14)]
                elif 'EC' in col.upper() and 'NHIỆT ĐỘ' not in col.upper():
                    df_final = df_final[(df_final[col] > 0) & (df_final[col] <= 10000)]

        # Bước 3: Áp dụng điều kiện 5 lần đọc tốt/ngày
        if check_loc_5_lan:
            df_final['Ngay_Tam'] = df_final['Thời gian'].dt.date
            # Đếm số dòng sạch của mỗi ngày
            counts = df_final.groupby(['STT', 'Ngay_Tam']).size().reset_index(name='Count')
            # Chỉ lấy những ngày có >= 5 dòng sạch
            ok_days = counts[counts['Count'] >= 5]
            df_final = df_final.merge(ok_days[['STT', 'Ngay_Tam']], on=['STT', 'Ngay_Tam'], how='inner')
            df_final.drop(columns=['Ngay_Tam'], inplace=True)

        # --- 5. HIỂN THỊ VÀ DOWNLOAD ---
        if not df_final.empty:
            st.success(f"✅ Thành công! Đã lọc được {len(df_final)} bản ghi đạt chuẩn chất lượng.")
            
            st.subheader("📊 Xem trước bảng dữ liệu sạch:")
            st.dataframe(df_final.head(50), use_container_width=True)

            st.markdown("---")
            col_dl1, col_dl2 = st.columns(2)

            # Xuất File Gốc
            csv_goc = df_final.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            col_dl1.download_button(
                label="📥 Tải File GỐC SẠCH (.csv)",
                data=csv_goc,
                file_name=f"Data_Sạch_{datetime.now().strftime('%d%m_%H%M')}.csv",
                mime='text/csv',
                use_container_width=True
            )

            # Xuất File AI
            if check_ai:
                df_ai = df_final.copy()
                # Sin/Cos thời gian
                if 'Thời gian' in df_ai.columns:
                    sec = df_ai['Thời gian'].dt.hour * 3600 + df_ai['Thời gian'].dt.minute * 60 + df_ai['Thời gian'].dt.second
                    df_ai['Time_Sin'] = np.sin(2 * np.pi * sec / 86400)
                    df_ai['Time_Cos'] = np.cos(2 * np.pi * sec / 86400)
                
                # Chuẩn hóa [-1, 1] cho tất cả cột số (trừ Sin/Cos/STT)
                cot_so = df_ai.select_dtypes(include=[np.number]).columns.tolist()
                cot_so = [c for c in cot_so if c not in ['Time_Sin', 'Time_Cos', 'STT']]
                
                for col in cot_so:
                    c_min, c_max = df_ai[col].min(), df_ai[col].max()
                    if c_max != c_min:
                        df_ai[col] = round(2 * ((df_ai[col] - c_min) / (c_max - c_min)) - 1, 4)
                    else:
                        df_ai[col] = 0.0
                
                csv_ai = df_ai.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                col_dl2.download_button(
                    label="🤖 Tải File HIỆU CHUẨN AI (.csv)",
                    data=csv_ai,
                    file_name=f"Data_AI_{datetime.now().strftime('%d%m_%H%M')}.csv",
                    mime='text/csv',
                    use_container_width=True
                )
        else:
            st.error("❌ Không tìm thấy dữ liệu nào thỏa mãn điều kiện 5 lần đọc tốt/ngày!")
else:
    st.warning("👈 Vui lòng upload cả 2 file JSON để bắt đầu.")
