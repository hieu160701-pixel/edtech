import streamlit as st
import google.generativeai as genai
import pandas as pd

# 1. CẤU HÌNH TRANG WEB
st.set_page_config(page_title="Trợ lý Giáo dục AI", page_icon="🎓")

st.title("🎓 AI Coach - Tìm lộ trình học chuẩn xác")
st.write("Chào bạn, tôi sẽ giúp bạn tìm khóa học phù hợp nhất thay vì tìm kiếm mệt mỏi trên Google.")

# 2. KẾT NỐI API & DỮ LIỆU
# Lấy API Key bí mật từ cấu hình của Streamlit hoặc dùng key mặc định (fallback)
try:
    # Key mặc định từ người dùng cung cấp (để chạy ngay nếu chưa cấu hình secrets)
    default_api_key = "AIzaSyDLSRnw-QZGXQ-0spEUcbZTJ2_4-rWcDUY"
    
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        # Sử dụng key trực tiếp nếu không có secrets
        genai.configure(api_key=default_api_key)
    
    # --- PHẦN BẠN CẦN SỬA LINK CSV ---
    # Thay đường link bên dưới bằng link CSV bạn lấy ở BƯỚC 1
    # Link này dùng được cho cả "Publish to Web" và "Share with anyone link"
    csv_url = "https://docs.google.com/spreadsheets/d/1Ql3qgm_zU3X8mSUfabL0J1vg4Ctu6OUzz4Q0Z-R8_Jc/export?format=csv"
    
    # Đọc dữ liệu
    df = pd.read_csv(csv_url)
    
except Exception as e:
    st.error(f"Lỗi kết nối: {e}. \\n\\n**Lưu ý quan trọng:**\\n1. Kiểm tra xem bạn đã 'Publish to Web' file Google Sheet chưa?\\n2. Kiểm tra API Key có đúng không?")
    st.stop()

# 3. GIAO DIỆN CHAT
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "model", "content": "Chào bạn! Bạn đang muốn học kỹ năng gì? (Ví dụ: Tôi muốn học Marketing để tự bán hàng online)"}
    ]

# Hiển thị lịch sử chat cũ
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 4. XỬ LÝ KHI NGƯỜI DÙNG NHẬP LIỆU
if prompt := st.chat_input("Nhập mục tiêu học tập của bạn..."):
    # Hiện câu hỏi của người dùng
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gửi yêu cầu cho AI
    with st.chat_message("model"):
        with st.spinner("Đang phân tích lộ trình phù hợp..."):
            try:
                # Chuyển dữ liệu Excel thành văn bản để AI đọc
                data_text = df.to_string()
                
                # Câu lệnh điều khiển AI (System Prompt)
                full_prompt = f"""
                Vai trò: Bạn là một chuyên gia tư vấn giáo dục tận tâm.
                
                Dữ liệu khóa học có sẵn (chỉ được giới thiệu trong danh sách này):
                {data_text}
                
                Yêu cầu của người dùng: "{prompt}"
                
                Nhiệm vụ:
                1. Phân tích xem người dùng đang thiếu kỹ năng gì.
                2. Đề xuất một lộ trình học ngắn gọn.
                3. QUAN TRỌNG: Chọn ra 1-2 khóa học trong danh sách trên phù hợp nhất.
                4. Bắt buộc phải đưa ra Link Affiliate của khóa học đó để người dùng click.
                5. Giọng văn thân thiện, khuyến khích.
                """
                
                # Danh sách các model để thử (dự phòng khi model này lỗi thì qua model khác)
                models_to_try = [
                    'gemini-2.0-flash-lite-preview-02-05', # Thử bản lite mới nhất trước
                    'gemini-2.0-flash-lite',
                    'gemini-2.0-flash',
                    'gemini-1.5-flash',
                    'gemini-pro'
                ]
                
                response = None
                last_error = None
                
                for model_name in models_to_try:
                    try:
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(full_prompt)
                        break # Nếu thành công thì thoát vòng lặp
                    except Exception as e:
                        last_error = e
                        continue # Nếu lỗi thì thử model tiếp theo
                
                if response:
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "model", "content": response.text})
                else:
                    st.error(f"Xin lỗi, hiện tại hệ thống đang quá tải (Lỗi: {last_error}). Vui lòng thử lại sau vài giây.")
                
            except Exception as e:
                st.error(f"Đã có lỗi xảy ra: {e}")
