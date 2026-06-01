import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
import os
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st

# Kích hoạt đọc file .env dưới máy local
load_dotenv()

# Lấy cấu hình URL kết nối thông minh
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")

def get_connection():
    """Tự động kết nối tới đúng hệ quản trị cơ sở dữ liệu dựa theo môi trường."""
    global DATABASE_URL
    
    if "sqlite" in DATABASE_URL:
        conn = sqlite3.connect("app.db", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    else:
        # Làm sạch khoảng trắng thừa
        clean_url = DATABASE_URL.strip().replace('"', '').replace("'", "")
        
        # Chỉ nắn đầu ngữ nếu nó là postgresql://
        if clean_url.startswith("postgresql://"):
            clean_url = clean_url.replace("postgresql://", "postgres://", 1)
            
        try:
            # Kết nối qua cổng Pooler IPv4 kèm tham số chống nghẽn bọc sẵn trong chuỗi
            conn = psycopg2.connect(clean_url)
            return conn
        except Exception as e:
            import streamlit as st
            st.error(f"💥 LỖI KẾT NỐI SUPABASE THỰC TẾ: {str(e)}")
            raise e

def init_db():
    """Khởi tạo toàn bộ hệ thống bảng và tự động cập nhật cột thiếu cho cả 2 môi trường."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if "sqlite" in DATABASE_URL:
        # --- CẤU HÌNH BẢNG CHO SQLITE (DƯỚI MÁY) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                role TEXT DEFAULT 'FREE',
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                data_json TEXT,
                created_at TEXT,
                updated_at TEXT,
                user_email TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS yoga_data (
                id INTEGER PRIMARY KEY,
                video_url TEXT,
                content_html TEXT
            )
        """)
        
        # 🔥 BỘ SỬA LỖI TỰ ĐỘNG (MIGRATION): Thử thêm cột user_email nếu bảng cũ chưa có
        try:
            cursor.execute("ALTER TABLE records ADD COLUMN user_email TEXT DEFAULT '';")
            conn.commit()
        except sqlite3.OperationalError:
            # Nếu cột đã tồn tại rồi, SQLite sẽ báo lỗi trùng lặp và ta bỏ qua một cách an toàn
            pass

        # Chèn dữ liệu mẫu cho SQLite
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
    else:
        # --- CẤU HÌNH BẢNG CHO POSTGRESQL (SUPABASE MÂY) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE,
                role TEXT DEFAULT 'FREE',
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id SERIAL PRIMARY KEY,
                title TEXT,
                data_json TEXT,
                created_at TEXT,
                updated_at TEXT,
                user_email TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS yoga_data (
                id INT PRIMARY KEY,
                video_url TEXT,
                content_html TEXT
            )
        """)
        
        # 🔥 BỘ SỬA LỖI TỰ ĐỘNG DÀNH CHO POSTGRES (SUPABASE) - ĐÃ ĐƯỢC FIX TRANSACTION LỖI
        try:
            cursor.execute("ALTER TABLE records ADD COLUMN IF NOT EXISTS user_email TEXT DEFAULT '';")
            conn.commit()
        except Exception:
            # 🚨 ĐOẠN QUAN TRỌNG: Phải rollback phiên lỗi để giải phóng hàng đợi của Postgres
            conn.rollback() 

        # Chèn dữ liệu mẫu cho Supabase
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
    cursor.close()
    conn.close()

# ==========================================
# PHẦN 1: CÁC HÀM XỬ LÝ USER
# ==========================================

def check_or_create_user(email):
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if "sqlite" in DATABASE_URL:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO users (email, role, created_at) VALUES (?, 'FREE', ?)", (email, now))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
        user = dict(row) if row else None
    else:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO users (email, role, created_at) VALUES (%s, 'FREE', %s)", (email, now))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()
        user = dict(row) if row else None
        
    cursor.close()
    conn.close()
    return user

def update_user_role(email, new_role):
    conn = get_connection()
    cursor = conn.cursor()
    if "sqlite" in DATABASE_URL:
        cursor.execute("UPDATE users SET role = ? WHERE email = ?", (new_role, email))
    else:
        cursor.execute("UPDATE users SET role = %s WHERE email = %s", (new_role, email))
    conn.commit()
    cursor.close()
    conn.close()

# ==========================================
# PHẦN 2: CÁC HÀM XỬ LÝ TAB 1 (SHEET NHẠC)
# ==========================================

def get_all_records():
    conn = get_connection()
    if "sqlite" in DATABASE_URL:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, user_email FROM records ORDER BY id DESC")
        rows = [dict(row) for row in cursor.fetchall()]
    else:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT id, title, user_email FROM records ORDER BY id DESC")
        rows = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return rows

def get_record_by_id(record_id):
    conn = get_connection()
    if "sqlite" in DATABASE_URL:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM records WHERE id = ?", (record_id,))
        row = cursor.fetchone()
    else:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM records WHERE id = %s", (record_id,))
        row = cursor.fetchone()
    
    result = dict(row) if row else None
    cursor.close()
    conn.close()
    return result

def insert_record(title, data_json):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_user = st.session_state.get('logged_in_user', '')
    
    if "sqlite" in DATABASE_URL:
        cursor.execute(
            "INSERT INTO records (title, data_json, created_at, updated_at, user_email) VALUES (?, ?, ?, ?, ?)",
            (title, data_json, now, now, current_user)
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return new_id
    else:
        try:
            cursor.execute(
                "INSERT INTO records (title, data_json, created_at, updated_at, user_email) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
                (title, data_json, now, now, current_user)
            )
            new_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            return new_id
        except Exception as e:
            st.error(f"💥 DETECTED SUPABASE INSERT ERROR: {str(e)}")
            cursor.close()
            conn.close()
            raise e

def add_record(title, data_json):
    return insert_record(title, data_json)

def update_record_data(record_id, data_json):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if "sqlite" in DATABASE_URL:
        cursor.execute(
            "UPDATE records SET data_json = ?, updated_at = ? WHERE id = ?",
            (data_json, now, record_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
    else:
        try:
            cursor.execute(
                "UPDATE records SET data_json = %s, updated_at = %s WHERE id = %s",
                (data_json, now, record_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"💥 DETECTED SUPABASE UPDATE ERROR: {str(e)}")
            cursor.close()
            conn.close()
            raise e

def update_record_title(record_id, new_title):
    conn = get_connection()
    cursor = conn.cursor()
    if "sqlite" in DATABASE_URL:
        cursor.execute("UPDATE records SET title = ? WHERE id = ?", (new_title, record_id))
    else:
        cursor.execute("UPDATE records SET title = %s WHERE id = %s", (new_title, record_id))
    conn.commit()
    cursor.close()
    conn.close()

def delete_record(record_id):
    conn = get_connection()
    cursor = conn.cursor()
    if "sqlite" in DATABASE_URL:
        cursor.execute("DELETE FROM records WHERE id = ?", (record_id,))
    else:
        cursor.execute("DELETE FROM records WHERE id = %s", (record_id,))
    conn.commit()
    cursor.close()
    conn.close()

# ==========================================
# PHẦN 3: CÁC HÀM XỬ LÝ NỘI DUNG PREMIUM (TAB 2 & TAB 3)
# ==========================================

def get_yoga_data_by_id(content_id):
    conn = get_connection()
    if "sqlite" in DATABASE_URL:
        cursor = conn.cursor()
        cursor.execute("SELECT video_url, content_html FROM yoga_data WHERE id = ?", (content_id,))
        row = cursor.fetchone()
    else:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT video_url, content_html FROM yoga_data WHERE id = %s", (content_id,))
        row = cursor.fetchone()
        
    result = dict(row) if row else None
    cursor.close()
    conn.close()
    return result

def update_yoga_data(content_id, video_url, content_html):
    conn = get_connection()
    cursor = conn.cursor()
    if "sqlite" in DATABASE_URL:
        cursor.execute(
            "UPDATE yoga_data SET video_url = ?, content_html = ? WHERE id = ?",
            (video_url, content_html, content_id)
        )
    else:
        cursor.execute(
            "UPDATE yoga_data SET video_url = %s, content_html = %s WHERE id = %s",
            (video_url, content_html, content_id)
        )
    conn.commit()
    cursor.close()
    conn.close()