# ====================== PHÒNG THỬ ĐỒ ẢO (CAT-VTON) ======================
if st.session_state.get('tryon_status') == 'processing' and 'tryon_item' in st.session_state:
    item = st.session_state['tryon_item']
    st.divider()
    st.subheader(f"🪞 Đang thử đồ: {item[0]}")

    with st.spinner("Đang upload ảnh và xử lý thử đồ bằng CAT-VTON (10–18 giây)..."):
        try:
            # 1. Lưu ảnh người dùng tạm thời
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(user_img.getvalue())
                person_local_path = tmp.name

            # 2. Upload ảnh người lên Fal.ai (quan trọng!)
            client = fal_client.SyncClient(api_key=FAL_API_KEY)
            
            # Upload human image và lấy URL công khai
            human_url = client.upload_file(person_local_path)
            
            garment_url = item[2]   # URL từ database

            # 3. Gọi CAT-VTON
            result = client.subscribe(
                "fal-ai/cat-vton",
                arguments={
                    "human_image_url": human_url,
                    "garment_image_url": garment_url,
                    "cloth_type": "upper",           # đổi thành "lower" nếu là quần/váy
                    "num_inference_steps": 25,
                    "guidance_scale": 7.0,
                },
                with_logs=True
            )

            # Cleanup file tạm
            if os.path.exists(person_local_path):
                os.unlink(person_local_path)

            if "images" in result and len(result["images"]) > 0:
                st.session_state['tryon_result'] = result["images"][0]["url"]
                st.session_state['tryon_status'] = 'success'
            else:
                st.session_state['tryon_status'] = 'error'

        except Exception as e:
            st.error(f"Lỗi khi xử lý thử đồ: {str(e)}")
            st.session_state['tryon_status'] = 'error'
        
        st.rerun()
