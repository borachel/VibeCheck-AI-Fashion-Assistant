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

st.set_page_config(page_title="AI Stylist MVP", layout="centered")

# --- HÀM XỬ LÝ ---

def get_recommendations(gender, style, occasion, body_shape):
    conn = sqlite3.connect('fashion_store.db')
    cursor = conn.cursor()
    # Truy vấn lấy thêm trường Price
    query = """
        SELECT name, price, image_url, id FROM products 
        WHERE gender = ? AND style = ? AND occasion = ?
        AND (body_shape = ? OR body_shape = 'All')
    """
    cursor.execute(query, (gender, style, occasion, body_shape))
    data = cursor.fetchall()
    conn.close()
    return data

def analyze_user_all_in_one(uploaded_file, gender, occasion):
    img = Image.open(uploaded_file)
    # Define trước các body_shape cho AI
    available_shapes = "Hourglass, Triangle, Inverted Triangle, Rectangle, Ovals"
    available_styles = "Minimalism, Y2K, Sporty, Vintage, Elegant"
    
    prompt = f"""
    Bạn là chuyên gia thời trang. Phân tích ảnh người (giới tính {gender}) dành cho dịp {occasion}.
    Chỉ được chọn Body Shape trong danh sách: [{available_shapes}].
    Chỉ được chọn Style trong danh sách: [{available_styles}].
    
    Trả về JSON nguyên bản:
    {{
      "body_shape": "Tên shape",
      "suggested_style": "Tên style",
      "reason": "Giải thích ngắn gọn"
    }}
    """
    response = gemini_model.generate_content([prompt, img])
    clean_json = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)

import os
from google import genai
from google.genai.types import RecontextImageSource, ProductImage, Image

# 1. Cấu hình:
os.environ["GOOGLE_CLOUD_PROJECT"] = "project-a8e13965-257b-422e-afa"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

def run_google_vto_2026(person_img_path, garment_img_path):
    try:
        # Khởi tạo Client theo chuẩn mới
        client = genai.Client()
        output_file = "vto_result_2026.png"

        # Gọi mô hình virtual-try-on-001
        response = client.models.recontext_image(
            model="virtual-try-on-001",
            source=RecontextImageSource(
                # Ảnh người dùng (từ file tạm)
                person_image=Image.from_file(location=person_img_path),
                product_images=[
                    # Ảnh sản phẩm (từ link hoặc file trong database)
                    ProductImage(product_image=Image.from_file(location=garment_img_path))
                ],
            ),
        )

        # Lưu ảnh kết quả
        response.generated_images[0].image.save(output_file)
        return output_file

    except Exception as e:
        print(f"Lỗi VTO 2026: {e}")
        return None

# --- GIAO DIỆN ---

st.title("👗 VibeCheck: Scan your style, find your fit")

# Sidebar: 
with st.sidebar:
    st.header("Thiết lập")
    gender = st.radio("Giới tính", ["Nam", "Nữ"])
    occasion_pref = st.selectbox("Dịp sử dụng", ["Đi làm", "Đi tiệc", "Đi chơi", "Đi hẹn hò"])
    user_img = st.file_uploader("Tải lên ảnh của bạn", type=['jpg', 'jpeg', 'png'])

if user_img:
    if st.button("✨ Phân tích & Gợi ý phong cách"):
        with st.spinner("AI đang làm việc..."):
            ans = analyze_user_all_in_one(user_img, gender, occasion_pref)
            st.session_state['analysis'] = ans
            st.session_state['product_recs'] = get_recommendations(
                gender, ans['suggested_style'], occasion_pref, ans['body_shape']
            )

    if 'analysis' in st.session_state:
        ans = st.session_state['analysis']
        st.success(f"Phong cách gợi ý: **{ans['suggested_style']}**")
        st.info(f"Dáng người: **{ans['body_shape']}** \n\n {ans['reason']}")

        # Hiển thị sản phẩm: Name, Price, Image
        if st.session_state.get('product_recs'):
            st.divider()
            st.subheader("Sản phẩm dành cho bạn")
            for item in st.session_state['product_recs']:
                col_img, col_info = st.columns([1, 2])
                with col_img:
                    st.image(item[2], width=120) # image_url
                with col_info:
                    st.write(f"**{item[0]}**") # name
                    st.write(f"Giá: {item[1]} VNĐ") # price
                    if st.button(f"Thử mẫu này", key=f"btn_{item[3]}"):
                        st.session_state['tryon_item'] = item
                        st.session_state['tryon_status'] = 'processing'

# 3. KHU VỰC THỬ ĐỒ ẢO (Xử lý Case Success/Error)
if 'tryon_item' in st.session_state:
    st.divider()
    st.subheader(f"🖼️ Phòng thử đồ: {st.session_state['tryon_item'][0]}")
    
    # Xử lý quá trình thử đồ
    if st.session_state.get('tryon_status') == 'processing':
        with st.spinner("Đang ghép ảnh..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(user_img.getvalue())
                user_path = tmp.name
            
            res = run_virtual_tryon(user_path, st.session_state['tryon_item'][2])
            
            if res:
                st.session_state['tryon_result'] = res
                st.session_state['tryon_status'] = 'success'
            else:
                st.session_state['tryon_status'] = 'error'
            st.rerun()

    # Trường hợp THÀNH CÔNG
    if st.session_state.get('tryon_status') == 'success':
        st.image(st.session_state['tryon_result'], use_column_width=True)
        st.success("Bạn thấy bộ này thế nào?")
        
        col_cart1, col_cart2 = st.columns(2)
        with col_cart1:
            if st.button("🛒 Thêm vào giỏ hàng"):
                st.toast(f"Đã thêm {st.session_state['tryon_item'][0]} vào giỏ!", icon="✅")
        with col_cart2:
            if st.button("❌ Bỏ qua"):
                del st.session_state['tryon_item']
                st.rerun()

    # Trường hợp LỖI
    if st.session_state.get('tryon_status') == 'error':
        st.error("Server thử đồ đang quá tải (Hugging Face Free Tier).")
        if st.button("🔄 Thử lại lần nữa"):
            st.session_state['tryon_status'] = 'processing'
            st.rerun()
