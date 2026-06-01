import streamlit as st
import database as db
import re
import time

# =====================================================================
# 🛠️ 1. CẤU HÌNH TRANG & ĐA NGÔN NGỮ KHỞI TẠO
# =====================================================================
st.set_page_config(page_title="🔑 MYDOJE - ADMINISTRATIVE CONTROL", layout="wide", page_icon="🔑")

# Khởi tạo database nếu chưa có
try:
    db.init_db()
except Exception as e:
    st.error(f"Lỗi khởi tạo DB: {e}")

# Giả lập từ điển đa ngôn ngữ từ hệ thống JSON
lang = {
    "admin_title": "👑 HỆ THỐNG QUẢN TRỊ VIÊN - MYDOJE",
    "admin_login_header": "XÁC THỰC QUYỀN TRUY CẬP HỆ THỐNG",
    "login_btn": "Đăng Nhập Quản Trị",
    "tab1_title": "👥 Quản Lý Thành Viên & Bản Ghi",
    "tab2_title": "💃 Cập Nhật Content Belly Dance",
    "tab3_title": "🧘 Cập Nhật Content Private Yoga",
    "msg_not_admin": "🛑 Tài khoản này không có quyền truy cập khu vực điều hành!",
    "msg_login_success": "Xác thực thành công! Đang chuyển hướng...",
    "save_content_btn": "💾 CẬP NHẬT NỘI DUNG LÊN HỆ THỐNG",
    "msg_update_success": "🎉 Đã cập nhật nội dung bài học thành công!"
}

# =====================================================================
# 🔐 2. GIAO DIỆN ĐĂNG NHẬP CHUẨN CARD (CĂN GIỮA MÀN HÌNH)
# =====================================================================
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False
if "admin_user" not in st.session_state:
    st.session_state["admin_user"] = ""

if not st.session_state["admin_logged_in"]:
    # Ép khung đăng nhập vào chính giữa màn hình (Tỷ lệ 1:1.6:1)
    side_col1, main_login_col, side_col3 = st.columns([1, 1.6, 1])
    
    with main_login_col:
        st.write("")
        st.write("")
        st.write("")
        
        with st.container(border=True):
            st.markdown(
                f"<h2 style='text-align: center; margin-bottom: 5px;'>🔒 ADMIN PANEL</h2>", 
                unsafe_allow_html=True
            )
            st.markdown(
                f"<p style='text-align: center; color: #888888; font-size: 14px; margin-bottom: 25px;'>{lang['admin_login_header']}</p>", 
                unsafe_allow_html=True
            )
            
            email_input = st.text_input(
                "Địa chỉ Email Admin:", 
                placeholder="admin@mydoje.com", 
                key="admin_email_input_field"
            ).strip().lower()
            
            st.write("")
            btn_login = st.button(lang["login_btn"], type="primary", use_container_width=True, key="admin_submit_login_btn")
            
            if btn_login:
                if not email_input or not re.match(r"[^@]+@[^@]+\.[^@]+", email_input):
                    st.error("Vui lòng nhập một địa chỉ Email hợp lệ!")
                else:
                    user_in_db = db.check_or_create_user(email_input)
                    
                    # Cơ chế đặc cách tài khoản admin hệ thống đầu tiên nếu hệ thống mới thiết lập
                    if email_input in ["admin@mydoje.com", "superadmin@gmail.com"] and user_in_db["role"] != "ADMIN":
                        db.update_user_role(email_input, "ADMIN")
                        user_in_db = db.check_or_create_user(email_input)
                        
                    if user_in_db and user_in_db["role"] == "ADMIN":
                        st.session_state["admin_logged_in"] = True
                        st.session_state["admin_user"] = email_input
                        st.toast(lang["msg_login_success"], icon="🔓")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(lang["msg_not_admin"])
    st.stop()

# =====================================================================
# 🎛️ 3. GIAO DIỆN MAIN DASHBOARD (KHI ĐÃ LOGIN THÀNH CÔNG)
# =====================================================================
st.title(lang["admin_title"])
st.caption(f"Trạng thái phiên: 🟢 Đã kết nối hệ thống | Tài khoản điều hành: **{st.session_state['admin_user']}**")

# Khởi tạo Tabs quản trị chuyên sâu
tab_users, tab_manage_belly, tab_manage_yoga = st.tabs([
    lang["tab1_title"], 
    lang["tab2_title"], 
    lang["tab3_title"]
])

