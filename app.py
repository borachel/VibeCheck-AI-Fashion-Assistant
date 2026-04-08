import streamlit as st
import sqlite3
import google.generativeai as genai
from PIL import Image
import json
import os
import tempfile

# --- CẤU HÌNH ---
GENAI_API_KEY = st.secrets.get("GENAI_API_KEY") 
genai.configure(api_key=GENAI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="VibeCheck: AI Stylist", layout="centered")

os.environ["GOOGLE_CLOUD_PROJECT"] = "project-a8e13965-257b-422e-afa"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# --- HÀM XỬ LÝ ---

def get_recommendations(gender: str, style: str, occasion: str, body_shape: str):
    """Lấy sản phẩm gợi ý từ SQLite"""
    try:
        conn = sqlite3.connect('fashion_store.db')
        cursor = conn.cursor()
        
        query = """
            SELECT name, price, image_url, id 
            FROM products
            WHERE gender = ? 
              AND style = ? 
              AND occasion = ?
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
    """Phân tích ảnh bằng Gemini 2.5 Flash - trả về JSON ổn định"""
    img = Image.open(uploaded_file)
    
    prompt = f"""Bạn là chuyên gia tư vấn thời trang cao cấp.
Phân tích ảnh người (giới tính: {gender}) phù hợp với dịp: {occasion}.

Chỉ được chọn giá trị trong danh sách sau:
- Body Shape: Hourglass, Triangle, Inverted Triangle, Rectangle, Ovals
- Style: Minimalism, Y2K, Sporty, Vintage, Elegant

Trả về **chính xác** định dạng JSON sau, không thêm bất kỳ text nào khác:

{{
  "body_shape": "Tên shape",
  "suggested_style": "Tên style",
  "reason": "Giải thích ngắn gọn bằng tiếng Việt (1-2 câu)"
}}
"""

    try:
        response = gemini_model.generate_content(
            [prompt, img],
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text.strip())
    except Exception as e:
        st.error(f"Lỗi khi phân tích ảnh: {e}")
        return None

import google.auth
from google import genai

try:
    credentials, project = google.auth.default()
    print(f"✅ Project: {project}")
    print(f"✅ Credentials: {type(credentials)}")
    
    client = genai.Client()
    print("✅ Client khởi tạo thành công")
except Exception as e:
    print(f"❌ Lỗi Authentication: {e}")
def run_vertex_vto(person_img_path: str, garment_img_path: str):
    """Virtual Try-On sử dụng Vertex AI virtual-try-on-001"""
    try:
        from google import genai
        from google.genai.types import (
            RecontextImageSource, 
            ProductImage, 
            Image as GenaiImage
        )

        client = genai.Client()

        response = client.models.recontext_image(
            model="virtual-try-on-001",
            source=RecontextImageSource(
                person_image=GenaiImage.from_file(location=person_img_path),
                product_images=[
                    ProductImage(
                        product_image=GenaiImage.from_file(location=garment_img_path)
                    )
                ],
            ),
        )

        output_file = "vto_result.png"
        response.generated_images[0].image.save(output_file)
        return output_file

    except Exception as e:
        st.error(f"Lỗi Vertex AI Virtual Try-On: {str(e)}")
        return None

# --- GIAO DIỆN ---

st.title("👗 VibeCheck: Scan your style, find your fit")

# Sidebar: 
with st.sidebar:
    st.header("Thông tin của bạn")
    gender = st.radio("Giới tính", ["Nam", "Nữ"], horizontal=True)
    occasion_pref = st.selectbox("Dịp sử dụng", ["Đi làm", "Đi tiệc", "Đi chơi", "Đi hẹn hò"])
    user_img = st.file_uploader("Tải lên ảnh của bạn", type=['jpg', 'jpeg', 'png'])

if user_img:
    if st.button("✨ Phân tích & Gợi ý phong cách", type="primary"):
        with st.spinner("AI đang phân tích vóc dáng và phong cách phù hợp..."):
            analysis = analyze_user_all_in_one(user_img, gender, occasion_pref)
            
            if analysis:
                st.session_state['analysis'] = analysis
                st.session_state['product_recs'] = get_recommendations(
                    gender, 
                    analysis['suggested_style'], 
                    occasion_pref, 
                    analysis['body_shape']
                )
                st.rerun()
# Hiển thị kết quả phân tích
    if 'analysis' in st.session_state:
        ans = st.session_state['analysis']
        st.success(f"Phong cách gợi ý: **{ans['suggested_style']}**")
        st.info(f"Dáng người: **{ans['body_shape']}** \n\n {ans['reason']}")

        # Hiển thị sản phẩm: Name, Price, Image
        # Hiển thị sản phẩm gợi ý
        if st.session_state.get('product_recs'):
            st.divider()
            st.subheader("👕 Sản phẩm gợi ý dành cho bạn")

            for item in st.session_state['product_recs']:
                name, price, image_url, item_id = item   # Giải nén rõ ràng
                
                col1, col2 = st.columns([1, 2])          # Đổi tên biến cho rõ
                
                with col1:
                    st.image(image_url, width=140)
                
                with col2:
                    st.write(f"**{name}**")
                    st.write(f"**Giá:** {price} VNĐ")
                    
                    if st.button("🪞 Thử sản phẩm", key=f"try_{item_id}"):
                        st.session_state['tryon_item'] = item
                        st.session_state['tryon_status'] = 'processing'
                        st.rerun()

# 3. KHU VỰC THỬ ĐỒ ẢO (Xử lý Case Success/Error)
if 'tryon_item' in st.session_state:
    item = st.session_state['tryon_item']
    st.divider()
    st.subheader(f"🪞 Phòng thử đồ: {item[0]}")

    if st.session_state.get('tryon_status') == 'processing':
        with st.spinner("Đang xử lý thử sản phẩm ảo (có thể mất 10–20 giây)..."):
            # Lưu ảnh người dùng vào file tạm
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(user_img.getvalue())
                person_path = tmp.name

            # Lưu ảnh sản phẩm từ URL (hoặc từ DB)
            garment_url = item[2]
            # Nếu garment_url là link online, cần tải về trước
            import requests
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_garment:
                response = requests.get(garment_url)
                tmp_garment.write(response.content)
                garment_path = tmp_garment.name

            result_path = run_vertex_vto(person_path, garment_path)

            # Cleanup file tạm
            for path in [person_path, garment_path]:
                if os.path.exists(path):
                    os.unlink(path)

            if result_path and os.path.exists(result_path):
                st.session_state['tryon_result'] = result_path
                st.session_state['tryon_status'] = 'success'
            else:
                st.session_state['tryon_status'] = 'error'
            st.rerun()

    # Thành công
    if st.session_state.get('tryon_status') == 'success':
        st.image(st.session_state['tryon_result'], use_column_width=True, caption="Kết quả thử sản phẩm")
        st.success("Bạn thấy bộ này thế nào?")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🛒 Thêm vào giỏ hàng"):
                st.toast(f"Đã thêm **{item[0]}** vào giỏ hàng!", icon="✅")
        with col2:
            if st.button("Thử sản phẩm khác"):
                if 'tryon_item' in st.session_state:
                    del st.session_state['tryon_item']
                if 'tryon_status' in st.session_state:
                    del st.session_state['tryon_status']
                st.rerun()

    # Lỗi
    if st.session_state.get('tryon_status') == 'error':
        st.error("Không thể tạo hình thử đồ. Hệ thống có thể đang quá tải quota hoặc lỗi tạm thời.")
        if st.button("🔄 Thử lại"):
            st.session_state['tryon_status'] = 'processing'
            st.rerun()
