from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import sqlite3

app = FastAPI()

# РАЗРЕШАЕМ ВСЁ (CORS), чтобы Netlify мог достучаться
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect('imperium.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, password TEXT, rating REAL DEFAULT 5.0, last_active TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, 
        title TEXT, price INTEGER, category TEXT, description TEXT, image TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, 
        receiver_id INTEGER, ad_id INTEGER, text TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# Схемы данных (должны строго совпадать с фронтендом)
class UserReg(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class AdCreate(BaseModel):
    owner_id: int; title: str; price: int; category: str; description: str; image: str

# --- МАРШРУТЫ ---

@app.get("/")
def home():
    return {"status": "ok", "info": "Imperium API is alive"}

@app.post("/api/register")
def register(user: UserReg):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (name, email, password, last_active) VALUES (?, ?, ?, ?)',
                       (user.name, user.email, user.password, datetime.now().isoformat()))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        print(f"Ошибка регистрации: {e}")
        raise HTTPException(status_code=400, detail="Email уже занят или ошибка базы")
    finally:
        conn.close()

@app.post("/api/login")
def login(user: UserLogin):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (user.email, user.password))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "name": row["name"], "email": row["email"], "rating": row["rating"]}
    raise HTTPException(status_code=401, detail="Неверный логин или пароль")

@app.get("/api/ads")
def get_ads():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ads.*, IFNULL(users.name, 'Аноним') as seller_name, IFNULL(users.rating, 5.0) as seller_rating 
        FROM ads LEFT JOIN users ON ads.owner_id = users.id 
        ORDER BY ads.id DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r["id"], "owner_id": r["owner_id"], "title": r["title"], "price": r["price"], 
            "image": r["image"], "category": r["category"], "description": r["description"],
            "seller": {"name": r["seller_name"], "rating": r["seller_rating"]}
        } for r in rows
    ]

@app.post("/api/ads")
def create_ad(ad: AdCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO ads (owner_id, title, price, category, description, image) VALUES (?,?,?,?,?,?)',
                   (ad.owner_id, ad.title, ad.price, ad.category, ad.description, ad.image))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/user/heartbeat/{user_id}")
def heartbeat(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_active = ? WHERE id = ?', (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}
