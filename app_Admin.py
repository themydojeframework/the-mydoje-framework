import streamlit as st
import database as db
import re
import time

# =====================================================================
# 🛠️ 1. CẤU HÌNH TRANG & ĐA NGÔN NGỮ KHỞI TẠO
# =====================================================================
st.set_page_config(page_title="👑 MYDOJE - SYSTEM ADMINISTRATION", layout="wide", page_icon="🔑")

# Khởi tạo database nếu chưa có
try:
    db.init_db()
except Exception as e:
    st.error(f"Lỗi khởi tạo DB: {e}")

# Giả lập từ điển đa ngôn ngữ (Đồng bộ cấu trúc như en.json / vi.json của bạn)
lang = {
    "admin_title": "👑 HỆ THỐNG QUẢN TRỊ VIÊN - MYDOJE",
    "admin_login_header": "XÁC THỰC QUYỀN TRUY CẬP HỆ THỐNG",
    "login_btn": "ĐĂNG NHẬP HỆ THỐNG",
    "tab1_title": "👥 QUẢN LÝ THÀNH VIÊN & BẢN GHI",
    "tab2_title": "💃 QUẢN LÝ NỘI DUNG BELLY DANCE",
    "tab3_title": "🧘 QUẢN LÝ NỘI DUNG PRIVATE YOGA",
    "col_email": "Email Người Dùng",
    "col_role": "Quyền Hạn",
    "col_action": "Thao Tác",
    "msg_not_admin": "🛑 Bạn không có quyền truy cập vào khu vực quản trị này!",
    "msg_login_success": "🔓 Đăng nhập thành công với quyền ADMIN!",
    "save_content_btn": "💾 CẬP NHẬT NỘI DUNG LÊN HỆ THỐNG",
    "msg_update_success": "🎉 Đã cập nhật nội dung bài học thành công!"
}

# Giao diện Theme cơ bản
theme_css = {
    'sheet_bg': '#ffffff' if st.session_state.get("app_theme", "☀️ Light") == "☀️ Light" else "#1e1e1e",
    'text_color': '#000000' if st.session_state.get("app_theme", "☀️ Light") == "☀️ Light" else "#ffffff",
    'border_color': '#d1d5db' if st.session_state.get("app_theme", "☀️ Light") == "☀️ Light" else "#444444"
}

# =====================================================================
# 🔐 2. KIỂM TRA ĐĂNG NHẬP CHUẨN LOCAL & CLOUD
# =====================================================================
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False
if "admin_user" not in st.session_state:
    st.session_state["admin_user"] = ""

if not st.session_state["admin_logged_in"]:
    st.subheader(lang["admin_login_header"])
    
    # Form đăng nhập hỗ trợ cả gõ tay test local và nhập email thực tế
    c_login1, c_login2 = st.columns([2, 1])
    with c_login1:
        email_input = st.text_input("Nhập Email Admin của bạn:", placeholder="admin@mydoje.com...").strip().lower()
    with c_login2:
        st.write("#")
        btn_login = st.button(lang["login_btn"], type="primary", use_container_width=True)
        
    if btn_login:
        if not email_input or "@" not in email_input:
            st.error("Vui lòng nhập một địa chỉ Email hợp lệ!")
        else:
            # Tra cứu quyền trong DB (Bất kể Local Sqlite hay Cloud Supabase)
            user_in_db = db.check_or_create_user(email_input)
            
            # Cơ chế đặc cách tài khoản admin hệ thống đầu tiên nếu DB trống/mới thiết lập
            if email_input in ["admin@mydoje.com", "superadmin@gmail.com"] and user_in_db["role"] != "ADMIN":
                db.update_user_role(email_input, "ADMIN")
                user_in_db = db.check_or_create_user(email_input)
                
            if user_in_db and user_in_db["role"] == "ADMIN":
                st.session_state["admin_logged_in"] = True
                st.session_state["admin_user"] = email_input
                st.toast(lang["msg_login_success"])
                st.rerun()
            else:
                st.error(lang["msg_not_admin"])
    st.stop()  # Ngăn chặn render nội dung bên dưới nếu chưa login thành công

# Giao diện chào đón khi đã đăng nhập admin thành công
st.title(lang["admin_title"])
st.caption(f"Trạng thái phiên: 🟢 Đã kết nối | Tài khoản điều hành: **{st.session_state['admin_user']}**")

# Khởi tạo Tabs quản trị chuyên sâu
tab_users, tab_manage_belly, tab_manage_yoga = st.tabs([
    lang["tab1_title"], 
    lang["tab2_title"], 
    lang["tab3_title"]
])

