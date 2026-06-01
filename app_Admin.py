import streamlit as st
import database as db
import re
import time
import smtplib
import math
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random

# =====================================================================
# 🛠️ 1. CẤU HÌNH TRANG & ĐA NGÔN NGỮ KHỞI TẠO
# =====================================================================
st.set_page_config(page_title="🔑 MYDOJE - ADMINISTRATIVE CONTROL", layout="wide", page_icon="🔑")

# Khởi tạo database nếu chưa có (Tự động chạy lệnh migration tách bảng mới của database.py)
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

# Giả định danh sách quản trị viên tối cao được phép truy cập hệ thống
ADMIN_WHITELIST = ["admin@mydoje.com", "themydojeframework@gmail.com"]

# =====================================================================
# 🔐 2. HỆ THỐNG ĐĂNG NHẬP ADMIN ĐA PHƯƠNG THỨC (GOOGLE & EMAIL OTP)
# =====================================================================
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False
if "admin_user" not in st.session_state:
    st.session_state["admin_user"] = ""
if "admin_otp_code" not in st.session_state:
    st.session_state["admin_otp_code"] = None
if "admin_otp_sent" not in st.session_state:
    st.session_state["admin_otp_sent"] = False
if "temp_admin_email" not in st.session_state:
    st.session_state["temp_admin_email"] = ""

# --- XỬ LÝ ĐĂNG NHẬP GOOGLE BIẾN TRẢ VỀ (REDIRECT OAUTH2) ---
query_params = st.query_params
if "code" in query_params and not st.session_state["admin_logged_in"]:
    try:
        google_email = "themydojeframework@gmail" # Dòng này thay bằng hàm lấy email thật từ Google của bạn
        
        if google_email in ADMIN_WHITELIST:
            user_in_db = db.check_or_create_user(google_email)
            if user_in_db["role"] != "ADMIN":
                db.update_user_role(google_email, "ADMIN")
            
            st.session_state["admin_logged_in"] = True
            st.session_state["admin_user"] = google_email
            st.query_params.clear() 
            st.rerun()
        else:
            st.error("Tài khoản Google này không có quyền truy cập vùng Quản trị!")
    except Exception as e:
        st.error(f"Lỗi xác thực Google: {e}")

