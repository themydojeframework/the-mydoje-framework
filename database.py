import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
import os
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st
import json
import ast

# Kích hoạt đọc file .env dưới máy local
load_dotenv()

# --- CHUẨN HÓA URL KẾT NỐI NGAY TỪ ĐẦU ---
raw_url = ""
if "DATABASE_URL" in st.secrets:
    raw_url = st.secrets["DATABASE_URL"]
else:
    raw_url = os.getenv("DATABASE_URL", "sqlite:///app.db")

# Làm sạch khoảng trắng và nháy thừa, đồng bộ đầu ngữ postgresql -> postgres cho psycopg2
clean_url = raw_url.strip().replace('"', '').replace("'", "")
if clean_url.startswith("postgresql://"):
    clean_url = clean_url.replace("postgresql://", "postgres://", 1)

DATABASE_URL = clean_url


def get_connection():
    """Tự động kết nối tới đúng hệ quản trị cơ sở dữ liệu dựa theo môi trường."""
    if "sqlite" in DATABASE_URL:
        conn = sqlite3.connect("app.db", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    else:
        try:
            # Kết nối qua cổng Pooler ổn định IPv4 của Supabase
            conn = psycopg2.connect(DATABASE_URL, sslmode="require")
            return conn
        except Exception as e:
            st.error(f"💥 LỖI KẾT NỐI SUPABASE THỰC TẾ: {str(e)}")
            raise e


def init_db():
    """Khởi tạo toàn bộ hệ thống bảng mới (Tách biệt morning_boost và deep_sleep) 
    và xóa bỏ hoàn toàn bảng cũ yoga_data."""
    conn = get_connection()
    
    if "sqlite" in DATABASE_URL:
        cursor = conn.cursor()
        # --- CẤU HÌNH BẢNG CHO SQLITE (DƯỚI MÁY LOCAL) ---
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
        
        # 🆕 Tạo 2 bảng mới phục vụ trang khóa học/tin tức có lưu lịch sử
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS morning_boost (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                video_url TEXT,
                content_html TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deep_sleep (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                video_url TEXT,
                content_html TEXT,
                created_at TEXT
            )
        """)
        
        # 🗑️ Xóa sổ hoàn toàn bảng yoga_data cũ (nếu có) để tránh xung đột
        try:
            cursor.execute("DROP TABLE IF EXISTS yoga_data;")
        except sqlite3.OperationalError:
            pass
            
        # 🔥 BỘ SỬA LỖI TỰ ĐỘNG (MIGRATION) CỘT USER_EMAIL
        try:
            cursor.execute("ALTER TABLE records ADD COLUMN user_email TEXT DEFAULT '';")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        cursor.close()
        conn.close()
        
    else:
        # --- CẤU HÌNH BẢNG CHO POSTGRESQL (SUPABASE CLOUD) ---
        conn.autocommit = True
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE,
                    role TEXT DEFAULT 'FREE',
                    created_at TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id SERIAL PRIMARY KEY,
                    title TEXT,
                    data_json TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    user_email TEXT
                );
            """)
            
            # 🆕 Tạo 2 bảng mới trên Supabase Cloud
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS morning_boost (
                    id SERIAL PRIMARY KEY,
                    title TEXT,
                    video_url TEXT,
                    content_html TEXT,
                    created_at TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deep_sleep (
                    id SERIAL PRIMARY KEY,
                    title TEXT,
                    video_url TEXT,
                    content_html TEXT,
                    created_at TEXT
                );
            """)
            
            # 🗑️ Xóa bảng yoga_data cũ trên Supabase Cloud
            cursor.execute("DROP TABLE IF EXISTS yoga_data;")
            
            # 🔥 BỘ SỬA LỖI TỰ ĐỘNG DÀNH CHO POSTGRES (SUPABASE)
            cursor.execute("ALTER TABLE records ADD COLUMN IF NOT EXISTS user_email TEXT DEFAULT '';")
            
        except Exception as e:
            st.error(f"💥 Lỗi thiết lập cấu hình bảng Supabase mới: {str(e)}")
        finally:
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


def _clean_json_helper(data_json):
    """Hàm phụ trợ ép dữ liệu thành chuỗi JSON nháy kép chuẩn."""
    try:
        if isinstance(data_json, (dict, list)):
            return json.dumps(data_json, ensure_ascii=False)
        elif isinstance(data_json, str):
            try:
                parsed_obj = json.loads(data_json)
                return json.dumps(parsed_obj, ensure_ascii=False)
            except Exception:
                try:
                    parsed_obj = ast.literal_eval(data_json)
                    return json.dumps(parsed_obj, ensure_ascii=False)
                except Exception:
                    return data_json
        else:
            return str(data_json)
    except Exception:
        return str(data_json)


def insert_record(title, data_json):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_user = st.session_state.get('logged_in_user', '')
    
    clean_json_str = _clean_json_helper(data_json)

    if "sqlite" in DATABASE_URL:
        cursor.execute(
            "INSERT INTO records (title, data_json, created_at, updated_at, user_email) VALUES (?, ?, ?, ?, ?)",
            (title, clean_json_str, now, now, current_user)
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
                (title, clean_json_str, now, now, current_user)
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
    
    clean_json_str = _clean_json_helper(data_json)
    
    if "sqlite" in DATABASE_URL:
        cursor.execute(
            "UPDATE records SET data_json = ?, updated_at = ? WHERE id = ?",
            (clean_json_str, now, record_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
    else:
        try:
            cursor.execute(
                "UPDATE records SET data_json = %s, updated_at = %s WHERE id = %s",
                (clean_json_str, now, record_id)
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