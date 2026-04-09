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


def run_cat_vton(person_local_path: str, garment_url: str):
    """Hàm CAT-VTON - Đã sửa để upload file đúng cách"""
    try:
        client = fal_client.SyncClient(api_key=FAL_API_KEY)
        
        # Upload ảnh người dùng lên Fal.ai để lấy URL công khai
        human_url = client.upload_file(person_local_path)
        
        # Gọi CAT-VTON với tham số CHUẨN theo tài liệu fal-ai/cat-vton
        result = client.subscribe(
            "fal-ai/cat-vton",
            arguments={
                "human_image_url": human_url,      # ← Đúng tên tham số
                "garment_image_url": garment_url,  # ← Đúng tên tham số
                "cloth_type": "upper",             # upper / lower / overall
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
            },
            with_logs=True
        )
        
        # Cấu trúc trả về thường là {"image": {"url": "..."}} hoặc {"images": [...]}
        if result and "image" in result:
            return result["image"]["url"]
        elif result and "images" in result and len(result["images"]) > 0:
            return result["images"][0]["url"]
        else:
            st.error("Model không trả về ảnh hợp lệ")
            return None

    except Exception as e:
        st.error(f"❌ Lỗi CAT-VTON: {str(e)}")
        print(f"DEBUG CAT-VTON: {e}")
        return None


# ====================== THỬ ĐỒ ẢO (CAT-VTON) ======================
if 'tryon_item' in st.session_state:
    item = st.session_state['tryon_item']
    st.divider()
   
    if st.session_state.get('tryon_status') == 'processing':
        st.subheader(f"🪞 Đang xử lý thử đồ: {item[0]}")
        
        with st.spinner("Đang upload ảnh và tạo thử đồ CAT-VTON (10–20 giây)..."):
            try:
                # Tạo file tạm từ ảnh người dùng upload
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(user_img.getvalue())
                    person_local_path = tmp.name
                
                # Gọi hàm run_cat_vton (đã sửa)
                result_url = run_cat_vton(person_local_path, item[2])
                
                # Cleanup file tạm
                if os.path.exists(person_local_path):
                    os.unlink(person_local_path)
                
                if result_url:
                    st.session_state['tryon_result'] = result_url
                    st.session_state['tryon_status'] = 'success'
                else:
                    st.session_state['tryon_status'] = 'error'
                    
            except Exception as e:
                st.error(f"❌ Lỗi khi xử lý thử đồ: {str(e)}")
                st.session_state['tryon_status'] = 'error'
            
            st.rerun()

    # Hiển thị kết quả khi thành công
    if st.session_state.get('tryon_status') == 'success':
        st.subheader("✨ Kết quả thử đồ của bạn")
        st.image(st.session_state['tryon_result'], use_container_width=True, caption="VibeCheck: AI Stylist Result")
        
        if st.button("❌ Đóng phòng thử đồ"):
            for key in ['tryon_item', 'tryon_status', 'tryon_result']:
                st.session_state.pop(key, None)
            st.rerun()


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

# ====================== THỬ ĐỒ ẢO (CAT-VTON) ======================
if 'tryon_item' in st.session_state:
    item = st.session_state['tryon_item']
    st.divider()
    
    # 1. Logic xử lý khi đang trong trạng thái 'processing'
    if st.session_state.get('tryon_status') == 'processing':
        st.subheader(f"🪞 Đang xử lý thử đồ: {item[0]}")
        with st.spinner("Đang mặc thử sản phẩm (10–20 giây)..."):
            try:
                # Tạo file tạm cho ảnh người dùng
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(user_img.getvalue())
                    person_local_path = tmp.name

                client = fal_client.SyncClient(api_key=FAL_API_KEY)
                
                # Upload lên Fal lấy URL
                person_url = client.upload_file(person_local_path)
                garment_url = item[2] # URL ảnh sản phẩm từ DB

                # Gọi CAT-VTON với tham số ĐÚNG
                result = client.subscribe(
                    "fal-ai/cat-vton",
                    arguments={
                        "person_image_url": person_url,      # Sửa tên từ human_image_url
                        "garment_image_url": garment_url,
                        "category": "upper_body",            # Sửa từ cloth_type
                        "num_inference_steps": 30,
                        "guidance_scale": 7.5,
                    }
                )

                # Cleanup file tạm
                if os.path.exists(person_local_path):
                    os.unlink(person_local_path)

                if result and "image" in result:
                    # Lưu kết quả URL vào session
                    st.session_state['tryon_result'] = result["image"]["url"]
                    st.session_state['tryon_status'] = 'success'
                else:
                    st.session_state['tryon_status'] = 'error'

            except Exception as e:
                st.error(f"❌ Lỗi CAT-VTON: {str(e)}")
                st.session_state['tryon_status'] = 'error'
            
            st.rerun()

    # 2. Logic hiển thị khi đã có kết quả (success)
    if st.session_state.get('tryon_status') == 'success':
        st.subheader("✨ Kết quả thử đồ của bạn")
        st.image(st.session_state['tryon_result'], use_container_width=True, caption="VibeCheck: AI Stylist Result")
        
        if st.button("❌ Đóng phòng thử đồ"):
            del st.session_state['tryon_item']
            del st.session_state['tryon_status']
            del st.session_state['tryon_result']
            st.rerun()
