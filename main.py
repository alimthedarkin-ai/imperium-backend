from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import sqlite3

app = FastAPI(title="IMPERIUM PRO API")

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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rating REAL DEFAULT 5.0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            title TEXT NOT NULL,
            price INTEGER NOT NULL,
            category TEXT,
            description TEXT,
            image TEXT,
            views INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER,
            ad_id INTEGER,
            PRIMARY KEY (user_id, ad_id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class UserReg(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class AdCreate(BaseModel):
    owner_id: int
    title: str
    price: int
    category: str
    description: str
    image: str

@app.get("/")
def read_root():
    return {"message": "IMPERIUM API работает! База на связи."}

@app.post("/api/register")
def register(user: UserReg):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                       (user.name, user.email, user.password))
        conn.commit()
        return {"status": "success"}
    except:
        raise HTTPException(status_code=400, detail="Email занят")
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
    raise HTTPException(status_code=401, detail="Ошибка входа")

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
            "id": r["id"], "title": r["title"], "price": r["price"], "image": r["image"],
            "views": r["views"], "category": r["category"], "description": r["description"],
            "seller": {"name": r["seller_name"], "rating": r["seller_rating"]}
        } for r in rows
    ]

@app.post("/api/ads")
def create_ad(ad: AdCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ads (owner_id, title, price, category, description, image) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (ad.owner_id, ad.title, ad.price, ad.category, ad.description, ad.image))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.post("/api/favorites/{ad_id}")
def add_fav(ad_id: int, user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO favorites (user_id, ad_id) VALUES (?, ?)', (user_id, ad_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}
