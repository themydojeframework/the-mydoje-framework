import datetime
import json
import sqlite3
import time
import hashlib
import smtplib
import random
import os
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from dotenv import load_dotenv
from streamlit_cookies_controller import CookieController
import database as db
import streamlit.components.v1 as components

# --- 1. CẤU HÌNH TRANG (BẮT BUỘC ĐẶT ĐẦU FILE) ---
st.set_page_config(
    page_title="KHUNG MYDJ OFFICIAL",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Tải biến môi trường từ file .env
load_dotenv()

# Thử nghiệm Import thư viện Google Auth
try:
    import streamlit_google_auth as oAuth
except ImportError:
    st.error("Chưa cài đặt thư viện! Hãy chạy lệnh: pip install streamlit-google-auth")
    oAuth = None

controller = CookieController()

# --- ĐỌC CẤU HÌNH EMAIL OTP ---
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")

# --- ĐỌC CẤU HÌNH GOOGLE OAUTH ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501").strip()

# --- KHỞI TẠO BỘ XÁC THỰC GOOGLE CHUẨN AN TOÀN ---
config = {
    "client_id": GOOGLE_CLIENT_ID,
    "client_secret": GOOGLE_CLIENT_SECRET,
    "redirect_uri": GOOGLE_REDIRECT_URI,
    "cookie_name": "google_oauth_cookie",
    "cookie_expiry_days": 7
}

@st.cache_resource
def init_authenticator():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return None
    try:
        if oAuth and hasattr(oAuth, 'Authenticate'):
            return oAuth.Authenticate(**config)
        elif oAuth and hasattr(oAuth, 'create_authenticator'):
            return oAuth.create_authenticator(config)
        else:
            from streamlit_google_auth import Authenticate
            return Authenticate(**config)
    except Exception:
        try:
            from streamlit_google_auth import Authenticate
            return Authenticate(
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                redirect_uri=config["redirect_uri"]
            )
        except Exception:
            return None

#----------------------------------
#KẾT NỐI DATABASE TRÊN SUPASE VÀ APP.DB Ở LOCAL
#----------------------------------
import os
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv  # Thêm thư viện để đọc file .env dưới máy

# Kích hoạt đọc file .env (Dưới local sẽ đọc được DATABASE_URL=sqlite:///app.db)
load_dotenv()

authenticator = init_authenticator()
db.init_db()

# --- ĐOẠN ĐỌC BIẾN MÔI TRƯỜNG PHÂN THÂN ---
# Nếu không tìm thấy DATABASE_URL trong hệ thống, mặc định sẽ dùng SQLite local
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")

# KIỂM TRA: Nếu trong link có chứa chữ "sqlite" -> Chạy máy Local (SQLite)
if "sqlite" in DATABASE_URL:
    # ----------------------------------------------------------------
    # CHẠY DƯỚI MÁY (LOCAL - SQLITE)
    # ----------------------------------------------------------------
    conn = sqlite3.connect("app.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Giúp trả về dạng Dictionary giống Postgres
    cursor = conn.cursor()
    
    # Tạo bảng kiểu SQLite (Dùng AUTOINCREMENT)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS yoga_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_url TEXT,
            content_html TEXT
        );
    """)
    conn.commit()
    
    # Kiểm tra và nạp dữ liệu mẫu cho SQLite nếu bảng trống
    cursor.execute("SELECT COUNT(*) FROM yoga_data;")
    if cursor.fetchone()[0] == 0:
        # SQLite dùng dấu hỏi chấm (?) làm tham số truyền vào
        cursor.execute(
            "INSERT INTO yoga_data (video_url, content_html) VALUES (?, ?);",
            ('https://youtu.be/1R6c6ABgDeE?si=5o8zf2awDTRHYDka', '<div class="yoga-card">Bài tập Yoga Thư giãn sâu đoạn 1</div><div class="yoga-card">Động tác kéo giãn cơ đoạn 2</div>')
        )
        cursor.execute(
            "INSERT INTO yoga_data (video_url, content_html) VALUES (?, ?);",
            ('https://youtu.be/1R6c6ABgDeE?si=5o8zf2awDTRHYDka', '<div class="yoga-card">Belly Dance Đánh hông cơ bản đoạn 1</div><div class="yoga-card">Sóng bụng dẻo dai đoạn 2</div>')
        )
        conn.commit()
        
    print("--- ĐÃ KẾT NỐI VÀO DATABASE SQLITE LOCAL THÀNH CÔNG ---")

else:
    # ----------------------------------------------------------------
    # CHẠY TRÊN MÂY (SUPABASE PROD - POSTGRESQL)
    # ----------------------------------------------------------------
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    # Tạo bảng kiểu Postgres (Dùng SERIAL)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS yoga_data (
            id SERIAL PRIMARY KEY,
            video_url TEXT,
            content_html TEXT
        );
    """)
    conn.commit()
    
    # Kiểm tra và nạp dữ liệu mẫu cho Postgres nếu bảng trống
    cursor.execute("SELECT COUNT(*) FROM yoga_data;")
    if cursor.fetchone()[0] == 0:
        # Postgres dùng dấu phần trăm s (%s) làm tham số truyền vào
        cursor.execute(
            "INSERT INTO yoga_data (video_url, content_html) VALUES (%s, %s);",
            ('https://youtu.be/1R6c6ABgDeE?si=5o8zf2awDTRHYDka', '<div class="yoga-card">Bài tập Yoga Thư giãn sâu đoạn 1</div><div class="yoga-card">Động tác kéo giãn cơ đoạn 2</div>')
        )
        cursor.execute(
            "INSERT INTO yoga_data (video_url, content_html) VALUES (%s, %s);",
            ('https://youtu.be/1R6c6ABgDeE?si=5o8zf2awDTRHYDka', '<div class="yoga-card">Belly Dance Đánh hông cơ bản đoạn 1</div><div class="yoga-card">Sóng bụng dẻo dai đoạn 2</div>')
        )
        conn.commit()
        
    print("--- ĐÃ KẾT NỐI VÀO DATABASE SUPABASE PROD THÀNH CÔNG ---")

# Đóng tài nguyên sau khi khởi tạo xong (Dùng chung cho cả 2 môi trường)
cursor.close()
conn.close()



