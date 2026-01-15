import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
import json
from datetime import datetime

# 1. CẤU HÌNH TRANG WEB
st.set_page_config(page_title="AI Advisor - Tư Vấn Lộ Trình Học", page_icon="🎓")

st.title("🎓 AI Advisor - Định Hướng Lộ Trình Học Tập")
st.write("Chào bạn! Tôi sẽ giúp bạn vạch ra lộ trình học tập phù hợp với mục tiêu của bạn.")

# 2. HÀM TIỆN ÍCH

def load_ai_config():
    """Đọc cấu hình AI từ file markdown"""
    config_path = os.path.join(os.path.dirname(__file__), 'ai_config.md')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        Vai trò: Bạn là một chuyên gia tư vấn giáo dục tận tâm, định hướng lộ trình học.
        
        Nhiệm vụ:
        1. Lắng nghe và hiểu mục tiêu sâu xa của người học.
        2. Vẽ lộ trình học tập chi tiết theo từng giai đoạn.
        3. Đề xuất 1-2 khóa học phù hợp từ database một cách tự nhiên.
        4. Sử dụng Rating, Students, Description để đánh giá và giới thiệu khóa học.
        5. Đưa link affiliate khéo léo, không lộ liễu.
        """

def prepare_course_data(df):
    """Chuẩn bị dữ liệu khóa học với ranking"""
    # Tạo bản sao để không ảnh hưởng df gốc
    df_ranked = df.copy()
    
    # Tính điểm ưu tiên cho mỗi khóa học
    # Dựa trên: Rating (cao nhất), Students (nhiều nhất), Price (hợp lý)
    try:
        # Chuẩn hóa các cột số
        df_ranked['Rating'] = pd.to_numeric(df_ranked.get('Rating', 0), errors='coerce').fillna(0)
        df_ranked['Students'] = pd.to_numeric(df_ranked.get('Students', 0), errors='coerce').fillna(0)
        df_ranked['Price'] = pd.to_numeric(df_ranked.get('Price', 0), errors='coerce').fillna(0)
        
        # Tính Priority Score
        df_ranked['Priority_Score'] = (
            df_ranked['Rating'] * 20 +
            df_ranked['Students'].apply(lambda x: min(x / 100, 50)) +
            df_ranked['Price'].apply(lambda x: max(0, 100 - x / 10000))
        )
        
        # Sắp xếp theo Priority Score giảm dần
        df_ranked = df_ranked.sort_values('Priority_Score', ascending=False)
    except Exception:
        pass  # Giữ nguyên nếu có lỗi
    
    return df_ranked

def log_conversation(user_query, ai_response, recommended_courses=None):
    """Ghi log cuộc hội thoại để phân tích sau"""
    log_path = os.path.join(os.path.dirname(__file__), 'conversation_logs.json')
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_query": user_query,
        "ai_response_length": len(ai_response),
        "recommended_courses": recommended_courses or [],
        "session_id": st.session_state.get('session_id', 'unknown')
    }
    
    try:
        # Đọc logs hiện có
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []
        
        # Thêm log mới
        logs.append(log_entry)
        
        # Giới hạn 1000 logs gần nhất
        logs = logs[-1000:]
        
        # Ghi lại
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # Không làm gián đoạn app nếu log fail

def format_course_data_for_ai(df):
    """Format data cho AI dễ đọc hơn"""
    formatted_rows = []
    
    for _, row in df.iterrows():
        course_info = []
        
        # Các trường quan trọng
        if 'Course Name' in df.columns:
            course_info.append(f"📚 Tên: {row.get('Course Name', 'N/A')}")
        if 'Category' in df.columns:
            course_info.append(f"   Thể loại: {row.get('Category', 'N/A')}")
        if 'Teacher' in df.columns:
            course_info.append(f"   Giảng viên: {row.get('Teacher', 'N/A')}")
        if 'Description' in df.columns:
            desc = str(row.get('Description', ''))[:500]  # Giới hạn 500 ký tự
            course_info.append(f"   Mô tả: {desc}")
        if 'Rating' in df.columns:
            course_info.append(f"   Đánh giá: {row.get('Rating', 'N/A')}/5")
        if 'Students' in df.columns:
            course_info.append(f"   Học viên: {row.get('Students', 'N/A')} người")
        if 'Price' in df.columns:
            course_info.append(f"   Giá: {row.get('Price', 'N/A')} VNĐ")
        if 'Affiliate Link' in df.columns:
            course_info.append(f"   Link: {row.get('Affiliate Link', 'N/A')}")
        
        formatted_rows.append("\n".join(course_info))
    
    return "\n\n---\n\n".join(formatted_rows)

# 3. KHỞI TẠO SESSION STATE
if 'session_id' not in st.session_state:
    st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "model", "content": """**Chào bạn! 👋**