# --- GIAO DIỆN KHUNG ĐĂNG NHẬP CĂN GIỮA ---
if not st.session_state["admin_logged_in"]:
    side_col1, main_login_col, side_col3 = st.columns([1, 1.6, 1])
    
    with main_login_col:
        st.write("")
        st.write("")
        
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; margin-bottom: 5px;'>🔒 ADMIN PANEL</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #888888; font-size: 14px; margin-bottom: 25px;'>Hệ thống xác thực quyền điều hành tối cao</p>", unsafe_allow_html=True)
            
            if not st.session_state["admin_otp_sent"]:
                try:
                    client_id = st.secrets["google"]["client_id"]
                    redirect_uri = st.secrets["google"]["redirect_uri"] 
                    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=openid%20email%20profile"
                    
                    google_btn_html = f"""
                    <a href="{google_auth_url}" target="_self" style="text-decoration: none;">
                        <div style="display: flex; align-items: center; justify-content: center; background-color: #ffffff; color: #3c4043; border: 1px solid #dadce0; padding: 10px; border-radius: 6px; font-weight: 600; cursor: pointer; margin-bottom: 20px; font-size: 14px; transition: background-color 0.2s;">
                            <img src="https://fonts.gstatic.com/s/i/productlogos/googleg/v6/web-24dp/logo_googleg_color_24dp.png" style="width:18px; margin-right:12px;"/>
                            Đăng nhập nhanh bằng Google Auth
                        </div>
                    </a>
                    """
                    st.markdown(google_btn_html, unsafe_allow_html=True)
                except:
                    st.caption("⚠️ Google Auth chưa cấu hình khóa Secrets, chuyển sang dùng mã OTP bên dưới.")
                
                st.markdown("<div style='text-align: center; color: #bbb; margin-bottom: 15px; font-size: 12px;'>— HOẶC SỬ DỤNG MÃ OTP EMAIL —</div>", unsafe_allow_html=True)

            if not st.session_state["admin_otp_sent"]:
                email_input = st.text_input(
                    "Địa chỉ Email Quản trị viên:", 
                    placeholder="nhập email admin...", 
                    key="admin_email_field"
                ).strip().lower()
                
                st.write("")
                btn_send = st.button("🚀 GỬI MÃ XÁC THỰC OTP", type="primary", use_container_width=True)
                
                if btn_send:
                    if not email_input or not re.match(r"[^@]+@[^@]+\.[^@]+", email_input):
                        st.error("Vui lòng nhập một địa chỉ Email hợp lệ!")
                    elif email_input not in ADMIN_WHITELIST:
                        st.error("Hệ thống từ chối! Email này không nằm trong danh sách đặc cách.")
                    else:
                        with st.spinner("Đang kết nối SMTP Server và gửi mã..."):
                            otp_generated = str(random.randint(100000, 999999))
                            
                            try:
                                msg = MIMEMultipart('alternative')
                                msg['From'] = st.secrets["smtp"]["user"]
                                msg['To'] = email_input
                                msg['Subject'] = "🔒 [MYDOJE ADMIN] - MÃ OTP TRUY CẬP HỆ THỐNG"

                                html_content = f"""
                                <html>
                                  <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; padding: 20px; margin: 0;">
                                    <div style="max-width: 500px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-top: 6px solid #FF4B4B;">
                                      <h2 style="color: #1E1E1E; text-align: center; margin-top: 0; font-size: 22px;">🔒 Xác Thực Hệ Thống</h2>
                                      <p style="color: #555555; font-size: 15px; line-height: 1.6; text-align: center;">
                                        Bạn đang yêu cầu truy cập vào ban điều hành tối cao của <strong>MyDoJe</strong>.<br>
                                        Vui lòng sử dụng mã OTP bảo mật dưới đây:
                                      </p>
                                      <div style="background: #FFF0F0; border: 2px dashed #FF4B4B; border-radius: 8px; padding: 15px; text-align: center; margin: 25px 0;">
                                        <span style="font-size: 36px; font-weight: bold; color: #FF4B4B; letter-spacing: 6px; font-family: monospace;">
                                          {otp_generated}
                                        </span>
                                      </div>
                                      <p style="color: #999999; font-size: 13px; text-align: center; margin-bottom: 0;">
                                        ⏳ Mã này có hiệu lực trong vòng <strong>5 phút</strong>.<br>
                                        Nếu không phải bạn thực hiện, vui lòng bỏ qua email này.
                                      </p>
                                    </div>
                                  </body>
                                </html>
                                """
                                msg.attach(MIMEText(html_content, 'html', 'utf-8'))

                                server = smtplib.SMTP(st.secrets["smtp"]["server"], st.secrets["smtp"]["port"])
                                server.starttls()
                                server.login(st.secrets["smtp"]["user"], st.secrets["smtp"]["password"])
                                server.sendmail(st.secrets["smtp"]["user"], email_input, msg.as_string())
                                server.quit()

                                st.session_state["admin_otp_code"] = otp_generated
                                st.session_state["temp_admin_email"] = email_input
                                st.session_state["admin_otp_sent"] = True

                                st.toast("📧 Mã OTP đã gửi thành công!")
                                time.sleep(0.4)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi gửi mail hệ thống: {e}. Vui lòng kiểm tra lại cấu hình mục Secrets của App này.")
                                
            else:
                st.success(f"Mã OTP đã được gửi đến: **{st.session_state['temp_admin_email']}**")
                
                otp_input = st.text_input(
                    "Nhập mã gồm 6 chữ số để mở khóa:", 
                    placeholder="••••••", 
                    max_chars=6,
                    key="admin_otp_input_field"
                ).strip()
                
                c_btn1, c_btn2 = st.columns([1, 1])
                with c_btn1:
                    btn_confirm = st.button("🔓 XÁC NHẬN ĐĂNG NHẬP", type="primary", use_container_width=True)
                with c_btn2:
                    btn_cancel = st.button("↩️ THAY ĐỔI EMAIL", type="secondary", use_container_width=True)
                
                if btn_confirm:
                    if otp_input == st.session_state["admin_otp_code"]:
                        user_in_db = db.check_or_create_user(st.session_state["temp_admin_email"])
                        if user_in_db["role"] != "ADMIN":
                            db.update_user_role(st.session_state["temp_admin_email"], "ADMIN")
                            
                        st.session_state["admin_logged_in"] = True
                        st.session_state["admin_user"] = st.session_state["temp_admin_email"]
                        st.toast("Mở khóa thành công! Chào mừng Admin.", icon="🔓")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Mã OTP không chính xác! Vui lòng kiểm tra lại hòm thư.")
                        
                if btn_cancel:
                    st.session_state["admin_otp_sent"] = False
                    st.session_state["admin_otp_code"] = None
                    st.rerun()
                    
    st.stop()

