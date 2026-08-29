import streamlit as st
import pandas as pd
import sqlite3
import datetime
import plotly.express as px
import plotly.graph_objects as go
import os
from fpdf import FPDF
import time


# ==========================================
# 1. KONFIGURASI HALAMAN & DATABASE
# ==========================================
st.set_page_config(
    page_title="NutriTrack Pro - Health & Nutrition Dashboard", 
    page_icon="🥗", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Theme (Modern Dark Glassmorphism)
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
</style>
""", unsafe_allow_html=True)

def init_db():
    conn = sqlite3.connect("nutrition_tracker.db")
    c = conn.cursor()
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
    
    for table in ["food_logs", "water_logs", "weight_logs"]:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN user_id TEXT DEFAULT 'guest'")
        except sqlite3.OperationalError:
            pass
            
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
    "Telur Dadar Sayur (1 porsi)": {"kalori": 170, "protein": 13.0, "karbo": 3.0, "lemak": 12.0},
    "Roti Tawar Gandum (2 lembar)": {"kalori": 130, "protein": 5.0, "karbo": 24.0, "lemak": 1.5},
    "Tempe Goreng Tepung (1 potong)": {"kalori": 90, "protein": 6.0, "karbo": 5.0, "lemak": 5.0},
    "Nasi Uduk Half + Telur Rebus": {"kalori": 280, "protein": 10.0, "karbo": 35.0, "lemak": 11.0},
    "Bubur Ayam Tanpa Kerupuk (1 mangkok)": {"kalori": 250, "protein": 14.0, "karbo": 35.0, "lemak": 5.0},
    "Nasi Kuning Half + Telur Suwir": {"kalori": 260, "protein": 11.0, "karbo": 36.0, "lemak": 8.0},
    "Lontong Sayur Telur Kuah Dikit": {"kalori": 270, "protein": 11.0, "karbo": 34.0, "lemak": 10.0},
    "Tahu Kukus Isi Daging (2 pcs)": {"kalori": 160, "protein": 14.0, "karbo": 5.0, "lemak": 9.0},
    "Oatmeal Instant + Susu Low Fat": {"kalori": 230, "protein": 10.0, "karbo": 36.0, "lemak": 5.0},
    "Ayam Goreng Lengkuas - Dada (1 potong)": {"kalori": 240, "protein": 35.0, "karbo": 2.0, "lemak": 10.0},
    "Ayam Bakar Kecap - Dada (1 potong)": {"kalori": 220, "protein": 35.0, "karbo": 5.0, "lemak": 6.0},
    "Ikan Lele Goreng (1 ekor)": {"kalori": 200, "protein": 18.0, "karbo": 2.0, "lemak": 13.0},
    "Ikan Nila Bakar (1 ekor/150g)": {"kalori": 190, "protein": 30.0, "karbo": 2.0, "lemak": 7.0},
    "Tahu Bacem (1 potong)": {"kalori": 80, "protein": 5.0, "karbo": 9.0, "lemak": 3.0},
    "Tempe Bacem (1 potong)": {"kalori": 100, "protein": 7.0, "karbo": 9.0, "lemak": 4.0},
    "Tumis Kangkung / Bayam (1 porsi)": {"kalori": 80, "protein": 3.0, "karbo": 6.0, "lemak": 5.0},
    "Soto Ayam Bening + Nasi Half": {"kalori": 290, "protein": 20.0, "karbo": 32.0, "lemak": 8.0},
    "Pecel Lele + Lalapan (Tanpa Nasi)": {"kalori": 220, "protein": 18.0, "karbo": 4.0, "lemak": 14.0},
    "Sayur Asem (1 mangkok)": {"kalori": 80, "protein": 2.0, "karbo": 14.0, "lemak": 2.0},
    "Ayam Suwir Balado - Dada (100g)": {"kalori": 190, "protein": 30.0, "karbo": 4.0, "lemak": 6.0},
    "Sup Ayam Bening - Dada (1 mangkok)": {"kalori": 190, "protein": 25.0, "karbo": 10.0, "lemak": 5.0},
    "Capcay Ayam Kuah (1 porsi)": {"kalori": 210, "protein": 22.0, "karbo": 12.0, "lemak": 8.0},
    "Sate Ayam Tanpa Bumbu Kacang (8 tusuk)": {"kalori": 200, "protein": 32.0, "karbo": 2.0, "lemak": 6.0},
    "Tumis Buncis Telur Orak-Arik (1 porsi)": {"kalori": 150, "protein": 9.0, "karbo": 8.0, "lemak": 9.0},
    "Ikan Tongkol Balado (1 potong/100g)": {"kalori": 180, "protein": 24.0, "karbo": 3.0, "lemak": 8.0},
    "Tahu Tek / Tahu Telur Sedikit Minyak": {"kalori": 250, "protein": 16.0, "karbo": 20.0, "lemak": 12.0},
    "Nasi Goreng Kampung Simpel + Telur": {"kalori": 320, "protein": 12.0, "karbo": 42.0, "lemak": 11.0},
    "Tumis Tahu Jamur (1 porsi)": {"kalori": 160, "protein": 12.0, "karbo": 8.0, "lemak": 9.0},
    "Soto Daging Bening Tanpa Santan": {"kalori": 220, "protein": 22.0, "karbo": 6.0, "lemak": 12.0},
    "Kentang Rebus (100g)": {"kalori": 87, "protein": 1.9, "karbo": 20.0, "lemak": 0.1},
    "Edamame Rebus (100g)": {"kalori": 120, "protein": 11.0, "karbo": 10.0, "lemak": 5.0},
    "Apel Red / Fuji (1 buah)": {"kalori": 80, "protein": 0.4, "karbo": 21.0, "lemak": 0.2},
    "Pisang Ambon / Sunpride (1 buah)": {"kalori": 90, "protein": 1.1, "karbo": 23.0, "lemak": 0.3},
    "Kacang Almond Panggang (15 butir)": {"kalori": 105, "protein": 4.0, "karbo": 3.0, "lemak": 9.0},
    "Roti Gandum + Peanut Butter (1 sheet)": {"kalori": 180, "protein": 7.0, "karbo": 20.0, "lemak": 8.0},
    "Puding Chia Seed / Agar Plain": {"kalori": 70, "protein": 3.0, "karbo": 8.0, "lemak": 3.0},
    "Dada Ayam Popcorn Airfryer (80g)": {"kalori": 130, "protein": 24.0, "karbo": 3.0, "lemak": 2.0},
    "Kacang Tanah Sangrai (25g)": {"kalori": 140, "protein": 6.0, "karbo": 5.0, "lemak": 12.0},
    "Keju Slice Low Fat (2 lembar)": {"kalori": 90, "protein": 8.0, "karbo": 2.0, "lemak": 5.0},
    "Dark Chocolate 70%+ (2 kotak/20g)": {"kalori": 110, "protein": 1.5, "karbo": 9.0, "lemak": 8.0},
    "Salmon Nigiri (2 pcs)": {"kalori": 130, "protein": 7.0, "karbo": 15.0, "lemak": 3.5},
    "Tuna Nigiri (2 pcs)": {"kalori": 110, "protein": 8.0, "karbo": 15.0, "lemak": 1.0},
    "Salmon Maki Roll (6 pcs)": {"kalori": 180, "protein": 9.0, "karbo": 28.0, "lemak": 3.0},
    "California Roll (8 pcs)": {"kalori": 280, "protein": 7.0, "karbo": 38.0, "lemak": 7.0},
    "Spicy Tuna Roll (8 pcs)": {"kalori": 320, "protein": 12.0, "karbo": 36.0, "lemak": 11.0},
    "Chicken Katsu Roll (8 pcs)": {"kalori": 380, "protein": 14.0, "karbo": 45.0, "lemak": 14.0},
    "Salmon Mentai Roll (8 pcs)": {"kalori": 450, "protein": 15.0, "karbo": 48.0, "lemak": 18.0},
    "Salmon Sashimi (5 pcs/Tanpa Nasi)": {"kalori": 170, "protein": 23.0, "karbo": 0.0, "lemak": 8.0},
}

# ==========================================
# 2. HELPER FUNCTIONS
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
    
    if not dates: return 0
    today = datetime.date.today()
    streak = 0
    check_date = today
    if today not in dates:
        check_date = today - datetime.timedelta(days=1)
        if check_date not in dates: return 0
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

class PDFWithWatermark(FPDF):
    def header(self):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(BASE_DIR, "logo-removebg-preview.png")
        if os.path.exists(logo_path):
            try:
                self.set_alpha(0.15)
                self.image(logo_path, x=55, y=90, w=100)
                self.set_alpha(1.0)
            except Exception as e:
                print(f"Error watermark: {e}")

def generate_pdf_report(user_id, tanggal, df_food, water_ml, target_kal, target_prot, target_karb, target_lem):
    pdf = PDFWithWatermark()
    pdf.add_page()
    
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, f"NutriTrack Pro - Daily Report", ln=True, align="C")
    
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"User ID: {user_id.upper()}  |  Tanggal: {tanggal}", ln=True, align="C")
    pdf.ln(6)
    
    tot_kal = df_food["Kalori (kcal)"].sum() if not df_food.empty else 0
    tot_prot = df_food["Protein (g)"].sum() if not df_food.empty else 0
    tot_karbo = df_food["Karbohidrat (g)"].sum() if not df_food.empty else 0
    tot_lemak = df_food["Lemak (g)"].sum() if not df_food.empty else 0
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1. Ringkasan Nutrisi Harian", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"- Total Kalori    : {tot_kal:.0f} / {target_kal} kcal", ln=True)
    pdf.cell(0, 6, f"- Total Protein   : {tot_prot:.1f} / {target_prot} g", ln=True)
    pdf.cell(0, 6, f"- Total Karbo     : {tot_karbo:.1f} / {target_karb} g", ln=True)
    pdf.cell(0, 6, f"- Total Lemak     : {tot_lemak:.1f} / {target_lem} g", ln=True)
    pdf.cell(0, 6, f"- Total Air Minum : {water_ml} ml", ln=True)
    pdf.ln(6)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2. Detail Log Makanan", ln=True)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(30, 7, "Waktu", 1)
    pdf.cell(75, 7, "Makanan", 1)
    pdf.cell(25, 7, "Kalori", 1)
    pdf.cell(25, 7, "Protein", 1)
    pdf.cell(25, 7, "Karbo", 1)
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 9)
    if not df_food.empty:
        for _, row in df_food.iterrows():
            pdf.cell(30, 6, str(row["Waktu"]), 1)
            pdf.cell(75, 6, str(row["Makanan"])[:38], 1)
            pdf.cell(25, 6, f"{row['Kalori (kcal)']:.0f} kcal", 1)
            pdf.cell(25, 6, f"{row['Protein (g)']:.1f} g", 1)
            pdf.cell(25, 6, f"{row['Karbohidrat (g)']:.1f} g", 1)
            pdf.ln()
    else:
        pdf.cell(180, 6, "Belum ada catatan makanan pada tanggal ini.", 1, ln=True, align="C")
        
    return bytes(pdf.output())


# ==========================================
# 3. MANAJEMEN URL QUERY PARAMS & STATE
# ==========================================

query_params = st.query_params

# Default User
default_user = query_params.get("user", "User1")
if "user_id_input" not in st.session_state:
    st.session_state["user_id_input"] = default_user

# Default Calculator Params (Di-sync ke Bookmark)
st.session_state.setdefault("calc_gender", query_params.get("gender", "Pria"))
st.session_state.setdefault("calc_usia", int(query_params.get("usia", 22)))
st.session_state.setdefault("calc_bb", float(query_params.get("bb", 65.0)))
st.session_state.setdefault("calc_tb", float(query_params.get("tb", 170.0)))
st.session_state.setdefault("calc_aktivitas", query_params.get("aktivitas", "Ringan (Olahraga 1-3 hari/minggu)"))
st.session_state.setdefault("calc_goal", query_params.get("goal", "Defisit Kalori (-500 kcal / Turun BB)"))

# Default Target Nutrisi Harian
st.session_state.setdefault('target_kalori_val', int(query_params.get("target_kal", 2000)))
st.session_state.setdefault('target_protein_val', int(query_params.get("target_prot", 120)))
st.session_state.setdefault('target_karbo_val', int(query_params.get("target_karb", 250)))
st.session_state.setdefault('target_lemak_val', int(query_params.get("target_lem", 60)))

def update_url_params():
    """Fungsi sync state ke URL browser untuk Bookmark"""
    st.query_params["user"] = st.session_state["user_id_input"]
    st.query_params["gender"] = st.session_state["calc_gender"]
    st.query_params["usia"] = str(st.session_state["calc_usia"])
    st.query_params["bb"] = str(st.session_state["calc_bb"])
    st.query_params["tb"] = str(st.session_state["calc_tb"])
    st.query_params["aktivitas"] = st.session_state["calc_aktivitas"]
    st.query_params["goal"] = st.session_state["calc_goal"]
    st.query_params["target_kal"] = str(st.session_state["target_kalori_val"])
    st.query_params["target_prot"] = str(st.session_state["target_protein_val"])
    st.query_params["target_karb"] = str(st.session_state["target_karbo_val"])
    st.query_params["target_lem"] = str(st.session_state["target_lemak_val"])


# ==========================================
# 4. SIDEBAR (PROFIL + KALKULATOR & TARGET)
# ==========================================

st.sidebar.title("📌 Menu & Pengaturan")

# --- PROFIL USER ---
st.sidebar.subheader("👤 Profil Pengguna")
raw_user = st.sidebar.text_input(
    "Masukkan Nama/ID Kamu:", 
    key="user_id_input",
    on_change=update_url_params,
    help="Gunakan nama unikmu agar data tidak kecampur"
)
user_id = raw_user.strip().lower() if raw_user.strip() else "guest"

streak_days = get_streak_count(user_id)
st.sidebar.markdown(f"🔥 Streak **[{user_id.upper()}]**: **{streak_days} Hari**")

st.sidebar.divider()

# --- MODE TANGGAL ---
use_today_auto = st.sidebar.checkbox("🔄 Reset Otomatis 24 Jam (Hari Ini)", value=True)
if use_today_auto:
    selected_date = datetime.date.today().strftime("%Y-%m-%d")
    st.sidebar.caption("⚡ Mode Otomatis Aktif: Tanggal hari ini.")
else:
    selected_date = st.sidebar.date_input("🗓️ Pilih Tanggal Log", datetime.date.today()).strftime("%Y-%m-%d")

st.sidebar.divider()

# --- KALKULATOR BMR & TDEE DI SIDEBAR ---
with st.sidebar.expander("⚖️ Kalkulator BMR & TDEE", expanded=False):
    list_jk = ["Pria", "Wanita"]
    list_aktivitas = [
        "Sedentary (Jarang olahraga)", 
        "Ringan (Olahraga 1-3 hari/minggu)",
        "Sedang (Olahraga 3-5 hari/minggu)", 
        "Berat (Olahraga 6-7 hari/minggu)",
        "Sangat Berat (Atlet / Pekerja Fisik)"
    ]
    list_goal = [
        "Maintenance (Jaga BB)", 
        "Defisit Kalori (-500 kcal / Turun BB)", 
        "Surplus Kalori (+300 kcal / Muscle Gain)"
    ]

    st.radio("Jenis Kelamin", list_jk, horizontal=True, key="calc_gender", on_change=update_url_params)
    st.number_input("Usia (tahun)", min_value=10, max_value=100, key="calc_usia", on_change=update_url_params)
    st.number_input("Berat Badan (kg)", min_value=30.0, max_value=200.0, step=0.5, key="calc_bb", on_change=update_url_params)
    st.number_input("Tinggi Badan (cm)", min_value=100.0, max_value=230.0, step=0.5, key="calc_tb", on_change=update_url_params)
    st.selectbox("Tingkat Aktivitas", list_aktivitas, key="calc_aktivitas", on_change=update_url_params)
    st.selectbox("Target Kebugaran", list_goal, key="calc_goal", on_change=update_url_params)

    # Hitung Rekomendasi
    _bb = st.session_state.calc_bb
    _tb = st.session_state.calc_tb
    _usia = st.session_state.calc_usia
    _gender = st.session_state.calc_gender
    _akt = st.session_state.calc_aktivitas
    _goal = st.session_state.calc_goal

    bmr = (10 * _bb) + (6.25 * _tb) - (5 * _usia) + (5 if _gender == "Pria" else -161)
    mult_dict = {
        "Sedentary (Jarang olahraga)": 1.2, 
        "Ringan (Olahraga 1-3 hari/minggu)": 1.375,
        "Sedang (Olahraga 3-5 hari/minggu)": 1.55, 
        "Berat (Olahraga 6-7 hari/minggu)": 1.725,
        "Sangat Berat (Atlet / Pekerja Fisik)": 1.9
    }
    tdee = bmr * mult_dict[_akt]
    target_calc = tdee
    if "Defisit" in _goal: target_calc -= 500
    elif "Surplus" in _goal: target_calc += 300

    st.info(f"**BMR:** {int(bmr)} kcal | **TDEE:** {int(tdee)} kcal\n\nRekomendasi: **{int(target_calc)} kcal**")
    
    if st.button("Terapkan Hasil Rekomendasi", use_container_width=True):
        st.session_state.target_kalori_val = int(target_calc)
        st.session_state.target_protein_val = int(_bb * 1.8)
        st.session_state.target_karbo_val = int((target_calc * 0.5) / 4)
        st.session_state.target_lemak_val = int((target_calc * 0.25) / 9)
        update_url_params()
        st.success("Target berhasil diperbarui!")
        st.rerun()

# --- CUSTOM TARGET MANUAL DI SIDEBAR ---
with st.sidebar.expander("🎯 Target Nutrisi Harian", expanded=False):
    st.number_input("Target Kalori (kcal)", step=50, key="target_kalori_val", on_change=update_url_params)
    st.number_input("Target Protein (g)", step=5, key="target_protein_val", on_change=update_url_params)
    st.number_input("Target Karbo (g)", step=10, key="target_karbo_val", on_change=update_url_params)
    st.number_input("Target Lemak (g)", step=5, key="target_lemak_val", on_change=update_url_params)

target_kalori = st.session_state.target_kalori_val
target_protein = st.session_state.target_protein_val
target_karbo = st.session_state.target_karbo_val
target_lemak = st.session_state.target_lemak_val
target_air = 2000

# Update URL awal
update_url_params()


# ==========================================
# 5. DASHBOARD UTAMA
# ==========================================

st.title("🥗 Food & Nutrition Tracker Pro")
st.caption(f"Aplikasi Monitoring Nutrisi Harian | User Active: **[{user_id.upper()}]** | Tanggal: **{selected_date}**")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🍱 Input Makanan", 
    "💧 Hydration Tracker", 
    "📊 Dashboard Visual", 
    "⚖️ Weight Progress", 
    "📈 Riwayat & Export",
    "☁️ Cloud Sync"
])

# --- TAB 1: INPUT MAKANAN ---
with tab1:
    subtab1, subtab2 = st.tabs(["🍱 Racik Menu (Database)", "✏️ Input Custom Manual"])
    
    with subtab1:
        st.subheader("Racik Piring Makan")
        waktu_makan = st.selectbox("Waktu Makan", ["Makan Pagi", "Makan Siang", "Makan Malam", "Camilan"], key="waktu_racik")
        
        filter_nutrisi = st.radio(
            "🎯 Filter Kategori Nutrisi:",
            ["Semua", "💪 Tinggi Protein", "🔥 Tinggi Kalori", "🍞 Tinggi Karbo", "🥑 Tinggi Lemak"],
            horizontal=True,
            key="filter_nutrisi_racik"
        )
        
        makanan_terfilter = []
        for nama, nutrisi in DATABASE_MAKANAN.items():
            if filter_nutrisi == "Semua":
                makanan_terfilter.append(nama)
            elif filter_nutrisi == "💪 Tinggi Protein" and nutrisi.get("protein", 0) >= 15:
                makanan_terfilter.append(nama)
            elif filter_nutrisi == "🔥 Tinggi Kalori" and nutrisi.get("kalori", 0) >= 300:
                makanan_terfilter.append(nama)
            elif filter_nutrisi == "🍞 Tinggi Karbo" and nutrisi.get("karbo", 0) >= 30:
                makanan_terfilter.append(nama)
            elif filter_nutrisi == "🥑 Tinggi Lemak" and nutrisi.get("lemak", 0) >= 10:
                makanan_terfilter.append(nama)
        
        item_terpilih = st.multiselect("Pilih Makanan yang Dimakan", options=makanan_terfilter, placeholder="Choose options")
        
        porsi_dict = {}
        if item_terpilih:
            st.write("**Atur Jumlah Porsi:**")
            cols = st.columns(min(len(item_terpilih), 3))
            for idx, item in enumerate(item_terpilih):
                with cols[idx % 3]:
                    porsi_dict[item] = st.number_input(f"Porsi {item}", min_value=0.1, value=1.0, step=0.1, key=f"porsi_{item}")
            
            if st.button("Tambah Semua ke Log"):
                for item in item_terpilih:
                    detail = DATABASE_MAKANAN[item]
                    p = porsi_dict[item]
                    add_food_to_db(
                        user_id, selected_date, waktu_makan, item, p,
                        round(detail["kalori"] * p, 1),
                        round(detail["protein"] * p, 1),
                        round(detail["karbo"] * p, 1),
                        round(detail["lemak"] * p, 1)
                    )
                st.success("Berhasil menambahkan makanan ke log!")
                st.rerun()

    with subtab2:
        st.subheader("Tambah Makanan Manual")
        with st.form("form_custom_makanan"):
            waktu_custom = st.selectbox("Waktu Makan", ["Makan Pagi", "Makan Siang", "Makan Malam", "Camilan"], key="waktu_custom")
            nama_custom = st.text_input("Nama Makanan", placeholder="Contoh: Ayam Geprek Sambal Korek")
            col_c1, col_c2, col_c3, col_c4 = st.columns(4)
            kal_custom = col_c1.number_input("Kalori (kcal)", min_value=0.0, step=5.0)
            prot_custom = col_c2.number_input("Protein (g)", min_value=0.0, step=1.0)
            karbo_custom = col_c3.number_input("Karbo (g)", min_value=0.0, step=1.0)
            lemak_custom = col_c4.number_input("Lemak (g)", min_value=0.0, step=1.0)
            
            submit_custom = st.form_submit_button("Tambah Custom Makanan")
            if submit_custom:
                if nama_custom:
                    add_food_to_db(user_id, selected_date, waktu_custom, f"[Custom] {nama_custom}", 1.0, kal_custom, prot_custom, karbo_custom, lemak_custom)
                    st.success(f"Berhasil menambahkan {nama_custom}!")
                    st.rerun()
                else:
                    st.error("Nama makanan tidak boleh kosong!")

    st.divider()
    st.subheader(f"📋 Log Makanan [{user_id.upper()}] - ({selected_date})")
    
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
                st.success("Item berhasil dihapus!")
                st.rerun()
        with col_del2:
            st.write(""); st.write("")
            if st.button("Hapus Semua Log Hari Ini"):
                clear_today_food_logs(user_id, selected_date)
                st.success("Seluruh log hari ini berhasil dihapus!")
                st.rerun()
    else:
        st.info("Belum ada makanan yang dicatat pada tanggal ini. (Reset otomatis tiap 24 jam)")

# --- TAB 2: HYDRATION TRACKER ---
with tab2:
    st.subheader(f"💧 Tracking Asupan Air Minum - [{user_id.upper()}]")
    
    current_water = get_water_total(user_id, selected_date)
    water_pct = min(1.0, current_water / target_air) if target_air > 0 else 0
    sisa_air = max(0, target_air - current_water)
    
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.markdown(f"""
        <div class="macro-card card-lemak">
            <div class="macro-title">Total Air Minum Hari Ini</div>
            <div class="macro-value">{current_water} <span style="font-size:1.1rem; font-weight:500;">ml</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col_stat2:
        st.markdown(f"""
        <div class="macro-card card-protein">
            <div class="macro-title">Target Harian</div>
            <div class="macro-value">{target_air} <span style="font-size:1.1rem; font-weight:500;">ml</span></div>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("")
    st.progress(water_pct)
    
    if current_water >= target_air:
        st.success("🎉 Selamat! Target asupan air minum hari ini sudah terpenuhi!")
    else:
        st.caption(f"💡 Kurang **{sisa_air} ml** lagi untuk mencapai target harianmu.")

    st.divider()

    st.write("**Tambah Asupan Air (Cepat):**")
    btn_c1, btn_c2, btn_c3, btn_c4 = st.columns(4)
    
    if btn_c1.button("🥤 +250 ml (Gelas)", use_container_width=True):
        add_water_to_db(user_id, selected_date, 250)
        st.rerun()
        
    if btn_c2.button("🍾 +500 ml (Botol)", use_container_width=True):
        add_water_to_db(user_id, selected_date, 500)
        st.rerun()
        
    if btn_c3.button("🍶 +600 ml (Sedang)", use_container_width=True):
        add_water_to_db(user_id, selected_date, 600)
        st.rerun()
        
    if btn_c4.button("🪣 +1500 ml (Galon)", use_container_width=True):
        add_water_to_db(user_id, selected_date, 1500)
        st.rerun()

    st.divider()
    
    col_custom_water, col_reset_water = st.columns([2, 1])
    with col_custom_water:
        w_custom_input = st.number_input("Jumlah Manual (ml):", min_value=50, step=50, value=200, key="water_custom_input")
        if st.button("Tambah Air Manual", use_container_width=True):
            add_water_to_db(user_id, selected_date, w_custom_input)
            st.success(f"Berhasil menambahkan {w_custom_input} ml air!")
            st.rerun()
            
    with col_reset_water:
        st.write(""); st.write("")
        if st.button("🔄 Reset Air Minum Hari Ini", use_container_width=True):
            reset_water_db(user_id, selected_date)
            st.rerun()

# --- TAB 3: DASHBOARD VISUAL ---
with tab3:
    st.subheader(f"📊 Summary Nutrisi & Schedule Protein - [{user_id.upper()}] ({selected_date})")
    
    df_today = load_food_logs(user_id, selected_date)
    
    tot_kalori = df_today["Kalori (kcal)"].sum() if not df_today.empty else 0
    tot_protein = df_today["Protein (g)"].sum() if not df_today.empty else 0
    tot_karbo = df_today["Karbohidrat (g)"].sum() if not df_today.empty else 0
    tot_lemak = df_today["Lemak (g)"].sum() if not df_today.empty else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="macro-card card-kalori">
            <div class="macro-title">🔥 Kalori Total</div>
            <div class="macro-value">{tot_kalori:.0f} <span style="font-size:0.9rem; font-weight:400; color:#8E9BAE;">/ {target_kalori} kcal</span></div>
            <div class="macro-sub" style="color: {'#FF5252' if tot_kalori > target_kalori else '#4CAF50'};">
                {'⚠️ Melebihi target' if tot_kalori > target_kalori else f'Sisa: {target_kalori - tot_kalori:.0f} kcal'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="macro-card card-protein">
            <div class="macro-title">🥩 Protein</div>
            <div class="macro-value">{tot_protein:.1f} <span style="font-size:0.9rem; font-weight:400; color:#8E9BAE;">/ {target_protein}g</span></div>
            <div class="macro-sub" style="color: #4CAF50;">Target Harian</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="macro-card card-karbo">
            <div class="macro-title">🌾 Karbohidrat</div>
            <div class="macro-value">{tot_karbo:.1f} <span style="font-size:0.9rem; font-weight:400; color:#8E9BAE;">/ {target_karbo}g</span></div>
            <div class="macro-sub" style="color: #FFB74D;">Target Harian</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="macro-card card-lemak">
            <div class="macro-title">🥑 Lemak</div>
            <div class="macro-value">{tot_lemak:.1f} <span style="font-size:0.9rem; font-weight:400; color:#8E9BAE;">/ {target_lemak}g</span></div>
            <div class="macro-sub" style="color: #29B6F6;">Target Harian</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("📅 Schedule Protein Timing Harian")
    st.caption("Target protein harian dipecah ideal ke 4 jadwal makan untuk penyerapan optimal:")
    
    target_prot_per_meal = target_protein / 4.0
    meals = ["Makan Pagi", "Makan Siang", "Makan Malam", "Camilan"]
    
    cols_meal = st.columns(4)
    for idx, m in enumerate(meals):
        with cols_meal[idx]:
            prot_makan = df_today[df_today["Waktu"] == m]["Protein (g)"].sum() if not df_today.empty else 0.0
            pct_makan = min(1.0, prot_makan / target_prot_per_meal) if target_prot_per_meal > 0 else 0
            
            st.markdown(f"**{m}**")
            st.write(f"🥩 **{prot_makan:.1f}** / {target_prot_per_meal:.1f} g")
            st.progress(pct_makan)

    st.divider()
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Proporsi Makronutrisi")
        if tot_protein == 0 and tot_karbo == 0 and tot_lemak == 0:
            st.info("Belum ada data makronutrisi hari ini.")
        else:
            df_macro = pd.DataFrame({
                'Nutrisi': ['Protein', 'Karbohidrat', 'Lemak'],
                'Gram': [tot_protein, tot_karbo, tot_lemak]
            })
            fig_pie = px.pie(
                df_macro, values='Gram', names='Nutrisi',
                color='Nutrisi',
                color_discrete_map={'Protein':'#4CAF50', 'Karbohidrat':'#FFB74D', 'Lemak':'#29B6F6'},
                hole=0.4
            )
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#FFFFFF")
            st.plotly_chart(fig_pie, use_container_width=True)
            
    with col_chart2:
        st.subheader("Kalori per Waktu Makan")
        if not df_today.empty:
            df_waktu = df_today.groupby("Waktu")["Kalori (kcal)"].sum().reset_index()
            fig_bar = px.bar(
                df_waktu, x="Waktu", y="Kalori (kcal)",
                color="Waktu",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#FFFFFF")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Belum ada data kalori per waktu makan.")

# --- TAB 4: WEIGHT PROGRESS ---
with tab4:
    st.subheader(f"⚖️ Catat & Pantau Berat Badan - [{user_id.upper()}]")
    
    col_w1, col_w2 = st.columns([1, 2])
    with col_w1:
        st.write("**Log Berat Badan Hari Ini:**")
        input_bb = st.number_input("Berat Badan (kg)", min_value=30.0, max_value=200.0, value=65.0, step=0.1, key="weight_input")
        if st.button("Simpan Berat Badan"):
            log_weight(user_id, selected_date, input_bb)
            st.success(f"Berat badan {input_bb} kg tersimpan untuk {selected_date}!")
            st.rerun()
            
    with col_w2:
        df_w = get_weight_history(user_id)
        if not df_w.empty:
            st.write("**Riwayat & Tren Berat Badan:**")
            fig_w = px.line(df_w, x="tanggal", y="berat", markers=True, title="Progress Berat Badan (kg)")
            fig_w.update_traces(line_color='#4CAF50', marker_size=8)
            fig_w.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#FFFFFF")
            st.plotly_chart(fig_w, use_container_width=True)
            st.dataframe(df_w, use_container_width=True)
        else:
            st.info("Belum ada riwayat berat badan yang dicatat.")

# --- TAB 5: RIWAYAT & EXPORT PDF ---
with tab5:
    st.subheader(f"📈 Riwayat Tren 7 Hari & Export PDF - [{user_id.upper()}]")
    
    df_today_export = load_food_logs(user_id, selected_date)
    water_export = get_water_total(user_id, selected_date)
    
    pdf_bytes = generate_pdf_report(
        user_id, selected_date, df_today_export, water_export, 
        target_kalori, target_protein, target_karbo, target_lemak
    )
    
    st.download_button(
        label="📄 Download PDF Tracker Report Harian",
        data=pdf_bytes,
        file_name=f"NutriTrack_Report_{user_id}_{selected_date}.pdf",
        mime="application/pdf"
    )
    
    st.divider()
    df_history = get_weekly_history(user_id)
    
    if not df_history.empty:
        fig_hist = px.bar(
            df_history, x="tanggal", y="total_kalori",
            title="Total Kalori Harian (7 Hari Terakhir)",
            text="total_kalori",
            color_discrete_sequence=['#FF5252']
        )
        fig_hist.add_hline(y=target_kalori, line_dash="dash", line_color="green", annotation_text="Target Kalori")
        fig_hist.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#FFFFFF")
        st.plotly_chart(fig_hist, use_container_width=True)
        
        st.subheader("Data Riwayat")
        st.dataframe(df_history, use_container_width=True)
    else:
        st.info("Belum ada riwayat data makanan.")

# --- TAB 6: CLOUD SYNC ---
with tab6:
    st.subheader("☁️ Google Sheets Cloud Sync")
    st.caption("Pilih opsi integrasi cloud untuk backup data kamu secara permanen.")
    
    sheet_url = st.text_input("Google Sheets Link / App Script URL:", placeholder="https://docs.google.com/spreadsheets/d/...")
    
    col_cs1, col_cs2 = st.columns(2)
    with col_cs1:
        if st.button("📤 Backup Local DB ke Cloud"):
            st.info("Proses backup ke Google Sheets...")
    with col_cs2:
        if st.button("📥 Sync/Fetch Data dari Cloud"):
            st.info("Proses sinkronisasi data...")
