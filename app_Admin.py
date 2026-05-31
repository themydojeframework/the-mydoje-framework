import streamlit as st
import pandas as pd
import json
import os
import sqlite3
from dotenv import load_dotenv
import database as db

# Tải cấu hình môi trường
load_dotenv()
SECRET_KEY = os.getenv("GOOGLE_SECRET_KEY", "fallback_key")

# Cấu hình trang Streamlit Admin
st.set_page_config(page_title="Hệ Thống Quản Trị - Admin Dashboard", layout="wide")


# =================================================================
# 🛠️ TỰ KHỞI TẠO CÁC HÀM XỬ LÝ DATABASE PHỤ TRÁNH LỖI FILE DATABASE.PY
# =================================================================

def get_yoga_data_by_id_local(target_id):
    """Lấy dữ liệu video và html của Tab 2 hoặc Tab 3 từ app.db"""
    conn = sqlite3.connect("app.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Tạo bảng dự phòng nếu chưa có cấu trúc này
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS yoga_data (
            id INTEGER PRIMARY KEY,
            video_url TEXT,
            content_html TEXT
        )
    """)
    conn.commit()
    
    cursor.execute("SELECT video_url, content_html FROM yoga_data WHERE id = ?", (target_id,))
    row = cursor.fetchone()
    
    if row:
        result = dict(row)
    else:
        # Nếu chưa có id này, trả về cấu trúc mặc định tránh crash giao diện admin
        result = {"video_url": "", "content_html": "<div class='yoga-card'>Nội dung mặc định đoạn 1</div>"}
        
    conn.close()
    return result


def update_yoga_data_local(target_id, video_url, content_html):
    """Cập nhật hoặc tự động chèn mới dữ liệu Premium của Admin vào app.db"""
    conn = sqlite3.connect("app.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Kiểm tra xem ID đã tồn tại chưa để quyết định INSERT hay UPDATE
    cursor.execute("SELECT id FROM yoga_data WHERE id = ?", (target_id,))
    if cursor.fetchone():
        cursor.execute(
            "UPDATE yoga_data SET video_url = ?, content_html = ? WHERE id = ?",
            (video_url, content_html, target_id)
        )
    else:
        cursor.execute(
            "INSERT INTO yoga_data (id, video_url, content_html) VALUES (?, ?, ?)",
            (target_id, video_url, content_html)
        )
        
    conn.commit()
    conn.close()


# =================================================================
# GIAO DIỆN CHÍNH CỦA TRANG QUẢN TRỊ
# =================================================================

st.title("👑 HỆ THỐNG QUẢN TRỊ TỐI CAO (ADMIN.PY)")
st.subheader("Quản lý cơ sở dữ liệu nhạc và nội dung nâng cao Yoga/Belly Dance")

# Khởi tạo DB tập trung từ file database.py
db.init_db()

# Chia thành 2 phân khu quản trị trực quan
admin_tab_music, admin_tab_premium = st.tabs(["🎵 Quản lý Sheet Nhạc (Tab 1)", "🌟 Quản lý Bài Học Premium (Tab 2 & 3)"])

# --- PHÂN KHU 1: QUẢN LÝ SHEET NHẠC ---
with admin_tab_music:
    # Lấy danh sách bài rút gọn cho Selectbox
    records_summary = db.get_all_records()
    total_records = len(records_summary)

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric(label="📊 Tổng số bài nhạc", value=total_records)
    with col_m2:
        st.metric(label="🔐 Mã khóa bảo mật", value=f"...{SECRET_KEY[-6:] if len(SECRET_KEY)>6 else SECRET_KEY}")

    if total_records == 0:
        st.info("Hiện tại chưa có dữ liệu nhạc nào.")
    else:
        # Hiển thị bảng danh sách trực quan cho Admin theo dõi
        df = pd.DataFrame([dict(r) for r in records_summary])
        df.columns = ["ID Bài Nhạc", "Tên Bài Nhạc"]
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        
        # Chọn bài nhạc cụ thể để can thiệp sâu
        record_map = {r["title"]: r["id"] for r in records_summary}
        selected_title = st.selectbox("Chọn bài nhạc can thiệp sâu:", list(record_map.keys()))
        
        if selected_title:
            rec_id = record_map[selected_title]
            # Gọi chi tiết bản ghi (bao gồm cả chuỗi JSON nốt nhạc)
            current_rec = db.get_record_by_id(rec_id)
            
            if current_rec:
                col_edit1, col_edit2 = st.columns([1, 2])
                
                with col_edit1:
                    st.warning(f"Đang can thiệp bài: {selected_title} (ID: {rec_id})")
                    new_title = st.text_input("Đổi tên bài nhạc (RENAME):", value=current_rec["title"])
                    
                    if st.button("📝 ĐỔI TÊN TIÊU ĐỀ", type="primary"):
                        if new_title.strip() != "":
                            db.update_record_title(rec_id, new_title.strip())
                            st.toast("Đã đổi tên bài nhạc thành công!")
                            st.rerun()
                        else:
                            st.error("Tên bài nhạc không được để trống!")
                            
                    st.markdown("---")
                    if st.button(f"🗑️ XÓA VĨNH VIỄN BÀI NÀY", type="secondary", use_container_width=True):
                        db.delete_record(rec_id)
                        st.success("Đã xóa bài nhạc khỏi hệ thống!")
                        st.rerun()
                        
                with col_edit2:
                    st.markdown("👁️ **Cấu trúc ma trận nốt nhạc hiện tại (JSON):**")
                    st.code(current_rec["data_json"], language="json")


# --- PHÂN KHU 2: QUẢN LÝ BÀI HỌC PREMIUM (YOGA & BELLY DANCE) ---
with admin_tab_premium:
    st.subheader("🛠️ Cấu hình nội dung phân phối luồng dữ liệu tự động")
    
    course_option = st.selectbox(
        "Chọn khung bài học muốn thay đổi nội dung:", 
        ["ID 2 - Khung Belly Dance (Tab 2)", "ID 1 - Khung Private Yoga (Tab 3)"]
    )
    target_id = 2 if "Belly" in course_option else 1
    
    # 🔥 Đã sửa: Thay đổi từ db.get_yoga_data_by_id sang hàm local chạy ổn định
    premium_data = get_yoga_data_by_id_local(target_id)
    
    curr_url = premium_data["video_url"] if premium_data else ""
    curr_html = premium_data["content_html"] if premium_data else ""
    
    st.markdown("---")
    new_url = st.text_input("🔗 Đường dẫn Video URL (Youtube / MP4):", value=curr_url)
    
    st.markdown("✍️ **Chỉnh sửa các khối nội dung (Đóng gói định dạng chuẩn `<div class='yoga-card'>Nội dung</div>`):**")
    new_html = st.text_area(
        "Mã HTML bài học tổng hợp:", 
        value=curr_html, 
        height=250, 
        help="Bắt buộc phải bọc các phân đoạn trong thẻ <div class='yoga-card'> để ứng dụng khách cắt chuỗi hiển thị chính xác."
    )
    
    if st.button("💾 LƯU PHÂN PHỐI NỘI DUNG PREMIUM", type="primary"):
        # 🔥 Đã sửa: Thay thế hàm lưu tập trung sang hàm local đồng bộ cả INSERT và UPDATE
        update_yoga_data_local(target_id, new_url, new_html)
        st.success("Đã đồng bộ hóa dữ liệu bài học Premium thành công lên hệ thống!")
        st.rerun()