# =====================================================================
# 🎛️ 3. GIAO DIỆN MAIN DASHBOARD (KHI ĐÃ LOGIN THÀNH CÔNG)
# =====================================================================
st.title(lang["admin_title"])
st.caption(f"Trạng thái phiên: 🟢 Đã kết nối hệ thống | Tài khoản điều hành: **{st.session_state['admin_user']}**")

# Cấu hình màu sắc giao diện phục vụ khối preview của Admin giống phía học viên
theme_css = {'sheet_bg': '#1e1e1e', 'text_color': '#ffffff', 'border_color': '#333333'}

# Khởi tạo các phân hệ Quản trị chính xác theo cấu trúc
tab_users, tab_manage_belly, tab_manage_yoga = st.tabs([
    lang["tab1_title"], 
    lang["tab2_title"], 
    lang["tab3_title"]
])

# =====================================================================
# 👥 TAB 1: KHU VỰC QUẢN LÝ USER, PHÂN QUYỀN, XÓA BẢN GHI NHANH (GIỮ NGUYÊN VẸN)
# =====================================================================
with tab_users:
    st.write("")
    all_sheets = db.get_all_records()
    unique_emails = sorted(list(set([sheet.get("user_email", "").strip() for sheet in all_sheets if sheet.get("user_email")])))
    if "admin@mydoje.com" not in unique_emails:
        unique_emails.append("admin@mydoje.com")

    with st.container(border=True):
        st.markdown("#### 🔍 Bộ Lọc Tìm Kiếm Thành Viên")
        c_flt1, c_flt2 = st.columns([2, 1])
        with c_flt1:
            search_email = st.text_input("🎯 Tìm nhanh theo Email:", placeholder="Gõ từ khóa email cần tìm...").strip().lower()
        with c_flt2:
            filter_role = st.selectbox("💎 Nhóm phân quyền:", ["TẤT CẢ", "FREE", "PREMIUM", "ADMIN", "BANNED"])

    st.write("")
    st.markdown("### 👤 Danh Sách Thành Viên & Quyền Hạn")
    
    for email in unique_emails:
        if search_email and search_email not in email:
            continue
            
        user_info = db.check_or_create_user(email)
        current_role = user_info.get("role", "FREE") if user_info else "FREE"
        
        if filter_role != "TẤT CẢ" and current_role != filter_role:
            continue
            
        user_sheet_count = sum(1 for s in all_sheets if s.get("user_email", "").strip().lower() == email.lower())
        
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
# 💃 TAB 2: BIÊN TẬP KHÓA HỌC / TIN TỨC BELLY DANCE (BẢNG: morning_boost)
# =====================================================================
with tab_manage_belly:
    st.write("")
    st.markdown("### 📝 ĐĂNG BÀI VIẾT BELLY DANCE MỚI (CHUYÊN MỤC: MORNING BOOST)")
    
    # 1. Form nhập bài viết lưu lịch sử vào bảng morning_boost
    with st.container(border=True):
        b_title = st.text_input("🏷️ Tiêu đề bài giảng / tin tức:", placeholder="Nhập tiêu đề bài viết Belly Dance...", key="b_title_in")
        b_url = st.text_input("🎥 Đường dẫn Video bài học (YouTube URL):", placeholder="https://www.youtube.com/watch?v=...", key="b_url_in")
        
        st.markdown("#### 📖 Văn bản chi tiết")
        b_txt_1 = st.text_area("Khung số 1 (Nội dung khối trên):", placeholder="Nội dung phân đoạn 1...", height=120, key="b_txt1_in")
        b_txt_2 = st.text_area("Khung số 2 (Nội dung khối dưới):", placeholder="Nội dung phân đoạn 2...", height=120, key="b_txt2_in")
        
        # Bọc thẻ HTML tự động theo thiết kế lõi
        final_b_html = f'<div class="yoga-card">{b_txt_1}</div><div class="yoga-card">{b_txt_2}</div>'
        
        st.write("")
        if st.button("🚀 XUẤT BẢN BÀI VIẾT BELLY DANCE", type="primary", use_container_width=True, key="b_btn_publish"):
            if not b_title.strip():
                st.error("❌ Thất bại: Vui lòng nhập tiêu đề bài viết!")
            else:
                success = db.insert_premium_post("morning_boost", b_title.strip(), b_url.strip(), final_b_html.strip())
                if success:
                    st.success("🎉 Đã xuất bản thành công bài viết mới vào chuyên mục Belly Dance!")
                    st.rerun()
                else:
                    st.error("💥 Lỗi: Không thể nạp dữ liệu vào Database.")

    st.write("---")
    st.markdown("### 🗂️ DANH SÁCH BÀI CŨ ĐÃ LƯU (PHÂN TRANG GOOGLE STYLE)")
    
    # 2. Xử lý thuật toán phân trang 3 bài/trang kiểu Google cho bảng morning_boost
    total_b_posts = db.get_total_posts_count("morning_boost")
    posts_per_page = 3
    
    if total_b_posts == 0:
        st.info("Hiện tại chuyên mục này chưa có bài viết nào lưu trong bảng `morning_boost`.")
    else:
        total_b_pages = math.ceil(total_b_posts / posts_per_page)
        
        if "pg_belly" not in st.session_state:
            st.session_state["pg_belly"] = 1
        current_b_page = st.session_state["pg_belly"]
        offset_b = (current_b_page - 1) * posts_per_page
        
        # Gọi hàm truy vấn phân trang thông minh từ db.py
        belly_posts_list = db.get_premium_posts_with_pagination("morning_boost", limit=posts_per_page, offset=offset_b)
        
        # Hiện danh sách log bài viết cho Admin xem
        for bp in belly_posts_list:
            with st.container(border=True):
                st.markdown(f"#### **Bài mẫu: {bp['title']}** (Mã ID: `{bp['id']}`)")
                st.caption(f"📅 Ngày đăng: `{bp['created_at']}` | 🔗 Link: {bp['video_url'] if bp['video_url'] else 'Không đính kèm Video'}")
                with st.expander("👁️ Xem nhanh cấu trúc hiển thị của học viên"):
                    if bp['video_url']: st.video(bp['video_url'])
                    blocks = re.findall(r'<div class="yoga-card">\s*(.*?)\s*</div>', bp['content_html'], re.DOTALL)
                    d1 = blocks[0] if len(blocks) >= 1 else "Trống phân đoạn 1"
                    d2 = blocks[2] if len(blocks) >= 2 else "Trống phân đoạn 2"
                    st.markdown(f'<div style="background-color:{theme_css["sheet_bg"]}; padding:15px; border-radius:8px; border-left:5px solid #1b8a5a; color:{theme_css["text_color"]}; margin-bottom:10px;">{d1}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="background-color:{theme_css["sheet_bg"]}; padding:15px; border-radius:8px; border-left:5px solid #1b8a5a; color:{theme_css["text_color"]};">{d2}</div>', unsafe_allow_html=True)

        # Thanh lật số trang Google: 1 | 2 | 3...
        st.write("Chuyển trang dữ liệu bài viết:")
        cols_b_nav = st.columns(total_b_pages + 10)
        for i in range(1, total_b_pages + 1):
            btn_lbl = f"**[{i}]**" if i == current_b_page else f"{i}"
            if cols_b_nav[i-1].button(btn_lbl, key=f"nav_b_{i}"):
                st.session_state["pg_belly"] = i
                st.rerun()

