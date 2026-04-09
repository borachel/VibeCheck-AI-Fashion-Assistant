import streamlit as st
import sqlite3
import os
import tempfile
import requests
import json
from PIL import Image
import fal_client

# ====================== CẤU HÌNH ======================
st.set_page_config(page_title="VibeCheck: AI Stylist", layout="centered")

# Lấy API Key từ Streamlit Secrets (khuyến nghị)
FAL_API_KEY = st.secrets.get("FAL_API_KEY")
if not FAL_API_KEY:
    st.error("Vui lòng thêm FAL_API_KEY vào Streamlit Secrets")
    st.stop()

# ====================== HÀM XỬ LÝ ======================

def get_recommendations(gender: str, style: str, occasion: str, body_shape: str):
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
        data = cursor.fetchall()
        conn.close()
        return data
    except Exception as e:
        st.error(f"Lỗi database: {e}")
        return []


def analyze_user_all_in_one(uploaded_file, gender: str, occasion: str):
    """Phân tích ảnh bằng Gemini"""
    img = Image.open(uploaded_file)
    prompt = f"""Bạn là chuyên gia thời trang. Phân tích ảnh người (giới tính: {gender}) phù hợp dịp: {occasion}.
Chỉ chọn trong danh sách:
Body Shape: Hourglass, Triangle, Inverted Triangle, Rectangle, Ovals
Style: Minimalism, Y2K, Sporty, Vintage, Elegant

Trả về JSON chính xác:
{{"body_shape": "...", "suggested_style": "...", "reason": "Giải thích ngắn"}}"""

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(
            [prompt, img],
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text.strip())
    except Exception as e:
        st.error(f"Lỗi phân tích ảnh: {e}")
        return None


def run_cat_vton(person_img_path: str, garment_img_url: str, cloth_type: str = "upper"):
    """Chạy CAT-VTON trên Fal.ai"""
    try:
        client = fal_client.SyncClient(api_key=FAL_API_KEY)

        result = client.subscribe(
            "fal-ai/cat-vton",
            arguments={
                "human_image_url": person_img_path,      # có thể là URL hoặc base64
                "garment_image_url": garment_img_url,
                "cloth_type": cloth_type,                # "upper" hoặc "lower"
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
            },
            with_logs=True
        )

        # Result thường trả về list ảnh, lấy ảnh đầu tiên
        if isinstance(result, dict) and "images" in result:
            return result["images"][0]["url"]
        elif isinstance(result, list) and len(result) > 0:
            return result[0]["url"]
        else:
            return result  # fallback

    except Exception as e:
        st.error(f"Lỗi CAT-VTON: {str(e)}")
        print(f"Debug CAT-VTON: {e}")
        return None


# ====================== GIAO DIỆN ======================
st.title("👗 VibeCheck: AI Stylist")

with st.sidebar:
    st.header("Thông tin của bạn")
    gender = st.radio("Giới tính", ["Nam", "Nữ"], horizontal=True)
    occasion_pref = st.selectbox("Dịp sử dụng", ["Đi làm", "Đi tiệc", "Đi chơi", "Đi hẹn hò"])
    user_img = st.file_uploader("Tải lên ảnh toàn thân", type=['jpg', 'jpeg', 'png'])

if user_img:
    if st.button("✨ Phân tích & Gợi ý phong cách", type="primary"):
        with st.spinner("AI đang phân tích..."):
            analysis = analyze_user_all_in_one(user_img, gender, occasion_pref)
            if analysis:
                st.session_state['analysis'] = analysis
                st.session_state['product_recs'] = get_recommendations(
                    gender, analysis.get('suggested_style'), occasion_pref, analysis.get('body_shape')
                )
                st.rerun()

    if 'analysis' in st.session_state:
        ans = st.session_state['analysis']
        st.success(f"**Phong cách gợi ý:** {ans.get('suggested_style')}")
        st.info(f"**Dáng người:** {ans.get('body_shape')}\n\n{ans.get('reason')}")

        if st.session_state.get('product_recs'):
            st.divider()
            st.subheader("👕 Sản phẩm gợi ý")
            for item in st.session_state['product_recs']:
                name, price, image_url, item_id = item
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(image_url, width=140)
                with col2:
                    st.write(f"**{name}**")
                    st.write(f"**Giá:** {price} VNĐ")
                    if st.button("🪞 Thử đồ ảo", key=f"try_{item_id}"):
                        st.session_state['tryon_item'] = item
                        st.session_state['tryon_status'] = 'processing'
                        st.rerun()

# ====================== PHÒNG THỬ ĐỒ ẢO (CAT-VTON) ======================
if st.session_state.get('tryon_status') == 'processing' and 'tryon_item' in st.session_state:
    item = st.session_state['tryon_item']
    st.divider()
    st.subheader(f"🪞 Đang thử đồ: {item[0]}")

    with st.spinner("Đang xử lý thử đồ ảo (thường 8–15 giây)..."):
        # Lưu ảnh người dùng thành file tạm và upload lên URL tạm (hoặc dùng base64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(user_img.getvalue())
            person_path = tmp.name

        # Tải garment từ URL trong DB
        garment_url = item[2]

        result_url = run_cat_vton(person_path, garment_url, cloth_type="upper") 

        # Cleanup
        if os.path.exists(person_path):
            os.unlink(person_path)

        if result_url:
            st.session_state['tryon_result'] = result_url
            st.session_state['tryon_status'] = 'success'
        else:
            st.session_state['tryon_status'] = 'error'
        st.rerun()

# Hiển thị kết quả thành công
if st.session_state.get('tryon_status') == 'success':
    st.image(st.session_state['tryon_result'], use_column_width=True, caption="Kết quả thử đồ")
    st.success("Bạn thấy bộ này thế nào?")
    if st.button("Thử sản phẩm khác"):
        for key in ['tryon_item', 'tryon_status', 'tryon_result']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Lỗi
if st.session_state.get('tryon_status') == 'error':
    st.error("Không thể tạo ảnh thử đồ. Vui lòng thử lại sau.")
    if st.button("🔄 Thử lại"):
        st.session_state['tryon_status'] = 'processing'
        st.rerun()