Tôi là AI Advisor, sẽ giúp bạn vạch ra lộ trình học tập phù hợp.

Để tư vấn tốt nhất, hãy chia sẻ:
- **Mục tiêu** bạn muốn đạt được là gì?
- Bạn đã có **kinh nghiệm/kiến thức** gì chưa?
- Bạn có thể dành **bao nhiêu thời gian** mỗi tuần để học?

*(Ví dụ: "Tôi muốn học Marketing để tự bán hàng online, chưa có kinh nghiệm gì")*"""}
    ]

if 'feedback_given' not in st.session_state:
    st.session_state.feedback_given = set()

# 4. KẾT NỐI API & DỮ LIỆU
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        st.error("Chưa cấu hình API Key trong Secrets. Vui lòng vào Cài đặt (Advanced Settings) trên Streamlit Cloud và thêm `GEMINI_API_KEY`.")
        st.stop()
    
    csv_url = "https://docs.google.com/spreadsheets/d/1GM4ueLMAb4A4VfzQc4Q8fnfCFLclMIjJUvFnqi__kac/export?format=csv"
    df = pd.read_csv(csv_url)
    
    # Chuẩn bị dữ liệu với ranking
    df = prepare_course_data(df)
    
except Exception as e:
    st.error(f"Lỗi kết nối: {e}. \n\n**Lưu ý quan trọng:**\n1. Kiểm tra xem bạn đã 'Publish to Web' file Google Sheet chưa?\n2. Kiểm tra API Key có đúng không?")
    st.stop()

# 5. HIỂN THỊ LỊCH SỬ CHAT
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Thêm feedback button cho mỗi response của AI
        if message["role"] == "model" and idx > 0:  # Bỏ qua tin nhắn chào mừng
            feedback_key = f"feedback_{idx}"
            if feedback_key not in st.session_state.feedback_given:
                col1, col2, col3 = st.columns([1, 1, 10])
                with col1:
                    if st.button("👍", key=f"helpful_{idx}"):
                        st.session_state.feedback_given.add(feedback_key)
                        st.toast("Cảm ơn phản hồi của bạn! 🎉")
                with col2:
                    if st.button("👎", key=f"not_helpful_{idx}"):
                        st.session_state.feedback_given.add(feedback_key)
                        st.toast("Cảm ơn! Tôi sẽ cố gắng cải thiện 💪")

# 6. XỬ LÝ KHI NGƯỜI DÙNG NHẬP LIỆU
if prompt := st.chat_input("Chia sẻ mục tiêu học tập của bạn..."):
    # Hiện câu hỏi của người dùng
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gửi yêu cầu cho AI
    with st.chat_message("model"):
        with st.spinner("Đang phân tích và vạch lộ trình cho bạn..."):
            try:
                # Đọc cấu hình AI
                ai_persona = load_ai_config()
                
                # Format dữ liệu khóa học cho AI
                data_text = format_course_data_for_ai(df)
                
                # Lấy conversation history (tối đa 6 tin nhắn gần nhất)
                conversation_history = ""
                recent_messages = st.session_state.messages[-6:]
                for msg in recent_messages[:-1]:  # Bỏ tin nhắn hiện tại
                    role = "Người dùng" if msg["role"] == "user" else "AI"
                    conversation_history += f"{role}: {msg['content'][:300]}...\n\n"
                
                # Câu lệnh điều khiển AI (System Prompt)
                full_prompt = f"""
{ai_persona}