# =====================================================================
# 👥 TAB 1: KHU VỰC QUẢN LÝ USER, PHÂN QUYỀN, XÓA BẢN GHI NHANH
# =====================================================================
with tab_users:
    st.write("")
    
    # Trích xuất toàn bộ dữ liệu bản ghi nhạc từ database
    all_sheets = db.get_all_records()
    
    # Gom nhóm danh sách người dùng duy nhất từ lịch sử bài nhạc
    unique_emails = sorted(list(set([sheet.get("user_email", "").strip() for sheet in all_sheets if sheet.get("user_email")])))
    if "admin@mydoje.com" not in unique_emails:
        unique_emails.append("admin@mydoje.com")

    # --- BLOCK 1: BỘ LỌC TÌM KIẾM THÔNG MINH ---
    with st.container(border=True):
        st.markdown("#### 🔍 Bộ Lọc Tìm Kiếm Thành Viên")
        c_flt1, c_flt2 = st.columns([2, 1])
        with c_flt1:
            search_email = st.text_input("🎯 Tìm nhanh theo Email:", placeholder="Gõ từ khóa email cần tìm...").strip().lower()
        with c_flt2:
            filter_role = st.selectbox("💎 Nhóm phân quyền:", ["TẤT CẢ", "FREE", "PREMIUM", "ADMIN", "BANNED"])

    st.write("")
    
    # --- BLOCK 2: GRID DANH SÁCH CHI TIẾT ---
    st.markdown("### 👤 Danh Sách Thành Viên & Quyền Hạn")
    
    for email in unique_emails:
        if search_email and search_email not in email:
            continue
            
        user_info = db.check_or_create_user(email)
        current_role = user_info.get("role", "FREE") if user_info else "FREE"
        
        if filter_role != "TẤT CẢ" and current_role != filter_role:
            continue
            
        user_sheet_count = sum(1 for s in all_sheets if s.get("user_email", "").strip().lower() == email.lower())
        
        # Thiết kế dạng Khung phẳng (Bordered Container) tối giản, hiện đại
        with st.container(border=True):
            col_u1, col_u2, col_u3, col_u4 = st.columns([3, 2, 2.5, 2.5])
            
            with col_u1:
                st.markdown(f"✉️ **{email}**")
                st.caption(f"Tổng số bài nhạc đã lưu: `{user_sheet_count}`")
                
            with col_u2:
                if current_role == "ADMIN":
                    st.markdown("<span style='background-color:#e0f2fe; color:#0369a1; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:bold;'>👑 ADMINISTRATOR</span>", unsafe_allow_html=True)
                elif current_role == "PREMIUM":
                    st.markdown("<span style='background-color:#fef3c7; color:#b45309; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:bold;'>⭐ PREMIUM</span>", unsafe_allow_html=True)
                elif current_role == "BANNED":
                    st.markdown("<span style='background-color:#fee2e2; color:#b91c1c; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:bold;'>🚫 BANNED</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span style='background-color:#f3f4f6; color:#4b5563; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:bold;'>👤 FREE MEMBER</span>", unsafe_allow_html=True)
                    
            with col_u3:
                if email == st.session_state["admin_user"]:
                    st.markdown("<p style='color:#888; font-style:italic; margin-top:5px;'>Tài khoản hiện tại</p>", unsafe_allow_html=True)
                else:
                    new_role_select = st.selectbox(
                        "Cấp quyền:", 
                        ["FREE", "PREMIUM", "ADMIN", "BANNED"], 
                        index=["FREE", "PREMIUM", "ADMIN", "BANNED"].index(current_role),
                        key=f"sel_role_{email}",
                        label_visibility="collapsed"
                    )
                    if new_role_select != current_role:
                        db.update_user_role(email, new_role_select)
                        st.toast(f"🔄 Đã đổi quyền của {email} thành {new_role_select}!")
                        time.sleep(0.4)
                        st.rerun()
                        
            with col_u4:
                # Quản lý danh sách bài hát qua Popover thanh lịch
                with st.popover(f"🎵 Thư viện bài ({user_sheet_count})", use_container_width=True):
                    user_sheets = [s for s in all_sheets if s.get("user_email", "").strip().lower() == email.lower()]
                    if not user_sheets:
                        st.caption("Người dùng chưa khởi tạo bài nhạc nào.")
                    else:
                        for usheet in user_sheets:
                            cc1, cc2 = st.columns([3, 1.2])
                            cc1.write(f"📄 {usheet['title']}")
                            if cc2.button("🗑️ Xóa", key=f"del_sh_{usheet['id']}", type="secondary", use_container_width=True):
                                db.delete_record(usheet['id'])
                                st.toast(f"❌ Đã xóa bài '{usheet['title']}'!")
                                time.sleep(0.4)
                                st.rerun()

