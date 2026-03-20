from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── USERNAMES PAR DÉFAUT ────────────────────────────────────────────────────

USERNAMES = {
    "746732917828354220": "Mazaa",
    "308974671611822082": "Silv3rTheOne",
    "416600327698120704": "TheWayneTV",
    "792423747540746301": "Foxy-Snake",
    "1255618873516884059": "BE_ToNio_13",
    "583292176054878208": "Jahwild56",
    "1304116365900255256": "Quirkybump",
    "781963566064467969": "nasto17",
    "819247548182953995": "darkdog",
    "549277000066531358": "Lovaa_z",
    "284431641705971713": "Goblin",
}

# ─── GRADES ───────────────────────────────────────────────────────────────────

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

# ─── DATABASE ─────────────────────────────────────────────────────────────────

def get_db():
    url = "postgresql://postgres:cXjcpmwvNCvKutTmqobyPeqjnJqsqyyt@tramway.proxy.rlwy.net:26562/railway"
    return psycopg2.connect(url, sslmode="require")

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id TEXT PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            total_kills INTEGER DEFAULT 0,
            total_captures INTEGER DEFAULT 0,
            username TEXT
        )
    """)
    # Ajouter la colonne username si elle n'existe pas encore
    cur.execute("""
        ALTER TABLE players ADD COLUMN IF NOT EXISTS username TEXT
    """)
    conn.commit()
    cur.close()
    conn.close()

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

def get_username(user_id: str, db_username: str = None) -> str:
    if db_username:
        return db_username
    return USERNAMES.get(user_id, f"#{user_id[-6:]}")

# ─── INIT ─────────────────────────────────────────────────────────────────────

init_db()

# ─── ROUTES PRINCIPALES ───────────────────────────────────────────────────────

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
            "username": get_username(p["user_id"], p.get("username")),
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
        "username": get_username(p["user_id"], p.get("username")),
        "xp": xp_total,
        "level": level,
        "grade": get_grade(level),
        "total_kills": p["total_kills"],
        "total_captures": p["total_captures"],
        "xp_current": xp_current,
        "xp_needed": xp_needed,
    }

@app.post("/profil/username")
def set_username(data: dict):
    user_id = data.get("user_id")
    username = data.get("username", "").strip()
    if not user_id or not username:
        return {"error": "ID et pseudo requis"}
    if len(username) > 30:
        return {"error": "Pseudo trop long (max 30 caractères)"}
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM players WHERE user_id = %s", (user_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        return {"error": "Membre introuvable — soumet d'abord un rapport sur Discord"}
    cur.execute("UPDATE players SET username = %s WHERE user_id = %s", (username, user_id))
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True, "username": username}

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

# ─── ADMIN ────────────────────────────────────────────────────────────────────

ADMIN_PASSWORD = "ghostxp2026"

@app.post("/admin/login")
def admin_login(data: dict):
    if data.get("password") == ADMIN_PASSWORD:
        return {"success": True, "token": "ghost_admin_token_2026"}
    return {"success": False}

@app.get("/admin/stats")
def admin_stats(token: str = ""):
    if token != "ghost_admin_token_2026":
        return {"error": "Non autorisé"}
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT COUNT(*) as total FROM players WHERE xp > 0")
    total = cur.fetchone()["total"]
    cur.execute("SELECT SUM(xp) as total_xp FROM players WHERE xp > 0")
    total_xp = cur.fetchone()["total_xp"] or 0
    cur.execute("SELECT SUM(total_kills) as total_kills FROM players WHERE xp > 0")
    total_kills = cur.fetchone()["total_kills"] or 0
    cur.execute("SELECT SUM(total_captures) as total_captures FROM players WHERE xp > 0")
    total_captures = cur.fetchone()["total_captures"] or 0
    cur.execute("SELECT MAX(level) as max_level FROM players WHERE xp > 0")
    max_level = cur.fetchone()["max_level"] or 0
    cur.close()
    conn.close()
    return {
        "total_membres": total,
        "total_xp": total_xp,
        "total_kills": total_kills,
        "total_captures": total_captures,
        "max_level": max_level
    }

@app.post("/admin/donnexp")
def admin_donnexp(data: dict):
    if data.get("token") != "ghost_admin_token_2026":
        return {"error": "Non autorisé"}
    user_id = data.get("user_id")
    montant = data.get("montant", 0)
    if not user_id or montant <= 0:
        return {"error": "Paramètres invalides"}
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM players WHERE user_id = %s", (user_id,))
    player = cur.fetchone()
    if not player:
        cur.close()
        conn.close()
        return {"error": "Joueur introuvable"}
    new_xp = player["xp"] + montant
    cur.execute("UPDATE players SET xp = %s WHERE user_id = %s", (new_xp, user_id))
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True, "new_xp": new_xp}

@app.post("/admin/resetxp")
def admin_resetxp(data: dict):
    if data.get("token") != "ghost_admin_token_2026":
        return {"error": "Non autorisé"}
    user_id = data.get("user_id")
    conn = get_db()
    cur = conn.cursor()
    if user_id:
        cur.execute("UPDATE players SET xp=0, level=1, total_kills=0, total_captures=0 WHERE user_id=%s", (user_id,))
    else:
        cur.execute("UPDATE players SET xp=0, level=1, total_kills=0, total_captures=0")
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True}

# ─── ÉVÉNEMENTS ───────────────────────────────────────────────────────────────

def init_events_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            titre TEXT NOT NULL,
            description TEXT,
            date_debut TIMESTAMP,
            date_fin TIMESTAMP,
            bonus_xp INTEGER DEFAULT 0,
            statut TEXT DEFAULT 'a_venir',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_events_db()

@app.get("/events")
def get_events():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM events ORDER BY date_debut DESC")
    events = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(e) for e in events]

@app.post("/admin/events/create")
def create_event(data: dict):
    if data.get("token") != "ghost_admin_token_2026":
        return {"error": "Non autorisé"}
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        INSERT INTO events (titre, description, date_debut, date_fin, bonus_xp, statut)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
    """, (data.get("titre"), data.get("description"), data.get("date_debut"),
          data.get("date_fin"), data.get("bonus_xp", 0), data.get("statut", "a_venir")))
    event = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return dict(event)

