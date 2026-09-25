import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime

# --- 1. Cấu hình trang Web ---
st.set_page_config(
    page_title="Sổ Ghi Nợ 2 Người", 
    page_icon="💸", 
    layout="wide"
)

# --- 2. CSS Tùy chỉnh ---
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 16px; 
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 900;
        background: linear-gradient(90deg, #FF4B4B, #FF8E53);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
        text-align: center;
    }
    .sub-title {
        text-align: center;
        color: #666;
        margin-bottom: 25px;
        font-size: 1.1rem;
    }
    .metric-container {
        display: flex;
        flex-direction: column; 
        gap: 15px;
        margin-bottom: 25px;
    }
    @media (min-width: 768px) {
        .metric-container {
            flex-direction: row;
        }
    }
    .metric-card {
        flex: 1;
        border-radius: 16px;
        padding: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-5px); }
    .card-debt { background: linear-gradient(135deg, #FF416C 0%, #FF4B2B 100%); }
    .card-paid { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .card-remaining { background: linear-gradient(135deg, #4A00E0 0%, #8E2DE2 100%); }
    .metric-label { font-size: 1.2rem; font-weight: 700; opacity: 0.9; margin-bottom: 8px; }
    .metric-value { font-size: 2.2rem; font-weight: 900; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }
    [data-testid="stDataFrame"] { font-size: 1.1rem !important; }
    [data-testid="stDataFrame"] th { background-color: #2b3a42 !important; color: white !important; font-weight: bold !important; font-size: 1.1rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 5px; overflow-x: auto; }
    .stTabs [data-baseweb="tab"] { height: auto; min-height: 48px; background-color: #f0f2f6; border-radius: 10px; padding: 10px 15px; font-size: 1rem !important; font-weight: 700 !important; color: #495057; border: none; white-space: nowrap; }
    .stTabs [aria-selected="true"] { background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%) !important; color: #000 !important; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    .stButton > button { border-radius: 12px; font-weight: 800; font-size: 1.2rem; padding: 12px 24px; width: 100%; transition: all 0.3s; }
</style>
""", unsafe_allow_html=True)

# --- 3. Khởi tạo CSDL & Hàm truy vấn Real-time (Bỏ Cache) ---
conn = st.connection("neon", type="sql")

def run_query(sql, params=None):
    """Hàm chạy SQL trực tiếp, bỏ qua bộ nhớ đệm của Streamlit để khắc phục delay data"""
    with conn.session as s:
        result = s.execute(text(sql), params or {})
        # Lấy dữ liệu và trả về DataFrame
        keys = result.keys()
        data = result.fetchall()
        return pd.DataFrame(data, columns=keys) if data else pd.DataFrame(columns=keys)

def init_db():
    with conn.session as s:
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(50) PRIMARY KEY,
                password VARCHAR(50) NOT NULL,
                role VARCHAR(20) NOT NULL,
                group_id VARCHAR(50) NOT NULL
            );
        """))
        s.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='debts' AND column_name='group_id') THEN
                    ALTER TABLE debts ADD COLUMN group_id VARCHAR(50) DEFAULT 'Mặc định';
                END IF;
            END $$;
        """))
        # Tạo Admin (Pass: admin123)
        count = s.execute(text("SELECT COUNT(*) FROM users WHERE role='admin';")).scalar()
        if count == 0:
            s.execute(text("INSERT INTO users (username, password, role, group_id) VALUES ('admin', 'admin123', 'admin', 'ALL')"))
        s.commit()

init_db()

def fetch_debts(role, group_id):
    if role == 'admin':
        return run_query("SELECT id, title, borrower, lender, total_amount, paid_amount, note, created_at, group_id FROM debts ORDER BY id DESC")
    else:
        return run_query("SELECT id, title, borrower, lender, total_amount, paid_amount, note, created_at, group_id FROM debts WHERE group_id = :g ORDER BY id DESC", params={"g": group_id})

# --- 4. GIAO DIỆN TRANG CHỦ & ĐĂNG NHẬP ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown('<div class="main-title">🚪 CỔNG VÀO SỔ GHI NỢ</div>', unsafe_allow_html=True)
    st.write("---")
    
    # Chia 2 cột cách đều nhau (gap="large")
    col1, col2 = st.columns(2, gap="large")
    
    # Khối 1: Danh sách các sổ nợ đã tạo
    with col1:
        with st.container(border=True):
            st.subheader("📖 Vào Sổ Nợ Của Bạn")
            users_df = run_query("SELECT username FROM users WHERE role='user'")
            
            if not users_df.empty:
                selected_group = st.selectbox("1. Chọn sổ nợ (Tên cặp):", users_df['username'].tolist())
                pwd = st.text_input("2. Mật khẩu sổ nợ:", type="password")
                
                if st.button("Mở Sổ Nợ", type="primary", use_container_width=True):
                    res = run_query("SELECT role, group_id FROM users WHERE username = :u AND password = :p", 
                                     params={"u": selected_group, "p": pwd})
                    if not res.empty:
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = selected_group
                        st.session_state['role'] = res.iloc[0]['role']
                        st.session_state['group_id'] = res.iloc[0]['group_id']
                        st.rerun()
                    else:
                        st.error("Sai mật khẩu của sổ này!")
            else:
                st.info("Chưa có sổ nợ nào. Hãy tạo sổ mới ở bên cạnh 👉")
                
            st.write("---")
            # Khối Admin (Pass mặc định: admin123)
            with st.expander("👑 Đăng nhập Admin (Full quyền)"):
                admin_u = st.text_input("Tài khoản Admin (Mặc định: admin)", key="ad_u")
                admin_p = st.text_input("Mật khẩu Admin (Mặc định: admin123)", type="password", key="ad_p")
                if st.button("Đăng nhập Admin", use_container_width=True):
                    res_ad = run_query("SELECT role, group_id FROM users WHERE username = :u AND password = :p AND role='admin'", 
                                     params={"u": admin_u, "p": admin_p})
                    if not res_ad.empty:
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = admin_u
                        st.session_state['role'] = res_ad.iloc[0]['role']
                        st.session_state['group_id'] = res_ad.iloc[0]['group_id']
                        st.rerun()
                    else:
                        st.error("Sai tài khoản hoặc mật khẩu Admin!")

    # Khối 2: Tạo khoản nợ / Tạo sổ mới
    with col2:
        with st.container(border=True):
            st.subheader("➕ Tạo Sổ Nợ Mới")
            st.info("Tạo một không gian chung để 2 người tự quản lý nợ nần với nhau.")
            with st.form("create_group_form"):
                new_group_name = st.text_input("Tên sổ nợ (VD: Nam_Nu, Vợ_Chồng...)")
                new_group_pwd = st.text_input("Tạo mật khẩu cho sổ này", type="password")
                
                if st.form_submit_button("Tạo Sổ Nợ & Đăng Nhập", type="primary", use_container_width=True):
                    if new_group_name and new_group_pwd:
                        # Kiểm tra trùng tên bằng Real-time query
                        check_exist = run_query("SELECT username FROM users WHERE username = :u", params={"u": new_group_name})
                        if not check_exist.empty:
                            st.error("Tên sổ nợ này đã tồn tại, vui lòng chọn tên khác!")
                        else:
                            with conn.session as s:
                                s.execute(text("INSERT INTO users (username, password, role, group_id) VALUES (:u, :p, 'user', :g)"), 
                                          {"u": new_group_name, "p": new_group_pwd, "g": new_group_name})
                                s.commit()
                            st.success("Tạo sổ thành công! Đang tự động đăng nhập...")
                            # Đăng nhập luôn
                            st.session_state['logged_in'] = True
                            st.session_state['username'] = new_group_name
                            st.session_state['role'] = 'user'
                            st.session_state['group_id'] = new_group_name
                            st.rerun()
                    else:
                        st.warning("Vui lòng nhập đầy đủ Tên sổ và Mật khẩu!")

    st.stop()


# --- 5. GIAO DIỆN CHÍNH (Chỉ hiện khi đã đăng nhập thành công) ---
st.sidebar.markdown(f"👤 **{st.session_state['username']}**")
st.sidebar.markdown(f"🏷️ Nhóm: **{st.session_state['group_id']}**")
if st.sidebar.button("Đăng xuất"):
    st.session_state.clear()
    st.rerun()

st.markdown('<div class="main-title">💸 SỔ GHI NỢ DÙNG CHUNG</div>', unsafe_allow_html=True)
if st.session_state['role'] == 'admin':
    st.markdown('<div class="sub-title">Chế độ Admin: Xem toàn bộ dữ liệu</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="sub-title">Không gian riêng của cặp: {st.session_state["group_id"]}</div>', unsafe_allow_html=True)

df = fetch_debts(st.session_state['role'], st.session_state['group_id'])

# --- Khối Tổng quan (Metrics) ---
if not df.empty:
    df["total_amount"] = pd.to_numeric(df["total_amount"])
    df["paid_amount"] = pd.to_numeric(df["paid_amount"])
    df["remaining"] = df["total_amount"] - df["paid_amount"]
    
    total_debt = float(df["total_amount"].sum())
    total_paid = float(df["paid_amount"].sum())
    total_remaining = float(df["remaining"].sum())

    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-card card-debt">
            <div class="metric-label">🔴 Tổng Nợ Gốc</div>
            <div class="metric-value">{total_debt:,.0f} ₫</div>
        </div>
        <div class="metric-card card-paid">
            <div class="metric-label">🟢 Đã Trả</div>
            <div class="metric-value">{total_paid:,.0f} ₫</div>
        </div>
        <div class="metric-card card-remaining">
            <div class="metric-label">🔵 Còn Thiếu</div>
            <div class="metric-value">{total_remaining:,.0f} ₫</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Các Tab chức năng ---
tab1, tab2, tab3, tab4 = st.tabs(["📋 Danh sách", "➕ Thêm mới", "💳 Trả tiền", "⚙️ Reset"])

with tab1:
    st.subheader("📋 Chi Tiết Các Khoản Nợ")
    if not df.empty:
        display_df = df.copy()
        def format_date(dt):
            if pd.isna(dt): return "Chưa rõ"
            try: return pd.to_datetime(dt).strftime('%d/%m/%Y %H:%M')
            except: return str(dt)

        display_df['Ngày vay'] = display_df['created_at'].apply(format_date)
        display_df["Trạng thái"] = display_df["remaining"].apply(lambda val: "✅ Hoàn tất" if val <= 0 else "⏳ Đang nợ")
        
        display_cols = ["id", "Ngày vay", "group_id", "title", "borrower", "lender", "total_amount", "paid_amount", "remaining", "Trạng thái", "note"]
        display_df = display_df[display_cols]
        
        st.dataframe(
            display_df,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "Ngày vay": st.column_config.TextColumn("Ngày tạo (Giờ)", width="medium"),
                "group_id": st.column_config.TextColumn("Nhóm", width="small"),
                "title": st.column_config.TextColumn("Nội dung", width="large"),
                "borrower": st.column_config.TextColumn("Người nợ", width="medium"),
                "lender": st.column_config.TextColumn("Chủ nợ", width="medium"),
                "total_amount": st.column_config.NumberColumn("Tổng nợ", format="%.0f ₫"),
                "paid_amount": st.column_config.NumberColumn("Đã trả", format="%.0f ₫"),
                "remaining": st.column_config.NumberColumn("Còn thiếu", format="%.0f ₫"),
                "Trạng thái": st.column_config.TextColumn("Trạng thái", width="small"),
                "note": st.column_config.TextColumn("Ghi chú", width="medium"),
            },
            use_container_width=True, hide_index=True, height=400
        )
    else:
        st.info("🎈 Sổ nợ đang trống.")

with tab2:
    st.subheader("➕ Ghi Khoản Nợ Mới")
    with st.form("add_debt_form", clear_on_submit=True):
        title = st.text_input("Nội dung khoản nợ")
        col_a, col_b = st.columns(2)
        borrower = col_a.text_input("Người nợ (Ai vay?)")
        lender = col_b.text_input("Chủ nợ (Ai cho mượn?)")
        total_amount = st.number_input("Tổng số tiền (VNĐ)", min_value=0.0, step=50000.0, format="%.0f")
        note = st.text_area("Ghi chú thêm (Tùy chọn)")
        
        submitted = st.form_submit_button("💾 LƯU KHOẢN NỢ GẤP", type="primary")
        if submitted:
            if title and total_amount > 0:
                with conn.session as s:
                    sql = text("""
                        INSERT INTO debts (title, borrower, lender, total_amount, paid_amount, note, group_id) 
                        VALUES (:title, :borrower, :lender, :total_amount, 0, :note, :group_id)
                    """)
                    s.execute(sql, {
                        "title": title, "borrower": borrower, "lender": lender, 
                        "total_amount": float(total_amount), "note": note,
                        "group_id": st.session_state['group_id']
                    })
                    s.commit()
                st.success("🎉 Ghi nợ thành công!")
                st.rerun()
            else:
                st.error("⚠️ Vui lòng nhập Nội dung và Số tiền lớn hơn 0.")

with tab3:
    st.subheader("💳 Ghi Nhận Trả Tiền")
    if not df.empty:
        unpaid_df = df[df["remaining"] > 0]
        if not unpaid_df.empty:
            debt_options = {
                f"#{row['id']} - {row['title']} | Còn thiếu: {float(row['remaining']):,.0f} ₫": int(row['id']) 
                for _, row in unpaid_df.iterrows()
            }
            selected_label = st.selectbox("1. Chọn khoản nợ cần thanh toán:", list(debt_options.keys()))
            selected_id = debt_options[selected_label]
            selected_row = df[df["id"] == selected_id].iloc[0]
            max_pay = float(selected_row["remaining"])
            
            pay_amount = st.number_input("2. Số tiền trả lần này (VNĐ)", min_value=1.0, max_value=max_pay, value=max_pay, step=50000.0, format="%.0f")
            
            if st.button("✅ XÁC NHẬN ĐÃ TRẢ", type="primary"):
                new_paid_total = float(selected_row["paid_amount"]) + float(pay_amount)
                with conn.session as s:
                    sql = text("UPDATE debts SET paid_amount = :new_paid WHERE id = :id")
                    s.execute(sql, {"new_paid": float(new_paid_total), "id": int(selected_id)})
                    s.commit()
                st.success(f"🎉 Đã cập nhật khoản trả {float(pay_amount):,.0f} ₫.")
                st.rerun()
        else:
            st.success("🎉 Wow! Không còn ai nợ ai cả.")

with tab4:
    st.subheader("⚙️ Chốt Sổ / Xóa Dữ Liệu")
    st.warning("**CẢNH BÁO:** Thao tác này sẽ xóa sạch danh sách nợ. User thường chỉ xóa được nợ của nhóm mình, Admin xóa toàn bộ.")
    
    confirm_code = st.text_input("Gõ chữ XOA vào ô dưới để mở khóa nút xóa", placeholder="Nhập XOA...")
    is_disabled = confirm_code.strip().upper() != "XOA"
    
    if st.button("🔥 XÓA SỔ NỢ", type="primary", disabled=is_disabled):
        with conn.session as s:
            if st.session_state['role'] == 'admin':
                s.execute(text("TRUNCATE TABLE debts RESTART IDENTITY;"))
            else:
                sql = text("DELETE FROM debts WHERE group_id = :g")
                s.execute(sql, {"g": st.session_state['group_id']})
            s.commit()
        st.success("🧹 Đã làm sạch sổ nợ thành công!")
        st.rerun()