import streamlit as st
import pandas as pd
import sqlite3
import datetime
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. KONFIGURASI HALAMAN & DATABASE
# ==========================================
st.set_page_config(
    page_title="NutriTrack Pro - Health & Nutrition Dashboard", 
    page_icon="🥗", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Theme (Modern Dark Glassmorphism, Apple Health Cards, Mobile Polish)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgba(18, 24, 38, 1) 0%, rgba(9, 13, 22, 1) 90%);
    }
    .macro-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(12px);
        border-radius: 16px;
        padding: 18px;
        transition: transform 0.2s ease, border-color 0.2s ease;
        margin-bottom: 10px;
    }
    .macro-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.2);
    }
    .macro-title {
        font-size: 0.82rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #8E9BAE; margin-bottom: 6px;
    }
    .macro-value { font-size: 1.6rem; font-weight: 800; color: #FFFFFF; }
    .macro-sub { font-size: 0.78rem; margin-top: 4px; font-weight: 500; }
    
    .card-kalori { border-left: 4px solid #FF5252; }
    .card-protein { border-left: 4px solid #4CAF50; }
    .card-karbo { border-left: 4px solid #FFB74D; }
    .card-lemak { border-left: 4px solid #29B6F6; }
    
    section[data-testid="stSidebar"] {
        background-color: rgba(13, 17, 28, 0.85);
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; background-color: rgba(255, 255, 255, 0.03); padding: 6px; border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px; padding: 8px 16px; color: #8E9BAE; font-weight: 600; border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(255, 255, 255, 0.1) !important; color: #FFFFFF !important;
    }
    .stButton>button {
        border-radius: 10px; font-weight: 600; border: 1px solid rgba(255, 255, 255, 0.1); transition: all 0.2s ease;
    }
    .stButton>button:hover { border-color: #4CAF50; color: #4CAF50; }
    
    @media (max-width: 768px) {
        .macro-value { font-size: 1.3rem; }
        .stTabs [data-baseweb="tab"] { padding: 6px 10px; font-size: 0.85rem; }
    }
</style>
""", unsafe_allow_html=True)


def init_db():
    conn = sqlite3.connect("nutrition_tracker.db")
    c = conn.cursor()
    # Ditambahkan kolom 'user_id' di setiap tabel
    c.execute('''
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'guest',
            tanggal TEXT, waktu TEXT, makanan TEXT, porsi REAL,
            kalori REAL, protein REAL, karbo REAL, lemak REAL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS water_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'guest',
            tanggal TEXT, jumlah_ml INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS weight_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'guest',
            tanggal TEXT, berat REAL,
            UNIQUE(user_id, tanggal)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

DATABASE_MAKANAN = {
    "Nasi Putih (1 piring/150g)": {"kalori": 204, "protein": 4.2, "karbo": 44.0, "lemak": 0.4},
    "Oatmeal (40g dry)": {"kalori": 150, "protein": 5.0, "karbo": 27.0, "lemak": 2.5},
    "Nasi Goreng (1 piring)": {"kalori": 510, "protein": 12.5, "karbo": 65.0, "lemak": 21.0},
    "Fried Chicken - Dada (1 pcs)": {"kalori": 390, "protein": 34.0, "karbo": 11.0, "lemak": 23.0},
    "Dada Ayam Bakar (100g)": {"kalori": 165, "protein": 31.0, "karbo": 0.0, "lemak": 3.6},
    "Dada Ayam Rebus/Kukus (100g)": {"kalori": 130, "protein": 28.0, "karbo": 0.0, "lemak": 2.0},
    "Telur Rebus (1 butir)": {"kalori": 78, "protein": 6.3, "karbo": 0.6, "lemak": 5.3},
    "Telur Dadar (1 butir)": {"kalori": 110, "protein": 6.5, "karbo": 0.8, "lemak": 9.0},
    "Tahu Goreng (1 potong)": {"kalori": 35, "protein": 2.0, "karbo": 1.5, "lemak": 2.5},
    "Tempe Goreng (1 potong)": {"kalori": 50, "protein": 4.0, "karbo": 3.0, "lemak": 3.0},
    "Susu UHT Full Cream (200ml)": {"kalori": 120, "protein": 6.0, "karbo": 9.0, "lemak": 7.0},
    "Whey Protein Shake (1 scoop)": {"kalori": 120, "protein": 24.0, "karbo": 3.0, "lemak": 1.5},
    "Kebab Daging (1 pcs)": {"kalori": 520, "protein": 20.0, "karbo": 45.0, "lemak": 28.0},
    "Sei Sapi (100g)": {"kalori": 240, "protein": 26.0, "karbo": 2.0, "lemak": 14.0},
    "Sate Ayam (10 tusuk)": {"kalori": 340, "protein": 28.0, "karbo": 12.0, "lemak": 20.0},
    "Martabak Telur (1 potong)": {"kalori": 150, "protein": 5.5, "karbo": 12.0, "lemak": 9.0},
    "Kwetiau Goreng (1 piring)": {"kalori": 470, "protein": 10.0, "karbo": 60.0, "lemak": 21.0},
    "Sayur Bayam (1 mangkok)": {"kalori": 45, "protein": 2.5, "karbo": 7.0, "lemak": 0.5},
    "Sayur Buncis Tumis (1 porsi)": {"kalori": 65, "protein": 2.0, "karbo": 8.0, "lemak": 3.0},
    "Mie Goreng (1 piring)": {"kalori": 380, "protein": 9.0, "karbo": 54.0, "lemak": 14.0},
    "Ayam Goreng Paha/Dada (1 pcs)": {"kalori": 260, "protein": 22.0, "karbo": 4.0, "lemak": 17.0},
    "Lumpia Ubi (1 pcs)": {"kalori": 110, "protein": 1.5, "karbo": 18.0, "lemak": 4.0},
}

# ==========================================
# 2. DATABASE HELPER FUNCTIONS (WITH USER ID)
# ==========================================

def add_food_to_db(user_id, tanggal, waktu, makanan, porsi, kalori, protein, karbo, lemak):
    conn = sqlite3.connect("nutrition_tracker.db")
    c = conn.cursor()
    c.execute('''
        INSERT INTO food_logs (user_id, tanggal, waktu, makanan, porsi, kalori, protein, karbo, lemak)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, tanggal, waktu, makanan, porsi, kalori, protein, karbo, lemak))
    conn.commit()
    conn.close()

def load_food_logs(user_id, tanggal):
    conn = sqlite3.connect("nutrition_tracker.db")
    df = pd.read_sql_query(
        "SELECT id, waktu as Waktu, makanan as Makanan, porsi as Porsi, kalori as [Kalori (kcal)], "
        "protein as [Protein (g)], karbo as [Karbohidrat (g)], lemak as [Lemak (g)] "
        "FROM food_logs WHERE user_id = ? AND tanggal = ?", conn, params=(user_id, tanggal)
    )
    conn.close()
    return df

def delete_food_item_db(user_id, item_id):
    conn = sqlite3.connect("nutrition_tracker.db")
    c = conn.cursor()
    c.execute("DELETE FROM food_logs WHERE user_id = ? AND id = ?", (user_id, item_id))
    conn.commit()
    conn.close()

def clear_today_food_logs(user_id, tanggal):
    conn = sqlite3.connect("nutrition_tracker.db")
    c = conn.cursor()
    c.execute("DELETE FROM food_logs WHERE user_id = ? AND tanggal = ?", (user_id, tanggal))
    conn.commit()
    conn.close()

def get_water_total(user_id, tanggal):
    conn = sqlite3.connect("nutrition_tracker.db")
    c = conn.cursor()
    c.execute("SELECT SUM(jumlah_ml) FROM water_logs WHERE user_id = ? AND tanggal = ?", (user_id, tanggal))
    res = c.fetchone()[0]
    conn.close()
    return res if res else 0

def add_water_to_db(user_id, tanggal, ml):
    conn = sqlite3.connect("nutrition_tracker.db")
    c = conn.cursor()
    c.execute("INSERT INTO water_logs (user_id, tanggal, jumlah_ml) VALUES (?, ?, ?)", (user_id, tanggal, ml))
    conn.commit()
    conn.close()

def reset_water_db(user_id, tanggal):
    conn = sqlite3.connect("nutrition_tracker.db")
    c = conn.cursor()
    c.execute("DELETE FROM water_logs WHERE user_id = ? AND tanggal = ?", (user_id, tanggal))
    conn.commit()
    conn.close()

def log_weight(user_id, tanggal, berat):
    conn = sqlite3.connect("nutrition_tracker.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO weight_logs (user_id, tanggal, berat) VALUES (?, ?, ?)", (user_id, tanggal, berat))
    conn.commit()
    conn.close()

def get_weight_history(user_id):
    conn = sqlite3.connect("nutrition_tracker.db")
    df = pd.read_sql_query("SELECT * FROM weight_logs WHERE user_id = ? ORDER BY tanggal ASC", conn, params=(user_id,))
    conn.close()
    return df

def get_streak_count(user_id):
    conn = sqlite3.connect("nutrition_tracker.db")
    c = conn.cursor()
    c.execute("SELECT DISTINCT tanggal FROM food_logs WHERE user_id = ? ORDER BY tanggal DESC", (user_id,))
    dates = [datetime.datetime.strptime(row[0], "%Y-%m-%d").date() for row in c.fetchall()]
    conn.close()
    
    if not dates:
        return 0
    today = datetime.date.today()
    streak = 0
    check_date = today
    if today not in dates:
        check_date = today - datetime.timedelta(days=1)
        if check_date not in dates:
            return 0
    while check_date in dates:
        streak += 1
        check_date -= datetime.timedelta(days=1)
    return streak

def get_weekly_history(user_id):
    conn = sqlite3.connect("nutrition_tracker.db")
    df = pd.read_sql_query("""
        SELECT tanggal, SUM(kalori) as total_kalori, SUM(protein) as total_protein, 
               SUM(karbo) as total_karbo, SUM(lemak) as total_lemak 
        FROM food_logs 
        WHERE user_id = ?
        GROUP BY tanggal 
        ORDER BY tanggal DESC LIMIT 7
    """, conn, params=(user_id,))
    conn.close()
    return df


# ==========================================
# 3. SIDEBAR (PROFIL USER & KALKULATOR)
# ==========================================

st.sidebar.title("⚙️ Fitur & Pengaturan")

# INPUT PROFILE / USER ID
st.sidebar.subheader("👤 Pilih Profil Pengguna")
raw_user = st.sidebar.text_input("Masukkan Nama/ID Kamu:", value="User1", help="Gunakan nama unikmu agar data tidak kecampur dengan orang lain")
user_id = raw_user.strip().lower() if raw_user.strip() else "guest"

# Streak Counter
streak_days = get_streak_count(user_id)
st.sidebar.markdown(f"### 🔥 Streak **[{user_id.upper()}]**: **{streak_days} Hari**")

st.sidebar.divider()
selected_date = st.sidebar.date_input("🗓️ Pilih Tanggal Log", datetime.date.today()).strftime("%Y-%m-%d")

# ------------------------------------------
# KALKULATOR BMR & TDEE
# ------------------------------------------
st.sidebar.divider()
st.sidebar.subheader("⚖️ Kalkulator BMR & TDEE")

qp = st.query_params

if "calc_jk" not in st.session_state:
    st.session_state.calc_jk = qp.get("jk", "Pria")
if "calc_usia" not in st.session_state:
    try: st.session_state.calc_usia = int(qp.get("usia", 22))
    except: st.session_state.calc_usia = 22
if "calc_bb" not in st.session_state:
    try: st.session_state.calc_bb = float(qp.get("bb", 65.0))
    except: st.session_state.calc_bb = 65.0
if "calc_tb" not in st.session_state:
    try: st.session_state.calc_tb = float(qp.get("tb", 170.0))
    except: st.session_state.calc_tb = 170.0
if "calc_akt" not in st.session_state:
    st.session_state.calc_akt = qp.get("aktivitas", "Sedentary (Jarang olahraga)")
if "calc_goal" not in st.session_state:
    st.session_state.calc_goal = qp.get("goal", "Maintenance (Jaga BB)")

def update_params():
    st.query_params["jk"] = st.session_state.calc_jk
    st.query_params["usia"] = str(st.session_state.calc_usia)
    st.query_params["bb"] = str(st.session_state.calc_bb)
    st.query_params["tb"] = str(st.session_state.calc_tb)
    st.query_params["aktivitas"] = st.session_state.calc_akt
    st.query_params["goal"] = st.session_state.calc_goal

with st.sidebar.expander("Hitung Kebutuhan Kalori", expanded=False):
    list_jk = ["Pria", "Wanita"]
    gender = st.radio("Jenis Kelamin", list_jk, key="calc_jk", horizontal=True, on_change=update_params)
    usia = st.number_input("Usia (tahun)", min_value=10, max_value=100, key="calc_usia", on_change=update_params)
    bb = st.number_input("Berat Badan (kg)", min_value=30.0, max_value=200.0, step=0.5, key="calc_bb", on_change=update_params)
    tb = st.number_input("Tinggi Badan (cm)", min_value=100.0, max_value=230.0, step=0.5, key="calc_tb", on_change=update_params)
    
    list_aktivitas = [
        "Sedentary (Jarang olahraga)", "Ringan (Olahraga 1-3 hari/minggu)",
        "Sedang (Olahraga 3-5 hari/minggu)", "Berat (Olahraga 6-7 hari/minggu)",
        "Sangat Berat (Atlet / Pekerja Fisik)"
    ]
    aktivitas = st.selectbox("Tingkat Aktivitas", list_aktivitas, key="calc_akt", on_change=update_params)
    
    list_goal = [
        "Maintenance (Jaga BB)", "Defisit Kalori (-500 kcal / Turun BB)", "Surplus Kalori (+300 kcal / Muscle Gain)"
    ]
    goal = st.selectbox("Target Kebugaran", list_goal, key="calc_goal", on_change=update_params)

    bmr = (10 * bb) + (6.25 * tb) - (5 * usia) + (5 if gender == "Pria" else -161)
    mult_dict = {
        "Sedentary (Jarang olahraga)": 1.2, "Ringan (Olahraga 1-3 hari/minggu)": 1.375,
        "Sedang (Olahraga 3-5 hari/minggu)": 1.55, "Berat (Olahraga 6-7 hari/minggu)": 1.725,
        "Sangat Berat (Atlet / Pekerja Fisik)": 1.9
    }
    tdee = bmr * mult_dict[aktivitas]
    
    target_calc = tdee
    if "Defisit" in goal: target_calc -= 500
    elif "Surplus" in goal: target_calc += 300
        
    st.info(f"**BMR:** {int(bmr)} kcal\n\n**TDEE:** {int(tdee)} kcal\n\n**Rekomendasi Target:** **{int(target_calc)} kcal**")
    
    if st.button("Gunakan Rekomendasi Ini"):
        st.session_state.target_kalori_val = int(target_calc)
        st.session_state.target_protein_val = int(bb * 1.8)
        st.session_state.target_karbo_val = int((target_calc * 0.5) / 4)
        st.session_state.target_lemak_val = int((target_calc * 0.25) / 9)
        st.success("Target berhasil diupdate!")

st.sidebar.divider()
st.sidebar.subheader("🎯 Custom Target Harian")

st.session_state.setdefault('target_kalori_val', 2000)
st.session_state.setdefault('target_protein_val', 120)
st.session_state.setdefault('target_karbo_val', 250)
st.session_state.setdefault('target_lemak_val', 60)

target_kalori = st.sidebar.number_input("Target Kalori (kcal)", value=st.session_state.target_kalori_val, step=50)
target_protein = st.sidebar.number_input("Target Protein (g)", value=st.session_state.target_protein_val, step=5)
target_karbo = st.sidebar.number_input("Target Karbo (g)", value=st.session_state.target_karbo_val, step=10)
target_lemak = st.sidebar.number_input("Target Lemak (g)", value=st.session_state.target_lemak_val, step=5)
target_air = st.sidebar.number_input("Target Air Minum (ml)", value=2000, step=250)


# ==========================================
# 4. DASHBOARD UTAMA & TABS
# ==========================================

st.title("🥗 Food & Nutrition Tracker Pro")
st.caption(f"Log & Monitoring Nutrisi | Profil: **{user_id.upper()}** | Tanggal: **{selected_date}**")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🍱 Input Makanan", "💧 Hydration Tracker", "📊 Dashboard Visual", 
    "⚖️ Weight Progress", "📈 Riwayat & Export", "☁️ Cloud Sync"
])

# ------------------------------------------
# TAB 1: INPUT MAKANAN
# ------------------------------------------
with tab1:
    subtab1, subtab2 = st.tabs(["🍱 Racik Menu", "✏️ Input Custom Manual"])
    
    with subtab1:
        st.subheader("Racik Piring Makan")
        waktu_makan = st.selectbox("Waktu Makan", ["Makan Pagi", "Makan Siang", "Makan Malam", "Camilan"], key="waktu_racik")
        item_terpilih = st.multiselect("Pilih Makanan yang Dimakan", list(DATABASE_MAKANAN.keys()))
        
        porsi_dict = {}
        if item_terpilih:
            st.write("**Atur Jumlah Porsi:**")
            cols = st.columns(min(len(item_terpilih), 3))
            for idx, item in enumerate(item_terpilih):
                with cols[idx % 3]:
                    porsi_dict[item] = st.number_input(
                        f"Porsi {item}", min_value=0.1, value=1.0, step=0.1, format="%g", key=f"porsi_{item}"
                    )
            
            if st.button("Tambah Semua ke Log"):
                for item in item_terpilih:
                    detail = DATABASE_MAKANAN[item]
                    p = porsi_dict[item]
                    add_food_to_db(
                        user_id, selected_date, waktu_makan, item, p,
                        round(detail["kalori"] * p, 1), round(detail["protein"] * p, 1),
                        round(detail["karbo"] * p, 1), round(detail["lemak"] * p, 1)
                    )
                st.success("Berhasil menambahkan makanan ke log!")
                st.rerun()

    with subtab2:
        st.subheader("Tambah Makanan Manual")
        with st.form("form_custom_makanan"):
            waktu_custom = st.selectbox("Waktu Makan", ["Makan Pagi", "Makan Siang", "Makan Malam", "Camilan"], key="waktu_custom")
            nama_custom = st.text_input("Nama Makanan", placeholder="Contoh: Ayam Geprek")
            c1, c2, c3, c4 = st.columns(4)
            kal_custom = c1.number_input("Kalori (kcal)", min_value=0.0, step=5.0, format="%g")
            prot_custom = c2.number_input("Protein (g)", min_value=0.0, step=1.0, format="%g")
            karbo_custom = c3.number_input("Karbo (g)", min_value=0.0, step=1.0, format="%g")
            lemak_custom = c4.number_input("Lemak (g)", min_value=0.0, step=1.0, format="%g")
            
            if st.form_submit_button("Tambah Custom Makanan"):
                if nama_custom:
                    add_food_to_db(user_id, selected_date, waktu_custom, f"[Custom] {nama_custom}", 1.0, kal_custom, prot_custom, karbo_custom, lemak_custom)
                    st.success(f"Berhasil menambahkan {nama_custom}!")
                    st.rerun()

    st.divider()
    st.subheader(f"📋 Log Makanan [{user_id.upper()}] ({selected_date})")
    df_today = load_food_logs(user_id, selected_date)
    
    if not df_today.empty:
        def color_waktu(val):
            colors = {
                "Makan Pagi": "background-color: rgba(255, 235, 59, 0.2); color: #FFF59D; font-weight: 600;",
                "Makan Siang": "background-color: rgba(255, 152, 0, 0.2); color: #FFCC80; font-weight: 600;",
                "Makan Malam": "background-color: rgba(156, 39, 176, 0.2); color: #E1BEE7; font-weight: 600;",
                "Camilan": "background-color: rgba(76, 175, 80, 0.2); color: #A5D6A7; font-weight: 600;"
            }
            return colors.get(val, '')

        df_styled = (
            df_today.drop(columns=["id"])
            .style.map(color_waktu, subset=["Waktu"])
            .format(precision=1)
        )
        st.dataframe(df_styled, use_container_width=True)
        
        col_del1, col_del2 = st.columns([2, 1])
        with col_del1:
            item_to_delete = st.selectbox("Pilih ID item untuk dihapus", df_today["id"].tolist())
            if st.button("Hapus Item Terpilih"):
                delete_food_item_db(user_id, item_to_delete)
                st.success("Item dihapus!")
                st.rerun()
        with col_del2:
            st.write("")
            st.write("")
            if st.button("Hapus Semua Log Hari Ini"):
                clear_today_food_logs(user_id, selected_date)
                st.rerun()
    else:
        st.info("Belum ada log makanan pada tanggal ini.")


# ------------------------------------------
# TAB 2: HYDRATION TRACKER
# ------------------------------------------
with tab2:
    st.subheader(f"💧 Hydration Tracker - {user_id.upper()}")
    current_water = get_water_total(user_id, selected_date)
    
    w_pct = min(1.0, current_water / target_air) if target_air > 0 else 0
    st.write(f"### Asupan Hari Ini: **{current_water} / {target_air} ml** ({int(w_pct * 100)}%)")
    st.progress(w_pct)
    
    st.write("#### Tambah Air Cepat:")
    w_col1, w_col2, w_col3, w_col4 = st.columns(4)
    if w_col1.button("🥤 +250 ml (Gelas)"):
        add_water_to_db(user_id, selected_date, 250); st.rerun()
    if w_col2.button("🍾 +500 ml (Botol Kecil)"):
        add_water_to_db(user_id, selected_date, 500); st.rerun()
    if w_col3.button("🍶 +600 ml (Botol Sedang)"):
        add_water_to_db(user_id, selected_date, 600); st.rerun()
    if w_col4.button("🪣 +1500 ml (Botol Besar)"):
        add_water_to_db(user_id, selected_date, 1500); st.rerun()
        
    st.divider()
    w_custom_input = st.number_input("Jumlah Manual (ml):", min_value=50, step=50, value=200)
    if st.button("Tambah Air Manual"):
        add_water_to_db(user_id, selected_date, w_custom_input)
        st.success(f"Berhasil menambahkan {w_custom_input} ml air!")
        st.rerun()
        
    if st.button("Reset Air Hari Ini"):
        reset_water_db(user_id, selected_date)
        st.rerun()


# ------------------------------------------
# TAB 3: DASHBOARD VISUAL
# ------------------------------------------
with tab3:
    st.subheader(f"🎯 Capaian Target Harian - {user_id.upper()}")
    df_today = load_food_logs(user_id, selected_date)
    
    tot_kal = df_today["Kalori (kcal)"].sum() if not df_today.empty else 0
    tot_prot = df_today["Protein (g)"].sum() if not df_today.empty else 0
    tot_karbo = df_today["Karbohidrat (g)"].sum() if not df_today.empty else 0
    tot_lemak = df_today["Lemak (g)"].sum() if not df_today.empty else 0
    
    c1, c2, c3, c4 = st.columns(4)
    
    kal_pct = (tot_kal / target_kalori * 100) if target_kalori else 0
    prot_pct = (tot_prot / target_protein * 100) if target_protein else 0
    karbo_pct = (tot_karbo / target_karbo * 100) if target_karbo else 0
    lemak_pct = (tot_lemak / target_lemak * 100) if target_lemak else 0

    with c1:
        st.markdown(f"""<div class="macro-card card-kalori"><div class="macro-title">🔥 Kalori Harian</div><div class="macro-value">{tot_kal:.0f} <span style="font-size:0.9rem;">/ {target_kalori} kcal</span></div><div class="macro-sub">{tot_kal - target_kalori:+.0f} kcal ({kal_pct:.0f}%)</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="macro-card card-protein"><div class="macro-title">🥩 Protein</div><div class="macro-value">{tot_prot:.1f} <span style="font-size:0.9rem;">/ {target_protein} g</span></div><div class="macro-sub">{tot_prot - target_protein:+.1f} g ({prot_pct:.0f}%)</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="macro-card card-karbo"><div class="macro-title">🌾 Karbohidrat</div><div class="macro-value">{tot_karbo:.1f} <span style="font-size:0.9rem;">/ {target_karbo} g</span></div><div class="macro-sub">{tot_karbo - target_karbo:+.1f} g ({karbo_pct:.0f}%)</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="macro-card card-lemak"><div class="macro-title">🥑 Lemak</div><div class="macro-value">{tot_lemak:.1f} <span style="font-size:0.9rem;">/ {target_lemak} g</span></div><div class="macro-sub">{tot_lemak - target_lemak:+.1f} g ({lemak_pct:.0f}%)</div></div>""", unsafe_allow_html=True)

    col_ring, col_chart2 = st.columns([1, 1])
    with col_ring:
        fig_ring = go.Figure()
        fig_ring.add_trace(go.Pie(values=[min(tot_kal, target_kalori), max(0, target_kalori - tot_kal)], hole=0.75, marker_colors=['#FF5252', 'rgba(255, 82, 82, 0.15)'], textinfo='none', hoverinfo='none', sort=False))
        fig_ring.add_trace(go.Pie(values=[min(tot_prot, target_protein), max(0, target_protein - tot_prot)], hole=0.55, domain={'x': [0.12, 0.88], 'y': [0.12, 0.88]}, marker_colors=['#4CAF50', 'rgba(76, 175, 80, 0.15)'], textinfo='none', hoverinfo='none', sort=False))
        fig_ring.update_layout(title="⭕ Activity Rings", showlegend=False, margin=dict(t=40, b=10, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', annotations=[{'text': f'<b>{int(kal_pct)}%</b>', 'x': 0.5, 'y': 0.5, 'font_size': 20, 'showarrow': False, 'font_color': '#FFFFFF'}])
        st.plotly_chart(fig_ring, use_container_width=True)

    with col_chart2:
        if not df_today.empty:
            breakdown_time = df_today.groupby("Waktu")["Kalori (kcal)"].sum().reset_index()
            fig_bar = px.bar(breakdown_time, x="Waktu", y="Kalori (kcal)", title="📊 Kalori per Waktu Makan", text_auto=True)
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#FFFFFF")
            st.plotly_chart(fig_bar, use_container_width=True)


# ------------------------------------------
# TAB 4: WEIGHT PROGRESS
# ------------------------------------------
with tab4:
    st.subheader(f"⚖️ Tracking Berat Badan - {user_id.upper()}")
    col_w1, col_w2 = st.columns([1, 2])
    with col_w1:
        input_bb = st.number_input("Berat Badan (kg)", min_value=30.0, max_value=200.0, value=65.0, step=0.1)
        if st.button("Simpan Berat Badan"):
            log_weight(user_id, selected_date, input_bb)
            st.success(f"Berat {input_bb} kg tersimpan!")
            st.rerun()
    with col_w2:
        df_w = get_weight_history(user_id)
        if not df_w.empty:
            fig_w = px.line(df_w, x="tanggal", y="berat", title="Grafik Berat Badan", markers=True)
            fig_w.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#FFFFFF")
            st.plotly_chart(fig_w, use_container_width=True)


# ------------------------------------------
# TAB 5: RIWAYAT & EXPORT
# ------------------------------------------
with tab5:
    st.subheader("📈 Riwayat Log 7 Hari Terakhir")
    df_history = get_weekly_history(user_id)
    if not df_history.empty:
        fig_line = px.line(df_history, x="tanggal", y="total_kalori", title="Tren Asupan Kalori Harian", markers=True)
        fig_line.add_hline(y=target_kalori, line_dash="dash", line_color="red")
        fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#FFFFFF")
        st.plotly_chart(fig_line, use_container_width=True)
        st.dataframe(df_history, use_container_width=True)


# ------------------------------------------
# TAB 6: GOOGLE SHEETS SYNC
# ------------------------------------------
with tab6:
    st.subheader("☁️ Sinkronisasi Data ke Google Sheets")
    gsheet_url = st.text_input("Masukkan Link Public Google Sheets kamu:")
    if st.button("Sync Database Sekarang"):
        if gsheet_url:
            try:
                conn_gs = st.connection("gsheets", type=GSheetsConnection)
                conn_local = sqlite3.connect("nutrition_tracker.db")
                df_to_sync = pd.read_sql_query("SELECT * FROM food_logs WHERE user_id = ?", conn_local, params=(user_id,))
                conn_local.close()
                conn_gs.update(spreadsheet=gsheet_url, data=df_to_sync)
                st.success("✅ Berhasil Backup data ke Google Sheets!")
            except Exception as e:
                st.error(f"Gagal sync: {e}")