@app.post("/admin/events/delete")
def delete_event(data: dict):
    if data.get("token") != "ghost_admin_token_2026":
        return {"error": "Non autorisé"}
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM events WHERE id = %s", (data.get("id"),))
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True}

@app.post("/admin/events/update")
def update_event(data: dict):
    if data.get("token") != "ghost_admin_token_2026":
        return {"error": "Non autorisé"}
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE events SET statut = %s WHERE id = %s", (data.get("statut"), data.get("id")))
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True}

# ─── CHAT ─────────────────────────────────────────────────────────────────────

def init_chat_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            username TEXT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_chat_db()

@app.get("/chat/messages")
def get_messages():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM messages ORDER BY created_at DESC LIMIT 50")
    messages = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(m) for m in reversed(messages)]

@app.post("/chat/send")
def send_message(data: dict):
    user_id = data.get("user_id")
    content = data.get("content", "").strip()
    if not user_id or not content:
        return {"error": "Paramètres invalides"}
    if len(content) > 500:
        return {"error": "Message trop long"}
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM players WHERE user_id = %s", (user_id,))
    player = cur.fetchone()
    if not player:
        cur.close()
        conn.close()
        return {"error": "Membre introuvable"}
    username = get_username(user_id, player.get("username"))
    cur.execute("INSERT INTO messages (user_id, username, content) VALUES (%s, %s, %s) RETURNING *",
        (user_id, username, content))
    msg = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return dict(msg)

@app.delete("/chat/messages/{msg_id}")
def delete_message(msg_id: int, token: str = ""):
    if token != "ghost_admin_token_2026":
        return {"error": "Non autorisé"}
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages WHERE id = %s", (msg_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True}

# ─── CLIPS ────────────────────────────────────────────────────────────────────

def init_clips_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clips (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            username TEXT,
            titre TEXT NOT NULL,
            description TEXT,
            url TEXT,
            type TEXT DEFAULT 'lien',
            likes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_clips_db()

@app.get("/clips")
def get_clips():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM clips ORDER BY created_at DESC")
    clips = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(c) for c in clips]