def check_or_create_user_local(email):
    conn_u = sqlite3.connect("app.db", check_same_thread=False)
    conn_u.row_factory = sqlite3.Row
    cursor_u = conn_u.cursor()
    cursor_u.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            role TEXT DEFAULT 'FREE'
        )
    """)
    conn_u.commit()
    cursor_u.execute("SELECT email, role FROM users WHERE email = ?", (email,))
    row_u = cursor_u.fetchone()
    if row_u:
        result = dict(row_u)
    else:
        cursor_u.execute("INSERT INTO users (email, role) VALUES (?, 'FREE')", (email,))
        conn_u.commit()
        result = {"email": email, "role": "FREE"}
    conn_u.close()
    return result


# =================================================================
# 🛡️ KIỂM SOÁT ĐĂNG NHẬP CHỐNG F5 & ĐỒNG BỘ REAL-TIME KHÔNG LỖI
# =================================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = ""
    st.session_state["user_role"] = "FREE"
    st.session_state["logged_in_user"] = ""

if "iframe_data_store" not in st.session_state:
    st.session_state.iframe_data_store = "{}"

cookie_email = controller.get("mydoje_user_email")

# 🔄 ĐỒNG BỘ REAL-TIME CHUẨN: Lấy email từ session hoặc cookie để ép đọc DB liên tục khi F5
active_email = st.session_state.user_email if st.session_state.user_email else cookie_email

if active_email:
    user_record = check_or_create_user_local(active_email)
    st.session_state.authenticated = True
    st.session_state.user_email = active_email
    st.session_state["logged_in_user"] = active_email
    st.session_state["user_role"] = user_record["role"]  # Luôn luôn lấy quyền từ Database gốc
    controller.set("mydoje_user_email", active_email)
    controller.set("mydoje_user_role", user_record["role"])

if authenticator:
    try: authenticator.check_authenticity()
    except: pass

    if st.session_state.get("connected", False):
        user_info = st.session_state.get("user_info", {})
        user_email = user_info.get("email") or st.session_state.get("email")
        if user_email:
            user_record = check_or_create_user_local(user_email)
            st.session_state.authenticated = True
            st.session_state.user_email = user_email
            st.session_state["logged_in_user"] = user_email
            st.session_state["user_role"] = user_record["role"]
            controller.set("mydoje_user_email", user_email)
            controller.set("mydoje_user_role", user_record["role"])
            time.sleep(0.2)

if "code" in st.query_params and not st.session_state.authenticated:
    st.session_state.authenticated = True
    st.session_state.user_email = "user.oauth2@gmail.com"
    st.session_state["logged_in_user"] = "user.oauth2@gmail.com"
    st.session_state["user_role"] = "FREE"  
    controller.set("mydoje_user_email", "user.oauth2@gmail.com")
    controller.set("mydoje_user_role", "FREE")
    time.sleep(0.2)
    st.query_params.clear()
    st.rerun()


# =================================================================
# 🎨 KHỞI TẠO BIẾN TRẠNG THÁI NGÔN NGỮ & THEME HỆ THỐNG
# =================================================================
if "app_language" not in st.session_state:
    st.session_state.app_language = "Tiếng Việt"

if "app_theme" not in st.session_state:
    st.session_state.app_theme = "☀️ Light"

# 1. Định nghĩa các biến màu sắc tĩnh (Giữ nguyên cấu trúc theme_css cũ của bạn cho Iframe)
if st.session_state.app_theme == "☀️ Light":
    st_bg_color = "#ffffff"
    st_text_color = "#333333"
    card_bg_color = "#f9f9f9"
    border_color = "#cccccc"
    
    theme_css = {
        "body_bg": "#ffffff", "sheet_bg": "#ffffff", "text_color": "#333333",
        "table_text": "#000000", "cell_bg": "#ffffff", "border_color": "#cccccc",
        "navbar_bg": "#f0f4f9", "navbar_border": "#1a73e8", "navbar_text": "#101010"
    }
    custom_widgets_css = ""
else:
    st_bg_color = "#121212"
    st_text_color = "#ffffff"
    card_bg_color = "#1e1e1e"
    border_color = "#555555"
    
    theme_css = {
        "body_bg": "#121212", "sheet_bg": "#1e1e1e", "text_color": "#ffffff",
        "table_text": "#ffffff", "cell_bg": "#2d2d2d", "border_color": "#555555",
        "navbar_bg": "#2d2d2d", "navbar_border": "#bb86fc", "navbar_text": "#ffffff"
    }
    
    # CSS bổ sung riêng cho các Input Widget khi ở Dark Mode
    custom_widgets_css = """
    div[data-baseweb="select"], div[data-baseweb="input"], .stSelectbox, .stTextInput input {
        background-color: #1e1e1e !important; color: #ffffff !important; border-color: #444444 !important;
    }
    button[data-baseweb="tab"] { color: #aaaaaa !important; }
    button[aria-selected="true"] { color: #bb86fc !important; border-bottom-color: #bb86fc !important; }
    """

# 2. Đổ bộ CSS chuẩn vào toàn trang - Tuyệt đối không bóp nghẹt padding-top của block-container hay h1 nữa
st.markdown(f"""
    <style>
    /* Ẩn các nút điều hướng sidebar thừa thãi của hệ thống */
    [data-testid="stSidebarCollapseButton"] {{ display: none !important; }}
    [data-testid="stSidebar"] {{ display: none !important; }}
    
    /* Đồng bộ nền mượt mà, giữ nguyên padding gốc của Streamlit để bảo vệ chữ không bị che mất */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ 
        background-color: {st_bg_color} !important; 
    }}
    
    /* Ép màu chữ đồng loạt theo chủ đề */
    h1, h2, h3, h4, h5, h6, p, span, label, th, td, .stMarkdown, [data-testid="stMarkdownContainer"] p {{ 
        color: {st_text_color} !important; 
    }}
    
    /* Khung Card hiển thị nội dung khóa học (Tab 2 & Tab 3) */
    .belly-flow-card {{
        background-color: {card_bg_color} !important; 
        padding: 22px !important; 
        border-radius: 12px !important;
        border-left: 6px solid #1b8a5a !important; 
        border: 1px solid {border_color};
        color: {st_text_color} !important; 
        font-family: sans-serif !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important; 
        margin-bottom: 20px !important; 
        line-height: 1.6 !important;
    }}
    
    /* Nhúng các tùy biến widget nâng cao */
    {custom_widgets_css}
    </style>