# =====================================================================
# 👥 TAB 1: KHU VỰC KIỂM TRA USER, QUYỀN, BẢN GHI, BAN/UNBAN
# =====================================================================
with tab_users:
    st.header("📋 BẢNG ĐIỀU KHIỂN THÀNH VIÊN CHI TIẾT")
    
    # 1. Trích xuất toàn bộ dữ liệu bản ghi nhạc từ database để phân tích/lọc bài
    all_sheets = db.get_all_records()
    
    # Gom nhóm danh sách người dùng duy nhất dựa trên lịch sử bản ghi nhạc đã tạo
    unique_emails = sorted(list(set([sheet.get("user_email", "").strip() for sheet in all_sheets if sheet.get("user_email")])))
    if "admin@mydoje.com" not in unique_emails:
        unique_emails.append("admin@mydoje.com")

    # Bộ lọc thông minh (Filter)
    st.markdown("### 🔍 Bộ Lọc Tìm Kiếm Nhanh")
    c_flt1, c_flt2 = st.columns([2, 2])
    with c_flt1:
        search_email = st.text_input("🎯 Tìm User theo Email:", placeholder="Gõ email cần tìm...").strip().lower()
    with c_flt2:
        filter_role = st.selectbox("💎 Lọc theo Cấp độ Quyền:", ["TẤT CẢ", "FREE", "PREMIUM", "ADMIN", "BANNED"])

    st.markdown("---")
    
    # 2. Hiển thị danh sách Người dùng dưới dạng bảng điều khiển tương tác
    st.markdown("### 👤 Danh Sách Thành Viên & Phân Quyền Hạn")
    
    for email in unique_emails:
        # Nếu có từ khóa tìm kiếm, lọc bỏ các user không khớp
        if search_email and search_email not in email:
            continue
            
        user_info = db.check_or_create_user(email)
        current_role = user_info.get("role", "FREE") if user_info else "FREE"
        
        # Nếu có bộ lọc Quyền, lọc bỏ các user không đúng nhóm quyền đã chọn
        if filter_role != "TẤT CẢ" and current_role != filter_role:
            continue
            
        # Đếm số lượng bản ghi nhạc mà user này sở hữu
        user_sheet_count = sum(1 for s in all_sheets if s.get("user_email", "").strip().lower() == email.lower())
        
        # Tạo khung bao bọc (Card) hiển thị thông tin từng user gọn gàng
        with st.container():
            col_u1, col_u2, col_u3, col_u4 = st.columns([3, 2, 2, 3])
            
            with col_u1:
                st.markdown(f"📩 **{email}**")
                st.caption(f"Tổng số bài nhạc đã lưu: `{user_sheet_count}` bản ghi")
                
            with col_u2:
                if current_role == "ADMIN":
                    st.markdown("👑 <span style='color:#3b82f6; font-weight:bold;'>ADMINISTRATOR</span>", unsafe_allow_html=True)
                elif current_role == "PREMIUM":
                    st.markdown("⭐ <span style='color:#f59e0b; font-weight:bold;'>PREMIUM MEMBER</span>", unsafe_allow_html=True)
                elif current_role == "BANNED":
                    st.markdown("🚫 <span style='color:#dc2626; font-weight:bold;'>ĐÃ BỊ KHÓA (BANNED)</span>", unsafe_allow_html=True)
                else:
                    st.markdown("👤 <span style='color:#6b7280;'>FREE MEMBER</span>", unsafe_allow_html=True)
                    
            with col_u3:
                # Không cho phép tự hạ quyền hoặc thay đổi quyền của chính mình đang đăng nhập
                if email == st.session_state["admin_user"]:
                    st.info("Tài khoản của bạn")
                else:
                    new_role_select = st.selectbox(
                        "Thay đổi quyền:", 
                        ["FREE", "PREMIUM", "ADMIN", "BANNED"], 
                        index=["FREE", "PREMIUM", "ADMIN", "BANNED"].index(current_role),
                        key=f"sel_role_{email}"
                    )
                    if new_role_select != current_role:
                        db.update_user_role(email, new_role_select)
                        st.toast(f"🔄 Đã cập nhật quyền của {email} thành {new_role_select}!")
                        time.sleep(0.5)
                        st.rerun()
                        
            with col_u4:
                # Khu vực quản lý tháo gỡ/xóa bài nhanh của user nếu vi phạm
                with st.popover(f"🎵 Xem danh sách bài ({user_sheet_count})"):
                    user_sheets = [s for s in all_sheets if s.get("user_email", "").strip().lower() == email.lower()]
                    if not user_sheets:
                        st.write("User này chưa có bài nhạc nào trên hệ thống.")
                    else:
                        for usheet in user_sheets:
                            cc1, cc2 = st.columns([3, 1])
                            cc1.write(f"📄 {usheet['title']} `(ID: {usheet['id']})`")
                            if cc2.button("🗑️ Xóa", key=f"del_sh_{usheet['id']}"):
                                db.delete_record(usheet['id'])
                                st.toast(f"❌ Đã xóa bài '{usheet['title']}'!")
                                time.sleep(0.5)
                                st.rerun()
            st.markdown("<hr style='margin: 8px 0; border-top: 1px dashed #ccc;' />", unsafe_allow_html=True)

