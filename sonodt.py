import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime, date

# --- 1. Cấu hình trang Web ---
st.set_page_config(
    page_title="Quản Lý Tài Chính 2 Người", 
    page_icon="💰", 
    layout="wide"
)

# --- 2. CSS Tùy chỉnh ---
st.markdown("""
<style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; font-size: 16px; }
    .main-title { font-size: 2.2rem; font-weight: 900; background: linear-gradient(90deg, #FF4B4B, #FF8E53); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; text-align: center; }
    .exp-title { font-size: 2.2rem; font-weight: 900; background: linear-gradient(90deg, #11998e, #38ef7d); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; text-align: center; }
    .sub-title { text-align: center; color: #666; margin-bottom: 25px; font-size: 1.1rem; }
    .metric-container { display: flex; flex-direction: column; gap: 15px; margin-bottom: 25px; }
    @media (min-width: 768px) { .metric-container { flex-direction: row; } }
    .metric-card { flex: 1; border-radius: 16px; padding: 20px; color: white; text-align: center; box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1); transition: transform 0.2s; }
    .metric-card:hover { transform: translateY(-5px); }
    .card-debt { background: linear-gradient(135deg, #FF416C 0%, #FF4B2B 100%); }
    .card-paid { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .card-remaining { background: linear-gradient(135deg, #4A00E0 0%, #8E2DE2 100%); }
    .card-exp1 { background: linear-gradient(135deg, #F2994A 0%, #F2C94C 100%); color: #333; }
    .card-exp2 { background: linear-gradient(135deg, #56CCF2 0%, #2F80ED 100%); }
    .metric-label { font-size: 1.2rem; font-weight: 700; opacity: 0.9; margin-bottom: 8px; }
    .metric-value { font-size: 2.2rem; font-weight: 900; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }
    [data-testid="stDataFrame"] th { background-color: #2b3a42 !important; color: white !important; font-weight: bold !important; font-size: 1.05rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 5px; overflow-x: auto; }
    .stTabs [data-baseweb="tab"] { height: auto; min-height: 48px; background-color: #f0f2f6; border-radius: 10px; padding: 10px 15px; font-size: 1rem !important; font-weight: 700 !important; color: #495057; border: none; white-space: nowrap; }
    .stTabs [aria-selected="true"] { background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%) !important; color: #000 !important; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    .stButton > button { border-radius: 12px; font-weight: 800; font-size: 1.2rem; padding: 12px 24px; width: 100%; transition: all 0.3s; }
</style>
""", unsafe_allow_html=True)

# --- 3. Khởi tạo CSDL & Xử lý kết nối ngầm ---
conn = st.connection("neon", type="sql")

# Bật Pre-ping chống timeout khi ngâm trang lâu
try:
    conn.engine.pool._pre_ping = True
except Exception:
    pass

def execute_db(sql, params=None):
    """Hàm thực thi ghi dữ liệu an toàn, tự khôi phục nếu đứt kết nối"""
    try:
        with conn.engine.begin() as s:
            s.execute(text(sql), params or {})
    except Exception:
        conn.engine.dispose()
        with conn.engine.begin() as s:
            s.execute(text(sql), params or {})

def run_query(sql, params=None):
    """Hàm đọc dữ liệu an toàn"""
    try:
        with conn.engine.connect() as c:
            result = c.execute(text(sql), params or {})
            keys = result.keys()
            data = result.fetchall()
            return pd.DataFrame(data, columns=keys) if data else pd.DataFrame(columns=keys)
    except Exception:
        conn.engine.dispose()
        with conn.engine.connect() as c:
            result = c.execute(text(sql), params or {})
            keys = result.keys()
            data = result.fetchall()
            return pd.DataFrame(data, columns=keys) if data else pd.DataFrame(columns=keys)

