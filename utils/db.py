import sqlite3, time, secrets, string
from config import DB_FILE, FREE_LIMIT

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
        lang TEXT DEFAULT 'fa', authed INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0, is_vip INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0, file_limit INTEGER DEFAULT 50,
        added_at INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS folders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        name TEXT, emoji TEXT DEFAULT '📁', created_at INTEGER,
        UNIQUE(user_id, name)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        unique_code TEXT UNIQUE, custom_name TEXT, folder_id INTEGER,
        description TEXT, tags TEXT, file_type TEXT,
        channel_msg_id INTEGER, uploaded_at INTEGER, deleted INTEGER DEFAULT 0,
        is_shared INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        amount_usd REAL, files_added INTEGER, payment_id TEXT,
        status TEXT DEFAULT 'pending', created_at INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        action TEXT, detail TEXT, created_at INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT
    )""")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('free_limit', ?)", (str(FREE_LIMIT),))
    c.execute("INSERT OR IGNORE INTO settings VALUES ('bot_password', '')")

    # Migrations for existing DBs
    try:
        c.execute("ALTER TABLE files ADD COLUMN is_shared INTEGER DEFAULT 0")
    except Exception:
        pass

    conn.commit()
    conn.close()

# ─── Settings ───────────────────────────────
def get_setting(key):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None

def set_setting(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()

# ─── Unique code ────────────────────────────
def gen_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(chars) for _ in range(8))
        conn = get_conn()
        ex = conn.execute("SELECT 1 FROM files WHERE unique_code=?", (code,)).fetchone()
        conn.close()
        if not ex:
            return code

# ─── Users ──────────────────────────────────
def get_user(uid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return dict(row) if row else None

def upsert_user(uid, username=None, first_name=None, lang=None, authed=None,
                is_admin=None, is_vip=None, is_blocked=None, file_limit=None):
    conn = get_conn()
    ex = conn.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone()
    if ex:
        for col, val in [("lang", lang), ("authed", authed), ("is_admin", is_admin),
                         ("is_vip", is_vip), ("is_blocked", is_blocked),
                         ("file_limit", file_limit), ("username", username), ("first_name", first_name)]:
            if val is not None:
                v = (1 if val else 0) if isinstance(val, bool) else val
                conn.execute(f"UPDATE users SET {col}=? WHERE user_id=?", (v, uid))
    else:
        limit = int(get_setting("free_limit") or FREE_LIMIT)
        conn.execute(
            "INSERT INTO users (user_id,username,first_name,lang,authed,is_admin,is_vip,is_blocked,file_limit,added_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (uid, username, first_name, lang or 'fa', 1 if authed else 0, 0, 0, 0, limit, int(time.time()))
        )
    conn.commit()
    conn.close()

def is_authed(uid):
    u = get_user(uid)
    return bool(u and u["authed"] and not u["is_blocked"])

def get_lang(uid):
    u = get_user(uid)
    return u["lang"] if u else "fa"

def get_file_limit(uid):
    u = get_user(uid)
    if not u:
        return FREE_LIMIT
    if u["is_admin"] or u["is_vip"]:
        return 999999
    return u["file_limit"]

def count_user_files(uid):
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as c FROM files WHERE user_id=? AND deleted=0", (uid,)).fetchone()
    conn.close()
    return row["c"] if row else 0

def add_file_quota(uid, amount):
    conn = get_conn()
    conn.execute("UPDATE users SET file_limit=file_limit+? WHERE user_id=?", (amount, uid))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_user_ids():
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM users WHERE authed=1 AND is_blocked=0").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]

# ─── User Stats ─────────────────────────────
def get_user_stats(uid):
    conn = get_conn()
    u = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    if not u:
        conn.close()
        return None
    total_files = conn.execute(
        "SELECT COUNT(*) as c FROM files WHERE user_id=? AND deleted=0", (uid,)
    ).fetchone()["c"]
    shared_files = conn.execute(
        "SELECT COUNT(*) as c FROM files WHERE user_id=? AND deleted=0 AND is_shared=1", (uid,)
    ).fetchone()["c"]
    total_purchases = conn.execute(
        "SELECT COUNT(*) as c, COALESCE(SUM(files_added),0) as total_bought FROM purchases WHERE user_id=? AND status='confirmed'",
        (uid,)
    ).fetchone()
    folder_count = conn.execute(
        "SELECT COUNT(*) as c FROM folders WHERE user_id=?", (uid,)
    ).fetchone()["c"]
    conn.close()
    return {
        "user": dict(u),
        "total_files": total_files,
        "shared_files": shared_files,
        "purchases": total_purchases["c"],
        "total_bought": total_purchases["total_bought"],
        "folder_count": folder_count,
    }

# ─── Folders ────────────────────────────────
def get_folders(uid):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM folders WHERE user_id=? ORDER BY name", (uid,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_folder(uid, name, emoji="📁"):
    try:
        conn = get_conn()
        conn.execute("INSERT INTO folders (user_id,name,emoji,created_at) VALUES (?,?,?,?)",
                     (uid, name, emoji, int(time.time())))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def delete_folder(fid, uid):
    conn = get_conn()
    conn.execute("DELETE FROM folders WHERE id=? AND user_id=?", (fid, uid))
    conn.execute("UPDATE files SET folder_id=NULL WHERE folder_id=? AND user_id=?", (fid, uid))
    conn.commit()
    conn.close()

def get_folder(fid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM folders WHERE id=?", (fid,)).fetchone()
    conn.close()
    return dict(row) if row else None

# ─── Files ──────────────────────────────────
def save_file(uid, custom_name, folder_id, description, tags, file_type, channel_msg_id):
    code = gen_code()
    conn = get_conn()
    conn.execute(
        """INSERT INTO files (user_id,unique_code,custom_name,folder_id,description,tags,file_type,channel_msg_id,uploaded_at)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (uid, code, custom_name, folder_id, description, tags, file_type, channel_msg_id, int(time.time()))
    )
    conn.commit()
    conn.close()
    add_log(uid, "upload", custom_name)
    return code

