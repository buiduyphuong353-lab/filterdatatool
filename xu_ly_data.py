import streamlit as st
import pandas as pd
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
import joblib

# Import hàm main từ file code Python thuần hôm trước của bạn
# (Hãy đảm bảo file cũ của bạn tên là xu_ly_data.py)
import xu_ly_data 

st.set_page_config(page_title="AI Tưới Tiêu", layout="wide")

st.title("🌱 Tool Xử Lý Dữ Liệu & AI Nông Nghiệp")

# Tạo 3 Tabs
tab1, tab2, tab3 = st.tabs(["1. Lọc Dữ Liệu", "2. Huấn Luyện AI", "3. Test Dự Đoán"])

# ==========================================
# TAB 1: XỬ LÝ DỮ LIỆU
# ==========================================
with tab1:
    st.header("Trạm Làm Sạch Dữ Liệu")
    
    col1, col2 = st.columns(2)
    with col1:
        file_cp = st.file_uploader("Tải file Châm Phân (JSON)", type=['json'])
    with col2:
        file_ng = st.file_uploader("Tải file Nhỏ Giọt (JSON)", type=['json'])

    if st.button("🚀 Bắt đầu Lọc & Chuẩn Hóa", type="primary"):
        if file_cp and file_ng:
            with st.spinner('Đang xử lý nhiễu và bùa số...'):
                # Lưu file tạm để đưa cho code cũ xử lý
                with open("temp_cp.json", "wb") as f: f.write(file_cp.getbuffer())
                with open("temp_ng.json", "wb") as f: f.write(file_ng.getbuffer())
                
                # Gọi hàm main từ file cũ của bạn
                xu_ly_data.main("temp_cp.json", "temp_ng.json")
                
                st.success("✅ Đã xử lý xong! Dữ liệu sạch đã nằm trong thư mục DuLieu_Loc_Sach_AI")
                
                # Hiển thị thử vài dòng cho đẹp
                try:
                    df_preview = pd.read_csv("DuLieu_Loc_Sach_AI/Data_STT_1_ChuanHoa.csv")
                    st.dataframe(df_preview.head())
                except:
                    pass
        else:
            st.warning("⚠️ Vui lòng up đủ 2 file JSON!")

# ==========================================
# TAB 2: HUẤN LUYỆN AI
# ==========================================
with tab2:
    st.header("Lò Luyện AI (Random Forest)")
    
    khu_vuc = st.selectbox("Chọn khu vực để dạy AI:", ["1", "2", "3", "4"])
    
    if st.button("🧠 Bắt đầu Train AI", type="primary"):
        file_data = f"DuLieu_Loc_Sach_AI/Data_STT_{khu_vuc}_ChuanHoa.csv"
        
        if os.path.exists(file_data):
            with st.spinner('Đang nhồi kiến thức cho AI...'):
                df = pd.read_csv(file_data)
                
                # Đề bài (X) và Đáp án (y)
                X = df[['Gio_Sin', 'Gio_Cos', 'EC_yeu_cau_norm', 'pH_norm']]
                y = df['Thoi_luong_giay']
                
                # Train model
                model = RandomForestRegressor(n_estimators=100, random_state=42)
                model.fit(X, y)
                
                # Tính sai số (Tự test chính nó)
                sai_so = mean_absolute_error(y, model.predict(X))
                
                # Lưu não AI
                model_path = f"ai_model_khu_{khu_vuc}.pkl"
                joblib.dump(model, model_path)
                
                st.success(f"✅ AI đã học xong! Sai số trung bình: **{sai_so:.1f} giây** / mẻ tưới.")
                st.info(f"Đã lưu bộ não tại: {model_path}")
        else:
            st.error("Chưa có data sạch. Hãy quay lại Tab 1 để lọc trước!")

# ==========================================
# TAB 3: DỰ ĐOÁN THỰC TẾ
# ==========================================
with tab3:
    st.header("Trợ Lý Trưởng Vườn")
    st.write("Nhập thông số hiện tại, AI sẽ báo bạn cần tưới bao lâu.")
    # Phần này sẽ gọi file thước đo (json) và file não AI (pkl) ra để tính toán
    st.info("Chức năng này sẽ được kích hoạt sau khi bạn Train AI thành công ở Tab 2!")
