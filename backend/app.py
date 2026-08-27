import os
import sys

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from functools import wraps

import pymysql
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from dashboard_api import dashboard_api
from attendance_api import attendance_api
from management_api import management_api
from werkzeug.security import check_password_hash

load_dotenv(".env")

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)

app.register_blueprint(management_api)

app.secret_key = os.getenv("SECRET_KEY", "attendx-dev-secret-change-me")

app.register_blueprint(dashboard_api)
app.register_blueprint(attendance_api)


def get_db():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "attendance_app"),
        password=os.getenv("DB_PASSWORD", "AttendX_DB_2006!"),
        database=os.getenv("DB_NAME", "student_attendance"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({
                "success": False,
                "error": "Authentication required"
            }), 401
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({
                    "success": False,
                    "error": "Authentication required"
                }), 401

            if session.get("role") not in roles:
                return jsonify({
                    "success": False,
                    "error": "Access denied"
                }), 403

            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.route("/")
def home():
    return render_template("index.html")


@app.get("/health")
def health():
    try:
        connection = get_db()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        connection.close()

        return jsonify({
            "status": "healthy",
            "application": "Student Attendance Management System",
            "server": "home-server",
            "database": "healthy"
        })

    except Exception as e:
        return jsonify({
            "status": "degraded",
            "application": "Student Attendance Management System",
            "server": "home-server",
            "database": "unavailable",
            "error": str(e)
        }), 503


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not username or not password:
        return jsonify({
            "success": False,
            "error": "Username and password are required"
        }), 400

    connection = None

    try:
        connection = get_db()

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, password_hash, role,
                       full_name, email, is_active
                FROM users
                WHERE username = %s
                LIMIT 1
            """, (username,))

            user = cursor.fetchone()

        if not user or not user["is_active"]:
            return jsonify({
                "success": False,
                "error": "Invalid username or password"
            }), 401

        if not check_password_hash(user["password_hash"], password):
            return jsonify({
                "success": False,
                "error": "Invalid username or password"
            }), 401

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]

        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"],
                "email": user["email"]
            }
        })

    except Exception as e:
        print("Login database error:", e)
        return jsonify({
            "success": False,
            "error": "Authentication service unavailable"
        }), 500

    finally:
        if connection:
            connection.close()


@app.get("/api/auth/me")
@login_required
def current_user():
    return jsonify({
        "success": True,
        "user": {
            "id": session["user_id"],
            "username": session["username"],
            "full_name": session["full_name"],
            "role": session["role"]
        }
    })


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({
        "success": True,
        "message": "Logged out successfully"
    })


@app.get("/api/admin")
@role_required("ADMIN")
def admin_portal():
    return jsonify({
        "success": True,
        "portal": "admin",
        "message": "Administrator portal access granted"
    })


@app.get("/api/faculty")
@role_required("FACULTY")
def faculty_portal():
    return jsonify({
        "success": True,
        "portal": "faculty",
        "message": "Faculty portal access granted"
    })


@app.get("/api/student")
@role_required("STUDENT")
def student_portal():
    return jsonify({
        "success": True,
        "portal": "student",
        "message": "Student portal access granted"
    })


@app.get("/api/hod")
@role_required("HOD")
def hod_portal():
    return jsonify({
        "success": True,
        "portal": "hod",
        "message": "HOD portal access granted"
    })


@app.get("/api/dashboard/stats")
@login_required
def dashboard_stats():
    connection = None

    try:
        connection = get_db()

        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM students")
            students = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM faculty")
            faculty = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM subjects")
            subjects = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM classes")
            classes = cursor.fetchone()["total"]

            cursor.execute("""
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(status = 'PRESENT'), 0) AS present,
                    COALESCE(SUM(status = 'ABSENT'), 0) AS absent
                FROM attendance
            """)
            attendance = cursor.fetchone()

            total = attendance["total"] or 0
            present = attendance["present"] or 0
            absent = attendance["absent"] or 0

            percentage = round((present / total) * 100, 1) if total else 0

        return jsonify({
            "success": True,
            "students": students,
            "faculty": faculty,
            "subjects": subjects,
            "classes": classes,
            "attendance": {
                "total": total,
                "present": present,
                "absent": absent,
                "percentage": percentage
            }
        })

    except Exception as e:
        print("Dashboard stats error:", e)
        return jsonify({
            "success": False,
            "error": "Dashboard data unavailable"
        }), 500

    finally:
        if connection:
            connection.close()


@app.get("/api/dashboard/logs")
@login_required
def dashboard_logs():
    connection = None

    try:
        connection = get_db()

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    al.id,
                    al.action,
                    al.old_status,
                    al.new_status,
                    al.ip_address,
                    al.created_at,
                    u.username,
                    u.full_name
                FROM attendance_logs al
                LEFT JOIN users u ON u.id = al.user_id
                ORDER BY al.created_at DESC
                LIMIT 12
            """)

            logs = cursor.fetchall()

        for log in logs:
            if log.get("created_at"):
                log["created_at"] = log["created_at"].isoformat()

        return jsonify({
            "success": True,
            "logs": logs
        })

    except Exception as e:
        print("Dashboard logs error:", e)
        return jsonify({
            "success": False,
            "error": "Activity logs unavailable"
        }), 500

    finally:
        if connection:
            connection.close()


@app.get("/api/dashboard/system")
def dashboard_system():
    database = "ONLINE"

    try:
        connection = get_db()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        connection.close()
    except Exception:
        database = "OFFLINE"

    return jsonify({
        "success": True,
        "server": "home-server",
        "database": database,
        "api": "ONLINE",
        "frontend": "ONLINE"
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