@st.cache_resource
def init_db():
    """Chỉ chạy 1 lần duy nhất khi khởi động ứng dụng"""
    execute_db("CREATE TABLE IF NOT EXISTS users (username VARCHAR(50) PRIMARY KEY, password VARCHAR(50) NOT NULL, role VARCHAR(20) NOT NULL, group_id VARCHAR(50) NOT NULL);")
    execute_db("CREATE TABLE IF NOT EXISTS debts (id SERIAL PRIMARY KEY, title TEXT NOT NULL, borrower VARCHAR(50), lender VARCHAR(50), total_amount NUMERIC DEFAULT 0, paid_amount NUMERIC DEFAULT 0, note TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, group_id VARCHAR(50) DEFAULT 'Mặc định');")
    execute_db("CREATE TABLE IF NOT EXISTS debt_logs (id SERIAL PRIMARY KEY, debt_id INT NOT NULL, log_type VARCHAR(50) NOT NULL, amount NUMERIC NOT NULL, note TEXT, created_by VARCHAR(50), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
    execute_db("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            amount NUMERIC DEFAULT 0,
            category VARCHAR(50),
            paid_by VARCHAR(50),
            note TEXT,
            expense_date DATE DEFAULT CURRENT_DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            group_id VARCHAR(50) NOT NULL
        );
    """)
    check_admin = run_query("SELECT COUNT(*) as count FROM users WHERE role='admin'")
    if check_admin.empty or check_admin.iloc[0]['count'] == 0:
        execute_db("INSERT INTO users (username, password, role, group_id) VALUES ('admin', 'admin123', 'admin', 'ALL')")

init_db()

# --- Các hàm Lấy Data ---
def fetch_debts(view_group):
    if view_group == "ALL":
        return run_query("SELECT id, title, borrower, lender, total_amount, paid_amount, note, created_at, group_id FROM debts ORDER BY id DESC")
    return run_query("SELECT id, title, borrower, lender, total_amount, paid_amount, note, created_at, group_id FROM debts WHERE group_id = :g ORDER BY id DESC", params={"g": view_group})

def fetch_logs(view_group):
    if view_group == "ALL":
        return run_query("SELECT l.id, l.created_at, d.group_id, d.title, l.log_type, l.amount, l.note, l.created_by FROM debt_logs l JOIN debts d ON l.debt_id = d.id ORDER BY l.id DESC")
    return run_query("SELECT l.id, l.created_at, d.group_id, d.title, l.log_type, l.amount, l.note, l.created_by FROM debt_logs l JOIN debts d ON l.debt_id = d.id WHERE d.group_id = :g ORDER BY l.id DESC", params={"g": view_group})

def fetch_expenses(view_group):
    if view_group == "ALL":
        return run_query("SELECT id, title, amount, category, paid_by, note, expense_date, group_id FROM expenses ORDER BY expense_date DESC, id DESC")
    return run_query("SELECT id, title, amount, category, paid_by, note, expense_date, group_id FROM expenses WHERE group_id = :g ORDER BY expense_date DESC, id DESC", params={"g": view_group})

# --- 4. GIAO DIỆN ĐĂNG NHẬP ---
if 'logged_in' not in st.session_state: 
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown('<div class="main-title">🚪 CỔNG QUẢN LÝ TÀI CHÍNH</div>', unsafe_allow_html=True)
    st.write("---")
    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.container(border=True):
            st.subheader("📖 Đăng nhập")
            users_df = run_query("SELECT username FROM users WHERE role='user'")
            if not users_df.empty:
                selected_group = st.selectbox("1. Chọn Sổ của bạn:", users_df['username'].tolist())
                pwd = st.text_input("2. Mật khẩu:", type="password")
                if st.button("Đăng Nhập Sổ", type="primary", use_container_width=True):
                    res = run_query("SELECT role, group_id FROM users WHERE username = :u AND password = :p", params={"u": selected_group, "p": pwd})
                    if not res.empty:
                        st.session_state.update({'logged_in': True, 'username': selected_group, 'role': res.iloc[0]['role'], 'group_id': res.iloc[0]['group_id']})
                        st.rerun()
                    else: 
                        st.error("Sai mật khẩu!")
            else: 
                st.info("Chưa có sổ nào. Hãy tạo sổ mới 👉")
            
            st.write("---")
            with st.expander("👑 Đăng nhập Admin"):
                admin_u = st.text_input("Tài khoản", value="admin", key="ad_u")
                admin_p = st.text_input("Mật khẩu", type="password", key="ad_p")
                if st.button("Vào Admin", use_container_width=True):
                    res_ad = run_query("SELECT role, group_id FROM users WHERE username = :u AND password = :p AND role='admin'", params={"u": admin_u, "p": admin_p})
                    if not res_ad.empty:
                        st.session_state.update({'logged_in': True, 'username': admin_u, 'role': res_ad.iloc[0]['role'], 'group_id': res_ad.iloc[0]['group_id']})
                        st.rerun()
                    else: 
                        st.error("Sai mật khẩu Admin!")

    with col2:
        with st.container(border=True):
            st.subheader("➕ Tạo Sổ Mới")
            with st.form("create_group_form"):
                new_group_name = st.text_input("Tên nhóm/cặp (VD: Nam_Nu)")
                new_group_pwd = st.text_input("Tạo mật khẩu", type="password")
                if st.form_submit_button("Tạo & Đăng Nhập", type="primary", use_container_width=True):
                    if new_group_name and new_group_pwd:
                        if not run_query("SELECT username FROM users WHERE username = :u", params={"u": new_group_name}).empty:
                            st.error("Tên sổ này đã tồn tại!")
                        else:
                            execute_db("INSERT INTO users (username, password, role, group_id) VALUES (:u, :p, 'user', :g)", {"u": new_group_name, "p": new_group_pwd, "g": new_group_name})
                            st.session_state.update({'logged_in': True, 'username': new_group_name, 'role': 'user', 'group_id': new_group_name})
                            st.rerun()
                    else: 
                        st.warning("Nhập đủ thông tin!")
    st.stop()

# --- 5. GIAO DIỆN CHÍNH ---
st.sidebar.markdown(f"👤 Tài khoản: **{st.session_state['username']}**")
st.sidebar.markdown(f"🏷️ Quyền: **{st.session_state['role'].upper()}**")

# BỘ LỌC ADMIN
if st.session_state['role'] == 'admin':
    st.sidebar.write("---")
    groups_df = run_query("SELECT username FROM users WHERE role='user'")
    all_groups = groups_df['username'].tolist() if not groups_df.empty else []
    view_mode = st.sidebar.selectbox("📂 Lọc dữ liệu theo Sổ:", ["Tất cả các sổ"] + all_groups)
    current_view_group = "ALL" if view_mode == "Tất cả các sổ" else view_mode
else:
    current_view_group = st.session_state['group_id']

st.sidebar.write("---")
if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True): 
    st.rerun()
st.sidebar.write("---")

app_mode = st.sidebar.radio("📌 CHỌN CHỨC NĂNG:", ["💸 Sổ Nợ Nần", "🛒 Sổ Chi Tiêu"])
st.sidebar.write("---")

if st.sidebar.button("Đăng xuất", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# ==========================================
# KHỐI 1: SỔ NỢ NẦN
# ==========================================
if app_mode == "💸 Sổ Nợ Nần":
    st.markdown('<div class="main-title">💸 SỔ GHI NỢ DÙNG CHUNG</div>', unsafe_allow_html=True)
    df = fetch_debts(current_view_group)

    if not df.empty:
        df["total_amount"] = pd.to_numeric(df["total_amount"])
        df["paid_amount"] = pd.to_numeric(df["paid_amount"])
        df["remaining"] = df["total_amount"] - df["paid_amount"]
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-card card-debt"><div class="metric-label">🔴 Tổng Nợ Gốc</div><div class="metric-value">{float(df["total_amount"].sum()):,.0f} ₫</div></div>
            <div class="metric-card card-paid"><div class="metric-label">🟢 Đã Trả</div><div class="metric-value">{float(df["paid_amount"].sum()):,.0f} ₫</div></div>
            <div class="metric-card card-remaining"><div class="metric-label">🔵 Còn Thiếu</div><div class="metric-value">{float(df["remaining"].sum()):,.0f} ₫</div></div>
        </div>
        """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Danh sách", "➕ Thêm Nợ", "💳 Trả tiền", "✏️ Sửa sai", "⚙️ Quản lý & Xóa"])

    with tab1:
        if not df.empty:
            display_df = df.copy()
            display_df['Ngày vay'] = display_df['created_at'].apply(lambda dt: pd.to_datetime(dt).strftime('%d/%m/%Y %H:%M') if pd.notna(dt) else "")
            display_df["Trạng thái"] = display_df["remaining"].apply(lambda val: "✅ Hoàn tất" if val <= 0 else "⏳ Đang nợ")
            st.dataframe(display_df[["id", "Ngày vay", "group_id", "title", "borrower", "lender", "total_amount", "paid_amount", "remaining", "Trạng thái", "note"]], hide_index=True, use_container_width=True)
            
            st.subheader("🔍 Nhật Ký Giao Dịch (Trả/Sửa)")
            logs_df = fetch_logs(current_view_group)
            if not logs_df.empty:
                logs_df['Thời gian'] = logs_df['created_at'].apply(lambda dt: pd.to_datetime(dt).strftime('%d/%m/%Y %H:%M') if pd.notna(dt) else "")
                st.dataframe(logs_df[["Thời gian", "group_id", "title", "log_type", "amount", "note", "created_by"]], hide_index=True, use_container_width=True)
        else: 
            st.info("Sổ nợ trống.")

    with tab2:
        if current_view_group == "ALL" and st.session_state['role'] == 'admin':
            st.warning("⚠️ **Quyền Admin:** Bạn đang xem Tất cả các sổ. Vui lòng chọn cụ thể 1 Sổ ở Sidebar bên trái nếu muốn thêm khoản nợ.")
        else:
            with st.form("add_debt_form", clear_on_submit=True):
                title = st.text_input("Nội dung khoản nợ")
                col_a, col_b = st.columns(2)
                borrower = col_a.text_input("Người nợ (Ai vay?)")
                lender = col_b.text_input("Chủ nợ (Ai cho mượn?)")
                total_amount = st.number_input("Tổng tiền (VNĐ)", min_value=0.0, step=50000.0, format="%.0f")
                note = st.text_area("Ghi chú")
                if st.form_submit_button("💾 LƯU KHOẢN NỢ", type="primary"):
                    if title and total_amount > 0:
                        execute_db("INSERT INTO debts (title, borrower, lender, total_amount, paid_amount, note, group_id) VALUES (:t, :b, :l, :a, 0, :n, :g)", {"t": title, "b": borrower, "l": lender, "a": float(total_amount), "n": note, "g": current_view_group})
                        st.success("Đã ghi nợ!"); st.rerun()
                    else: 
                        st.error("Nhập đủ Nội dung và Số tiền!")

    with tab3:
        if not df.empty and not df[df["remaining"] > 0].empty:
            unpaid_df = df[df["remaining"] > 0]
            opts = {f"#{row['id']} [{row['group_id']}] - {row['title']} | Thiếu: {float(row['remaining']):,.0f} ₫": int(row['id']) for _, row in unpaid_df.iterrows()}
            sel_id = opts[st.selectbox("Chọn nợ:", list(opts.keys()))]
            row_sel = df[df["id"] == sel_id].iloc[0]
            pay_amt = st.number_input("Số tiền trả", min_value=1.0, max_value=float(row_sel["remaining"]), value=float(row_sel["remaining"]), step=10000.0)
            pay_note = st.text_input("Lý do trả (Bắt buộc)")
            if st.button("✅ XÁC NHẬN TRẢ", type="primary"):
                if pay_note:
                    execute_db("UPDATE debts SET paid_amount = paid_amount + :p WHERE id = :id", {"p": pay_amt, "id": sel_id})
                    execute_db("INSERT INTO debt_logs (debt_id, log_type, amount, note, created_by) VALUES (:id, '💳 Trả tiền', :amt, :n, :c)", {"id": sel_id, "amt": pay_amt, "n": pay_note, "c": st.session_state['username']})
                    st.success("Đã lưu!"); st.rerun()
                else: 
                    st.error("Vui lòng nhập lý do!")

    with tab4:
        if not df.empty:
            opts = {f"#{row['id']} [{row['group_id']}] - {row['title']} | Gốc: {float(row['total_amount']):,.0f} ₫": int(row['id']) for _, row in df.iterrows()}
            sel_id = opts[st.selectbox("Chọn khoản nợ bị sai:", list(opts.keys()))]
            adj_type = st.radio("Thao tác:", ["Cộng thêm (ghi thiếu)", "Trừ bớt (ghi thừa)"], horizontal=True)
            adj_amt = st.number_input("Số tiền điều chỉnh", min_value=1.0, step=10000.0)
            adj_note = st.text_input("Lý do điều chỉnh (Bắt buộc)")
            if st.button("💾 LƯU ĐIỀU CHỈNH", type="primary"):
                if adj_note:
                    curr_amt = float(df[df["id"] == sel_id].iloc[0]["total_amount"])
                    new_amt = curr_amt + adj_amt if "Cộng" in adj_type else max(0, curr_amt - adj_amt)
                    log_str = "🟢 Cộng tiền gốc" if "Cộng" in adj_type else "🔴 Trừ tiền gốc"
                    execute_db("UPDATE debts SET total_amount = :na WHERE id = :id", {"na": new_amt, "id": sel_id})
                    execute_db("INSERT INTO debt_logs (debt_id, log_type, amount, note, created_by) VALUES (:id, :lt, :a, :n, :c)", {"id": sel_id, "lt": log_str, "a": adj_amt, "n": adj_note, "c": st.session_state['username']})
                    st.success("Đã sửa!"); st.rerun()
                else: 
                    st.error("Nhập lý do!")

    with tab5:
        st.subheader("⚙️ Quản Lý & Xóa Dữ Liệu")
        if st.session_state['role'] == 'admin':
            st.info("👑 **Quyền Admin:** Bạn có thể chọn tích chọn xóa cụ thể các khoản nợ, xóa sổ nợ theo nhóm hoặc reset toàn bộ hệ thống.")
            
            st.markdown("### 🗑️ 1. Xóa Chi Tiết Các Khoản Nợ (Tích Chọn)")
            if current_view_group == "ALL":
                admin_df = run_query("SELECT id, group_id, title, total_amount FROM debts ORDER BY id DESC")
            else:
                admin_df = run_query("SELECT id, group_id, title, total_amount FROM debts WHERE group_id = :g ORDER BY id DESC", {"g": current_view_group})
                
            if not admin_df.empty:
                admin_df['Chọn'] = False
                edited_df = st.data_editor(
                    admin_df[["Chọn", "id", "group_id", "title", "total_amount"]],
                    column_config={
                        "Chọn": st.column_config.CheckboxColumn("Xóa?"),
                        "id": st.column_config.NumberColumn("ID", width="small"),
                        "group_id": st.column_config.TextColumn("Nhóm", width="small"),
                        "title": st.column_config.TextColumn("Nội dung", width="large"),
                        "total_amount": st.column_config.NumberColumn("Tổng tiền", format="%.0f ₫"),
                    },
                    hide_index=True, use_container_width=True
                )
                sel_ids = edited_df[edited_df["Chọn"] == True]["id"].tolist()
                
                if sel_ids:
                    if st.button("🔥 XÓA CÁC KHOẢN NỢ ĐÃ CHỌN", type="primary"):
                        for did in sel_ids:
                            execute_db("DELETE FROM debt_logs WHERE debt_id = :did", {"did": int(did)})
                            execute_db("DELETE FROM debts WHERE id = :did", {"did": int(did)})
                        st.success(f"🧹 Đã xóa thành công {len(sel_ids)} khoản nợ!"); st.rerun()
            else:
                st.caption("Không có khoản nợ nào trong sổ này.")

            st.write("---")
            st.markdown("### 🗑️ 2. Xóa Vĩnh Viễn 1 Sổ Nợ Cụ Thể")
            all_users = run_query("SELECT username FROM users WHERE role='user'")
            if not all_users.empty:
                group_to_delete = st.selectbox("Chọn sổ nợ (Tên cặp) muốn xóa hoàn toàn:", all_users['username'].tolist(), index=0)
                confirm_del_single = st.text_input(f"Gõ đúng chữ **`XOASO`** để xác nhận xóa sổ [{group_to_delete}]:", key="del_single_box")
                
                if st.button(f"🔥 XÓA VĨNH VIỄN SỔ [{group_to_delete}]", type="primary", disabled=(confirm_del_single.strip().upper() != "XOASO")):
                    execute_db("DELETE FROM debt_logs WHERE debt_id IN (SELECT id FROM debts WHERE group_id = :g)", {"g": group_to_delete})
                    execute_db("DELETE FROM debts WHERE group_id = :g", {"g": group_to_delete})
                    execute_db("DELETE FROM users WHERE username = :u AND role = 'user'", {"u": group_to_delete})
                    st.success(f"🧹 Đã xóa vĩnh viễn sổ nợ [{group_to_delete}]!"); st.rerun()
            else:
                st.write("Chưa có sổ nợ nào trong hệ thống.")
                
            st.write("---")
            st.markdown("### 💥 3. Xóa Sạch Tất Cả Các Sổ Nợ & Lịch Sử (Reset Hệ Thống)")
            confirm_all = st.text_input("Gõ chữ **`XOAALL`** để xóa toàn bộ tất cả sổ nợ trên web:", key="xoa_all_box")
            
            if st.button("🔥 RESET TOÀN BỘ HỆ THỐNG", type="primary", disabled=(confirm_all.strip().upper() != "XOAALL")):
                execute_db("TRUNCATE TABLE debt_logs RESTART IDENTITY;")
                execute_db("TRUNCATE TABLE debts RESTART IDENTITY CASCADE;")
                execute_db("DELETE FROM users WHERE role = 'user';")
                st.success("🧹 Đã xóa sạch toàn bộ sổ nợ và giao dịch!"); st.rerun()

        else:
            st.warning("⚠️ **BẢO MẬT TUYỆT ĐỐI:** Yêu cầu **nhập Mật khẩu Admin** để xóa sạch lịch sử nợ của nhóm này.")
            entered_admin_pwd = st.text_input("Nhập Mật khẩu Admin để xác nhận xóa:", type="password", key="admin_pwd_reset")
            confirm_code = st.text_input("Gõ chữ **`XOA`** vào ô dưới", placeholder="Nhập XOA...", key="xoa_user_box")
            
            is_admin_pwd_correct = False
            if entered_admin_pwd:
                check_admin = run_query("SELECT username FROM users WHERE role = 'admin' AND password = :p", params={"p": entered_admin_pwd})
                if not check_admin.empty:
                    is_admin_pwd_correct = True

            is_disabled = not (is_admin_pwd_correct and confirm_code.strip().upper() == "XOA")
            
            if st.button("🔥 XÓA SỔ NỢ NHÓM NÀY", type="primary", disabled=is_disabled):
                execute_db("DELETE FROM debt_logs WHERE debt_id IN (SELECT id FROM debts WHERE group_id = :g)", {"g": st.session_state['group_id']})
                execute_db("DELETE FROM debts WHERE group_id = :g", {"g": st.session_state['group_id']})
                st.success("🧹 Đã xóa sạch lịch sử nợ của nhóm bạn!"); st.rerun()
            
            if entered_admin_pwd and not is_admin_pwd_correct:
                st.error("❌ Mật khẩu Admin không chính xác!")

# ==========================================
# KHỐI 2: SỔ CHI TIÊU
# ==========================================
elif app_mode == "🛒 Sổ Chi Tiêu":
    st.markdown('<div class="exp-title">🛒 SỔ GHI CHÉP CHI TIÊU</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Ghi chép và theo dõi dòng tiền hàng ngày</div>', unsafe_allow_html=True)
    
    exp_df = fetch_expenses(current_view_group)
    
    if not exp_df.empty:
        exp_df["amount"] = pd.to_numeric(exp_df["amount"])
        total_exp = float(exp_df["amount"].sum())
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-card card-exp1"><div class="metric-label">🛒 Tổng Tiền Đã Chi</div><div class="metric-value">{total_exp:,.0f} ₫</div></div>
            <div class="metric-card card-exp2"><div class="metric-label">📝 Số Giao Dịch</div><div class="metric-value">{len(exp_df)} Lần</div></div>
        </div>
        """, unsafe_allow_html=True)

    tab_e1, tab_e2, tab_e3 = st.tabs(["📋 Lịch sử & Thống kê", "➕ Thêm Khoản Chi", "⚙️ Quản lý (Xóa)"])

    with tab_e1:
        if not exp_df.empty:
            display_exp = exp_df.copy()
            display_exp['Ngày chi'] = display_exp['expense_date'].apply(lambda dt: pd.to_datetime(dt).strftime('%d/%m/%Y') if pd.notna(dt) else "")
            
            st.dataframe(
                display_exp[["id", "Ngày chi", "group_id", "title", "amount", "category", "paid_by", "note"]],
                column_config={
                    "amount": st.column_config.NumberColumn("Số tiền", format="%.0f ₫"),
                    "title": "Nội dung", "category": "Danh mục", "paid_by": "Người trả", "note": "Ghi chú"
                },
                hide_index=True, use_container_width=True
            )
        else:
            st.info("Chưa có khoản chi nào. Hãy thêm khoản chi đầu tiên nhé!")

    with tab_e2:
        if current_view_group == "ALL" and st.session_state['role'] == 'admin':
             st.warning("⚠️ **Quyền Admin:** Bạn đang xem Tất cả các sổ. Vui lòng chọn cụ thể 1 Sổ ở Sidebar bên trái nếu muốn thêm khoản chi.")
        else:
            with st.form("add_exp_form", clear_on_submit=True):
                exp_title = st.text_input("Nội dung chi (VD: Đi siêu thị, Ăn lẩu)")
                exp_amount = st.number_input("Số tiền (VNĐ)", min_value=0.0, step=50000.0, format="%.0f")
                
                col_x, col_y, col_z = st.columns(3)
                exp_cat = col_x.selectbox("Danh mục", ["Ăn uống", "Mua sắm", "Hóa đơn/Tiện ích", "Giải trí", "Đi lại", "Khác"])
                exp_paid_by = col_y.text_input("Người rút ví trả")
                exp_date = col_z.date_input("Ngày chi", value=date.today())
                exp_note = st.text_area("Ghi chú thêm (Tùy chọn)")
                
                if st.form_submit_button("🛒 LƯU KHOẢN CHI", type="primary"):
                    if exp_title and exp_amount > 0:
                        execute_db("""
                            INSERT INTO expenses (title, amount, category, paid_by, note, expense_date, group_id) 
                            VALUES (:t, :a, :c, :p, :n, :d, :g)
                        """, {
                            "t": exp_title, "a": float(exp_amount), "c": exp_cat, 
                            "p": exp_paid_by, "n": exp_note, "d": exp_date, "g": current_view_group
                        })
                        st.success("Đã ghi nhận khoản chi thành công!"); st.rerun()
                    else:
                        st.error("⚠️ Vui lòng nhập Tên khoản chi và Số tiền lớn hơn 0.")

    with tab_e3:
        if st.session_state['role'] == 'admin':
            st.markdown("### 🗑️ Xóa Chi Tiết Khoản Chi Tiêu (Tích Chọn)")
            if not exp_df.empty:
                exp_df['Chọn'] = False
                edited_exp = st.data_editor(
                    exp_df[["Chọn", "id", "group_id", "expense_date", "title", "amount"]],
                    column_config={"amount": st.column_config.NumberColumn("Số tiền", format="%.0f ₫")},
                    hide_index=True, use_container_width=True
                )
                sel_exp_ids = edited_exp[edited_exp["Chọn"] == True]["id"].tolist()
                
                if sel_exp_ids:
                    if st.button("🔥 XÓA CÁC KHOẢN CHI ĐÃ CHỌN", type="primary"):
                        for eid in sel_exp_ids:
                            execute_db("DELETE FROM expenses WHERE id = :id", {"id": int(eid)})
                        st.success(f"Đã xóa {len(sel_exp_ids)} khoản chi!"); st.rerun()
            else:
                st.caption("Chưa có dữ liệu.")
        else:
            st.warning("⚠️ Chỉ Admin mới có quyền xóa dữ liệu chi tiêu.")
