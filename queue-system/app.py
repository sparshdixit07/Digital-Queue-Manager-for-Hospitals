import sqlite3
from flask import Flask, g, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime, date

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "b93f1a5e78dd9037e45b9a47bfa1c65ef1f71d3b213498cb27b40ef73245dd4a"  

DATABASE = "queue.db"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"  

# Database helpers
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE, check_same_thread=False)
        db.row_factory = sqlite3.Row
    return db
def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_number TEXT NOT NULL,
            category TEXT NOT NULL,
            name TEXT,
            mobile TEXT,
            issued_at TEXT NOT NULL,
            served INTEGER DEFAULT 0,
            served_at TEXT,
            counter TEXT,
            day TEXT NOT NULL
        );
        """
    )
    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


#  Utilities 
CATEGORY_PREFIX = {
    "general": "G",
    "emergency": "E",
    "lab": "L"
}

def today_str():
    return date.today().isoformat()

def next_token_number(category):
    db = get_db()
    day = today_str()
    cur = db.execute(
        "SELECT COUNT(*) as cnt FROM tokens WHERE day = ? AND category = ?",
        (day, category),
    ).fetchone()
    seq = (cur["cnt"] or 0) + 1
    prefix = CATEGORY_PREFIX.get(category, "G")
    return f"{prefix}-{seq:03d}"


#  Routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin", methods=["GET", "POST"])
def admin():
    # simple login
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")
        if user == ADMIN_USER and pwd == ADMIN_PASS:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        else:
            return render_template("admin.html", login_error="Invalid credentials")
    if not session.get("admin_logged_in"):
        return render_template("admin.html", show_login=True)
    return render_template("admin.html", show_login=False)


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin"))


# API
@app.route("/api/generate_token", methods=["POST"])
def generate_token():
    data = request.get_json()
    name = (data.get("name") or "").strip()
    mobile = (data.get("mobile") or "").strip()
    category = (data.get("category") or "general").lower()
    if category not in CATEGORY_PREFIX:
        category = "general"
    #make name and mobile required
    if not name or not mobile:
        return jsonify({"success":False,"error":"Name and mobile number are required"}), 400

    db = get_db()
    token_number = next_token_number(category)
    issued_at = datetime.now().isoformat()
    day = today_str()
    db.execute(
        "INSERT INTO tokens (token_number, category, name, mobile, issued_at, day) VALUES (?, ?, ?, ?, ?, ?)",
        (token_number, category, name, mobile, issued_at, day),
    )
    db.commit()
    return jsonify({"success": True, "token": token_number})


@app.route("/api/tokens", methods=["GET"])
def list_tokens():
    """
    Returns tokens for today. Query params:
    - today_only (default true)
    - served (optional): '0' or '1' to filter
    """
    db = get_db()
    day = today_str()
    served = request.args.get("served")
    if served is None:
        rows = db.execute(
            "SELECT * FROM tokens WHERE day = ? ORDER BY served ASC, issued_at ASC", (day,)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM tokens WHERE day = ? AND served = ? ORDER BY issued_at ASC", (day, int(served))
        ).fetchall()
    tokens = [dict(r) for r in rows]
    return jsonify(tokens)


@app.route("/api/stats", methods=["GET"])
def stats():
    db = get_db()
    day = today_str()
    total = db.execute("SELECT COUNT(*) as cnt FROM tokens WHERE day = ?", (day,)).fetchone()["cnt"]
    waiting = db.execute("SELECT COUNT(*) as cnt FROM tokens WHERE day = ? AND served = 0", (day,)).fetchone()["cnt"]
    served = db.execute("SELECT COUNT(*) as cnt FROM tokens WHERE day = ? AND served = 1", (day,)).fetchone()["cnt"]
    return jsonify({"total": total, "waiting": waiting, "served": served})


@app.route("/api/serve_token", methods=["POST"])
def serve_token():
    if not session.get("admin_logged_in"):
        return jsonify({"success": False, "error": "Authentication required"}), 401
    data = request.get_json()
    db = get_db()
    token_id = data.get("id")  # ID (preferred) or token_number could be accepted
    counter = (data.get("counter") or "").strip()
    if token_id is None:
        return jsonify({"success": False, "error": "token id required"}), 400
    served_at = datetime.now().isoformat()
    db.execute(
        "UPDATE tokens SET served = 1, served_at = ?, counter = ? WHERE id = ?",
        (served_at, counter, token_id),
    )
    db.commit()
    return jsonify({"success": True})


@app.route("/api/serve_next", methods=["POST"])
def serve_next():
    if not session.get("admin_logged_in"):
        return jsonify({"success": False, "error": "Authentication required"}), 401
    data = request.get_json()
    counter = (data.get("counter") or "").strip()
    db = get_db()
    day = today_str()
    # Priority: emergency -> lab -> general, then oldest
    row = db.execute(
        """
        SELECT * FROM tokens
        WHERE day = ? AND served = 0
        ORDER BY
          CASE WHEN category = 'emergency' THEN 0
               WHEN category = 'lab' THEN 1
               ELSE 2 END,
          issued_at ASC
        LIMIT 1
        """,
        (day,),
    ).fetchone()
    if not row:
        return jsonify({"success": False, "error": "No waiting tokens"})
    token_id = row["id"]
    served_at = datetime.now().isoformat()
    db.execute(
        "UPDATE tokens SET served = 1, served_at = ?, counter = ? WHERE id = ?",
        (served_at, counter, token_id),
    )
    db.commit()
    return jsonify({"success": True, "token": dict(row)})


# Init
if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=False)