# =====================================================================
# 💃 TAB 2: BIÊN TẬP NỘI DUNG BELLY DANCE (ID = 2)
# =====================================================================
with tab_manage_belly:
    st.write("")
    st.markdown("### 📝 BIÊN TẬP KHÓA HỌC BELLY DANCE PREMIUM")
    
    belly_data = db.get_yoga_data_by_id(2)
    current_belly_url = belly_data["video_url"] if belly_data else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    current_belly_html = belly_data["content_html"] if belly_data else '<div class="yoga-card">Đoạn 1 trống</div><div class="yoga-card">Đoạn 2 trống</div>'
    
    blocks_b = re.findall(r'<div class="yoga-card">\s*(.*?)\s*</div>', current_belly_html, re.DOTALL)
    b_txt_1 = blocks_b[0] if len(blocks_b) >= 1 else "Nhập nội dung phân đoạn 1..."
    b_txt_2 = blocks_b[1] if len(blocks_b) >= 2 else "Nhập nội dung phân đoạn 2..."
    
    # Form điền dữ liệu đồng bộ
    with st.container(border=True):
        new_belly_url = st.text_input("🎥 Đường dẫn Video bài học (YouTube/MP4):", value=current_belly_url, key="input_url_b")
        st.markdown("---")
        st.markdown("#### 📖 Văn bản hướng dẫn kỹ thuật")
        new_b_txt_1 = st.text_area("Khung Thẻ Số 1 (Hiển thị khối trên):", value=b_txt_1, height=150)
        new_b_txt_2 = st.text_area("Khung Thẻ Số 2 (Hiển thị khối dưới):", value=b_txt_2, height=150)
        
        final_belly_html = f'<div class="yoga-card">{new_b_txt_1}</div><div class="yoga-card">{new_b_txt_2}</div>'
        
        st.write("")
        if st.button(lang["save_content_btn"], type="primary", use_container_width=True, key="btn_save_b"):
            db.update_yoga_data(2, new_belly_url, final_belly_html)
            st.success(lang["msg_update_success"])

# =====================================================================
# 🧘 TAB 3: BIÊN TẬP NỘI DUNG PRIVATE YOGA (ID = 1)
# =====================================================================
with tab_manage_yoga:
    st.write("")
    st.markdown("### 📝 BIÊN TẬP KHÓA HỌC PRIVATE YOGA PREMIUM")
    
    yoga_data = db.get_yoga_data_by_id(1)
    current_yoga_url = yoga_data["video_url"] if yoga_data else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    current_yoga_html = yoga_data["content_html"] if yoga_data else '<div class="yoga-card">Đoạn 1 trống</div><div class="yoga-card">Đoạn 2 trống</div>'
    
    blocks_y = re.findall(r'<div class="yoga-card">\s*(.*?)\s*</div>', current_yoga_html, re.DOTALL)
    y_txt_1 = blocks_y[0] if len(blocks_y) >= 1 else "Nhập nội dung phân đoạn 1..."
    y_txt_2 = blocks_y[1] if len(blocks_y) >= 2 else "Nhập nội dung phân đoạn 2..."
    
    # Form điền dữ liệu đồng bộ
    with st.container(border=True):
        new_yoga_url = st.text_input("🎥 Đường dẫn Video bài học (YouTube/MP4):", value=current_yoga_url, key="input_url_y")
        st.markdown("---")
        st.markdown("#### 📖 Văn bản hướng dẫn kỹ thuật")
        new_y_txt_1 = st.text_area("Khung Thẻ Số 1 (Hiển thị khối trên):", value=y_txt_1, height=150)
        new_y_txt_2 = st.text_area("Khung Thẻ Số 2 (Hiển thị khối dưới):", value=y_txt_2, height=150)
        
        final_yoga_html = f'<div class="yoga-card">{new_y_txt_1}</div><div class="yoga-card">{new_y_txt_2}</div>'
        
        st.write("")
        if st.button(lang["save_content_btn"], type="primary", use_container_width=True, key="btn_save_y"):
            db.update_yoga_data(1, new_yoga_url, final_yoga_html)
            st.success(lang["msg_update_success"])