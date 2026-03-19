from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GRADES = [
    (50, "👑 Légende du champ de bataille"),
    (40, "🔥 Commandant"),
    (30, "⭐ Opérateur Ghost"),
    (20, "🏅 Élite"),
    (15, "💣 Vétéran"),
    (10, "🎯 Spécialiste"),
    (5,  "🎖️ Soldat"),
    (1,  "🪖 Recrue"),
]

def get_db():
    url = "postgresql://postgres:cXjcpmwvNCvKutTmqobyPeqjnJqsqyyt@tramway.proxy.rlwy.net:26562/railway"
    return psycopg2.connect(url, sslmode="require")

def get_grade(level: int) -> str:
    for min_level, grade in GRADES:
        if level >= min_level:
            return grade
    return "🪖 Recrue"

def xp_for_next_level(level: int) -> int:
    if level == 1:
        return 8_000
    elif level < 5:
        return 10_000
    elif level < 10:
        return 12_000
    elif level < 15:
        return 14_000
    else:
        return 15_000

def xp_in_current_level(xp: int, level: int) -> int:
    spent = 0
    for l in range(1, level):
        spent += xp_for_next_level(l)
    return xp - spent

@app.get("/")
def root():
    return {"status": "Ghost XP API en ligne ✅"}

@app.get("/classement")
def classement():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM players WHERE xp > 0 ORDER BY xp DESC")
    players = cur.fetchall()
    cur.close()
    conn.close()

    result = []
    for i, p in enumerate(players):
        level = p["level"]
        xp_total = p["xp"]
        xp_current = xp_in_current_level(xp_total, level)
        xp_needed = xp_for_next_level(level)
        result.append({
            "rank": i + 1,
            "user_id": p["user_id"],
            "xp": xp_total,
            "level": level,
            "grade": get_grade(level),
            "total_kills": p["total_kills"],
            "total_captures": p["total_captures"],
            "xp_current": xp_current,
            "xp_needed": xp_needed,
        })
    return result

@app.get("/profil/{user_id}")
def profil(user_id: str):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM players WHERE user_id = %s", (user_id,))
    p = cur.fetchone()
    cur.close()
    conn.close()

    if not p:
        return {"error": "Joueur introuvable"}

    level = p["level"]
    xp_total = p["xp"]
    xp_current = xp_in_current_level(xp_total, level)
    xp_needed = xp_for_next_level(level)

    return {
        "user_id": p["user_id"],
        "xp": xp_total,
        "level": level,
        "grade": get_grade(level),
        "total_kills": p["total_kills"],
        "total_captures": p["total_captures"],
        "xp_current": xp_current,
        "xp_needed": xp_needed,
    }

@app.get("/stats")
def stats():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT COUNT(*) as total, SUM(xp) as total_xp, MAX(level) as max_level FROM players WHERE xp > 0")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return {
        "total_membres": row["total"],
        "total_xp": row["total_xp"],
        "niveau_max": row["max_level"],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
