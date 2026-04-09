import streamlit as st
import sqlite3
import os
import tempfile
import requests
import json
from PIL import Image
import google.generativeai as genai
import fal_client

# ====================== CẤU HÌNH ======================
FAL_API_KEY = st.secrets.get("FAL_API_KEY")
GENAI_API_KEY = st.secrets.get("GENAI_API_KEY")

if not FAL_API_KEY:
    st.error("❌ Chưa thiết lập FAL_API_KEY trong Streamlit Secrets")
    st.stop()

genai.configure(api_key=GENAI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="VibeCheck: AI Stylist", layout="centered")

# ====================== HÀM ======================
def get_recommendations(gender, style, occasion, body_shape):
    try:
        conn = sqlite3.connect('fashion_store.db')
        cursor = conn.cursor()
        query = """
            SELECT name, price, image_url, id 
            FROM products
            WHERE gender = ? AND style = ? AND occasion = ?
              AND (body_shape = ? OR body_shape = 'All')
            LIMIT 8
        """
        cursor.execute(query, (gender, style, occasion, body_shape))
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Lỗi database: {e}")
        return []


def analyze_user_all_in_one(uploaded_file, gender, occasion):
    img = Image.open(uploaded_file)
    prompt = f"""Bạn là chuyên gia thời trang. Phân tích ảnh người (giới tính: {gender}) cho dịp {occasion}.
Chỉ chọn trong danh sách:
- Body Shape: Hourglass, Triangle, Inverted Triangle, Rectangle, Ovals
- Style: Minimalism, Y2K, Sporty, Vintage, Elegant

Trả về JSON: {{"body_shape": "...", "suggested_style": "...", "reason": "..."}}"""

    try:
        response = gemini_model.generate_content(
            [prompt, img],
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text.strip())
    except Exception as e:
        st.error(f"Lỗi phân tích: {e}")
        return None


def run_cat_vton(person_local_path: str, garment_url: str):
    try:
        client = fal_client.SyncClient(api_key=FAL_API_KEY)
        human_url = client.upload_file(person_local_path)

        result = client.subscribe(
            "fal-ai/cat-vton",
            arguments={
                "human_image_url": human_url,
                "garment_image_url": garment_url,
                "cloth_type": "upper",
                "num_inference_steps": 25,
                "guidance_scale": 7.0,
            },
            with_logs=True
        )
        return result["images"][0]["url"] if "images" in result else None

    except Exception as e:
        st.error(f"Lỗi CAT-VTON: {str(e)}")
        return None


# ====================== GIAO DIỆN ======================
st.title("👗 VibeCheck - CAT-VTON")

with st.sidebar:
    st.header("Thông tin của bạn")
    gender = st.radio("Giới tính", ["Nam", "Nữ"], horizontal=True)
    occasion_pref = st.selectbox("Dịp sử dụng", ["Đi làm", "Đi tiệc", "Đi chơi", "Đi hẹn hò"])
    user_img = st.file_uploader("Tải lên ảnh toàn thân", type=['jpg', 'jpeg', 'png'])

if user_img:
    if st.button("✨ Phân tích & Gợi ý", type="primary"):
        with st.spinner("Đang phân tích..."):
            analysis = analyze_user_all_in_one(user_img, gender, occasion_pref)
            if analysis:
                st.session_state['analysis'] = analysis
                st.session_state['product_recs'] = get_recommendations(
                    gender, analysis.get('suggested_style'), occasion_pref, analysis.get('body_shape')
                )
                st.rerun()

    if 'analysis' in st.session_state:
        ans = st.session_state['analysis']
        st.success(f"**Phong cách:** {ans.get('suggested_style')}")
        st.info(f"**Dáng người:** {ans.get('body_shape')}\n\n{ans.get('reason')}")

        if st.session_state.get('product_recs'):
            st.divider()
            st.subheader("Sản phẩm gợi ý")
            for item in st.session_state['product_recs']:
                name, price, image_url, item_id = item
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(image_url, width=130)
                with col2:
                    st.write(f"**{name}**")
                    st.write(f"Giá: **{price}** VNĐ")
                    if st.button("🪞 Thử đồ CAT-VTON", key=f"try_{item_id}"):
                        st.session_state['tryon_item'] = item
                        st.session_state['tryon_status'] = 'processing'
                        st.rerun()

# ====================== THỬ ĐỒ ẢO ======================
if st.session_state.get('tryon_status') == 'processing' and 'tryon_item' in st.session_state:
    item = st.session_state['tryon_item']
    st.divider()
    st.subheader(f"🪞 Đang thử đồ: {item[0]}")

    with st.spinner("Đang upload ảnh và xử lý thử đồ (10–18 giây)..."):
        # Lưu ảnh tạm
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(user_img.getvalue())
            person_local_path = tmp.name

        garment_url = item[2]
        result_url = run_cat_vton(person_local_path, garment_url)

        # Cleanup
        if os.path.exists(person_local_path):
            os.unlink(person_local_path)

        if result_url:
            st.session_state['tryon_result'] = result_url
            st.session_state['tryon_status'] = 'success'
        else:
            st.session_state['tryon_status'] = 'error'
        st.rerun()

if st.session_state.get('tryon_status') == 'success':
    st.image(st.session_state['tryon_result'], use_column_width=True)
    st.success("✅ Thử đồ thành công!")
    if st.button("Thử sản phẩm khác"):
        for k in ['tryon_item', 'tryon_status', 'tryon_result']:
            st.session_state.pop(k, None)
        st.rerun()

if st.session_state.get('tryon_status') == 'error':
    st.error("Không tạo được ảnh thử đồ. Vui lòng thử lại.")
    if st.button("🔄 Thử lại"):
        st.session_state['tryon_status'] = 'processing'
        st.rerun()