# =====================================================================
# 💃 TAB 2: POST & CẬP NHẬT NỘI DUNG BELLY DANCE (ID = 2)
# =====================================================================
with tab_manage_belly:
    st.header("📝 BIÊN TẬP KHÓA HỌC BELLY DANCE PREMIUM")
    st.caption("Nội dung đăng tải tại đây sẽ hiển thị lập tức tại Tab 2 của ứng dụng học viên.")
    
    # Tải dữ liệu Belly Dance hiện tại lên từ DB (Hỗ trợ lai thông minh)
    belly_data = db.get_yoga_data_by_id(2)
    
    current_belly_url = belly_data["video_url"] if belly_data else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    current_belly_html = belly_data["content_html"] if belly_data else '<div class="yoga-card">Đoạn 1 trống</div><div class="yoga-card">Đoạn 2 trống</div>'
    
    # Thử bẻ nhỏ chuỗi HTML bằng regex để đẩy vào 2 ô nhập liệu trực quan cho Admin dễ sửa
    blocks_b = re.findall(r'<div class="yoga-card">\s*(.*?)\s*</div>', current_belly_html, re.DOTALL)
    b_txt_1 = blocks_b[0] if len(blocks_b) >= 1 else "Nhập nội dung phân đoạn 1..."
    b_txt_2 = blocks_b[1] if len(blocks_b) >= 2 else "Nhập nội dung phân đoạn 2..."
    
    # Form điền dữ liệu
    new_belly_url = st.text_input("🎥 Đường dẫn Video bài học (YouTube/MP4):", value=current_belly_url, key="input_url_b")
    
    st.markdown("#### 📖 Nội dung văn bản hướng dẫn chi tiết")
    new_b_txt_1 = st.text_area("Segment 1 (Khung Thẻ Số 1):", value=b_txt_1, height=120)
    new_b_txt_2 = st.text_area("Segment 2 (Khung Thẻ Số 2):", value=b_txt_2, height=120)
    
    # Hợp nhất dữ liệu thô thành khối mã HTML chuẩn hóa cấu trúc của hệ thống thẻ .yoga-card
    final_belly_html = f'<div class="yoga-card">{new_b_txt_1}</div><div class="yoga-card">{new_b_txt_2}</div>'
    
    st.write("")
    if st.button(lang["save_content_btn"], type="primary", key="btn_save_b"):
        db.update_yoga_data(2, new_belly_url, final_belly_html)
        st.success(lang["msg_update_success"])
        st.toast(lang["msg_update_success"])

# =====================================================================
# 🧘 TAB 3: POST & CẬP NHẬT NỘI DUNG PRIVATE YOGA (ID = 1)
# =====================================================================
with tab_manage_yoga:
    st.header("📝 BIÊN TẬP KHÓA HỌC PRIVATE YOGA PREMIUM")
    st.caption("Nội dung đăng tải tại đây sẽ hiển thị lập tức tại Tab 3 của ứng dụng học viên.")
    
    # Tải dữ liệu Private Yoga hiện tại lên từ DB (Hỗ trợ lai thông minh)
    yoga_data = db.get_yoga_data_by_id(1)
    
    current_yoga_url = yoga_data["video_url"] if yoga_data else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    current_yoga_html = yoga_data["content_html"] if yoga_data else '<div class="yoga-card">Đoạn 1 trống</div><div class="yoga-card">Đoạn 2 trống</div>'
    
    # Thử bẻ nhỏ chuỗi HTML bằng regex để đẩy vào 2 ô nhập liệu cho Admin
    blocks_y = re.findall(r'<div class="yoga-card">\s*(.*?)\s*</div>', current_yoga_html, re.DOTALL)
    y_txt_1 = blocks_y[0] if len(blocks_y) >= 1 else "Nhập nội dung phân đoạn 1..."
    y_txt_2 = blocks_y[1] if len(blocks_y) >= 2 else "Nhập nội dung phân đoạn 2..."
    
    # Form điền dữ liệu
    new_yoga_url = st.text_input("🎥 Đường dẫn Video bài học (YouTube/MP4):", value=current_yoga_url, key="input_url_y")
    
    st.markdown("#### 📖 Nội dung văn bản hướng dẫn chi tiết")
    new_y_txt_1 = st.text_area("Segment 1 (Khung Thẻ Số 1):", value=y_txt_1, height=120)
    new_y_txt_2 = st.text_area("Segment 2 (Khung Thẻ Số 2):", value=y_txt_2, height=120)
    
    # Hợp nhất dữ liệu thô thành khối mã HTML tương thích ngược hoàn toàn với app.py học viên
    final_yoga_html = f'<div class="yoga-card">{new_y_txt_1}</div><div class="yoga-card">{new_y_txt_2}</div>'
    
    st.write("")
    if st.button(lang["save_content_btn"], type="primary", key="btn_save_y"):
        db.update_yoga_data(1, new_yoga_url, final_yoga_html)
        st.success(lang["msg_update_success"])
        st.toast(lang["msg_update_success"])