def get_file_by_code(code, uid):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM files WHERE unique_code=? AND user_id=? AND deleted=0", (code, uid)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_file_by_unique_code(code):
    """Get any file by unique_code regardless of user (for shared file access)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM files WHERE unique_code=? AND deleted=0 AND is_shared=1", (code,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_files_by_folder(uid, folder_id):
    conn = get_conn()
    if folder_id is None:
        rows = conn.execute(
            "SELECT * FROM files WHERE user_id=? AND folder_id IS NULL AND deleted=0 ORDER BY uploaded_at DESC",
            (uid,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM files WHERE user_id=? AND folder_id=? AND deleted=0 ORDER BY uploaded_at DESC",
            (uid, folder_id)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def search_files(uid, query):
    q = f"%{query}%"
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM files WHERE user_id=? AND deleted=0
        AND (custom_name LIKE ? OR tags LIKE ? OR unique_code LIKE ? OR description LIKE ?)
        ORDER BY uploaded_at DESC""",
        (uid, q, q, q, q)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def search_all_files(query):
    q = f"%{query}%"
    conn = get_conn()
    rows = conn.execute(
        """SELECT f.*, u.username, u.first_name FROM files f
        LEFT JOIN users u ON f.user_id=u.user_id
        WHERE f.deleted=0 AND (f.custom_name LIKE ? OR f.tags LIKE ? OR f.unique_code LIKE ?)
        ORDER BY f.uploaded_at DESC LIMIT 20""",
        (q, q, q)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_file(fid, uid, **kwargs):
    conn = get_conn()
    for k, v in kwargs.items():
        if k in ("custom_name", "folder_id", "description", "tags"):
            conn.execute(f"UPDATE files SET {k}=? WHERE id=? AND user_id=?", (v, fid, uid))
    conn.commit()
    conn.close()

def delete_file(fid, uid):
    conn = get_conn()
    row = conn.execute("SELECT custom_name FROM files WHERE id=? AND user_id=?", (fid, uid)).fetchone()
    conn.execute("UPDATE files SET deleted=1 WHERE id=? AND user_id=?", (fid, uid))
    conn.commit()
    conn.close()
    if row:
        add_log(uid, "delete", row["custom_name"])

def admin_delete_file(fid):
    conn = get_conn()
    conn.execute("UPDATE files SET deleted=1 WHERE id=?", (fid,))
    conn.commit()
    conn.close()

def get_file_by_id(fid, uid):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM files WHERE id=? AND user_id=? AND deleted=0", (fid, uid)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_file_by_id_admin(fid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM files WHERE id=? AND deleted=0", (fid,)).fetchone()
    conn.close()
    return dict(row) if row else None

