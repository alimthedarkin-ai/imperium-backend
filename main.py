from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import sqlite3

app = FastAPI()

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
    # Таблица юзеров + поле последнего входа
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, password TEXT, 
        rating REAL DEFAULT 5.0, last_active DATETIME)''')
    # Таблица объявлений
    cursor.execute('''CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, 
        title TEXT, price INTEGER, category TEXT, description TEXT, image TEXT)''')
    # Таблица сообщений
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, 
        receiver_id INTEGER, ad_id INTEGER, text TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- Схемы ---
class MsgSend(BaseModel):
    sender_id: int; receiver_id: int; ad_id: int; text: str

# --- ЧАТ ---
@app.post("/api/messages")
def send_msg(m: MsgSend):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (sender_id, receiver_id, ad_id, text) VALUES (?,?,?,?)',
                   (m.sender_id, m.receiver_id, m.ad_id, m.text))
    conn.commit(); conn.close()
    return {"status": "sent"}

@app.get("/api/messages/{u1}/{u2}")
def get_chat(u1: int, u2: int):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute('SELECT * FROM messages WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?) ORDER BY timestamp ASC', (u1, u2, u2, u1))
    rows = cursor.fetchall(); conn.close()
    return [dict(r) for r in rows]

# --- АДМИН-ПАНЕЛЬ ---
@app.get("/api/admin/stats")
def get_admin_stats():
    conn = get_db(); cursor = conn.cursor()
    # Считаем всё
    users = [dict(r) for r in cursor.execute('SELECT id, name, email, last_active FROM users').fetchall()]
    ads_count = cursor.execute('SELECT COUNT(*) FROM ads').fetchone()[0]
    msgs_count = cursor.execute('SELECT COUNT(*) FROM messages').fetchone()[0]
    conn.close()
    return {"users": users, "total_ads": ads_count, "total_messages": msgs_count}

# Обновление онлайна (вызывается при каждом входе юзера)
@app.post("/api/user/heartbeat/{user_id}")
def heartbeat(user_id: int):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_active = ? WHERE id = ?', (datetime.now(), user_id))
    conn.commit(); conn.close()
    return {"status": "ok"}

# (Остальные маршруты /register, /login, /ads оставь как были)
