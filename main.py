from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="IMPERIUM PRO CLOUD")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Твоя вечная ссылка на базу данных Neon
DB_URL = "postgresql://neondb_owner:npg_f0ThB5DxjWQN@ep-proud-credit-agch52vv-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require"

def get_db():
    # RealDictCursor позволяет получать данные в виде красивых словарей (как JSON)
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    # Таблица пользователей (с рейтингом и галочкой верификации)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT, email TEXT UNIQUE, password TEXT, 
        rating REAL DEFAULT 5.0, reviews_count INTEGER DEFAULT 0,
        is_verified BOOLEAN DEFAULT FALSE, last_active TIMESTAMP)''')
    
    # Таблица объявлений
    cursor.execute('''CREATE TABLE IF NOT EXISTS ads (
        id SERIAL PRIMARY KEY, owner_id INTEGER, 
        title TEXT, price INTEGER, category TEXT, description TEXT, image TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Таблица для чата
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY, sender_id INTEGER, 
        receiver_id INTEGER, ad_id INTEGER, text TEXT, 
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Таблица для отзывов
    cursor.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id SERIAL PRIMARY KEY, reviewer_id INTEGER, user_id INTEGER,
        rating INTEGER, comment TEXT, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

# Запускаем создание таблиц
try:
    init_db()
except Exception as e:
    print("Ошибка базы данных:", e)

# --- СХЕМЫ ДАННЫХ ---
class UserReg(BaseModel): name: str; email: str; password: str
class UserLogin(BaseModel): email: str; password: str
class AdCreate(BaseModel): owner_id: int; title: str; price: int; category: str; description: str; image: str
class MsgSend(BaseModel): sender_id: int; receiver_id: int; ad_id: int; text: str

# --- МАРШРУТЫ ---

@app.get("/")
def home():
    return {"status": "ok", "message": "IMPERIUM POSTGRESQL DB IS LIVE!"}

@app.post("/api/register")
def register(user: UserReg):
    conn = get_db(); cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (name, email, password, last_active) VALUES (%s, %s, %s, %s)',
                       (user.name, user.email, user.password, datetime.now()))
        conn.commit()
        return {"status": "success"}
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=400, detail="Email уже занят")
    finally:
        conn.close()

@app.post("/api/login")
def login(user: UserLogin):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (user.email, user.password))
    row = cursor.fetchone()
    conn.close()
    if row: return dict(row)
    raise HTTPException(status_code=401, detail="Неверный логин или пароль")

@app.get("/api/ads")
def get_ads():
    conn = get_db(); cursor = conn.cursor()
    cursor.execute('''
        SELECT ads.*, COALESCE(users.name, 'Аноним') as seller_name, 
               COALESCE(users.rating, 5.0) as seller_rating, 
               COALESCE(users.is_verified, FALSE) as is_verified
        FROM ads LEFT JOIN users ON ads.owner_id = users.id 
        ORDER BY ads.id DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/ads")
def create_ad(ad: AdCreate):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute('INSERT INTO ads (owner_id, title, price, category, description, image) VALUES (%s,%s,%s,%s,%s,%s)',
                   (ad.owner_id, ad.title, ad.price, ad.category, ad.description, ad.image))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.post("/api/user/heartbeat/{user_id}")
def heartbeat(user_id: int):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_active = %s WHERE id = %s', (datetime.now(), user_id))
    conn.commit(); conn.close()
    return {"status": "ok"}

# --- МАРШРУТЫ ДЛЯ ЧАТА ---
@app.post("/api/messages")
def send_msg(m: MsgSend):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (sender_id, receiver_id, ad_id, text) VALUES (%s,%s,%s,%s)',
                   (m.sender_id, m.receiver_id, m.ad_id, m.text))
    conn.commit(); conn.close()
    return {"status": "sent"}

@app.get("/api/messages/{u1}/{u2}")
def get_chat(u1: int, u2: int):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute('SELECT * FROM messages WHERE (sender_id=%s AND receiver_id=%s) OR (sender_id=%s AND receiver_id=%s) ORDER BY timestamp ASC', (u1, u2, u2, u1))
    rows = cursor.fetchall(); conn.close()
    return [dict(r) for r in rows]