# =====================================================================
# 🧘 TAB 3: BIÊN TẬP KHÓA HỌC / TIN TỨC PRIVATE YOGA (BẢNG: deep_sleep)
# =====================================================================
with tab_manage_yoga:
    st.write("")
    st.markdown("### 📝 ĐĂNG BÀI VIẾT PRIVATE YOGA MỚI (CHUYÊN MỤC: DEEP SLEEP)")
    
    # 1. Form nhập bài viết lưu lịch sử vào bảng deep_sleep
    with st.container(border=True):
        y_title = st.text_input("🏷️ Tiêu đề bài giảng / tin tức:", placeholder="Nhập tiêu đề bài viết Yoga...", key="y_title_in")
        y_url = st.text_input("🎥 Đường dẫn Video bài học (YouTube URL):", placeholder="https://www.youtube.com/watch?v=...", key="y_url_in")
        
        st.markdown("#### 📖 Văn bản chi tiết")
        y_txt_1 = st.text_area("Khung số 1 (Nội dung khối trên):", placeholder="Nội dung phân đoạn 1...", height=120, key="y_txt1_in")
        y_txt_2 = st.text_area("Khung số 2 (Nội dung khối dưới):", placeholder="Nội dung phân đoạn 2...", height=120, key="y_txt2_in")
        
        # Bọc thẻ HTML tự động theo thiết kế lõi
        final_y_html = f'<div class="yoga-card">{y_txt_1}</div><div class="yoga-card">{y_txt_2}</div>'
        
        st.write("")
        if st.button("🚀 XUẤT BẢN BÀI VIẾT PRIVATE YOGA", type="primary", use_container_width=True, key="y_btn_publish"):
            if not y_title.strip():
                st.error("❌ Thất bại: Vui lòng nhập tiêu đề bài viết!")
            else:
                success = db.insert_premium_post("deep_sleep", y_title.strip(), y_url.strip(), final_y_html.strip())
                if success:
                    st.success("🎉 Đã xuất bản thành công bài viết mới vào chuyên mục Private Yoga!")
                    st.rerun()
                else:
                    st.error("💥 Lỗi: Không thể nạp dữ liệu vào Database.")

    st.write("---")
    st.markdown("### 🗂️ DANH SÁCH BÀI CŨ ĐÃ LƯU (PHÂN TRANG GOOGLE STYLE)")
    
    # 2. Xử lý thuật toán phân trang 3 bài/trang kiểu Google cho bảng deep_sleep
    total_y_posts = db.get_total_posts_count("deep_sleep")
    
    if total_y_posts == 0:
        st.info("Hiện tại chuyên mục này chưa có bài viết nào lưu trong bảng `deep_sleep`.")
    else:
        total_y_pages = math.ceil(total_y_posts / posts_per_page)
        
        if "pg_yoga" not in st.session_state:
            st.session_state["pg_yoga"] = 1
        current_y_page = st.session_state["pg_yoga"]
        offset_y = (current_y_page - 1) * posts_per_page
        
        # Gọi hàm truy vấn phân trang thông minh từ db.py
        yoga_posts_list = db.get_premium_posts_with_pagination("deep_sleep", limit=posts_per_page, offset=offset_y)
        
        # Hiện danh sách log bài viết cho Admin xem
        for yp in yoga_posts_list:
            with st.container(border=True):
                st.markdown(f"#### **Bài mẫu: {yp['title']}** (Mã ID: `{yp['id']}`)")
                st.caption(f"📅 Ngày đăng: `{yp['created_at']}` | 🔗 Link: {yp['video_url'] if yp['video_url'] else 'Không đính kèm Video'}")
                with st.expander("👁️ Xem nhanh cấu trúc hiển thị của học viên"):
                    if yp['video_url']: st.video(yp['video_url'])
                    blocks = re.findall(r'<div class="yoga-card">\s*(.*?)\s*</div>', yp['content_html'], re.DOTALL)
                    d1 = blocks[0] if len(blocks) >= 1 else "Trống phân đoạn 1"
                    d2 = blocks[1] if len(blocks) >= 2 else "Trống phân đoạn 2"
                    st.markdown(f'<div style="background-color:{theme_css["sheet_bg"]}; padding:15px; border-radius:8px; border-left:5px solid #1b8a5a; color:{theme_css["text_color"]}; margin-bottom:10px;">{d1}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="background-color:{theme_css["sheet_bg"]}; padding:15px; border-radius:8px; border-left:5px solid #1b8a5a; color:{theme_css["text_color"]};">{d2}</div>', unsafe_allow_html=True)

        # Thanh lật số trang Google: 1 | 2 | 3...
        st.write("Chuyển trang dữ liệu bài viết:")
        cols_y_nav = st.columns(total_y_pages + 10)
        for i in range(1, total_y_pages + 1):
            btn_lbl = f"**[{i}]**" if i == current_y_page else f"{i}"
            if cols_y_nav[i-1].button(btn_lbl, key=f"nav_y_{i}"):
                st.session_state["pg_yoga"] = i
                st.rerun()