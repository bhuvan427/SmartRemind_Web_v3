import os
from contextlib import contextmanager
from pathlib import Path

_pool = None
_db_type = None  # 'mysql' or 'sqlite'


def init_db():
    """Initialize the database. Try MySQL first, fall back to SQLite for local testing."""
    global _pool, _db_type
    config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "smartremind"),
        "pool_name": "smartremind_pool",
        "pool_size": 5,
    }
    # Try MySQL
    try:
        import mysql.connector
        from mysql.connector import pooling as mysql_pooling
        base = {k: config[k] for k in ("host", "port", "user", "password")}
        conn = mysql.connector.connect(**base)
        cur = conn.cursor()
        db = config["database"].replace("`", "")
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.close(); conn.close()
        _pool = mysql_pooling.MySQLConnectionPool(**config)
        _db_type = "mysql"
    except Exception:
        # Fall back to sqlite
        import sqlite3
        db_path = Path(__file__).resolve().parent / "smartremind.sqlite3"
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _pool = conn
        _db_type = "sqlite"

    # Create tables for whichever DB is active
    with get_conn() as conn:
        cur = conn.cursor()
        if _db_type == "mysql":
            cur.execute("""CREATE TABLE IF NOT EXISTS saved_places (
                id INT AUTO_INCREMENT PRIMARY KEY,
                place_name VARCHAR(255) NOT NULL,
                place_type VARCHAR(100) NULL,
                village VARCHAR(255) NULL,
                city VARCHAR(255) NULL,
                district VARCHAR(255) NULL,
                state VARCHAR(255) NULL,
                country VARCHAR(255) NULL,
                latitude DOUBLE NOT NULL,
                longitude DOUBLE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_saved_place (place_name, latitude, longitude)
            ) ENGINE=InnoDB""")
            cur.execute("""CREATE TABLE IF NOT EXISTS reminders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_name VARCHAR(200) NOT NULL,
                place_name VARCHAR(255) NOT NULL,
                latitude DOUBLE NOT NULL,
                longitude DOUBLE NOT NULL,
                radius_m DOUBLE NOT NULL DEFAULT 500,
                weather_condition VARCHAR(50) NULL,
                battery_threshold TINYINT NULL,
                time_start VARCHAR(5) NULL,
                time_end VARCHAR(5) NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                last_triggered_at DATETIME NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB""")
            cur.execute("""CREATE TABLE IF NOT EXISTS trigger_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                reminder_id INT NULL,
                task_name VARCHAR(200) NOT NULL,
                message VARCHAR(500) NOT NULL,
                distance_m DOUBLE NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX(reminder_id),
                FOREIGN KEY(reminder_id) REFERENCES reminders(id) ON DELETE SET NULL
            ) ENGINE=InnoDB""")
            conn.commit()
        else:
            # SQLite-compatible table definitions
            cur.execute("""CREATE TABLE IF NOT EXISTS saved_places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                place_name TEXT NOT NULL,
                place_type TEXT NULL,
                village TEXT NULL,
                city TEXT NULL,
                district TEXT NULL,
                state TEXT NULL,
                country TEXT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(place_name, latitude, longitude)
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                place_name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                radius_m REAL NOT NULL DEFAULT 500,
                weather_condition TEXT NULL,
                battery_threshold INTEGER NULL,
                time_start TEXT NULL,
                time_end TEXT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                last_triggered_at DATETIME NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS trigger_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id INTEGER NULL,
                task_name TEXT NOT NULL,
                message TEXT NOT NULL,
                distance_m REAL NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            conn.commit()
        cur.close()


@contextmanager
def get_conn():
    if _pool is None:
        init_db()
    if _db_type == "mysql":
        conn = _pool.get_connection()
        try:
            yield conn
        finally:
            conn.close()
    else:
        # sqlite: _pool is a Connection
        yield _pool


def _rows(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _run(sql, params=None, fetch=False, commit=False, dict_cursor=False):
    params = params or ()
    if _db_type == "sqlite":
        sql = sql.replace("%s", "?")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        if commit:
            conn.commit()
        if fetch:
            rows = cur.fetchall()
            if dict_cursor and _db_type == "mysql":
                return rows
            if _db_type == "sqlite":
                # sqlite Row -> dict
                return [dict(row) for row in rows]
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in rows]
        lastrowid = getattr(cur, "lastrowid", None) or getattr(cur, "lastrowid", None)
        cur.close()
        return lastrowid


def list_reminders(active_only=False):
    sql = "SELECT * FROM reminders" + (" WHERE active=TRUE" if active_only else "") + " ORDER BY created_at DESC"
    return _run(sql, fetch=True, dict_cursor=True)


def create_reminder(data):
    sql = """INSERT INTO reminders(task_name,place_name,latitude,longitude,radius_m,weather_condition,battery_threshold,time_start,time_end)
                      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    rid = _run(sql, params=(data["task_name"], data["place_name"], data["latitude"], data["longitude"], data["radius_m"],
                             data.get("weather_condition"), data.get("battery_threshold"), data.get("time_start"), data.get("time_end")), commit=True)
    return next(r for r in list_reminders() if r["id"] == rid)


def delete_reminder(reminder_id):
    sql = "DELETE FROM reminders WHERE id=%s"
    _run(sql, params=(reminder_id,), commit=True)
    # best-effort: return True
    return True


def add_log(reminder_id, task_name, message, distance_m):
    sql = "INSERT INTO trigger_logs(reminder_id,task_name,message,distance_m) VALUES(%s,%s,%s,%s)"
    _run(sql, params=(reminder_id, task_name, message, distance_m), commit=True)


def mark_triggered(reminder_id):
    if _db_type == "sqlite":
        sql = "UPDATE reminders SET last_triggered_at=CURRENT_TIMESTAMP WHERE id=%s"
        _run(sql, params=(reminder_id,), commit=True)
    else:
        sql = "UPDATE reminders SET last_triggered_at=NOW() WHERE id=%s"
        _run(sql, params=(reminder_id,), commit=True)


def list_logs(limit=50):
    sql = "SELECT * FROM trigger_logs ORDER BY created_at DESC LIMIT %s"
    return _run(sql, params=(limit,), fetch=True, dict_cursor=True)


def list_places():
    sql = "SELECT * FROM saved_places ORDER BY created_at DESC"
    return _run(sql, fetch=True, dict_cursor=True)


def save_place(data):
    # SQLite does not support ON DUPLICATE KEY; emulate with INSERT OR IGNORE then UPDATE
    if _db_type == "sqlite":
        sql = "INSERT OR IGNORE INTO saved_places(place_name,place_type,village,city,district,state,country,latitude,longitude) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        _run(sql, params=(data["place_name"], data.get("place_type"), data.get("village"), data.get("city"), data.get("district"), data.get("state"), data.get("country"), data["latitude"], data["longitude"]), commit=True)
        # update fields
        sql = "UPDATE saved_places SET place_type=%s, village=%s, city=%s, district=%s, state=%s, country=%s WHERE place_name=%s AND latitude=%s AND longitude=%s"
        _run(sql, params=(data.get("place_type"), data.get("village"), data.get("city"), data.get("district"), data.get("state"), data.get("country"), data["place_name"], data["latitude"], data["longitude"]), commit=True)
        # fetch id
        rows = _run("SELECT id FROM saved_places WHERE place_name=%s AND latitude=%s AND longitude=%s", params=(data["place_name"], data["latitude"], data["longitude"]), fetch=True)
        place_id = rows[0]["id"]
    else:
        sql = """INSERT INTO saved_places(place_name,place_type,village,city,district,state,country,latitude,longitude)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON DUPLICATE KEY UPDATE place_type=VALUES(place_type), village=VALUES(village), city=VALUES(city), district=VALUES(district), state=VALUES(state), country=VALUES(country)"""
        place_id = _run(sql, params=(data["place_name"], data.get("place_type"), data.get("village"), data.get("city"), data.get("district"), data.get("state"), data.get("country"), data["latitude"], data["longitude"]), commit=True)
    return next(p for p in list_places() if p["id"] == place_id)


def delete_place(place_id):
    sql = "DELETE FROM saved_places WHERE id=%s"
    _run(sql, params=(place_id,), commit=True)
    return True
