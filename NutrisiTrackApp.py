import streamlit as st
import pandas as pd
import sqlite3
import datetime
import plotly.express as px
import plotly.graph_objects as go
import os
from fpdf import FPDF
import time

st.set_page_config(
    page_title="NutriTrack Pro - Health & Nutrition Dashboard", 
    page_icon="🥗", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Desain Card Modern yang Otomatis Menyesuaikan Tema */
    .macro-card, .metric-card {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(150, 150, 150, 0.15);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
        border-radius: 24px;
        padding: 22px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 12px;
        position: relative;
        overflow: hidden;
    }
    .macro-card:hover, .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
    }
    
    /* Tipografi Card yang Mengikuti Text-Color Streamlit */
    .macro-title, .metric-title {
        font-size: 0.85rem; 
        font-weight: 700; 
        text-transform: capitalize; 
        color: var(--text-color); 
        opacity: 0.7;
        margin-bottom: 8px;
    }
    .macro-value, .metric-value { 
        font-size: 1.8rem; 
        font-weight: 800; 
        color: var(--text-color); 
    }
    .macro-sub, .metric-sub { 
        font-size: 0.75rem; 
        margin-top: 6px; 
        font-weight: 600; 
        color: var(--text-color);
        opacity: 0.7;
    }
    
    /* Aksen Warna Pastel */
    .card-kalori { border-bottom: 5px solid #D291BC; } 
    .card-protein { border-bottom: 5px solid #FFB7B2; } 
    .card-karbo { border-bottom: 5px solid #E2F0CB; } 
    .card-lemak { border-bottom: 5px solid #B5EAD7; } 
    
    /* PERBAIKAN FINAL & PALING AMPUH UNTUK TAB STREAMLIT */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; 
        background-color: var(--secondary-background-color); 
        padding: 8px; 
        border-radius: 16px; 
        border: 1px solid rgba(150, 150, 150, 0.15);
    }
    
    /* Target langsung tag button dari tab */
    .stTabs button[data-baseweb="tab"] {
        border-radius: 12px; 
        padding: 8px 16px; 
        font-weight: 600; 
        border: none !important;
        background-color: transparent !important;
        color: var(--text-color) !important;
    }

    /* Ketika Tab Aktif */
    .stTabs button[data-baseweb="tab"][aria-selected="true"] {
        background-color: var(--primary-color) !important; 
        border-radius: 12px !important;
    }

    /* Memaksa warna teks di dalam tombol tab aktif menjadi putih */
    .stTabs button[data-baseweb="tab"][aria-selected="true"] * {
        color: #FFFFFF !important;
    }
    
    /* Tombol Dinamis */
    .stButton>button {
        border-radius: 18px; 
        font-weight: 700; 
        background-color: var(--secondary-background-color); 
        border: 1px solid rgba(150, 150, 150, 0.3); 
        color: var(--text-color); 
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        transition: all 0.2s ease; 
    }
    .stButton>button:hover { 
        border-color: var(--primary-color); 
        color: var(--primary-color); 
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS workout_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'guest',
            tanggal TEXT,
            jenis_latihan TEXT,
            durasi_menit INTEGER,
            kalori_terbakar REAL
        )
    ''')
    
    for table in ["food_logs", "water_logs", "weight_logs", "workout_logs"]:
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
    "Roti Tawar Gandum (2 lembar)": {"kalori": 130, "protein": 5.0, "karbo": 24.0, "lemak": 1.5},

    "Dubai Chewy Cookies (1 pcs/70g)": {"kalori": 320, "protein": 4.5, "karbo": 38.0, "lemak": 17.0},
    "Es Krim Vanilla / Cokelat (1 scoop/75g)": {"kalori": 150, "protein": 2.5, "karbo": 18.0, "lemak": 7.5},
    "Kopi Hitam / Americano Unsweetened (1 gelas)": {"kalori": 5, "protein": 0.3, "karbo": 0.0, "lemak": 0.0},
    "Milk Tea / Boba Drink (1 cup standard)": {"kalori": 350, "protein": 3.0, "karbo": 58.0, "lemak": 12.0},
    "Yogurt Plain / Greek Yogurt (1 cup/125g)": {"kalori": 100, "protein": 7.0, "karbo": 8.0, "lemak": 4.0},
    
    "Ayam Goreng - Dada (1 pcs)": {"kalori": 220, "protein": 29.0, "karbo": 0.0, "lemak": 11.0},
    "Ayam Goreng - Paha Atas / Thigh (1 pcs)": {"kalori": 210, "protein": 22.0, "karbo": 0.0, "lemak": 13.0},
    "Ayam Goreng - Paha Bawah / Drumstick (1 pcs)": {"kalori": 160, "protein": 18.0, "karbo": 0.0, "lemak": 9.5},
    "Ayam Goreng - Kepak / Sayap (1 pcs)": {"kalori": 140, "protein": 12.0, "karbo": 0.0, "lemak": 10.0},
    "Ayam Goreng - Ati Ampela (1 pasang)": {"kalori": 120, "protein": 16.0, "karbo": 0.5, "lemak": 5.5},

    "Fried Chicken - Dada (1 pcs)": {"kalori": 390, "protein": 34.0, "karbo": 11.0, "lemak": 23.0},
    "Fried Chicken - Paha Upper (1 pcs)": {"kalori": 330, "protein": 24.0, "karbo": 9.0, "lemak": 22.0},
    "Fried Chicken - Paha Bawah / Drumstick (1 pcs)": {"kalori": 220, "protein": 16.0, "karbo": 7.0, "lemak": 14.0},
    "Fried Chicken - Sayap (1 pcs)": {"kalori": 210, "protein": 13.0, "karbo": 8.0, "lemak": 14.0},
    "Ayam Geprek + Tepung (1 porsi)": {"kalori": 420, "protein": 28.0, "karbo": 15.0, "lemak": 27.0},
    "Ayam Popcorn / Crispy Bites (100g)": {"kalori": 290, "protein": 18.0, "karbo": 16.0, "lemak": 17.0},
    "Dada Ayam Bakar (100g)": {"kalori": 165, "protein": 31.0, "karbo": 0.0, "lemak": 3.6},
    "Dada Ayam Rebus/Kukus (100g)": {"kalori": 130, "protein": 28.0, "karbo": 0.0, "lemak": 2.0},
    "Sate Ayam + Bumbu Kacang (10 tusuk)": {"kalori": 420, "protein": 32.0, "karbo": 12.0, "lemak": 26.0},
    "Dimsum Ayam (4 pcs)": {"kalori": 210, "protein": 14.0, "karbo": 18.0, "lemak": 9.0},

    "Sayur Lodeh": {"calories": 150, "protein": 4, "carbs": 15, "fat": 8},
    "Pecel Ayam": {"calories": 450, "protein": 35, "carbs": 15, "fat": 28},
    "Pecel Lele": {"calories": 400, "protein": 25, "carbs": 15, "fat": 25},
    "Sayur Pecel (Nasi + Sayur)": {"calories": 350, "protein": 8, "carbs": 50, "fat": 12},
    "Indomie Rebus": {"calories": 380, "protein": 8, "carbs": 54, "fat": 14},
    "Indomie Goreng": {"calories": 420, "protein": 9, "carbs": 60, "fat": 16},
    
    "Martabak Telur Daging Sapi (4 Telur - 1 Potong)": {"kalori": 190, "protein": 9.5, "karbo": 10.0, "lemak": 12.5},
    "Telur Rebus (1 butir)": {"kalori": 78, "protein": 6.3, "karbo": 0.6, "lemak": 5.3},
    "Telur Dadar (1 butir)": {"kalori": 110, "protein": 6.5, "karbo": 0.8, "lemak": 9.0},
    "Tahu Goreng (1 potong)": {"kalori": 35, "protein": 2.0, "karbo": 1.5, "lemak": 2.5},
    "Tempe Goreng (1 potong)": {"kalori": 50, "protein": 4.0, "karbo": 3.0, "lemak": 3.0},
    "Whey Protein Shake (1 scoop)": {"kalori": 120, "protein": 24.0, "karbo": 3.0, "lemak": 1.5},

    "Susu Dancow FortiGro Full Cream (1 saset/27g)": {"kalori": 130, "protein": 6.0, "karbo": 12.0, "lemak": 7.0},
    "Susu Dancow FortiGro Cokelat (1 saset/39g)": {"kalori": 160, "protein": 5.0, "karbo": 23.0, "lemak": 5.0},
    "Susu Zee Swirtz Cokelat/Vanila (1 saset/40g)": {"kalori": 160, "protein": 5.0, "karbo": 24.0, "lemak": 4.5},
    "Susu Milo Bubuk (1 saset/22g)": {"kalori": 90, "protein": 2.0, "karbo": 14.0, "lemak": 2.5},
    "Susu UHT Full Cream / Ultra Milk (200ml)": {"kalori": 120, "protein": 6.0, "karbo": 9.0, "lemak": 7.0},
    "Susu Indomilk UHT Cokelat (190ml)": {"kalori": 140, "protein": 5.0, "karbo": 21.0, "lemak": 4.0},
    "Susu Bear Brand / Beruang (1 kaleng/189ml)": {"kalori": 120, "protein": 6.0, "karbo": 9.0, "lemak": 7.0},

    "Martabak Manis Cokelat Keju (1 potong)": {"kalori": 270, "protein": 5.0, "karbo": 34.0, "lemak": 13.0},
    "Pisang Goreng (1 pcs)": {"kalori": 140, "protein": 1.2, "karbo": 22.0, "lemak": 5.5},
    "Roti Bakar Cokelat Keju (1 porsi)": {"kalori": 380, "protein": 8.0, "karbo": 52.0, "lemak": 16.0},
    "Kue Klepon (3 pcs)": {"kalori": 135, "protein": 1.5, "karbo": 26.0, "lemak": 3.0},
    "Donat Cokelat Meses (1 pcs)": {"kalori": 240, "protein": 4.0, "karbo": 31.0, "lemak": 11.0},
    "Es Cendol / Dawet (1 gelas)": {"kalori": 220, "protein": 2.0, "karbo": 38.0, "lemak": 7.0},
    "Es Teler (1 mangkok)": {"kalori": 310, "protein": 3.5, "karbo": 48.0, "lemak": 12.0},
    "Kopi Susu Gula Aren (1 gelas)": {"kalori": 180, "protein": 3.0, "karbo": 25.0, "lemak": 7.0},
}

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

def add_workout_log(user_id, tanggal, jenis, durasi, kalori):
    conn = sqlite3.connect("nutrition_tracker.db")
    c = conn.cursor()
    c.execute("INSERT INTO workout_logs (user_id, tanggal, jenis_latihan, durasi_menit, kalori_terbakar) VALUES (?, ?, ?, ?, ?)", 
            (user_id, tanggal, jenis, durasi, kalori))
    conn.commit()
    conn.close()

def get_workout_logs(user_id, tanggal):
    conn = sqlite3.connect("nutrition_tracker.db")
    df = pd.read_sql_query("SELECT id, jenis_latihan as [Jenis Latihan], durasi_menit as [Durasi (menit)], kalori_terbakar as [Kalori Terbakar (kcal)] FROM workout_logs WHERE user_id = ? AND tanggal = ?", conn, params=(user_id, tanggal))
    conn.close()
    return df

def delete_workout_log(user_id, item_id):
    conn = sqlite3.connect("nutrition_tracker.db")
    c = conn.cursor()
    c.execute("DELETE FROM workout_logs WHERE user_id = ? AND id = ?", (user_id, item_id))
    conn.commit()
    conn.close()

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
        logo_path = "logo-removebg-preview.png"
        if os.path.exists(logo_path):
            try:
                self.image(logo_path, x=55, y=90, w=100)
            except Exception as e:
                st.error(f"Gagal memuat watermark: {e}")

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

query_params = st.query_params

default_user = query_params.get("user", "User1")
if "user_id_input" not in st.session_state:
    st.session_state["user_id_input"] = default_user

st.session_state.setdefault("calc_gender", query_params.get("gender", "Pria"))
st.session_state.setdefault("calc_usia", int(query_params.get("usia", 22)))
st.session_state.setdefault("calc_bb", float(query_params.get("bb", 65.0)))
st.session_state.setdefault("calc_tb", float(query_params.get("tb", 170.0)))
st.session_state.setdefault("calc_aktivitas", query_params.get("aktivitas", "Ringan (Olahraga 1-3 hari/minggu)"))
st.session_state.setdefault("calc_goal", query_params.get("goal", "Defisit Kalori (-500 kcal / Turun BB)"))

st.session_state.setdefault('target_kalori_val', int(query_params.get("target_kal", 2000)))
st.session_state.setdefault('target_protein_val', int(query_params.get("target_prot", 120)))
st.session_state.setdefault('target_karbo_val', int(query_params.get("target_karb", 250)))
st.session_state.setdefault('target_lemak_val', int(query_params.get("target_lem", 60)))

def update_url_params():
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

st.sidebar.title("📌 Menu & Pengaturan")

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

use_today_auto = st.sidebar.checkbox("🔄 Reset Otomatis 24 Jam (Hari Ini)", value=True)
if use_today_auto:
    selected_date = datetime.date.today().strftime("%Y-%m-%d")
    st.sidebar.caption("⚡ Mode Otomatis Aktif: Tanggal hari ini.")
else:
    selected_date = st.sidebar.date_input("🗓️ Pilih Tanggal Log", datetime.date.today()).strftime("%Y-%m-%d")

st.sidebar.divider()

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

update_url_params()

st.title("🥗 Food & Nutrition Tracker Pro")
st.caption(f"Aplikasi Monitoring Nutrisi Harian | User Active: **[{user_id.upper()}]** | Tanggal: **{selected_date}**")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🍱 Input Makanan", 
    "💧 Hydration Tracker", 
    "📊 Dashboard Visual", 
    "🏋️ Jadwal Latihan", 
    "⚖️ Weight Progress", 
    "📈 Riwayat & Export",
    "☁️ Cloud Sync"
])

with tab1:
    subtab1, subtab2 = st.tabs(["🍱 Racik Menu", "✏️ Input Custom Manual"])
    
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

with tab4:
    st.subheader(f"🏋️ Workout Schedule & Log - [{user_id.upper()}]")
    st.caption("Pilih Split Program Latihan Mingguan dan Catat Sesi Latihan Harianmu.")
    
    subtab_sched, subtab_log = st.tabs(["🗓️ Panduan Program Latihan", "📝 Catat Sesi Selesai Manual"])
    
    with subtab_sched:
        col_opt1, col_opt2 = st.columns([1, 2])
        with col_opt1:
            pilih_split = st.selectbox("Pilih Split Program:", [
                "Push / Pull / Legs (PPL - 3/6 Hari)",
                "Upper / Lower Body (4 Hari)",
                "Full Body Workout (3 Hari Rumahan)"
            ])
            pilih_hari = st.selectbox("Pilih Hari:", ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"])

        with col_opt2:
            st.write(f"### 📋 Menu Latihan: **{pilih_hari}**")
            
            if "Push / Pull / Legs" in pilih_split:
                program = {
                    "Senin": [("Push-ups / Bench Press", "4 Set x 10-12 Reps"), ("Overhead Shoulder Press", "3 Set x 12 Reps"), ("Tricep Dips", "3 Set x 15 Reps"), ("Incline Push-ups", "3 Set x 12 Reps")],
                    "Selasa": [("Pull-ups / Inverted Row", "4 Set x 8-10 Reps"), ("Dumbbell / Resistance Band Row", "3 Set x 12 Reps"), ("Bicep Curls", "3 Set x 12 Reps"), ("Face Pulls / Rear Delt Fly", "3 Set x 15 Reps")],
                    "Rabu": [("Bodyweight / Barbell Squats", "4 Set x 12 Reps"), ("Romanian Deadlifts / Glute Bridges", "3 Set x 10 Reps"), ("Walking Lunges", "3 Set x 12 Reps/kaki"), ("Calf Raises", "4 Set x 20 Reps")],
                    "Kamis": [("Rest Day / Kardio Ringan", "Jalan santai 30 menit atau stretching")],
                    "Jumat": [("Push-ups Varian / Chest Fly", "4 Set x 12 Reps"), ("Lateral Raises", "4 Set x 15 Reps"), ("Skullcrushers / Overhead Tricep Extension", "3 Set x 12 Reps")],
                    "Sabtu": [("Lat Pulldown / Chin-ups", "4 Set x 10 Reps"), ("Hammer Curls", "3 Set x 12 Reps"), ("Plank to Push-up", "3 Set x 10 Reps")],
                    "Minggu": [("Rest Day / Pemulihan Total", "Fokus tidur cukup & minum air")]
                }
            elif "Upper / Lower" in pilih_split:
                program = {
                    "Senin": [("Push-ups", "4 Set x 12 Reps"), ("Rows", "4 Set x 12 Reps"), ("Shoulder Press", "3 Set x 12 Reps"), ("Bicep & Tricep Supersets", "3 Set x 15 Reps")],
                    "Selasa": [("Squats", "4 Set x 15 Reps"), ("Lunges", "3 Set x 12 Reps"), ("Leg Raises", "3 Set x 15 Reps"), ("Plank", "3 Set x 45 Detik")],
                    "Rabu": [("Rest Day", "Stretching Ringan")],
                    "Kamis": [("Incline Push-ups", "4 Set x 12 Reps"), ("Pull-ups / Band Pull", "4 Set x 10 Reps"), ("Lateral Raises", "3 Set x 15 Reps")],
                    "Jumat": [("Deadlifts / Glute Bridge", "4 Set x 10 Reps"), ("Bulgarian Split Squat", "3 Set x 10 Reps/kaki"), ("Crunches", "3 Set x 20 Reps")],
                    "Sabtu": [("Kardio / HIIT", "20-30 Menit")],
                    "Minggu": [("Rest Day", "Pemulihan Total")]
                }
            else:
                program = {
                    "Senin": [("Jumping Jacks", "3 Set x 30 Detik"), ("Bodyweight Squat", "3 Set x 15 Reps"), ("Push-ups", "3 Set x 10 Reps"), ("Plank", "3 Set x 30 Detik")],
                    "Selasa": [("Rest Day / Jalan Cepat", "30 Menit")],
                    "Rabu": [("Burpees", "3 Set x 10 Reps"), ("Lunges", "3 Set x 12 Reps"), ("Mountain Climbers", "3 Set x 30 Detik"), ("Crunches", "3 Set x 15 Reps")],
                    "Kamis": [("Rest Day", "Stretching Fleksibilitas")],
                    "Jumat": [("High Knees", "3 Set x 30 Detik"), ("Knee Push-ups / Standard Push-ups", "3 Set x 12 Reps"), ("Chair Squat", "3 Set x 15 Reps"), ("Plank", "3 Set x 40 Detik")],
                    "Sabtu": [("Rest Day / Kardio Ringan", "Jalan Santai")],
                    "Minggu": [("Rest Day Total", "Istirahat Total")]
                }
                
            tasks = program.get(pilih_hari, [("Istirahat", "Tidak ada jadwal latihan")])
            
            with st.form("form_checklist_workout"):
                selected_exercises = []
                for idx, (ex_nama, ex_set) in enumerate(tasks):
                    chk = st.checkbox(f"**{ex_nama}** — `{ex_set}`", key=f"chk_{pilih_hari}_{idx}")
                    if chk:
                        selected_exercises.append(ex_nama)
                
                default_durasi = max(10, len(selected_exercises) * 8)
                durasi_input = st.number_input("Estimasi Total Durasi (menit):", min_value=5, value=default_durasi, step=5)
                
                bb_user = st.session_state.get("calc_bb", 65.0)
                met_value = 5.0 if "Rest Day" not in pilih_hari else 2.0
                kalori_hitung_otomatis = round((met_value * 3.5 * bb_user / 200) * durasi_input, 1)
                
                st.caption(f"🔥 *Estimasi Otomatis (BB: {bb_user}kg, {durasi_input} mnt):* **~{kalori_hitung_otomatis} kcal**")
                
                btn_simpan_checklist = st.form_submit_button("💾 Simpan Latihan Tercentang ke Log")
                
                if btn_simpan_checklist:
                    if selected_exercises:
                        nama_gabungan = f"{pilih_split.split(' ')[0]} ({pilih_hari}): " + ", ".join(selected_exercises)
                        add_workout_log(user_id, selected_date, nama_gabungan, durasi_input, kalori_hitung_otomatis)
                        st.success(f"Berhasil menyimpan {len(selected_exercises)} latihan ke database (~{kalori_hitung_otomatis} kcal)!")
                        st.rerun()
                    else:
                        st.warning("Pilih/centang minimal 1 gerakan latihan terlebih dahulu!")

    with subtab_log:
        st.subheader("Catat Sesi Latihan Manual")
        with st.form("form_workout_log"):
            w_jenis = st.text_input("Nama/Jenis Latihan:", placeholder="Contoh: Running 5KM / Main Futsal")
            col_w1, col_w2 = st.columns(2)
            w_durasi = col_w1.number_input("Durasi (Menit):", min_value=5, step=5, value=30)
            w_kalori = col_w2.number_input("Perkiraan Kalori Terbakar (kcal):", min_value=10, step=10, value=150)
            
            submit_w = st.form_submit_button("Simpan Log Manual")
            if submit_w:
                if w_jenis:
                    add_workout_log(user_id, selected_date, w_jenis, w_durasi, w_kalori)
                    st.success(f"Berhasil mencatat sesi {w_jenis}!")
                    st.rerun()
                else:
                    st.error("Nama latihan wajib diisi!")
        
        st.divider()
        st.write(f"**Log Latihan Tanggal ({selected_date}):**")
        df_w_logs = get_workout_logs(user_id, selected_date)
        if not df_w_logs.empty:
            st.dataframe(df_w_logs, use_container_width=True)
            w_del_id = st.selectbox("Pilih ID latihan untuk dihapus:", df_w_logs["id"].tolist())
            if st.button("Hapus Log Latihan"):
                delete_workout_log(user_id, w_del_id)
                st.success("Log latihan berhasil dihapus!")
                st.rerun()
        else:
            st.info("Belum ada latihan yang dicatat pada tanggal ini.")

with tab5:
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

with tab6:
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

with tab7:
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