""", unsafe_allow_html=True)


# =================================================================
# 🌐 TỰ ĐỘNG NẠP TỪ ĐIỂN ĐA NGÔN NGỮ TỪ THƯ MỤC "lang"
# =================================================================
file_name = "vi.json" if st.session_state.app_language == "Tiếng Việt" else "en.json"
lang_file_path = os.path.join(os.path.dirname(__file__), "lang", file_name)

try:
    with open(lang_file_path, "r", encoding="utf-8") as f:
        lang = json.load(f)
except Exception as e:
    st.error(f"❌ Không thể tải file ngôn ngữ từ đường dẫn: {lang_file_path}! Lỗi: {e}")
    st.stop()
    

# =================================================================
# GIAO DIỆN ĐĂNG NHẬP
# =================================================================
if not st.session_state.authenticated:
    st.title(lang["app_title"])
    st.subheader("🔐 LOGIN / PERMISSION CONTROL")
    
    test_role = st.selectbox("Simulate Account Rank / Giả lập hạng:", ["FREE", "PREMIUM", "ADMIN"], key="login_simulate_role_box")
    auth_method = st.radio("Authentication Method / Phương thức đăng nhập:", ["Google Login", "Email OTP"], horizontal=True, key="login_auth_method_radio")
    
    if auth_method == "Google Login":
        if authenticator:
            with st.container(): authenticator.login()
        else:
            google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&response_type=code&scope=openid%20email%20profile"
            st.markdown(f'<a href="{google_auth_url}" target="_self" style="text-decoration:none;"><div style="background-color: #df4930; color: white; text-align: center; padding: 12px; border-radius: 5px; font-weight: bold; cursor: pointer;">🛑 LOGIN WITH GOOGLE ACCOUNT</div></a>', unsafe_allow_html=True)
            
    elif auth_method == "Email OTP":
        email_input = st.text_input("Enter Email / Nhập Email:", placeholder="example@gmail.com", key="login_email_input_field")
        if "generated_otp" not in st.session_state: 
            st.session_state.generated_otp = ""
            st.session_state.target_email = ""
            
        if st.session_state.generated_otp == "":
            if st.button("Send OTP to Email", key="login_send_otp_btn"):
                if email_input.strip():
                    def send_otp_email_inner(receiver_email, otp_code):
                        try:
                            msg = MIMEMultipart()
                            msg['From'] = SENDER_EMAIL
                            msg['To'] = receiver_email
                            msg['Subject'] = f"[{otp_code}] Verification Code"
                            body = f"<h3>Your OTP Verification code is: <b style='font-size: 20px; color: #1b8a5a;'>{otp_code}</b></h3>"
                            msg.attach(MIMEText(body, 'html', 'utf-8'))
                            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                                server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
                            return True
                        except: return False

                    otp = str(random.randint(100000, 999999))
                    if send_otp_email_inner(email_input.strip(), otp):
                        st.session_state.generated_otp = otp
                        st.session_state.target_email = email_input.strip()
                        st.success("OTP Code has been sent successfully!")
                        st.rerun()
                else:
                    st.warning("Please input an email address first!")
        else:
            otp_code = st.text_input("Enter 6-digit OTP:", type="password", key="login_otp_code_verify_field")
            if st.button("Confirm Login", type="primary", key="login_confirm_submit_btn"):
                if otp_code == st.session_state.generated_otp:
                    user_rec = check_or_create_user_local(st.session_state.target_email)
                    final_role = test_role if test_role != "FREE" else user_rec["role"]
                    
                    st.session_state.authenticated = True
                    st.session_state.user_email = st.session_state.target_email
                    st.session_state["logged_in_user"] = st.session_state.target_email
                    st.session_state["user_role"] = final_role
                    
                    controller.set("mydoje_user_email", st.session_state.target_email)
                    controller.set("mydoje_user_role", final_role)
                    time.sleep(0.3)
                    st.rerun()
                else:
                    st.error("Invalid OTP Code!")
    st.stop()


# =================================================================
# 🏢 GIAO DIỆN CHÍNH TRÊN ĐẦU TRANG (TOP NAVBAR)
# =================================================================
st.title(lang["app_title"])

top_col1, top_col2, top_col3, top_col4, top_col5 = st.columns([2.2, 1.6, 0.9, 0.8, 0.7])

with top_col1:
    st.markdown(f"""
    <div style="background-color: {theme_css['navbar_bg']}; padding: 6px 12px; border-radius: 6px; border: 1px solid {theme_css['navbar_border']}; font-size: 14px; text-align: center; color: {theme_css['navbar_text']}; font-family: sans-serif; height: 38px; line-height:24px;">
        {lang['welcome']}: <b>{st.session_state.user_email}</b> ({lang['membership_tier']}: <span style='color:#dc2626; font-weight:bold;'>{st.session_state['user_role']}</span>)
    </div>
    """, unsafe_allow_html=True)

with top_col2:
    current_lang = st.selectbox("🌐 Lang", ["Tiếng Việt", "English"], index=0 if st.session_state.app_language == "Tiếng Việt" else 1, label_visibility="collapsed", key="navbar_lang_selector")
    if current_lang != st.session_state.app_language:
        st.session_state.app_language = current_lang
        st.rerun()

with top_col3:
    chosen_theme = st.selectbox("🎨 Theme", ["☀️ Light", "🌙 Dark"], index=0 if st.session_state.app_theme == "☀️ Light" else 1, label_visibility="collapsed", key="navbar_theme_selector")
    if chosen_theme != st.session_state.app_theme:
        st.session_state.app_theme = chosen_theme
        st.rerun()

with top_col4:
    if st.button(lang["logout_btn"], use_container_width=True, key="navbar_logout_btn"):
        if authenticator:
            try: authenticator.logout()
            except: pass
        controller.remove("mydoje_user_email")
        controller.remove("mydoje_user_role")
        time.sleep(0.2)
        for key in ["connected", "user_info", "email", "user_email", "user_role", "logged_in", "authenticated", "generated_otp", "target_email"]:
            if key in st.session_state: del st.session_state[key]
        st.rerun()

with top_col5:
    st.write("")

st.markdown("---")


# =====================================================================
# ✉️ HÀM GỬI EMAIL PREMIUM (Đặt trên hệ thống Tabs để gọi khi cần)
# =====================================================================
def send_PREMIUM_upgrade_email(receiver_email):
    if not receiver_email: return False
    try:
        if not SENDER_EMAIL or not SENDER_PASSWORD: return False
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        msg['Subject'] = "🌟 Premium Activation Details - MYDOJE"
        body = f"""
        <h3>Thank you for your interest in our premium subscription!</h3>
        <p>To unlock Tab 2 (Belly Dance) & Tab 3 (Private Yoga), please finalize the bank transfer:</p>
        <ul>
            <li><b>Amount:</b> 199.000đ / month</li>
            <li><b>Bank name:</b> Vietcombank</li>
            <li><b>Account number:</b> 1234567890</li>
            <li><b>Transfer Code:</b> DK KHUNG MYDOJE PREMIUM {receiver_email}</li>
        </ul>
        <p>Your access will be provisioned automatically once the transaction is captured.</p>
        """
        msg.attach(MIMEText(body, 'html', 'utf-8'))
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        return True
    except: return False


# =====================================================================
# 🧭 HỆ THỐNG TABS CHỨC NĂNG CHÍNH ĐƯỢC ĐƯA LÊN TRÊN CÙNG (DƯỚI NAVBAR)
# =====================================================================
tab1, tab_belly, tab_yoga = st.tabs([lang["tab_1_title"], lang["tab_2_title"], lang["tab_3_title"]])

# ---------------------------------------------------------------------
# NỘI DUNG TAB 1: BIÊN SOẠN NHẠC
# ---------------------------------------------------------------------
with tab1:
    title_text = lang.get("tab1_info_title", "🪜 KHUNG aa")
    desc_text = lang.get("tab1_info_desc", "💡 Khung aa")
    video_text = lang.get("tab1_video_lbl", "▶️ Video hướng dẫn sử dụng Khung aa")

    st.subheader(title_text)
    st.info(f"""
    {desc_text}\n
    {video_text} [bấm vào đây](https://youtube.com)
    """)
    
    # 📦 Khởi tạo dữ liệu mặc định ban đầu cho bảng nhạc
    DEFAULT_DATA = {
        "cell_1_1": "[", "cell_1_2": "DO", "cell_1_3": "RE", "cell_1_4": "MI", "cell_1_5": "FA",
        "cell_1_6": "SOL", "cell_1_7": "LA", "cell_1_8": "SI", "cell_1_9": "JE", "cell_1_10": "] n",
        "cell_7_1": "[", "cell_7_2": "DO", "cell_7_3": "RE", "cell_7_4": "MI", "cell_7_5": "FA",
        "cell_7_6": "SOL", "cell_7_7": "LA", "cell_7_8": "SI", "cell_7_9": "JE", "cell_7_10": "] n"
    }
    DEFAULT_JSON_STR = json.dumps(DEFAULT_DATA)

    # --- HÀM TRÍCH XUẤT STRING JSON SẠCH TUYỆT ĐỐI ---
    def clean_json_string(raw_input):
        if raw_input is None:
            return DEFAULT_JSON_STR
        if isinstance(raw_input, str):
            cleaned = raw_input.strip()
            if cleaned.startswith("{") and cleaned.endswith("}"):
                return cleaned
        if not isinstance(raw_input, str):
            if hasattr(raw_input, "value") and isinstance(raw_input.value, str):
                raw_input = raw_input.value
            elif hasattr(raw_input, "data") and isinstance(raw_input.data, str):
                raw_input = raw_input.data
            else:
                try: raw_input = str(raw_input)
                except: return DEFAULT_JSON_STR
        cleaned = str(raw_input).strip()
        if "st.components.v1" in cleaned or "DeltaGenerator" in cleaned or "html" in cleaned:
            backup = st.session_state.get("current_sheet_json", DEFAULT_JSON_STR)
            if isinstance(backup, str) and backup.strip().startswith("{"):
                return backup.strip()
            return DEFAULT_JSON_STR
        return cleaned if (cleaned.startswith("{") and cleaned.endswith("}")) else DEFAULT_JSON_STR

    # 🔐 Đảm bảo các biến State quản lý Iframe và Bài hát luôn tồn tại
    if "selected_sheet_id" not in st.session_state: st.session_state["selected_sheet_id"] = None
    if "sheet_title_input" not in st.session_state: st.session_state["sheet_title_input"] = lang.get("untitled_record", "Bản ghi chưa đặt tên")
    if "current_sheet_json" not in st.session_state: st.session_state["current_sheet_json"] = DEFAULT_JSON_STR
    if "iframe_key" not in st.session_state: st.session_state["iframe_key"] = "music_sheet_init"
    if "iframe_data_store" not in st.session_state: st.session_state["iframe_data_store"] = DEFAULT_JSON_STR

    # =====================================================================
    # 🔥 🔥 BỘ HỨNG VÀ ĐỒNG BỘ DỮ LIỆU TỪ IFRAME (QUAN TRỌNG NHẤT KHẮC PHỤC LỖI MẤT DATA)
    # =====================================================================
    url_grid_data = st.query_params.get("grid_data", None)
    if url_grid_data: 
        cleaned_url_data = clean_json_string(url_grid_data)
        # Đồng bộ thẳng vào kho lưu trữ tạm thời để nút SAVE xử lý đúng
        st.session_state["iframe_data_store"] = cleaned_url_data
        st.session_state["current_sheet_json"] = cleaned_url_data

    # Lấy thông tin người dùng và thời gian
    current_user = st.session_state.get('logged_in_user', '')
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 📊 1. XỬ LÝ LẤY DỮ LIỆU BẢN GHI
    try: records_list = db.get_all_records() 
    except: records_list = []

    new_track_label = f"🎶 {lang.get('new_record_option', 'Tạo mới bản ghi')}"
    sheet_options = {new_track_label: None}
    for r in records_list:
        if "user_email" in r and r["user_email"] != current_user:
            continue
        sheet_options[f"🎵 {r['title']} (ID: {r['id']})"] = r["id"]

    list_options = list(sheet_options.keys())

    current_id = st.session_state["selected_sheet_id"]
    default_index = 0
    if current_id is not None:
        for idx, name in enumerate(list_options):
            if sheet_options[name] == current_id:
                default_index = idx
                break

    # Giao diện Selectbox
    col_meta1, col_meta2 = st.columns([3, 2])

    with col_meta2:
        selectbox_dynamic_key = f"sheet_db_selectbox_{st.session_state.app_language}_{st.session_state.get('iframe_key', 'init')}"
        selected_option = st.selectbox(
            lang.get("select_record", "Chọn bài nhạc từ thư viện của bạn:"), 
            options=list_options, 
            index=default_index,
            key=selectbox_dynamic_key
        )
        
        if sheet_options[selected_option] != st.session_state["selected_sheet_id"]:
            st.session_state["selected_sheet_id"] = sheet_options[selected_option]
            st.query_params.clear()

            if st.session_state["selected_sheet_id"] is not None:
                record_data = db.get_record_by_id(st.session_state["selected_sheet_id"])
                if record_data:
                    st.session_state["sheet_title_input"] = record_data["title"]
                    st.session_state["current_sheet_json"] = record_data["data_json"] if record_data["data_json"] else DEFAULT_JSON_STR
            else:
                st.session_state["sheet_title_input"] = lang.get("untitled_record", "Bản ghi chưa đặt tên")
                st.session_state["current_sheet_json"] = DEFAULT_JSON_STR

            st.session_state["iframe_data_store"] = st.session_state["current_sheet_json"]
            st.session_state["iframe_key"] = f"sheet_{time.time()}"
            st.rerun()

    with col_meta1:
        if st.session_state["selected_sheet_id"] is not None: 
            st.markdown(f"<p style='margin-bottom:2px; font-size:14px;'>{lang.get('record_opening_lbl', 'Bản ghi đang mở:')}</p><h3 style='margin-top:0; color:#1a73e8;'>🎵 {st.session_state['sheet_title_input']}</h3>", unsafe_allow_html=True)

            c_ren1, c_ren2 = st.columns([3, 1])
            with c_ren1:
                rename_input_val = st.text_input(lang.get("rename_placeholder", "Nhập tên mới vào đây để đổi:"), value=st.session_state["sheet_title_input"], key="rename_input_field_tab1", label_visibility="collapsed")
            with c_ren2:
                if st.button(lang.get("btn_rename", "📝 ĐỔI TÊN"), use_container_width=True, key="btn_submit_rename_tab1"):  
                    if rename_input_val.strip() and rename_input_val.strip() != st.session_state["sheet_title_input"]:
                        db.update_record_title(st.session_state["selected_sheet_id"], rename_input_val.strip())
                        st.session_state["sheet_title_input"] = rename_input_val.strip()
                        st.toast(lang.get("msg_success_rename", "Đã đổi tên bài nhạc thành công!"))
                        st.rerun()
        else: 
            st.session_state["sheet_title_input"] = st.text_input(lang.get("input_title_label", "Tạo tên cho bản ghi mới:"), value=st.session_state["sheet_title_input"], key="new_title_input_field")

    # 🎛️ 3. THANH HÀNH ĐỘNG BỐN NÚT (ĐÃ FIX CHỐNG XÓA / BẢNG TRẮNG)
    st.write("")
    c_act1, c_act2, c_act3, c_act4 = st.columns([1, 1, 1, 1])

    with c_act1:
        if st.button(lang.get("btn_save", "💾 SAVE RECORD"), type="primary", use_container_width=True, key="btn_save_music_tab1"):  
            # KIỂM TRA CHẶN DỮ LIỆU RỖNG TỪ IFRAME
            raw_data = st.session_state.get("iframe_data_store", "{}")
            if not raw_data or str(raw_data).strip() == "{}" or "cell_" not in str(raw_data):
                raw_data = st.session_state.get("current_sheet_json", DEFAULT_JSON_STR)
                
            latest_grid_data = clean_json_string(raw_data)
            st.query_params.clear()
            current_title_to_save = st.session_state["sheet_title_input"].strip()
            
            if not current_title_to_save or current_title_to_save == lang.get("untitled_record", "Bản ghi chưa đặt tên"):
                st.error(lang.get("msg_error_title", "Vui lòng nhập một tên tiêu đề hợp lệ!"))
            else:
                if st.session_state["selected_sheet_id"] is None:
                    try: new_id = db.add_record(current_title_to_save, latest_grid_data)
                    except: new_id = db.insert_record(current_title_to_save, latest_grid_data)
                    st.session_state["selected_sheet_id"] = new_id
                else:
                    db.update_record_data(st.session_state["selected_sheet_id"], latest_grid_data)
                    try: current_db_title = db.get_record_by_id(st.session_state["selected_sheet_id"])["title"]
                    except: current_db_title = ""
                    if current_title_to_save != current_db_title:
                        db.update_record_title(st.session_state["selected_sheet_id"], current_title_to_save)

                st.session_state["current_sheet_json"] = latest_grid_data
                st.session_state["iframe_data_store"] = latest_grid_data
                st.toast(lang.get("msg_success_save", "Đã lưu dữ liệu vào hệ thống thành công!"))
                st.session_state["iframe_key"] = f"save_{time.time()}"
                st.rerun()

    with c_act2:
        if st.button(lang.get("btn_reset", "🔄 RESET BLANK"), use_container_width=True, key="btn_reset_grid_tab1"):  
            # Chỉ reset dữ liệu lưới nhạc về mặc định (bảng trống)
            st.session_state["current_sheet_json"] = DEFAULT_JSON_STR
            st.session_state["iframe_data_store"] = DEFAULT_JSON_STR
            
            st.query_params.clear()
            # Buộc Iframe render lại với lưới trống của bài hiện tại
            st.session_state["iframe_key"] = f"forced_reset_{time.time()}"
            st.toast(lang.get("msg_reset_success", "🧹 Đã xóa sạch các nốt trên lưới nhạc hiện tại!"))
            st.rerun()

    with c_act3:
        if st.button(lang.get("btn_duplicate", "👯 DUPLICATE"), use_container_width=True, key="btn_duplicate_sheet_tab1"):  
            if st.session_state["selected_sheet_id"] is not None:
                st.query_params.clear()
                dup_title = f"{st.session_state['sheet_title_input']} ({lang.get('copy_suffix', 'Bản sao')})"

                # ƯU TIÊN LẤY TỪ DATABASE HOẶC KHÓA CỨNG ĐỂ CHỐNG BẢNG TRẮNG
                record_goc = db.get_record_by_id(st.session_state["selected_sheet_id"])
                if record_goc:
                    record_goc = dict(record_goc)
                
                if record_goc and record_goc.get("data_json"):
                    dup_grid_data = record_goc["data_json"]
                else:
                    raw_dup_data = st.session_state.get("current_sheet_json", DEFAULT_JSON_STR)
                    if not raw_dup_data or "cell_" not in str(raw_dup_data):
                        raw_dup_data = st.session_state.get("iframe_data_store", DEFAULT_JSON_STR)
                    dup_grid_data = clean_json_string(raw_dup_data)

                try: 
                    new_dup_id = db.add_record(dup_title, dup_grid_data)
                except: 
                    new_dup_id = db.insert_record(dup_title, dup_grid_data)

                st.session_state["selected_sheet_id"] = new_dup_id
                st.session_state["sheet_title_input"] = dup_title
                st.session_state["current_sheet_json"] = dup_grid_data
                st.session_state["iframe_data_store"] = dup_grid_data
                
                st.session_state["iframe_key"] = f"duplicate_{time.time()}"
                st.toast(lang.get("msg_duplicate_success", "👯 Đã sao chép bản ghi nhạc thành công!"))
                st.rerun()
            else:
                st.warning(lang.get("msg_warning_duplicate", "Bạn không thể sao chép một bản ghi chưa được lưu!"))

    with c_act4:
        if st.button(lang.get("btn_delete", "🗑️ DELETE"), type="secondary", use_container_width=True, key="btn_delete_sheet_tab1"):  
            if st.session_state["selected_sheet_id"] is not None:
                try: db.delete_record(st.session_state["selected_sheet_id"])
                except: db.delete_record_by_id(st.session_state["selected_sheet_id"])

                st.session_state["selected_sheet_id"] = None
                st.session_state["sheet_title_input"] = lang.get("untitled_record", "Bản ghi chưa đặt tên")
                st.session_state["current_sheet_json"] = DEFAULT_JSON_STR
                st.session_state["iframe_data_store"] = DEFAULT_JSON_STR
                st.session_state["iframe_key"] = f"delete_{time.time()}"
                st.toast(lang.get("msg_delete_success", "🗑️ Đã xóa bản ghi nhạc khỏi hệ thống!"))
                st.rerun()
            else:
                st.warning(lang.get("msg_warning_delete", "Bản ghi mới chưa lưu không thể xóa!"))

    # =====================================================================
    # 🎹 4. KHỞI TẠO BIẾN ĐỒNG BỘ VÀ XỬ LÝ HTML/PNG
    # =====================================================================
    try: parsed_json = json.loads(clean_json_string(st.session_state["current_sheet_json"]))
    except: parsed_json = DEFAULT_DATA

    def get_val(cell_id, default_val=""): return parsed_json.get(cell_id, default_val)
    def get_class(cell_id): return "user-note" if cell_id in parsed_json and parsed_json[cell_id] != DEFAULT_DATA.get(cell_id, "") else ""

    current_title = st.session_state["sheet_title_input"]
    safe_filename = re.sub(r'[\\/*?:"<>| ]', '_', current_title) + ".png" if current_title else "music_sheet.png"

    html_body_bg = "#ffffff" if st.session_state.get("app_theme", "☀️ Light") == "☀️ Light" else "#1e1e1e"
    html_text_color = "#000000" if st.session_state.get("app_theme", "☀️ Light") == "☀️ Light" else "#ffffff"
    

       
    # =====================================================================
    # ĐOẠN SỬA LỖI: NHÚNG MÃ NGUỒN HTML IFRAME EDITOR & THANH HÀNH ĐỘNG ĐỒNG BỘ
    # =====================================================================
    html_src = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
                <style>
                    body {{ 
                        background:{html_body_bg}; 
                        font-family:Arial, sans-serif; 
                        margin:0; 
                        padding:5px; 
                        color:{html_text_color}; 
                    }}
                    .sheet-container {{ width:100%; max-width:1460px; margin:5px auto; }}
                    .sheet {{ 
                        width:100%; 
                        border:2px dashed #1b8a5a; 
                        padding:15px; 
                        background:#ffffff; 
                        overflow-x: auto; 
                        box-sizing: border-box; 
                    }}
                    table {{ 
                        width:100%; 
                        border-collapse:collapse; 
                        table-layout:fixed; 
                        background:#ffffff; 
                        margin-bottom: 0px;
                    }}
                    td {{ 
                        border:1px solid #444; 
                        height:32px; 
                        text-align:center; 
                        font-size:13px; 
                        font-weight:bold; 
                        color:#000; 
                        background:#ffffff; 
                        cursor:pointer; 
                        word-wrap: break-word;
                        white-space: pre-wrap;
                    }}
                    /* Class chuẩn: Chỉ tô đậm TRÊN/DƯỚI, ẩn hoàn toàn TRÁI/PHẢI */
                    .bold-border {{
                        border-top: 3px solid #000 !important;
                        border-bottom: 3px solid #000 !important;
                        border-left: none !important;
                        border-right: none !important;
                    }}
                    /* Chỉ tô đen hoàn toàn cho dòng nốt nhạc DO RE MI... */ 
                    .black-note-bar {{ background:#000!important; color:#fff!important; cursor:not-allowed!important; font-size:14px; }}
                    
                    /* Class chỉ tô đậm 2 cạnh TRÊN và DƯỚI của ô */
                    .bold-border {{
                        border-top: 3px solid #000 !important;
                        border-bottom: 3px solid #000 !important;
                    }}
                    /* Các ô tiêu đề bị khóa: Giữ màu trắng tinh, đổi con trỏ thành dấu cấm */
                    .locked-title {{ background:#ffffff!important; color:#000!important; cursor:not-allowed!important; }}
                    
                    /* Định dạng các loại ô đặc biệt */ 
                    .gray {{ background:#ffffff!important; }} 
                    .purple {{ background:#f2e1f7!important; }}
                    .treble {{ font-size:90px; background:#ffffff!important; width: 65px; border-right: 1px solid #444; cursor:default; }}
                    .user-note {{ color:#1a73e8!important; background:#e8f0fe!important; }}
                    
                    /* Thanh ngăn cách Foundation BƯỚC */                    
                    .foundation-bar {{
                        background-image: radial-gradient(#444 20%, transparent 20%), radial-gradient(#444 20%, transparent 20%);
                        background-size: 6px 6px;
                        background-position: 0 0, 3px 3px;
                        background-color: #e5e5e5;
                        color: #0d1117;
                        font-weight: bold;
                        font-size: 16px;
                        letter-spacing: 2px;
                        height: 25px;
                        text-align: center;
                        cursor: default;
                    }}
                    /* Bảng thông tin văn bản bên dưới */ 
                    .info-table td {{
                        text-align: left;
                        padding-left: 10px;
                        font-size: 13px;
                        height: 35px;
                        background:#ffffff!important;
                    }}
                    .info-label {{ font-weight: bold; cursor: default; }}
                    .info-purple {{ color: #7b1fa2; font-weight: bold; cursor: default; }}
                     
                    .btn-export {{ 
                        background:#1b8a5a; 
                        color:#fff; 
                        border:none; 
                        padding:10px 20px; 
                        font-weight:bold; 
                        border-radius:5px; 
                        cursor:pointer; 
                        margin-bottom:10px; 
                    }}
                    .foundation-bar {{
                        padding: 15px 0 !important;
                    }}
                    
                </style>
                
                <script>
                    // 1. DANH SÁCH 23 Ô ĐƯỢC PHÉP CHỈNH SỬA DỮ LIỆU
                    const ALLOWED_EDIT_CELLS = [
                        "cell_1", "cell_2", "cell_3", "cell_4", "cell_5", "cell_6", "cell_7", "cell_8", 
                        "cell_9", "cell_10", "cell_11", "cell_12", "cell_13", "cell_14", "cell_15", "cell_16",
                        "cell_17", "cell_18", "cell_19", "cell_20", "cell_21", "cell_22", "cell_23"
                    ];

                    // 2. CHỨC NĂNG CŨ: Điền ID vào đây nếu bạn muốn chủ động khóa thêm ô nào trong 23 ô trên
                    let lockedCells = []; 
                    
                    // Tự động kiểm tra quyền sửa và thiết lập giao diện khi tải trang
                    window.addEventListener("DOMContentLoaded", () => {{
                        document.querySelectorAll("td[id]").forEach(cell => {{
                            let cellId = cell.id;
                            
                            // Nếu KHÔNG thuộc 23 ô tương tác, HOẶC nằm trong danh sách chủ động khóa thêm (lockedCells)
                            if (!ALLOWED_EDIT_CELLS.includes(cellId) || lockedCells.includes(cellId)) {{
                                cell.removeAttribute("onclick");
                                
                                // Nếu không thuộc nhóm thanh nốt nhạc màu đen thì chuyển thành class khóa trắng tinh
                                if (!cell.className.includes("black-note-bar")) {{
                                    cell.className = "locked-title";
                                }}
                            }}
                        }});
                    }});

                    function syncDataToParentURL() {{
                        let data = {{}}; 
                        document.querySelectorAll("td[id]").forEach(c => {{ 
                            if(!c.className.includes("locked-title") && !c.className.includes("black-note-bar")) {{
                                data[c.id] = c.innerText; 
                            }}
                        }});
                        let pUrl = new URL(window.parent.location.href); 
                        pUrl.searchParams.set("grid_data", JSON.stringify(data));
                        window.parent.history.replaceState({{}}, "", pUrl.toString());
                    }}

                    // 🔥 THÊM HÀM NÀY: Xử lý biến dấu | thành dấu xuống hàng thực tế \n
                    // Cấu hình mới: Nhận diện cụm ".." để bẻ dòng xuống hàng \n
                    function formatText(text) {{
                        if(!text) return "";
                        return text.split('..').map(item => item.trim()).join('\\n');
                    }}

                    function cellAction(e, d) {{
                        if(confirm("{lang['cell_edit_confirm']}")) {{
                            
                            // Khi khách nhấn sửa lại, tự động chuyển các dòng đang xuống hàng thành dấu ..
                            let currentText = e.innerText.replace(/\\n/g, " .. ");
                            
                            // Câu thông báo hướng dẫn siêu ngắn gọn, dễ hiểu cho cả người già lẫn trẻ nhỏ
                            let v = prompt("{lang['cell_prompt_title']}", currentText || d);
                            if(v!==null){{ 
                                e.innerText = formatText(v); 
                                e.className = e.className.includes("purple") ? "purple user-note" : "gray user-note"; 
                                syncDataToParentURL(); 
                            }}
                        }} else {{ e.innerText=""; syncDataToParentURL(); }}
                    }}

                    function exportToPNG() {{
                        html2canvas(document.getElementById("music-sheet-area"),{{useCORS:true,backgroundColor:"#ffffff"}}).then(canvas => {{
                            let a = document.createElement("a"); a.href = canvas.toDataURL("image/png"); a.download = "{safe_filename}"; a.click();
                        }});
                    }}
                </script>
            </head>
            <body>
                <div class="sheet-container">
                    <button class="btn-export" onclick="exportToPNG()">{lang['btn_export_png']}</button>
                     
                    <div id="music-sheet-area" class="sheet">
                        <table>
                            <tr>
                                <td class="treble bold-border" rowspan="1"></td>
                                <td id="bot_bracket_open" class="black-note-bar">{get_val('bot_bracket_open', '[')}</td>
                                <td id="bot_do" class="black-note-bar">{get_val('bot_do', 'DO')}</td>
                                <td id="bot_re" class="black-note-bar">{get_val('bot_re', 'RE')}</td>
                                <td id="bot_mi" class="black-note-bar">{get_val('bot_mi', 'MI')}</td>
                                <td id="bot_fa" class="black-note-bar">{get_val('bot_fa', 'FA')}</td>
                                <td id="bot_sol" class="black-note-bar">{get_val('bot_sol', 'SOL')}</td>
                                <td id="bot_la" class="black-note-bar">{get_val('bot_la', 'LA')}</td>
                                <td id="bot_si" class="black-note-bar">{get_val('bot_si', 'SI')}</td>
                                <td id="bot_je" class="black-note-bar">{get_val('bot_je', 'JE')}</td>
                                <td id="bot_bracket_close" class="black-note-bar">{get_val('bot_bracket_close', '] n')}</td>
                                <td class="treble bold-border" rowspan="1"></td> 
                            </tr>
                             
                            <tr>
                                <td class="treble bold-border" rowspan="5">𝄞</td>
                                
                                <td id="label_ht100_left" class="gray" style="font-weight:bold;" rowspan="4">{lang['lbl_ht100_side']}</td>
                                <td id="BƯỚC_1" colspan="3" class="gray">{lang['step_1']}</td>
                                <td id="BƯỚC_2" colspan="2" class="gray">{lang['step_2']}</td>
                                <td id="BƯỚC_3" class="gray">{lang['step_3']}</td>
                                <td id="BƯỚC_4" class="gray">{lang['step_4']}</td>
                                <td id="BƯỚC_5" class="gray">{lang['step_5']}</td>
                                <td id="label_ht100_right" class="gray" style="font-weight:bold;" rowspan="4">{lang['lbl_ht100_side']}</td>
                                
                            </tr>
                             
                            <tr>
                                <td id="BƯỚC_1a" colspan="3" class="gray">{lang['step_1a_title']}</td>
                                <td id="BƯỚC_2a" colspan="2" class="gray">{lang['step_2a_title']}</td>
                                <td id="BƯỚC_3a" class="gray">{lang['step_3a_title']}</td>
                                <td id="BƯỚC_4a" class="gray">{lang['step_4a_title']}</td>
                                <td id="BƯỚC_5a" class="gray">{lang['step_5a_title']}</td>
                            </tr>
                             
                            <tr>
                                <td id="sub_a1" class="gray">{lang['sub_a1']}</td>
                                <td id="sub_a2" class="gray">{lang['sub_a2']}</td>
                                <td id="sub_a3" class="gray">{lang['sub_a3']}</td>
                                <td id="sub_b1" class="gray">{lang['sub_b1']}</td>
                                <td id="sub_b2" class="gray">{lang['sub_b2']}</td>
                                <td id="sub_c1" class="gray">{lang['sub_c1']}</td>
                                <td id="sub_d1" class="gray">{lang['sub_d1']}</td>
                                <td id="sub_e1" class="gray">{lang['sub_e1']}</td>
                            </tr>
                             
                            <tr>
                                <td id="cell_1" class="gray {get_class('cell_1')}" onclick="cellAction(this, '1')">{get_val('cell_1', '')}</td>
                                <td id="cell_2" class="gray {get_class('cell_2')}" onclick="cellAction(this, '2')">{get_val('cell_2', '')}</td>
                                <td id="cell_3" class="gray {get_class('cell_3')}" style="color:#1a73e8;" onclick="cellAction(this, '3')">{get_val('cell_3', '')}</td>
                                <td id="cell_7" class="gray {get_class('cell_7')}" onclick="cellAction(this, '7')">{get_val('cell_7', '')}</td>
                                <td id="cell_9" class="gray {get_class('cell_9')}" onclick="cellAction(this, '9')">{get_val('cell_9', '')}</td>
                                <td id="cell_11" class="gray {get_class('cell_11')}" onclick="cellAction(this, '11')">{get_val('cell_11', '')}</td>
                                <td id="cell_13" class="gray {get_class('cell_13')}" onclick="cellAction(this, '13')">{get_val('cell_13', '')}</td>
                                <td id="cell_15" class="gray {get_class('cell_15')}" onclick="cellAction(this, '15')">{get_val('cell_15', '')}</td>
                            </tr>
                             
                            <tr>
                                
                                <td id="label_a200_left" class="gray" style="font-weight:bold;">{lang['lbl_a200_side']}</td>
                                <td id="cell_4" class="purple {get_class('cell_4')}" onclick="cellAction(this, '4')">{get_val('cell_4', 'Đôi ')}</td>
                                <td id="cell_5" class="gray {get_class('cell_5')}" onclick="cellAction(this, '5')">{get_val('cell_5', '')}</td>
                                <td id="cell_6" class="gray {get_class('cell_6')}" onclick="cellAction(this, '6')">{get_val('cell_6', '')}</td>
                                <td id="cell_8" class="gray {get_class('cell_8')}" onclick="cellAction(this, '8')">{get_val('cell_8', '')}</td>
                                <td id="cell_10" class="gray {get_class('cell_10')}" onclick="cellAction(this, '10')">{get_val('cell_10', '')}</td>
                                <td id="cell_12" class="gray {get_class('cell_12')}" onclick="cellAction(this, '12')">{get_val('cell_12', '')}</td>
                                <td id="cell_14" class="gray {get_class('cell_14')}" onclick="cellAction(this, '14')">{get_val('cell_14', '')}</td>
                                <td id="cell_16" class="purple {get_class('cell_16')}" onclick="cellAction(this, '16')">{get_val('cell_16', '8! </br>Sự  ')}</td>
                                <td id="label_a200_right" class="gray" style="font-weight:bold;">{lang['lbl_a200_side']}</td>
                                
                            </tr>
                             
                            <tr>
                                <td class="treble bold-border" rowspan="1"></td>   
                                <td colspan="10" class="foundation-bar">{lang['foundation_step_lbl']}</td>
                                <td class="treble bold-border" rowspan="1"></td>   
                            </tr>
                             
                            <tr>
                                <td class="treble bold-border" rowspan="1"></td> 
                                <td id="bot_bracket_open" class="black-note-bar">{get_val('bot_bracket_open', '[')}</td>
                                <td id="bot_do" class="black-note-bar">{get_val('bot_do', 'DO')}</td>
                                <td id="bot_re" class="black-note-bar">{get_val('bot_re', 'RE')}</td>
                                <td id="bot_mi" class="black-note-bar">{get_val('bot_mi', 'MI')}</td>
                                <td id="bot_fa" class="black-note-bar">{get_val('bot_fa', 'FA')}</td>
                                <td id="bot_sol" class="black-note-bar">{get_val('bot_sol', 'SOL')}</td>
                                <td id="bot_la" class="black-note-bar">{get_val('bot_la', 'LA')}</td>
                                <td id="bot_si" class="black-note-bar">{get_val('bot_si', 'SI')}</td>
                                <td id="bot_je" class="black-note-bar">{get_val('bot_je', 'JE')}</td>
                                <td id="bot_bracket_close" class="black-note-bar">{get_val('bot_bracket_close', '] n')}</td>
                                <td class="treble bold-border" rowspan="1"></td>  
                            </tr>
                        </table>

                        <table class="info-table" style="margin-top: 15px; width: 92%; margin-left: 4%;">
                            <colgroup>
                                <col style="width: 11%;">
                                <col style="width: 20%;">
                                <col style="width: 11%;">
                                <col style="width: 19%;">
                                <col style="width: 10%;">
                                <col style="width: 30%;">
                            </colgroup>
                            <tr>
                                <td class="info-label">{lang['field_lbl']}</td>
                                <td id="cell_17" onclick="cellAction(this, '17')">{get_val('cell_17', '')}</td>
                                <td class="info-label">{lang['problem_lbl']}</td>
                                <td id="cell_20" onclick="cellAction(this, '20')">{get_val('cell_20', '')}</td>
                                <td class="info-purple" style="text-align:center;">{lang['result_lbl']}</td>
                                <td id="cell_22" onclick="cellAction(this, '22')">{get_val('cell_22', '')}</td>
                            </tr>
                            <tr>
                                <td class="info-label">{lang['date_lbl']}</td>
                                <td id="cell_18" onclick="cellAction(this, '18')">{get_val('cell_18', '')}</td>
                                <td class="info-label" rowspan="2">{lang['note_lbl']}</td>
                                <td id="cell_21" rowspan="2" onclick="cellAction(this, '21')">{get_val('cell_21', '')}</td>
                                <td class="info-purple" style="text-align:center;" rowspan="2">{lang['summary_lbl']}</td>
                                <td id="cell_23" rowspan="2" onclick="cellAction(this, '23')">{get_val('cell_23', '')}</td>
                                
                            </tr>
                            <tr>
                                <td class="info-label">{lang['myn_lbl']}</td>
                                <td id="cell_19" onclick="cellAction(this, '19')">{get_val('cell_19', '')}</td>                                
                            </tr>
                        </table>
                    </div>
                </div>
            </body>
            </html>
"""


    

    

    

    # 🔄 1. Render Iframe Editor lên màn hình
    with st.container(key=st.session_state["iframe_key"]): 
        transfer_json = st.components.v1.html(html_src, height=700, scrolling=True)
        
        # 🔥 ĐOẠN ĐÃ ĐƯỢC SỬA: Bộ lọc dữ liệu thông minh chặn đứng chuỗi rỗng
        if transfer_json and str(transfer_json).strip() != "{}" and "cell_" in str(transfer_json):
            st.session_state.iframe_data_store = transfer_json
            st.session_state["current_sheet_json"] = transfer_json

    st.markdown("---")
        
    # 📝 2. Hiển thị dòng ghi chú hướng dẫn chính ở cuối trang
    col_margin, col_list = st.columns([1, 10]) 

    with col_list:
        st.markdown(f"### {lang.get('steps_main_title', 'Hướng dẫn')}")
        st.markdown(f"""
        * **{lang.get('step_1_title', 'Bước 1:')}** {lang.get('step_1_desc', 'Chỉnh sửa trên lưới.')}
        * **{lang.get('step_2_title', 'Bước 2:')}** {lang.get('step_2_desc', 'Nhấn nút SAVE để lưu lại.')}
        * **{lang.get('step_3_title', 'Bước 3:')}** {lang.get('step_3_desc', 'Tận hưởng kết quả.')}
        """)

    # 🔒 3. Đóng kết nối DB an toàn khi kết thúc Tab 1
    try: conn_g.close()
    except: pass


# ---------------------------------------------------------------------
# 💃 NỘI DUNG TAB 2: BELLY DANCE (CẬP NHẬT THEO YÊU CẦU)
# ---------------------------------------------------------------------
with tab_belly:
    st.subheader(lang["belly_subtitle"])
    if st.session_state["user_role"] not in ["PREMIUM", "ADMIN"]:
        st.error(lang["premium_lock_title"])
        st.markdown(f"""
        <div style="background-color: #fffbeb; border-left: 5px solid #f59e0b; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="color: #b45309; margin-top: 0px; font-family: sans-serif;">{lang['premium_info_header']}</h3>
            <div style="background-color: #ffffff; border: 1px dashed #d1d5db; padding: 15px; border-radius: 6px; font-family: sans-serif; font-size: 15px; line-height: 1.6; color:#000;">
                • <b>{lang['premium_price_label']}:</b> <span style="color: #dc2626; font-weight: bold;">199.000đ / month</span><br>
                • <b>{lang['premium_bank_label']}:</b> Vietcombank | <b>STK:</b> <span style="font-family: monospace; font-weight: bold; color: #1e3a8a;">1234567890</span><br>
                • <b>{lang['premium_content_label']}:</b> <code style="background-color: #f3f4f6; color: #dc2626; padding: 3px 8px; border-radius: 4px; font-family: monospace; font-weight: bold;">DK KHUNG MYDOJE PREMIUM {st.session_state["logged_in_user"]}</code>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(lang["premium_email_btn"], key="btn_mail_belly"):
            if send_PREMIUM_upgrade_email(st.session_state["logged_in_user"]):
                st.success(lang["premium_email_success"])
            else:
                st.warning("SMTP Error!")
    else:
        st.success(lang["premium_welcome_belly"])
        st.write("---")
        
        conn_b = sqlite3.connect("app.db", check_same_thread=False)
        conn_b.row_factory = sqlite3.Row
        cursor_b = conn_b.cursor()
        cursor_b.execute("SELECT video_url, content_html FROM yoga_data WHERE id = 2")
        row = cursor_b.fetchone()
        conn_b.close()
        
        if row:
            video_url, content_html = row["video_url"], row["content_html"]
            if video_url: st.video(video_url)
            
            blocks = re.findall(r'<div class="yoga-card">\s*(.*?)\s*</div>', content_html, re.DOTALL)
            doan_1 = blocks[0] if len(blocks) >= 1 else "Updating segment 1..."
            doan_2 = blocks[1] if len(blocks) >= 2 else "Updating segment 2..."
            
            st.markdown(f"""
                <style>
                    .belly-flow-card {{
                        background-color: {theme_css['sheet_bg']} !important;
                        padding: 22px !important;
                        border-radius: 12px !important;
                        border-left: 6px solid #1b8a5a !important;
                        color: {theme_css['text_color']} !important;
                        font-family: sans-serif !important;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
                        margin-bottom: 20px !important;
                        line-height: 1.6 !important;
                        border: 1px solid {theme_css['border_color']};
                    }}
                </style>
                <div class="belly-flow-card">{doan_1}</div>
                <div class="belly-flow-card">{doan_2}</div>
            """, unsafe_allow_html=True)


# ---------------------------------------------------------------------
# 🧘 NỘI DUNG TAB 3: PRIVATE YOGA (CẬP NHẬT THEO YÊU CẦU)
# ---------------------------------------------------------------------
with tab_yoga:
    st.subheader(lang["yoga_subtitle"])
    if st.session_state["user_role"] not in ["PREMIUM", "ADMIN"]:
        st.error(lang["premium_lock_title"])
        st.markdown(f"""
        <div style="background-color: #fffbeb; border-left: 5px solid #f59e0b; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="color: #b45309; margin-top: 0px; font-family: sans-serif;">{lang['premium_info_header']}</h3>
            <div style="background-color: #ffffff; border: 1px dashed #d1d5db; padding: 15px; border-radius: 6px; font-family: sans-serif; font-size: 15px; line-height: 1.6; color:#000;">
                • <b>{lang['premium_price_label']}:</b> <span style="color: #dc2626; font-weight: bold;">199.000đ / month</span><br>
                • <b>{lang['premium_bank_label']}:</b> Vietcombank | <b>STK:</b> <span style="font-family: monospace; font-weight: bold; color: #1e3a8a;">1234567890</span><br>
                • <b>{lang['premium_content_label']}:</b> <code style="background-color: #f3f4f6; color: #dc2626; padding: 3px 8px; border-radius: 4px; font-family: monospace; font-weight: bold;">DK KHUNG MYDOJE PREMIUM {st.session_state["logged_in_user"]}</code>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(lang["premium_email_btn"], key="btn_mail_yoga"):
            if send_PREMIUM_upgrade_email(st.session_state["logged_in_user"]):
                st.success(lang["premium_email_success"])
            else:
                st.warning("SMTP Error!")
    else:
        st.success(lang["premium_welcome_yoga"])
        st.write("---")
        
        conn_y = sqlite3.connect("app.db", check_same_thread=False)
        conn_y.row_factory = sqlite3.Row
        cursor_y = conn_y.cursor()
        cursor_y.execute("SELECT video_url, content_html FROM yoga_data WHERE id = 1")
        row_y = cursor_y.fetchone()
        conn_y.close()
        
        if row_y:
            video_url, content_html = row_y["video_url"], row_y["content_html"]
            if video_url: st.video(video_url)
            
            blocks = re.findall(r'<div class="yoga-card">\s*(.*?)\s*</div>', content_html, re.DOTALL)
            doan_1 = blocks[0] if len(blocks) >= 1 else "Updating segment 1..."
            doan_2 = blocks[1] if len(blocks) >= 2 else "Updating segment 2..."
            
            st.markdown(f"""
                <div class="belly-flow-card">{doan_1}</div>
                <div class="belly-flow-card">{doan_2}</div>
            """, unsafe_allow_html=True)