---

## LỊCH SỬ HỘI THOẠI (để hiểu context)
{conversation_history if conversation_history else "(Đây là tin nhắn đầu tiên)"}

---

## DỮ LIỆU KHÓA HỌC CÓ SẴN
(Đã sắp xếp theo độ ưu tiên: Rating cao > Nhiều học viên > Giá hợp lý)
(Chỉ được giới thiệu khóa học trong danh sách này)

{data_text}

---

## YÊU CẦU CỦA NGƯỜI DÙNG
"{prompt}"

---

## HƯỚNG DẪN TRẢ LỜI
1. Nếu người dùng chưa rõ mục tiêu → Hỏi thêm để hiểu rõ
2. Nếu đã hiểu mục tiêu → Vẽ lộ trình học tập theo giai đoạn
3. Trong lộ trình, giới thiệu 1-2 khóa học phù hợp nhất một cách TỰ NHIÊN
4. ĐỌC KỸ Description để mô tả nội dung khóa học cho người dùng
5. Dùng Rating, Students, Teacher để tạo niềm tin
6. Đưa link affiliate như một phần của thông tin, KHÔNG hối thúc click
7. KHÔNG BAO GIỜ đề cập "affiliate", "commission", "hoa hồng"

Trả lời bằng tiếng Việt, giọng thân thiện như một mentor.
"""
                
                # Danh sách các model để thử
                models_to_try = [
                    'gemini-2.0-flash',
                    'gemini-2.0-flash-lite',
                    'gemini-2.0-flash-exp',
                    'gemini-flash-latest',
                ]
                
                response = None
                error_log = []
                
                for model_name in models_to_try:
                    try:
                        import time
                        time.sleep(1)
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(full_prompt)
                        break
                    except Exception as e:
                        error_log.append(f"{model_name}: {str(e)}")
                        continue
                
                if response:
                    response_text = response.text
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "model", "content": response_text})
                    
                    # Log conversation
                    log_conversation(prompt, response_text)
                    
                    # Feedback buttons
                    col1, col2, col3 = st.columns([1, 1, 10])
                    with col1:
                        if st.button("👍", key="helpful_current"):
                            st.toast("Cảm ơn phản hồi của bạn! 🎉")
                    with col2:
                        if st.button("👎", key="not_helpful_current"):
                            st.toast("Cảm ơn! Tôi sẽ cố gắng cải thiện 💪")
                else:
                    error_details = "\n".join(error_log)
                    st.error(f"Hệ thống đang rất bận. Đã thử tất cả các models nhưng đều thất bại:\n{error_details}\n\nVui lòng đợi 1 phút và thử lại.")
                
            except Exception as e:
                st.error(f"Đã có lỗi xảy ra: {e}")

# 7. SIDEBAR - THÔNG TIN BỔ SUNG
with st.sidebar:
    st.header("📊 Thông tin")
    st.write(f"**Số khóa học:** {len(df)}")
    
    # Hiển thị top categories
    if 'Category' in df.columns:
        st.write("**Top thể loại:**")
        top_categories = df['Category'].value_counts().head(5)
        for cat, count in top_categories.items():
            st.write(f"• {cat}: {count} khóa")
    
    st.divider()
    
    # Clear chat button
    if st.button("🗑️ Xóa lịch sử chat"):
        st.session_state.messages = [
            {"role": "model", "content": """**Chào bạn! 👋**

Tôi là AI Advisor, sẽ giúp bạn vạch ra lộ trình học tập phù hợp.

Để tư vấn tốt nhất, hãy chia sẻ:
- **Mục tiêu** bạn muốn đạt được là gì?
- Bạn đã có **kinh nghiệm/kiến thức** gì chưa?
- Bạn có thể dành **bao nhiêu thời gian** mỗi tuần để học?"""}
        ]
        st.session_state.feedback_given = set()
        st.rerun()
    
    st.divider()
    st.caption("v2.0 - AI Advisor Mode")
