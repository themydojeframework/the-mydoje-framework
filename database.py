import sqlite3
import os
from datetime import datetime

DB_NAME = "app.db"

def get_connection():
    """Tạo kết nối tới SQLite vật lý và cấu hình trả về dạng Row."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Giúp lấy dữ liệu theo tên cột như một Dictionary
    return conn

def init_db():
    """Khởi tạo file app.db và tự động tạo toàn bộ hệ thống bảng dữ liệu nếu chưa có."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Bảng lưu User (Mặc định phân quyền ban đầu là FREE)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            role TEXT DEFAULT 'FREE',
            created_at TEXT
        )
    """)
    
    # 2. Bảng lưu dữ liệu Tab 1 (Sheet Nhạc và Ma trận nốt nhạc JSON)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            data_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # 3. Bảng lưu dữ liệu nâng cao cho Tab 2 (Belly Dance) & Tab 3 (Private Yoga)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS yoga_data (
            id INTEGER PRIMARY KEY,
            video_url TEXT,
            content_html TEXT
        )
    """)
    
    # Tự động chèn dữ liệu mẫu ban đầu cho Belly Dance và Yoga nếu bảng đang trống
    cursor.execute("SELECT COUNT(*) FROM yoga_data")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO yoga_data (id, video_url, content_html) 
            VALUES (1, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 
            '<div class="yoga-card">Bài tập Yoga Thư giãn sâu đoạn 1</div><div class="yoga-card">Động tác kéo giãn cơ đoạn 2</div>')
        """)
        cursor.execute("""
            INSERT INTO yoga_data (id, video_url, content_html) 
            VALUES (2, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 
            '<div class="yoga-card">Belly Dance Đánh hông cơ bản đoạn 1</div><div class="yoga-card">Sóng bụng dẻo dai đoạn 2</div>')
        """)
        
    conn.commit()
    conn.close()

# ==========================================
# PHẦN 1: CÁC HÀM XỬ LÝ USER (PHÂN QUYỀN ĐĂNG NHẬP)
# ==========================================

def check_or_create_user(email):
    """Kiểm tra user đăng nhập, nếu chưa có tự động tạo tài khoản mới hạng FREE."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    
    if not user:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO users (email, role, created_at) VALUES (?, 'FREE', ?)", (email, now))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
    conn.close()
    return user

def update_user_role(email, new_role):
    """Cập nhật thứ hạng tài khoản (Ví dụ: Nâng từ FREE lên PREMIUM hoặc ADMIN)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE email = ?", (new_role, email))
    conn.commit()
    conn.close()

# ==========================================
# PHẦN 2: CÁC HÀM XỬ LÝ TAB 1 (DANH SÁCH SHEET NHẠC)
# ==========================================

def get_all_records():
    """Lấy danh sách rút gọn (ID, Title) để xếp vào Selectbox tại Sidebar."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM records ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_record_by_id(record_id):
    """Lấy chi tiết toàn bộ dữ liệu bao gồm cả chuỗi nốt nhạc JSON của một bài nhạc."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def insert_record(title, data_json):
    """Tạo mới một bài nhạc (Khi người dùng bấm SAVE NEW trên giao diện khách)."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO records (title, data_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (title, data_json, now, now)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def update_record_data(record_id, data_json):
    """Cập nhật ma trận nốt nhạc JSON, giữ nguyên tiêu đề bài nhạc cũ."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE records SET data_json = ?, updated_at = ? WHERE id = ?",
        (data_json, now, record_id)
    )
    conn.commit()
    conn.close()

def update_record_title(record_id, new_title):
    """Đổi tên tiêu đề bài nhạc độc lập (Khi Admin/User kích hoạt tính năng RENAME)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE records SET title = ? WHERE id = ?", (new_title, record_id))
    conn.commit()
    conn.close()

def delete_record(record_id):
    """Xóa vĩnh viễn một bài nhạc khỏi hệ thống cơ sở dữ liệu."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

# ==========================================
# PHẦN 3: CÁC HÀM XỬ LÝ NỘI DUNG PREMIUM (TAB 2 & TAB 3)
# ==========================================

def get_yoga_data_by_id(content_id):
    """Lấy link video bài giảng và khối mã HTML của Belly Dance (id=2) hoặc Yoga (id=1)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT video_url, content_html FROM yoga_data WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def update_yoga_data(content_id, video_url, content_html):
    """Cập nhật link video mới hoặc chỉnh sửa các khối kiến thức phân đoạn HTML."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE yoga_data SET video_url = ?, content_html = ? WHERE id = ?",
        (video_url, content_html, content_id)
    )
    conn.commit()
    conn.close()