def toggle_file_share(fid, uid):
    """Toggle is_shared for a file. Returns new state (True=shared, False=unshared)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT is_shared FROM files WHERE id=? AND user_id=? AND deleted=0", (fid, uid)
    ).fetchone()
    if not row:
        conn.close()
        return None
    new_state = 0 if row["is_shared"] else 1
    conn.execute("UPDATE files SET is_shared=? WHERE id=? AND user_id=?", (new_state, fid, uid))
    conn.commit()
    conn.close()
    return bool(new_state)

# ─── Stats ──────────────────────────────────
def get_stats():
    conn = get_conn()
    users  = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    files  = conn.execute("SELECT COUNT(*) as c FROM files WHERE deleted=0").fetchone()["c"]
    today  = int(time.time()) - 86400
    new_u  = conn.execute("SELECT COUNT(*) as c FROM users WHERE added_at>=?", (today,)).fetchone()["c"]
    new_f  = conn.execute("SELECT COUNT(*) as c FROM files WHERE uploaded_at>=? AND deleted=0", (today,)).fetchone()["c"]
    blocked = conn.execute("SELECT COUNT(*) as c FROM users WHERE is_blocked=1").fetchone()["c"]
    vip    = conn.execute("SELECT COUNT(*) as c FROM users WHERE is_vip=1").fetchone()["c"]
    conn.close()
    return {"users": users, "files": files, "new_users": new_u, "new_files": new_f, "blocked": blocked, "vip": vip}

# ─── Purchases ──────────────────────────────
def save_purchase(uid, amount_usd, files_added, payment_id):
    conn = get_conn()
    conn.execute(
        "INSERT INTO purchases (user_id,amount_usd,files_added,payment_id,created_at) VALUES (?,?,?,?,?)",
        (uid, amount_usd, files_added, payment_id, int(time.time()))
    )
    conn.commit()
    conn.close()

def get_all_purchases():
    conn = get_conn()
    rows = conn.execute(
        """SELECT p.*, u.username, u.first_name FROM purchases p
        LEFT JOIN users u ON p.user_id=u.user_id ORDER BY p.created_at DESC LIMIT 50"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_pending_purchases():
    conn = get_conn()
    rows = conn.execute(
        """SELECT p.*, u.username, u.first_name FROM purchases p
        LEFT JOIN users u ON p.user_id=u.user_id
        WHERE p.status='pending' ORDER BY p.created_at DESC LIMIT 20"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_purchase_by_payment_id(payment_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM purchases WHERE payment_id=?", (payment_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_purchase_by_id(purchase_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM purchases WHERE id=?", (purchase_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_purchase_status(payment_id, status):
    conn = get_conn()
    conn.execute("UPDATE purchases SET status=? WHERE payment_id=?", (status, payment_id))
    conn.commit()
    conn.close()

def confirm_purchase_by_id(purchase_id):
    """Admin manual confirmation. Returns (uid, files_added) or None."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM purchases WHERE id=? AND status='pending'", (purchase_id,)).fetchone()
    if not row:
        conn.close()
        return None
    uid = row["user_id"]
    files_added = row["files_added"]
    conn.execute("UPDATE purchases SET status='confirmed' WHERE id=?", (purchase_id,))
    conn.execute("UPDATE users SET file_limit=file_limit+? WHERE user_id=?", (files_added, uid))
    conn.commit()
    conn.close()
    add_log(uid, "purchase_confirmed_manual", f"+{files_added} files")
    return uid, files_added

# ─── Logs ───────────────────────────────────
def add_log(uid, action, detail=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO logs (user_id,action,detail,created_at) VALUES (?,?,?,?)",
        (uid, action, detail, int(time.time()))
    )
    conn.commit()
    conn.close()

def get_user_logs(uid, limit=30):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM logs WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (uid, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_recent_logs(limit=50):
    conn = get_conn()
    rows = conn.execute(
        """SELECT l.*, u.username FROM logs l
        LEFT JOIN users u ON l.user_id=u.user_id ORDER BY l.created_at DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
