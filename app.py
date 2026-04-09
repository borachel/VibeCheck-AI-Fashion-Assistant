import streamlit as st
import sqlite3
import os
import tempfile
import requests
import json
from PIL import Image
import google.generativeai as genai
import replicate

# ====================== CẤU HÌNH ======================
os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
GENAI_API_KEY = st.secrets.get("GENAI_API_KEY")

genai.configure(api_key=GENAI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="VibeCheck: AI Stylist", layout="centered")

# ====================== HÀM ======================
def get_recommendations(gender, style, occasion, body_shape):
    """Query linh hoạt hơn, ưu tiên style rồi mới đến occasion"""
    try:
        conn = sqlite3.connect('fashion_store.db')
        cursor = conn.cursor()

        # Query 1: Ưu tiên khớp cả style và occasion
        query = """
            SELECT name, price, image_url, id 
            FROM products
            WHERE gender = ?
              AND (style = ? OR style = 'All')
              AND (occasion = ? OR occasion = 'All')
              AND (body_shape = ? OR body_shape = 'All')
            ORDER BY 
                CASE WHEN style = ? THEN 1 ELSE 2 END,
                CASE WHEN occasion = ? THEN 1 ELSE 2 END
            LIMIT 8
        """
        cursor.execute(query, (gender, style, occasion, body_shape, style, occasion))
        results = cursor.fetchall()

        # Query 2: Nếu không có kết quả, nới lỏng (chỉ giữ gender + style)
        if not results:
            cursor.execute("""
                SELECT name, price, image_url, id 
                FROM products
                WHERE gender = ?
                  AND (style = ? OR style = 'All')
                LIMIT 8
            """, (gender, style))
            results = cursor.fetchall()

        # Query 3: Fallback cuối cùng (chỉ theo gender)
        if not results:
            cursor.execute("""
                SELECT name, price, image_url, id 
                FROM products
                WHERE gender = ?
                LIMIT 8
            """, (gender,))
            results = cursor.fetchall()

        conn.close()
        return results

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


def run_replicate_vton(person_local_path: str, garment_url: str):
    try:
        # Sử dụng client trực tiếp để tránh lỗi infer type
        client = replicate.Client(api_token=st.secrets["REPLICATE_API_TOKEN"])
        
        output = client.run(
            "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985",
            input={
                "human_img": open(person_local_path, "rb"),
                "garm_img": garment_url,
                "garment_des": "fashion item"
            }
        )
        
        # Thử lấy URL từ output (Replicate đôi khi trả về đối tượng file hoặc link)
        if hasattr(output, 'url'):
            return output.url
        return str(output)
    except Exception as e:
        st.error(f"Lỗi: {e}")
        return None

def run_replicate_vton(person_local_path: str, garment_url: str):
    """Sử dụng IDM-VTON bản cuuupid trên Replicate"""
    try:
        # Gọi model với ID chính xác từ tài liệu của bạn
        output = replicate.run(
            "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985",
            input={
                "human_img": open(person_local_path, "rb"),
                "garm_img": garment_url, # Có thể truyền URL trực tiếp
                "garment_des": "fashion item for VibeCheck Stylist"
            }
        )
        
        # Theo docs: output trả về một đối tượng có thuộc tính .url
        if hasattr(output, 'url'):
            return output.url
        return str(output)

    except Exception as e:
        st.error(f"❌ Lỗi Replicate: {str(e)}")
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

# ====================== KHU VỰC XỬ LÝ AI (DÁN Ở CUỐI FILE) ======================

if st.session_state.get('tryon_status') == 'processing' and 'tryon_item' in st.session_state:
    item = st.session_state['tryon_item']
    
    with st.spinner("🚀 Đang gửi dữ liệu đến Replicate (15-40 giây)..."):
        try:
            # 1. Tạo file tạm cho ảnh người dùng (từ file_uploader)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_p:
                tmp_p.write(user_img.getvalue())
                person_path = tmp_p.name

            # 2. Chạy model (Dùng URL ảnh sản phẩm trực tiếp từ Database)
            # item[2] là image_url của sản phẩm
            result_url = run_replicate_vton(person_path, item[2])

            # 3. Cleanup file tạm ngay lập tức
            if os.path.exists(person_path):
                os.unlink(person_path)

            if result_url:
                st.session_state['tryon_result'] = result_url
                st.session_state['tryon_status'] = 'success'
            else:
                st.session_state['tryon_status'] = 'error'

        except Exception as e:
            st.error(f"🔥 Lỗi hệ thống: {e}")
            st.session_state['tryon_status'] = 'error'
        
        # Rerun để hiển thị kết quả success/error
        st.rerun()

# --- HIỂN THỊ KẾT QUẢ ---
if st.session_state.get('tryon_status') == 'success':
    st.divider()
    st.subheader("✨ Gương soi ảo: Kết quả thử đồ")
    st.image(st.session_state['tryon_result'], use_container_width=True)
    
    if st.button("❌ Thoát phòng thử đồ"):
        # Dọn dẹp session
        for key in ['tryon_item', 'tryon_status', 'tryon_result']:
            st.session_state.pop(key, None)
        st.rerun()

if st.session_state.get('tryon_status') == 'error':
    st.error("Không thể tạo ảnh. Kiểm tra lại API Token hoặc số dư tài khoản Replicate.")
    if st.button("🔄 Thử lại"):
        st.session_state['tryon_status'] = 'processing'
        st.rerun()
