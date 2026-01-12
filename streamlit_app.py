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
        st.error("Chưa cấu hình API Key trong Secrets. Vui lòng vào Cài đặt (Advanced Settings) trên Streamlit Cloud và thêm `GEMINI_API_KEY`.")
        st.stop()
    
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
                # Danh sách các model để thử (Chỉ dùng các key đã kiểm tra là có sẵn)
                models_to_try = [
                    'gemini-2.0-flash',             # Bản ổn định
                    'gemini-2.0-flash-lite',        # Bản nhẹ
                    'gemini-2.0-flash-exp',         # Bản thử nghiệm (thường ít bị limit)
                    'gemini-flash-latest',          # Alias trỏ về bản flash mới nhất (thường là 1.5)
                ]
                
                response = None
                error_log = []
                
                for model_name in models_to_try:
                    try:
                        # Thêm delay nhỏ để tránh spam request quá nhanh lỗi 429 liên hoàn
                        import time
                        time.sleep(1) 
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(full_prompt)
                        break
                    except Exception as e:
                        error_log.append(f"{model_name}: {str(e)}")
                        continue
                
                if response:
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "model", "content": response.text})
                else:
                    error_details = "\\n".join(error_log)
                    st.error(f"Hệ thống đang rất bận. Đã thử tất cả các models nhưng đều thất bại:\\n{error_details}\\n\\nVui lòng đợi 1 phút và thử lại.")
                
            except Exception as e:
                st.error(f"Đã có lỗi xảy ra: {e}")