@app.post("/clips/add")
def add_clip(data: dict):
    user_id = data.get("user_id")
    if not user_id:
        return {"error": "Non autorisé"}
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM players WHERE user_id = %s", (user_id,))
    player = cur.fetchone()
    if not player:
        cur.close()
        conn.close()
        return {"error": "Membre introuvable"}
    username = get_username(user_id, player.get("username"))
    cur.execute("""
        INSERT INTO clips (user_id, username, titre, description, url, type)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
    """, (user_id, username, data.get("titre"), data.get("description", ""), data.get("url", ""), data.get("type", "lien")))
    clip = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return dict(clip)

@app.post("/clips/like/{clip_id}")
def like_clip(clip_id: int):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("UPDATE clips SET likes = likes + 1 WHERE id = %s RETURNING likes", (clip_id,))
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {"likes": result["likes"]}

@app.delete("/clips/{clip_id}")
def delete_clip(clip_id: int, token: str = ""):
    if token != "ghost_admin_token_2026":
        return {"error": "Non autorisé"}
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM clips WHERE id = %s", (clip_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True}

# ─── DEMANDES ─────────────────────────────────────────────────────────────────

def init_demandes_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS demandes (
            id SERIAL PRIMARY KEY,
            pseudo TEXT NOT NULL,
            discord_id TEXT,
            plateforme TEXT NOT NULL,
            motivation TEXT NOT NULL,
            statut TEXT DEFAULT 'en_attente',
            message_admin TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_demandes_db()

@app.get("/demandes")
def get_demandes(token: str = ""):
    if token != "ghost_admin_token_2026":
        return {"error": "Non autorisé"}
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM demandes ORDER BY created_at DESC")
    demandes = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(d) for d in demandes]

@app.post("/demandes/submit")
def submit_demande(data: dict):
    pseudo = data.get("pseudo", "").strip()
    plateforme = data.get("plateforme", "").strip()
    motivation = data.get("motivation", "").strip()
    if not pseudo or not plateforme or not motivation:
        return {"error": "Tous les champs sont requis"}
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("INSERT INTO demandes (pseudo, discord_id, plateforme, motivation) VALUES (%s, %s, %s, %s) RETURNING *",
        (pseudo, data.get("discord_id", ""), plateforme, motivation))
    demande = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return dict(demande)

@app.post("/demandes/repondre")
def repondre_demande(data: dict):
    if data.get("token") != "ghost_admin_token_2026":
        return {"error": "Non autorisé"}
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE demandes SET statut = %s, message_admin = %s WHERE id = %s",
        (data.get("statut"), data.get("message_admin", ""), data.get("id")))
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True}

@app.delete("/demandes/{demande_id}")
def delete_demande(demande_id: int, token: str = ""):
    if token != "ghost_admin_token_2026":
        return {"error": "Non autorisé"}
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM demandes WHERE id = %s", (demande_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True}

# ─── PRÉSENTATIONS ────────────────────────────────────────────────────────────

def init_presentations_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS presentations (
            id SERIAL PRIMARY KEY,
            user_id TEXT UNIQUE NOT NULL,
            pseudo TEXT NOT NULL,
            plateforme TEXT NOT NULL,
            classe TEXT NOT NULL,
            style TEXT NOT NULL,
            arme TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_presentations_db()

@app.get("/presentations")
def get_presentations():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT p.*, pl.xp, pl.level
        FROM presentations p
        LEFT JOIN players pl ON p.user_id = pl.user_id
        ORDER BY p.created_at DESC
    """)
    presentations = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(p) for p in presentations]

@app.post("/presentations/submit")
def submit_presentation(data: dict):
    user_id = data.get("user_id")
    if not user_id:
        return {"error": "ID requis"}
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM players WHERE user_id = %s", (user_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        return {"error": "Membre introuvable"}
    cur.execute("""
        INSERT INTO presentations (user_id, pseudo, plateforme, classe, style, arme)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE
        SET pseudo=%s, plateforme=%s, classe=%s, style=%s, arme=%s
        RETURNING *
    """, (
        user_id, data.get("pseudo"), data.get("plateforme"),
        data.get("classe"), data.get("style"), data.get("arme"),
        data.get("pseudo"), data.get("plateforme"),
        data.get("classe"), data.get("style"), data.get("arme")
    ))
    pres = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return dict(pres)

@app.delete("/presentations/{user_id}")
def delete_presentation(user_id: str, token: str = ""):
    if token != "ghost_admin_token_2026":
        return {"error": "Non autorisé"}
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM presentations WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True}
