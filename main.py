from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

app = FastAPI()

# Разрешаем доступ всем (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Функция подключения к базе
def get_db():
    conn = sqlite3.connect('imperium.db')
    conn.row_factory = sqlite3.Row
    return conn

# Инициализация таблиц
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, password TEXT, rating REAL DEFAULT 5.0, last_active DATETIME)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, 
        title TEXT, price INTEGER, category TEXT, description TEXT, image TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, 
        receiver_id INTEGER, ad_id INTEGER, text TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# Схемы
class AdCreate(BaseModel):
    owner_id: int; title: str; price: int; category: str; description: str; image: str

# --- ПРОВЕРОЧНЫЕ МАРШРУТЫ ---

@app.get("/")
def home():
    return {"message": "Сервер запущен! Попробуй зайти на /api/ads"}

@app.get("/api/ads")
def get_ads():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ads ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/ads")
def create_ad(ad: AdCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO ads (owner_id, title, price, category, description, image) VALUES (?,?,?,?,?,?)',
                   (ad.owner_id, ad.title, ad.price, ad.category, ad.description, ad.image))
    conn.commit()
    conn.close()
    return {"status": "success"}

# (Добавь сюда маршруты для /login и /register из предыдущих сообщений, если они нужны сейчас)
