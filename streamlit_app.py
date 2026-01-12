import streamlit as st
import google.generativeai as genai
import pandas as pd

# 1. CẤU HÌNH TRANG WEB
st.set_page_config(page_title="Trợ lý Giáo dục AI", page_icon="🎓")

st.title("🎓 AI Coach - Tìm lộ trình học chuẩn xác")
st.write("Chào bạn, tôi sẽ giúp bạn tìm khóa học phù hợp nhất thay vì tìm kiếm mệt mỏi trên Google.")

# 2. KẾT NỐI API & DỮ LIỆU
# Lấy API Key bí mật từ cấu hình của Streamlit
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        st.error("Chưa nhập API Key vào Secrets.")
        st.stop()
    
    # --- PHẦN BẠN CẦN SỬA LINK CSV ---
    # Thay đường link bên dưới bằng link CSV bạn lấy ở BƯỚC 1
    # VÍ DỤ: csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ.../pub?output=csv"
    csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTq9...THAY_LINK_CUA_BAN_VAO_DAY.../pub?output=csv"
    
    # Đọc dữ liệu
    df = pd.read_csv(csv_url)
    
except Exception as e:
    st.error(f"Lỗi kết nối: {e}. Hãy kiểm tra lại link CSV hoặc API Key.")
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
                
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(full_prompt)
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "model", "content": response.text})
                
            except Exception as e:
                st.error(f"Đã có lỗi xảy ra: {e}")
