import streamlit as st
import sqlite3
import os
import tempfile
import json
from PIL import Image
import google.generativeai as genai
import fal_client

# ====================== CẤU HÌNH ======================
FAL_API_KEY = st.secrets.get("FAL_API_KEY")
GENAI_API_KEY = st.secrets.get("GENAI_API_KEY")

if not FAL_API_KEY or not GENAI_API_KEY:
    st.error("❌ Thiếu API Key trong Streamlit Secrets!")
    st.stop()

# Thiết lập API cho Gemini
genai.configure(api_key=GENAI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash')

# Thiết lập môi trường cho Fal
os.environ["FAL_KEY"] = FAL_API_KEY

st.set_page_config(page_title="VibeCheck: AI Stylist", layout="centered")

# ====================== HÀM XỬ LÝ ======================

def get_recommendations(gender, style, occasion, body_shape):
    try:
        conn = sqlite3.connect('fashion_store.db')
        cursor = conn.cursor()
        # Query thông minh: Ưu tiên Style > Occasion > Body Shape
        query = """
            SELECT name, price, image_url, id FROM products
            WHERE gender = ? 
            AND (style = ? OR style = 'All')
            AND (body_shape = ? OR body_shape = 'All')
            ORDER BY CASE WHEN occasion = ? THEN 1 ELSE 2 END
            LIMIT 8
        """
        cursor.execute(query, (gender, style, body_shape, occasion))
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        return []

def analyze_user_all_in_one(uploaded_file, gender, occasion):
    img = Image.open(uploaded_file)
    prompt = f"""Bạn là chuyên gia thời trang. Phân tích ảnh người ({gender}) cho dịp {occasion}.
    Trả về JSON: {{"body_shape": "...", "suggested_style": "...", "reason": "..."}}
    Danh sách Body Shape: Hourglass, Triangle, Inverted Triangle, Rectangle, Ovals.
    Danh sách Style: Minimalism, Y2K, Sporty, Vintage, Elegant."""

    try:
        response = gemini_model.generate_content(
            [prompt, img],
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text.strip())
    except Exception:
        return None

# ====================== GIAO DIỆN CHÍNH ======================
st.title("👗 VibeCheck - AI Personal Stylist")

with st.sidebar:
    st.header("Thông tin của bạn")
    gender = st.radio("Giới tính", ["Nam", "Nữ"], horizontal=True)
    occasion_pref = st.selectbox("Dịp sử dụng", ["Đi làm", "Đi tiệc", "Đi chơi", "Đi hẹn hò"])
    user_img = st.file_uploader("Tải lên ảnh toàn thân", type=['jpg', 'jpeg', 'png'])

if user_img:
    if st.button("✨ Phân tích & Gợi ý", type="primary"):
        with st.spinner("Đang phân tích vóc dáng..."):
            analysis = analyze_user_all_in_one(user_img, gender, occasion_pref)
            if analysis:
                st.session_state['analysis'] = analysis
                st.session_state['product_recs'] = get_recommendations(
                    gender, analysis.get('suggested_style'), occasion_pref, analysis.get('body_shape')
                )
                st.rerun()

    # Hiển thị kết quả phân tích
    if 'analysis' in st.session_state:
        ans = st.session_state['analysis']
        st.success(f"**Phong cách gợi ý:** {ans.get('suggested_style')}")
        st.info(f"**Dáng người:** {ans.get('body_shape')} - {ans.get('reason')}")

        if st.session_state.get('product_recs'):
            st.divider()
            st.subheader("👕 Sản phẩm dành riêng cho bạn")
            for item in st.session_state['product_recs']:
                name, price, image_url, item_id = item
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.image(image_url, width=130)
                with c2:
                    st.write(f"**{name}**")
                    st.write(f"Giá: {price} VNĐ")
                    if st.button("🪞 Thử đồ ngay", key=f"btn_{item_id}"):
                        st.session_state['tryon_item'] = item
                        st.session_state['tryon_status'] = 'processing'
                        st.rerun()

# ====================== LOGIC PHÒNG THỬ ĐỒ (CAT-VTON) ======================

if 'tryon_item' in st.session_state:
    item = st.session_state['tryon_item']
    
    if st.session_state.get('tryon_status') == 'processing':
        st.divider()
        with st.spinner(f"🤖 AI đang mặc thử {item[0]} cho bạn..."):
            try:
                # 1. Xử lý ảnh tạm
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(user_img.getvalue())
                    person_path = tmp.name

                # 2. Gọi Fal.ai CAT-VTON
                # Chú ý: .upload_file và .subscribe là cách dùng chuẩn của fal-client mới
                human_url = fal_client.upload_file(person_path)
                
                result = fal_client.subscribe(
                    "fal-ai/cat-vton",
                    arguments={
                        "human_image_url": human_url,
                        "garment_image_url": item[2],
                        "cloth_type": "upper",  # Có thể tùy chỉnh dựa vào Database
                    }
                )

                os.unlink(person_path) # Xóa file tạm

                if result and "image" in result:
                    st.session_state['tryon_result'] = result["image"]["url"]
                    st.session_state['tryon_status'] = 'success'
                else:
                    st.session_state['tryon_status'] = 'error'
            except Exception as e:
                st.error(f"Lỗi AI: {e}")
                st.session_state['tryon_status'] = 'error'
            st.rerun()

    if st.session_state.get('tryon_status') == 'success':
        st.divider()
        st.subheader("✨ Gương soi ảo (VibeCheck Result)")
        st.image(st.session_state['tryon_result'], use_container_width=True)
        
        if st.button("❌ Thoát phòng thử đồ"):
            for key in ['tryon_item', 'tryon_status', 'tryon_result']:
                st.session_state.pop(key, None)
            st.rerun()
